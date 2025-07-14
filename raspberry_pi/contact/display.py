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

import threading
import time
from typing import TYPE_CHECKING, Any, Optional

from audio.devices import Statue, dynConfig

from .config import TONE_FREQUENCIES

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

    def __init__(self, link_tracker: 'LinkStateTracker', devices: list[dict[str, Any]], freq_controller=None) -> None:
        """Initialize the status display.

        Args:
            link_tracker (LinkStateTracker): Connection state tracker
            devices (list): List of device configurations with statue info
            freq_controller (FrequencyController, optional): Frequency controller for interactive mode
        """
        self.link_tracker = link_tracker
        self.devices = devices
        self.freq_controller = freq_controller
        self.running = True
        # 2D metrics: {detector_statue: {target_statue: {'level': float, 'snr': float}}}
        self.detection_metrics = {}
        self.lock = threading.Lock()
        self.first_draw = True

        # Initialize 2D metrics for all statue pairs
        for detector_device in devices:
            detector = detector_device['statue']
            self.detection_metrics[detector] = {}
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

    def format_cell(self, level: float, is_self: bool = False) -> str:
        """Format a single cell with level and box indicators."""
        if is_self:
            return "  ---  "

        level_str = f"{level:.3f}"

        if level > dynConfig["touch_threshold"]:
            # LINKED - double box around value
            return f"╔{level_str:^5}╗"
        elif level > dynConfig["touch_threshold"] * 0.5:
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
            else:
                freq = TONE_FREQUENCIES.get(statue, 0)
            
            # Each cell is centered in 9 chars
            header_line1 += f"  {name:^7}  "
            header_line2 += f"  {freq:^7.0f}  "

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
            print("\r\nInteractive Controls: W/S=Navigate statues | A/D=Adjust frequency (±500Hz) | Q=Quit\r", flush=True)
        else:
            print("\r\nPress Ctrl+C to stop\r", flush=True)
        # Add some blank lines to ensure we overwrite any previous content
        print("\r\n" * 3, end='', flush=True)

    def run(self) -> None:
        """Run the display update loop."""
        self.hide_cursor()
        while self.running:
            try:
                self.draw_interface()
                time.sleep(0.25)  # Update every 250ms (4Hz)
            except Exception:
                # Don't crash the display thread
                pass

    def stop(self) -> None:
        """Stop the display."""
        self.running = False
        time.sleep(0.2)  # Give display thread time to exit
        self.show_cursor()
        self.clear_screen()
