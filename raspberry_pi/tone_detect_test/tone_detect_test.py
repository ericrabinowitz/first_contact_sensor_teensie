#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./tone_detect_test.py

import os
import threading
import time
import sys
import termios
import tty
import select
from datetime import datetime

# Add parent directory to path for imports
sys.path.append('../')

import fastgoertzel as G
import numpy as np
import sounddevice as sd
import soundfile as sf

# Import device configuration from audio module
from audio.devices import Statue, dynConfig, configure_devices
from audio.music import play_audio, ToggleableMultiChannelPlayback


# TODOs
# How to support multiple detection channels? goertzel is only efficient for a
# limited number of frequencies. The Pi is limited to 4 cores, 1 thread/core.

# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://docs.scipy.org/doc/scipy/reference/signal.html
# https://pypi.org/project/fastgoertzel/
# https://arlpy.readthedocs.io/en/latest/signal.html


AUDIO_JACK = "bcm2835 headphones"

# Frequencies optimized based on frequency sweep test results
# Selected for good detection and minimal cable attenuation
tones_hz = {
    Statue.EROS: 3000,      # 100% detection, 33.8dB SNR
    Statue.ELEKTRA: 4500,   # Avoiding problematic 5639Hz
    Statue.SOPHIA: 7500,    # Good mid-range frequency
    Statue.ULTIMO: 10000,   # High frequency but still reliable
    Statue.ARIEL: 15000,    # High frequency with good SNR
}
# tone_streams = {}  # No longer needed - tones handled through audio playback
audio_playback = None  # Global audio playback instance


class LinkStateTracker:
    """Tracks link states between statues and detects changes."""

    def __init__(self, playback=None, quiet=False):
        # Track which statues are linked to which
        self.links = {}  # {statue: set(linked_statues)}
        # Track link state for each statue (any links at all)
        self.has_links = {}  # {statue: bool}
        # Initialize all statues as unlinked
        for statue in Statue:
            self.links[statue] = set()
            self.has_links[statue] = False
        # Audio playback controller
        self.playback = playback
        # Map statue to channel index using enum order
        self.statue_to_channel = {statue: list(Statue).index(statue) for statue in Statue}
        # Quiet mode suppresses print statements
        self.quiet = quiet

    def _update_audio_channel(self, statue, is_linked):
        """Helper to update audio channel based on link state."""
        if self.playback and statue in self.statue_to_channel:
            channel = self.statue_to_channel[statue]
            if is_linked and not self.playback.channel_enabled[channel]:
                # Turn on channel
                self.playback.toggle_channel(channel)
                if not self.quiet:
                    print(f"  ♪ Audio channel {channel} ON for {statue.value}")
            elif not is_linked and self.playback.channel_enabled[channel]:
                # Turn off channel
                self.playback.toggle_channel(channel)
                if not self.quiet:
                    print(f"  ♪ Audio channel {channel} OFF for {statue.value}")

    def update_link(self, detector_statue, source_statue, is_linked):
        """
        Update link state and return True if state changed.
        Links are bidirectional.
        """
        changed = False

        if is_linked:
            # Add link if not already present
            if source_statue not in self.links[detector_statue]:
                self.links[detector_statue].add(source_statue)
                self.links[source_statue].add(detector_statue)
                changed = True
                if not self.quiet:
                    print(f"🔗 Link established: {detector_statue.value} ↔ {source_statue.value}")
        else:
            # Remove link if present
            if source_statue in self.links[detector_statue]:
                self.links[detector_statue].remove(source_statue)
                self.links[source_statue].remove(detector_statue)
                changed = True
                if not self.quiet:
                    print(f"🔌 Link broken: {detector_statue.value} ↔ {source_statue.value}")

        # Update has_links status
        old_has_links_detector = self.has_links[detector_statue]
        old_has_links_source = self.has_links[source_statue]

        self.has_links[detector_statue] = len(self.links[detector_statue]) > 0
        self.has_links[source_statue] = len(self.links[source_statue]) > 0

        # Check if overall link status changed
        if old_has_links_detector != self.has_links[detector_statue]:
            status = "linked" if self.has_links[detector_statue] else "unlinked"
            if not self.quiet:
                print(f"  → {detector_statue.value} is now {status}")
            changed = True
            # Update audio channel
            self._update_audio_channel(detector_statue, self.has_links[detector_statue])

        if old_has_links_source != self.has_links[source_statue]:
            status = "linked" if self.has_links[source_statue] else "unlinked"
            if not self.quiet:
                print(f"  → {source_statue.value} is now {status}")
            changed = True
            # Update audio channel
            self._update_audio_channel(source_statue, self.has_links[source_statue])

        return changed

    def get_link_summary(self):
        """Return human-readable link summary."""
        summary = []
        summary.append("=== Current Link Status ===")

        # Show linked statues
        linked = [s for s in Statue if self.has_links[s]]
        unlinked = [s for s in Statue if not self.has_links[s]]

        if linked:
            summary.append("Linked statues:")
            for statue in linked:
                linked_to = ", ".join([s.value for s in self.links[statue]])
                summary.append(f"  {statue.value} ↔ {linked_to}")

        if unlinked:
            summary.append("Unlinked statues:")
            summary.append("  " + ", ".join([s.value for s in unlinked]))

        return "\n".join(summary)


