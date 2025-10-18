"""Terminal display for tone detection status.

This module provides a real-time terminal interface showing connection status,
audio playback state, and detection metrics in an easy-to-read format.

Display Components:
1. Connection Status: Shows each statue's link state with visual indicators
2. Audio Status: Displays playback progress and active channel count
3. Detection Matrix: 2D grid showing signal levels between all statue pairs

The detection matrix uses visual encoding to quickly identify connections:
- "---": Self-detection (diagonal)
- Numeric values: Signal strength (0.000-1.000)
- Color/box indicators could be added for different signal strengths

Terminal Control:
- Uses ANSI escape sequences for cursor control
- Updates in-place without flickering
- Hides cursor during operation for clean display
- Handles graceful shutdown with cursor restoration

Example Display:
    === Missing Link Tone Detection ===

    CONNECTION STATUS:
    eros     [ON]  ━━━━━━━━━━━━  Linked to: elektra
    elektra  [ON]  ━━━━━━━━━━━━  Linked to: eros
    sophia   [OFF] ────────────  Not linked

    TONE DETECTION MATRIX:
    DETECTOR    │   EROS    ELEKTRA  SOPHIA
    ────────────┼─────────────────────────────
    EROS        │    ---     0.152    0.001
    ELEKTRA     │   0.148     ---     0.000
    SOPHIA      │   0.000    0.001     ---
"""

import json
import select
import sys
import termios
import threading
import time
import tty
from typing import TYPE_CHECKING, Any, Optional

import ultraimport as ui

Statue = ui.ultraimport("__dir__/../audio/devices.py", "Statue")
TONE_FREQUENCIES = ui.ultraimport("__dir__/config.py", "TONE_FREQUENCIES")

try:
    from audio.devices import dynConfig
except ImportError:
    # dynConfig not available - use default threshold for MQTT mode
    dynConfig = {"touch_threshold": 0.1}

if TYPE_CHECKING:
    from .link_state import LinkStateTracker


class StatusDisplay:
    """Terminal-based status display for tone detection.

    This class manages a real-time terminal display that shows:
    - Individual statue connection states
    - Audio playback status and channel activity
    - Full detection matrix with signal levels

    The display updates every 100ms and uses terminal control sequences
    to update in-place without scrolling. The detection matrix provides
    a comprehensive view of all statue-to-statue signal levels.

    Attributes:
        link_tracker (LinkStateTracker): Provides connection state info
        devices (list): Device configurations for all statues
        detection_metrics (dict): 2D dictionary of signal levels
        running (bool): Controls the display update loop
    """

    def __init__(self, link_tracker: 'LinkStateTracker', devices: list[dict[str, Any]], freq_controller=None, mqtt_mode: bool = False, log_file: Optional[str] = None, replay_file: Optional[str] = None) -> None:
        """Initialize the status display.

        Args:
            link_tracker (LinkStateTracker): Connection state tracker
            devices (list): List of device configurations with statue info
            freq_controller (FrequencyController, optional): Frequency controller for interactive mode
            mqtt_mode (bool): If True, use MQTT-optimized display instead of detection matrix
            log_file (str, optional): Path to JSONL file for logging snapshots
            replay_file (str, optional): Path to JSONL file for replay mode
        """
        self.link_tracker = link_tracker
        self.devices = devices
        self.freq_controller = freq_controller
        self.mqtt_mode = mqtt_mode
        self.running = True
        # 2D metrics: {detector_statue: {target_statue: {'level': float, 'snr': float}}}
        self.detection_metrics = {}
        # Track last update timestamp per detector
        self.last_update: dict[Statue, float] = {}
        # Track threshold per statue (from MQTT config messages)
        self.thresholds: dict[Statue, float] = {}
        # Track climax state (for MQTT mode)
        self.climax_state: str = "inactive"
        self.climax_connected_pairs: list = []
        self.climax_missing_pairs: list = []
        self.lock = threading.Lock()
        self.first_draw = True

        # Logging support
        self.log_file = log_file
        self.log_handle = None
        if self.log_file:
            self.log_handle = open(self.log_file, 'a')

        # Replay support
        self.replay_mode = replay_file is not None
        self.replay_data: list[dict] = []
        self.replay_index: int = 0
        if replay_file:
            self.load_replay_data(replay_file)
            # Start at first snapshot
            if self.replay_data:
                self.restore_snapshot(self.replay_data[0])

        # Initialize 2D metrics for all statue pairs
        for detector_device in devices:
            detector = detector_device['statue']
            self.detection_metrics[detector] = {}
            self.last_update[detector] = 0.0
            for target_device in devices:
                target = target_device['statue']
                if detector != target:  # Can't detect self
                    self.detection_metrics[detector][target] = {
                        'level': 0.0,
                        'snr': 0.0,
                        'freq': TONE_FREQUENCIES.get(target, 0)
                    }

    def update_metrics(self, detector: Statue, target: Statue, level: float, snr: Optional[float] = None) -> None:
        """Update detection metrics for a detector-target pair.

        Called by detection threads to update the signal level between
        a specific pair of statues. Thread-safe via internal locking.

        Args:
            detector (Statue): The detecting statue
            target (Statue): The target statue being detected
            level (float): Signal level (0.0-1.0)
            snr (float, optional): Signal-to-noise ratio in dB
        """
        with self.lock:
            if detector in self.detection_metrics and target in self.detection_metrics[detector]:
                metrics = self.detection_metrics[detector][target]
                metrics['level'] = level
                if snr is not None:
                    metrics['snr'] = snr

    def update_detector_timestamp(self, detector: Statue) -> None:
        """Update the last update timestamp for a detector.

        Called when receiving MQTT messages to track when each detector
        last reported its state.

        Args:
            detector (Statue): The detector statue that sent an update
        """
        with self.lock:
            self.last_update[detector] = time.time()

    def update_threshold(self, statue: Statue, threshold: float) -> None:
        """Update the detection threshold for a statue.

        Called when receiving MQTT config messages with threshold values.

        Args:
            statue (Statue): The statue whose threshold is being updated
            threshold (float): The detection threshold value
        """
        with self.lock:
            self.thresholds[statue] = threshold

    def update_climax_state(self, state: str, connected_pairs: list, missing_pairs: list) -> None:
        """Update the climax state.

        Called when receiving MQTT climax messages.

        Args:
            state (str): Climax state ("active" or "inactive")
            connected_pairs (list): List of connected neighbor pairs [[statue1, statue2], ...]
            missing_pairs (list): List of missing neighbor pairs needed for climax
        """
        with self.lock:
            self.climax_state = state
            self.climax_connected_pairs = connected_pairs
            self.climax_missing_pairs = missing_pairs

    def capture_snapshot(self) -> dict:
        """Capture current state as a serializable snapshot.

        Returns:
            dict: Complete state snapshot with timestamp
        """
        with self.lock:
            # Convert detection_metrics to serializable format
            metrics_serializable = {}
            for detector, targets in self.detection_metrics.items():
                metrics_serializable[detector.value] = {}
                for target, metrics in targets.items():
                    metrics_serializable[detector.value][target.value] = metrics.copy()

            # Convert links to serializable format
            links_serializable = {}
            for statue, linked_set in self.link_tracker.links.items():
                links_serializable[statue.value] = [s.value for s in linked_set]

            # Convert has_links to serializable format
            has_links_serializable = {statue.value: has_link for statue, has_link in self.link_tracker.has_links.items()}

            # Convert last_update to serializable format
            last_update_serializable = {statue.value: timestamp for statue, timestamp in self.last_update.items()}

            # Convert thresholds to serializable format
            thresholds_serializable = {statue.value: threshold for statue, threshold in self.thresholds.items()}

            snapshot = {
                'timestamp': time.time(),
                'detection_metrics': metrics_serializable,
                'links': links_serializable,
                'has_links': has_links_serializable,
                'last_update': last_update_serializable,
                'thresholds': thresholds_serializable,
                'climax_state': self.climax_state,
                'climax_connected_pairs': self.climax_connected_pairs,
                'climax_missing_pairs': self.climax_missing_pairs,
            }
            return snapshot

    def log_snapshot(self) -> None:
        """Log current state snapshot to JSONL file."""
        if not self.log_handle:
            return
        snapshot = self.capture_snapshot()
        self.log_handle.write(json.dumps(snapshot) + '\n')
        self.log_handle.flush()

    def restore_snapshot(self, snapshot: dict) -> None:
        """Restore state from a snapshot.

        Args:
            snapshot (dict): Snapshot to restore from
        """
        with self.lock:
            # Restore detection_metrics
            self.detection_metrics = {}
            for detector_str, targets in snapshot.get('detection_metrics', {}).items():
                detector = Statue(detector_str)
                self.detection_metrics[detector] = {}
                for target_str, metrics in targets.items():
                    target = Statue(target_str)
                    self.detection_metrics[detector][target] = metrics.copy()

            # Restore links
            links_dict = {}
            for statue_str, linked_list in snapshot.get('links', {}).items():
                statue = Statue(statue_str)
                links_dict[statue] = set(Statue(s) for s in linked_list)
            self.link_tracker.links = links_dict

            # Restore has_links
            has_links_dict = {}
            for statue_str, has_link in snapshot.get('has_links', {}).items():
                statue = Statue(statue_str)
                has_links_dict[statue] = has_link
            self.link_tracker.has_links = has_links_dict

            # Restore last_update
            self.last_update = {}
            for statue_str, timestamp in snapshot.get('last_update', {}).items():
                statue = Statue(statue_str)
                self.last_update[statue] = timestamp

            # Restore thresholds
            self.thresholds = {}
            for statue_str, threshold in snapshot.get('thresholds', {}).items():
                statue = Statue(statue_str)
                self.thresholds[statue] = threshold

            # Restore climax state
            self.climax_state = snapshot.get('climax_state', 'inactive')
            self.climax_connected_pairs = snapshot.get('climax_connected_pairs', [])
            self.climax_missing_pairs = snapshot.get('climax_missing_pairs', [])

    def load_replay_data(self, file_path: str) -> None:
        """Load replay data from JSONL file.

        Args:
            file_path (str): Path to JSONL file
        """
        self.replay_data = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        snapshot = json.loads(line)
                        self.replay_data.append(snapshot)
            print(f"Loaded {len(self.replay_data)} snapshots from {file_path}")
        except Exception as e:
            print(f"Error loading replay data: {e}")
            self.replay_data = []

    def get_keyboard_input(self) -> Optional[str]:
        """Non-blocking keyboard input reader.

        Returns:
            str or None: Key pressed, or None if no input
        """
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def handle_replay_navigation(self) -> None:
        """Handle keyboard navigation in replay mode."""
        key = self.get_keyboard_input()
        if not key:
            return

        max_index = len(self.replay_data) - 1
        if max_index < 0:
            return

        changed = False

        if key == 'j' or key == '\x1b[D':  # j or left arrow
            # Step backward
            if self.replay_index > 0:
                self.replay_index -= 1
                changed = True
        elif key == 'l' or key == '\x1b[C':  # l or right arrow
            # Step forward
            if self.replay_index < max_index:
                self.replay_index += 1
                changed = True
        elif key == 'h' or key == '\x1b[H':  # h or Home
            # Jump to start
            self.replay_index = 0
            changed = True
        elif key == ';' or key == '\x1b[F':  # ; or End
            # Jump to end
            self.replay_index = max_index
            changed = True
        elif key in '0123456789':
            # Jump to percentage
            percent = int(key) * 10
            if percent == 0:
                self.replay_index = 0
            else:
                self.replay_index = int(max_index * percent / 100)
            changed = True
        elif key == 'q':
            # Quit
            self.running = False

        if changed:
            self.restore_snapshot(self.replay_data[self.replay_index])
            self.first_draw = True  # Force redraw

    def format_cell(self, level: float, is_self: bool = False, threshold: Optional[float] = None) -> str:
        """Format a single cell with level and box indicators.

        Args:
            level: Signal level (0.0-1.0)
            is_self: If True, format as self-detection marker
            threshold: Detection threshold to use for box indicators. If None, uses dynConfig["touch_threshold"]

        Returns:
            7-character string with visual indicators
        """
        if is_self:
            return "  ---  "

        # Use provided threshold or fall back to global default
        if threshold is None:
            threshold = dynConfig["touch_threshold"]

        level_str = f"{level:.3f}"

        if level > threshold:
            # LINKED - double box around value
            return f"╔{level_str:^5}╗"
        elif level > threshold * 0.5:
            # WEAK - single box around value
            return f"┌{level_str:^5}┐"
        else:
            # NO SIGNAL - just value
            return f" {level_str:^5} "

    def clear_screen(self) -> None:
        """Clear terminal screen."""
        print("\033[2J\033[H", end='', flush=True)

    def hide_cursor(self):
        """Hide terminal cursor."""
        print("\033[?25l", end='', flush=True)

    def show_cursor(self):
        """Show terminal cursor."""
        print("\033[?25h", end='', flush=True)

    def enter_alt_screen(self):
        """Enter alternate screen buffer."""
        print("\033[?1049h", end='', flush=True)

    def exit_alt_screen(self):
        """Exit alternate screen buffer."""
        print("\033[?1049l", end='', flush=True)

    def move_cursor_home(self):
        """Move cursor to home position without clearing."""
        print("\033[H", end='', flush=True)

    def draw_interface(self) -> None:
        """Draw the status interface."""
        if self.first_draw:
            self.clear_screen()
            self.first_draw = False
        else:
            self.move_cursor_home()

        # Header
        print("=== Missing Link Tone Detection ===\r\n\r", flush=True)

        # Connection Status
        print("CONNECTION STATUS:\r", flush=True)
        for device in self.devices:
            statue = device['statue']
            is_linked = self.link_tracker.has_links[statue]
            status = "ON " if is_linked else "OFF"
            bar = "█" * 12 if is_linked else "─" * 12

            # Get linked statues
            linked_to = []
            if is_linked:
                linked_to = [s.value for s in self.link_tracker.links[statue]]
            linked_str = " ↔ " + ", ".join(linked_to) if linked_to else " Not linked"

            # Pad the line to ensure we overwrite any previous content
            line = f"{statue.value:8s} [{status}] {bar} {linked_str}"
            print(f"{line:<80}\r", flush=True)  # Pad to 80 chars

        # Audio Status
        print("\r\nAUDIO STATUS:\r", flush=True)
        if self.link_tracker.playback:
            progress = self.link_tracker.playback.get_progress()
            active = self.link_tracker.playback.active_count
            total = len(self.devices)
            playing = "Playing" if self.link_tracker.playback.is_playing else "Stopped"
            print(f"Playback: {playing} ({progress}%)  |  Active channels: {active}/{total}\r", flush=True)
        else:
            print("Playback: No audio loaded\r", flush=True)

        # Tone Detection Matrix
        print("\r\nTONE DETECTION MATRIX:\r", flush=True)
        print("                    TRANSMITTER (Playing Tone)\r", flush=True)

        # Header row with statue names and frequencies
        # Row label format is: "  {detector.value.upper():11s} │" = 16 chars total
        header_line1 = "  DETECTOR    │"  # Match the row label format
        header_line2 = "  (Listening) │"  # Match the row label format

        for d in self.devices:
            statue = d['statue']
            name = statue.value.upper()

            # Use dynamic frequency if frequency controller is available
            if self.freq_controller:
                freq = self.freq_controller.get_current_frequency(statue)
                # Mark selected statue with arrow
                if statue == self.freq_controller.get_selected_statue():
                    name = f"→{name}←"
                # Show muted status
                if self.freq_controller.is_muted(statue):
                    freq_str = "MUTED"
                else:
                    freq_str = f"{freq:.0f}"
            else:
                freq = TONE_FREQUENCIES.get(statue, 0)
                freq_str = f"{freq:.0f}"

            # Each cell is centered in 9 chars
            header_line1 += f"  {name:^7}  "
            header_line2 += f"  {freq_str:^7}  "

        print(header_line1 + "\r", flush=True)
        print(header_line2 + "Hz\r", flush=True)
        print("  ───────────────" + "─" * (len(self.devices) * 11) + "\r", flush=True)

        with self.lock:
            # For each detector (row)
            for detector_device in self.devices:
                detector = detector_device['statue']

                # Row label - ensure consistent spacing
                row_label = f"  {detector.value.upper():11s} │"
                row_line = row_label

                # For each target/transmitter (column)
                for target_device in self.devices:
                    target = target_device['statue']

                    if detector == target:
                        # Self-detection
                        cell = self.format_cell(0, is_self=True)
                    else:
                        # Get detection level
                        level = 0.0
                        if detector in self.detection_metrics and target in self.detection_metrics[detector]:
                            level = self.detection_metrics[detector][target]['level']
                        cell = self.format_cell(level)

                    # Add cell to row with spacing
                    row_line += f"  {cell}  "

                # Print the row with padding to ensure clean overwrites
                print(f"{row_line:<100}\r", flush=True)

        # Legend
        threshold = dynConfig["touch_threshold"]
        print(f"\r\nLegend: ╔═╗ LINKED (>{threshold:.2f})  "
              f"┌─┐ WEAK (>{threshold*0.5:.2f})  "
              f"Plain text: NO SIGNAL (<{threshold*0.5:.2f})\r", flush=True)

        if self.freq_controller:
            print("\r\nInteractive Controls: A/D=Navigate statues | W/S=Adjust frequency (±500Hz) | Space=Mute/Unmute | Q=Quit\r", flush=True)
        else:
            print("\r\nPress Ctrl+C to stop\r", flush=True)
        # Add some blank lines to ensure we overwrite any previous content
        print("\r\n" * 3, end='', flush=True)

    def draw_mqtt_interface(self) -> None:
        """Draw the MQTT-optimized status interface.

        Shows detector → emitters in a simple table format with timestamps
        and placeholders for future level/SNR data.
        """
        # Always clear screen to prevent smearing
        self.clear_screen()

        # Header
        if self.replay_mode:
            print("=== Missing Link MQTT Status Monitor - REPLAY MODE ===\n", end='', flush=True)
            # Show replay position and timestamp
            if self.replay_data:
                current_snapshot = self.replay_data[self.replay_index]
                timestamp = current_snapshot.get('timestamp', 0)
                import datetime
                dt = datetime.datetime.fromtimestamp(timestamp)
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"Frame {self.replay_index + 1}/{len(self.replay_data)} - {timestamp_str}\n", end='', flush=True)
                print("Controls: j/← Prev | l/→ Next | h/Home Start | ;/End End | 0-9 Jump % | q Quit\n", end='', flush=True)
        else:
            print("=== Missing Link MQTT Status Monitor ===\n", end='', flush=True)
        print("\n", end='', flush=True)  # Blank line

        # Climax status section
        with self.lock:
            climax_indicator = "●" if self.climax_state == "active" else "○"
            climax_label = "CLIMAX"

            if self.climax_state == "active":
                # Show active climax
                print(f"{climax_indicator} {climax_label}: ACTIVE\n", end='', flush=True)
            else:
                # Show inactive climax with missing pairs
                if self.climax_missing_pairs:
                    missing_str = ", ".join([f"{p[0]}↔{p[1]}" for p in self.climax_missing_pairs])
                    print(f"{climax_indicator} {climax_label}: INACTIVE - Missing: {missing_str}\n", end='', flush=True)
                else:
                    print(f"{climax_indicator} {climax_label}: INACTIVE\n", end='', flush=True)

        print("\n", end='', flush=True)  # Blank line after climax status

        # Get current detector→emitters mapping from link tracker
        detector_emitters = self.link_tracker.get_detector_emitters()

        # Build table header with column for each statue
        header = f"{'DETECTOR':<10} {'EMITTERS':<20} {'UPDATE':<10}"
        for device in self.devices:
            statue = device['statue']
            header += f" {statue.value.upper():<7}"
        header += f" {'THRESHOLD':<9}"
        print(header + "\n", end='', flush=True)
        print("─" * len(header) + "\n", end='', flush=True)

        current_time = time.time()
        with self.lock:
            # Display each detector's state
            for device in self.devices:
                detector = device['statue']
                emitters = detector_emitters.get(detector, [])

                # Format emitters list
                if emitters:
                    emitters_str = ",".join([e.value for e in emitters])
                else:
                    emitters_str = "(none)"

                # Status indicator based on has_links (includes both outgoing and incoming)
                status_indicator = "●" if self.link_tracker.has_links[detector] else "○"

                # Format last update time (shortened)
                last_update_time = self.last_update.get(detector, 0.0)
                if last_update_time == 0.0:
                    update_str = "Never"
                else:
                    elapsed = current_time - last_update_time
                    if elapsed < 60:
                        update_str = f"{elapsed:.1f}s"
                    elif elapsed < 3600:
                        update_str = f"{elapsed/60:.1f}m"
                    else:
                        update_str = f"{elapsed/3600:.1f}h"

                # Build row starting with detector, emitters, update
                line = f"{status_indicator} {detector.value:<8} {emitters_str:<20} {update_str:<10}"

                # Add level column for each emitter statue
                for emitter_device in self.devices:
                    emitter = emitter_device['statue']

                    if detector == emitter:
                        # Can't detect self
                        cell = self.format_cell(0.0, is_self=True)
                    else:
                        # Get level from detection metrics
                        level = 0.0
                        if detector in self.detection_metrics and emitter in self.detection_metrics[detector]:
                            level = self.detection_metrics[detector][emitter]['level']

                        # Use detector-specific threshold if available
                        detector_threshold = self.thresholds.get(detector, None)
                        cell = self.format_cell(level, is_self=False, threshold=detector_threshold)

                    line += f" {cell}"

                # Add threshold column
                if detector in self.thresholds:
                    threshold_str = f"{self.thresholds[detector]:.3f}"
                else:
                    threshold_str = "[N/A]"
                line += f" {threshold_str:<9}"

                # Print row with padding
                print(f"{line:<120}\n", end='', flush=True)

        # Legend
        print("\n", end='', flush=True)  # Blank line
        print("Legend: ● = Linked  ○ = Unlinked  --- = Self-detection\n", end='', flush=True)
        print("        ╔═╗ LINKED (>threshold)  ┌─┐ WEAK (>threshold×0.5)  Plain: NO SIGNAL\n", end='', flush=True)
        print("Signal levels updated from missing_link/signals MQTT topic (published every 100ms)\n", end='', flush=True)
        print("Box indicators based on per-detector threshold values shown in THRESHOLD column\n", end='', flush=True)
        print("\n", end='', flush=True)  # Blank line
        print("Press Ctrl+C to stop\n", end='', flush=True)

    def run(self) -> None:
        """Run the display update loop."""
        self.enter_alt_screen()
        self.hide_cursor()

        # Set up raw terminal mode for replay keyboard input
        old_settings = None
        if self.replay_mode:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

        try:
            while self.running:
                try:
                    # Handle replay navigation
                    if self.replay_mode:
                        self.handle_replay_navigation()

                    # Draw interface
                    if self.mqtt_mode:
                        self.draw_mqtt_interface()
                    else:
                        self.draw_interface()

                    # Log snapshot if logging enabled
                    if self.log_handle and not self.replay_mode:
                        self.log_snapshot()

                    time.sleep(0.5)  # Update every 500ms (2Hz)
                except Exception:
                    # Don't crash the display thread
                    pass
        finally:
            # Restore terminal settings
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

            # Close log file
            if self.log_handle:
                self.log_handle.close()

            # Always clean up, even on exception
            self.show_cursor()
            self.exit_alt_screen()

    def stop(self) -> None:
        """Stop the display."""
        self.running = False
        time.sleep(0.2)  # Give display thread time to exit
        # Cleanup is now handled in run() finally block