class StatusDisplay:
    """Terminal-based status display for tone detection."""
    
    def __init__(self, link_tracker, devices):
        self.link_tracker = link_tracker
        self.devices = devices
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
                        'freq': tones_hz.get(target, 0)
                    }
    
    def update_metrics(self, detector, target, level, snr=None):
        """Update detection metrics for a detector-target pair."""
        with self.lock:
            if detector in self.detection_metrics and target in self.detection_metrics[detector]:
                metrics = self.detection_metrics[detector][target]
                metrics['level'] = level
                if snr is not None:
                    metrics['snr'] = snr
    
    def format_cell(self, level, is_self=False):
        """Format a single cell with level and box indicators."""
        if is_self:
            return "   ---   "
        
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
    
    def clear_screen(self):
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
    
    def draw_interface(self):
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
        
        # Header row with statue names
        statue_names = [d['statue'].value.upper() for d in self.devices]
        header = "  DETECTOR     " + "".join(f"{name:^9}" for name in statue_names)
        print(header + "\r", flush=True)
        print("  (Listening)  " + "─" * (len(statue_names) * 9) + "\r", flush=True)
        
        with self.lock:
            # For each detector (row)
            for detector_device in self.devices:
                detector = detector_device['statue']
                
                # Row label
                row_label = f"  {detector.value.upper():8s}│ "
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
                    row_line += f" {cell} "
                
                # Print the row with padding to ensure clean overwrites
                print(f"{row_line:<100}\r", flush=True)
                
                if detector != self.devices[-1]['statue']:  # Don't print separator after last row
                    print("            │\r", flush=True)  # Blank line between rows
        
        # Legend
        threshold = dynConfig["touch_threshold"]
        print(f"\r\nLegend: ╔═╗ LINKED (>{threshold:.2f})  "
              f"┌─┐ WEAK (>{threshold*0.5:.2f})  "
              f"Plain text: NO SIGNAL (<{threshold*0.5:.2f})\r", flush=True)
        
        print("\r\nPress Ctrl+C to stop\r", flush=True)
        # Add some blank lines to ensure we overwrite any previous content
        print("\r\n" * 3, end='', flush=True)
    
    def run(self):
        """Run the display update loop."""
        self.hide_cursor()
        while self.running:
            try:
                self.draw_interface()
                time.sleep(0.25)  # Update every 250ms (4Hz)
            except Exception:
                # Don't crash the display thread
                pass
    
    def stop(self):
        """Stop the display."""
        self.running = False
        time.sleep(0.2)  # Give display thread time to exit
        self.show_cursor()
        self.clear_screen()




def create_tone_generator(frequency, sample_rate):
    """Create a tone generator closure for the given frequency."""
    phase = 0

    def generate_tone(frames):
        nonlocal phase
        t = (np.arange(frames) + phase) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        # Update phase for continuity
        phase = (phase + frames) % int(sample_rate / frequency)
        return tone

    return generate_tone


def initialize_audio_playback(devices):
    """Initialize 6-channel audio playback for link detection with tone generation."""
    audio_file = "../../audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"

    if not os.path.exists(audio_file):
        print(f"\nAudio file not found: {audio_file}")
        print("Continuing without audio playback")
        return None

    try:
        print(f"\nLoading audio: {os.path.basename(audio_file)}")
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"  Duration: {len(audio_data) / sample_rate:.1f} seconds")
        print(f"  Channels: {audio_data.shape[1]}")

        # Create tone generators for right channel of each device
        right_channel_callbacks = {}
        for i, device in enumerate(devices):
            statue = device['statue']
            if statue in tones_hz:
                freq = tones_hz[statue]
                device_sample_rate = device.get('sample_rate', sample_rate)
                right_channel_callbacks[i] = create_tone_generator(freq, device_sample_rate)
                print(f"  Created tone generator for {statue.value}: {freq}Hz")

        # Create toggleable playback instance with tone generators
        playback = ToggleableMultiChannelPlayback(audio_data, sample_rate, devices,
                                                   right_channel_callbacks=right_channel_callbacks)
        playback.start()
        print("  ✓ Audio playback initialized with tone generators")

        return playback

    except Exception as e:
        print(f"Warning: Could not load audio file: {e}")
        print("Continuing without audio playback")
        return None


# Device configuration is now imported from audio.devices module


# Old play_tone function - no longer needed since tones are generated through audio playback
# def play_tone(statue):
#     config = dynConfig[statue.value]["tone"]
#     freq = dynConfig[statue.value]["tone_freq"]
#
#     if config["device_index"] == -1:
#         print(f"WARNING: No output device configured for {statue.value}")
#         return
#
#     channel_name = "left" if config["channel"] == 0 else "right"
#     print(f"Playing {freq}Hz tone for {statue.value} on device {config['device_index']} ({channel_name} channel)")
#
#     def callback(outdata, frames, time_info, status):
#         if status:
#             print(f"Stream status: {status}")
#         t = (np.arange(frames) + callback.phase) / config["sample_rate"]
#         # Generate sine wave for stereo output with specific channel
#         sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)
#
#         # Route to specific channel: 0=left (tip), 1=right (ring)
#         if config["channel"] == 0:  # Left channel (TRS tip)
#             outdata[:, 0] = sine_wave
#             outdata[:, 1] = 0  # Silence right channel
#         else:  # Right channel (TRS ring)
#             outdata[:, 0] = 0  # Silence left channel
#             outdata[:, 1] = sine_wave
#
#         callback.phase = (callback.phase + frames) % config["sample_rate"]
#
#     callback.phase = 0
#
#     # Create and start the output stream
#     stream = sd.OutputStream(
#         device=config["device_index"],
#         channels=2,  # Stereo output (required to route to specific channel)
#         samplerate=config["sample_rate"],
#         blocksize=dynConfig["block_size"],
#         callback=callback
#     )
#
#     tone_streams[statue.value] = stream
#     stream.start()
#     print(f"✓ Tone stream started for {statue.value} on channel {config['channel']}")



def detect_tone(statue, other_statues, link_tracker, status_display=None):
    config = dynConfig[statue.value]["detect"]  # Use detect config, not tone

    if config["device_index"] == -1:
        print(f"WARNING: No input device configured for {statue.value}")
        return

    freqs = [dynConfig[s.value]["tone_freq"] for s in other_statues]
    if not link_tracker.quiet:
        print(f"{statue.value} listening for tones {freqs}Hz on device {config['device_index']}")

    stream = sd.InputStream(
        device=config["device_index"],
        channels=1,  # Mono input
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
    )

    stream.start()
    if not link_tracker.quiet:
        print(f"✓ Detection started for {statue.value}")

    # Track current detection state for each statue
    detection_state = {s: False for s in other_statues}

    # Detect tones using the Goertzel algorithm
    while True:
        try:
            audio, overflowed = stream.read(dynConfig["block_size"])
            if overflowed:
                print("Input overflow!")

            # Convert to float64 for Goertzel
            audio_data = audio[:, 0].astype(np.float64)

            # Calculate overall signal power for noise estimation
            total_power = np.mean(audio_data ** 2)
            
            # Check for each other statue's tone
            for s in other_statues:
                freq = dynConfig[s.value]["tone_freq"]
                normalized_freq = freq / config["sample_rate"]
                level, _ = G.goertzel(audio_data, normalized_freq)

                # Simple SNR calculation
                if total_power > 0:
                    snr_db = 10 * np.log10(level / total_power) if level > 0 else -20
                else:
                    snr_db = 0
                
                # Update status display if available
                if status_display:
                    status_display.update_metrics(statue, s, level, snr_db)

                # Determine if currently detected
                currently_detected = level > dynConfig["touch_threshold"]

                # Check if state changed
                if currently_detected != detection_state[s]:
                    detection_state[s] = currently_detected
                    # Update link tracker (handles printing)
                    link_tracker.update_link(statue, s, currently_detected)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in detection: {e}")
            break

    stream.stop()
    stream.close()
    if not link_tracker.quiet:
        print(f"Detection stopped for {statue.value}")


def play_and_detect_tones(devices, link_tracker, status_display=None):
    """
    Start tone generation and detection for all configured statues.
    Each statue plays its unique tone and detects all other statue tones.
    """
    if not link_tracker.quiet:
        print("\nStarting tone generation and detection...")
        print(f"Configured statues: {[dev['statue'].value for dev in devices]}")

    # Get list of configured statues
    configured_statues = [dev['statue'] for dev in devices]

    # Tone generation now handled through audio playback system
    if not link_tracker.quiet:
        print("\nTone generators integrated with audio playback")

    # Small delay to ensure all tones are playing
    time.sleep(0.5)

    # Start detection threads for statues with input capability
    if not link_tracker.quiet:
        print("\nStarting detection threads:")
    detection_threads = []

    for statue in configured_statues:
        if dynConfig[statue.value]["detect"]["device_index"] != -1:
            # Each statue detects all other statues
            other_statues = [s for s in configured_statues if s != statue]
            if other_statues:
                thread = threading.Thread(
                    target=detect_tone,
                    args=(statue, other_statues, link_tracker, status_display),
                    daemon=True,
                    name=f"detect_{statue.value}"
                )
                detection_threads.append(thread)
                thread.start()

    if not link_tracker.quiet:
        print(f"\n{len(detection_threads)} detection thread(s) started")
        print("\nMonitoring for connections... Press Ctrl+C to stop")

        # Print initial status
        time.sleep(1)
        print("\n" + link_tracker.get_link_summary())


if __name__ == "__main__":
    print("=== Missing Link Tone Detection Test ===")
    print("Press Ctrl+C to stop\n")

    devices = configure_devices(max_devices=5)  # Configure up to 5 devices for all statues
    if not devices:
        print("Device configuration failed!")
        exit(1)

    # Set tone frequencies for all configured devices
    for device in devices:
        statue = device['statue']
        if statue in tones_hz:
            dynConfig[statue.value]["tone_freq"] = tones_hz[statue]

    if dynConfig["debug"]:
        print(f"\nTone frequencies configured:")
        for device in devices:
            statue = device['statue']
            freq = dynConfig[statue.value].get('tone_freq', -1)
            if freq > 0:
                print(f"  {statue.value.upper()}: {freq}Hz")

    # Initialize audio playback
    audio_playback = initialize_audio_playback(devices)

    # Initialize link tracker with audio playback in quiet mode
    link_tracker = LinkStateTracker(audio_playback, quiet=True)

    # Create status display
    status_display = StatusDisplay(link_tracker, devices)

    # Start display thread
    display_thread = threading.Thread(target=status_display.run, daemon=True)
    display_thread.start()

    play_and_detect_tones(devices, link_tracker, status_display)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        status_display.stop()
        print("\n\nShutting down...")
        # Stop audio playback
        if audio_playback:
            audio_playback.stop()
            print("Audio playback stopped")
        time.sleep(0.5)
        print("Done")
