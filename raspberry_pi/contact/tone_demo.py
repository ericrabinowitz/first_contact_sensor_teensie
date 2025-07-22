#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile"]
# ///

"""Interactive Tone Generator for Missing Link Statues

Interactive tool for testing and adjusting tone frequencies across
multiple USB audio devices. Allows real-time frequency adjustment
and individual statue control.
"""

import select
import sys
import termios
import threading
import time
import tty

import numpy as np

from audio.devices import Statue, configure_devices
from audio.music import ToggleableMultiChannelPlayback
from config import TONE_FREQUENCIES


def create_tone_generator(frequency: float, sample_rate: int):
    """Create a tone generator closure for the given frequency.

    This is the working implementation from tone_detect.py, copied here
    to avoid import dependencies.
    """
    phase = 0

    def generate_tone(frames):
        nonlocal phase
        t = (np.arange(frames) + phase) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        # Update phase for continuity
        phase = (phase + frames) % int(sample_rate / frequency)
        return tone

    return generate_tone


class DynamicToneGenerator:
    """Dynamic tone generator with real-time frequency updates."""

    def __init__(self, initial_frequency: float, sample_rate: int):
        # Store the working tone generator closure
        self.base_generator = create_tone_generator(initial_frequency, sample_rate)
        self.frequency = initial_frequency
        self.sample_rate = sample_rate
        self.lock = threading.Lock()

    def set_frequency(self, new_frequency: float):
        """Update frequency by creating a new generator."""
        with self.lock:
            self.frequency = max(500, new_frequency)  # Enforce minimum
            # Create new generator with updated frequency
            self.base_generator = create_tone_generator(self.frequency, self.sample_rate)

    def __call__(self, frames):
        """Generate tone samples using the working generator."""
        with self.lock:
            return self.base_generator(frames)


def handle_key_input(key, ui):
    """Handle keyboard input for the interactive UI."""
    if key == 'q' or key == 'Q' or key == '\x1b':  # ESC key
        return False  # Signal to exit
    elif key == ' ':  # Space bar
        ui.toggle_statue()
    elif key == 'w' or key == 'W':  # Up (w key)
        ui.navigate_up()
    elif key == 's' or key == 'S':  # Down (s key)
        ui.navigate_down()
    elif key == 'a' or key == 'A':  # Left (a key)
        ui.adjust_frequency(-500)
    elif key == 'd' or key == 'D':  # Right (d key)
        ui.adjust_frequency(+500)
    elif key.isdigit():  # Number keys for direct statue selection
        statue_index = int(key) - 1
        if 0 <= statue_index < len(ui.devices):
            ui.selected_index = statue_index
    return True  # Continue running


class InteractiveUI:
    """Manages the interactive terminal UI."""

    def __init__(self, devices, tone_frequencies):
        self.devices = devices
        self.frequencies = {i: tone_frequencies[dev['statue']] for i, dev in enumerate(devices)}
        self.selected_index = 0
        self.tone_enabled = [True] * len(devices)
        self.running = True
        self.old_settings = None

    def setup_terminal(self):
        """Set terminal to raw mode for immediate key capture."""
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        except (termios.error, OSError):
            # Not a real terminal (e.g., running over SSH without TTY)
            self.old_settings = None
            print("WARNING: Terminal input not available (running over SSH or non-TTY)")
            print("Interactive controls disabled. Press Ctrl+C to exit.")

    def restore_terminal(self):
        """Restore terminal to normal mode."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

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
        """Move cursor to home position."""
        print("\033[H", end='', flush=True)

    def draw_ui(self):
        """Draw the interactive UI."""
        if not hasattr(self, 'first_draw'):
            self.first_draw = True

        if self.first_draw:
            self.clear_screen()
            self.first_draw = False
        else:
            self.move_cursor_home()

        # Header
        print("=== Interactive Tone Generator ===\r\n\r", flush=True)
        print("CONFIGURED STATUES:\r", flush=True)

        for i, device in enumerate(self.devices):
            statue = device['statue']
            freq = self.frequencies[i]
            status = "♪ PLAYING" if self.tone_enabled[i] else "  MUTED "
            cursor = ">" if i == self.selected_index else " "

            line = f"{cursor} {statue.value.upper():8s} [{freq:5d} Hz]  {status}"
            print(f"{line:<50}\r", flush=True)  # Pad to ensure full line overwrite

        print("\r", flush=True)
        print("CONTROLS:\r", flush=True)
        print("  W/S Select statue    A/D Frequency ±500Hz\r", flush=True)
        print("  SPACE Toggle on/off  Q/ESC Quit\r", flush=True)
        print("  1-9 Direct selection\r", flush=True)
        print("\r", flush=True)

        selected_statue = self.devices[self.selected_index]['statue']
        selected_freq = self.frequencies[self.selected_index]
        selected_status = "PLAYING" if self.tone_enabled[self.selected_index] else "MUTED"
        line1 = f"Selected: {selected_statue.value.upper()} ({selected_freq} Hz) - {selected_status}"
        line2 = "Frequency range: 500Hz - 20000Hz"
        print(f"{line1:<60}\r", flush=True)
        print(f"{line2:<60}\r", flush=True)

        # Add blank lines to ensure clean display
        print("\r\n\r\n\r", end='', flush=True)

    def navigate_up(self):
        """Move selection up to previous statue."""
        if self.selected_index > 0:
            self.selected_index -= 1

    def navigate_down(self):
        """Move selection down to next statue."""
        if self.selected_index < len(self.devices) - 1:
            self.selected_index += 1

    def adjust_frequency(self, delta):
        """Adjust frequency of selected statue by delta Hz."""
        current_freq = self.frequencies[self.selected_index]
        new_freq = max(500, min(20000, current_freq + delta))  # Enforce 500-20000Hz range

        # Only update if frequency actually changed
        if new_freq != current_freq:
            self.frequencies[self.selected_index] = new_freq

            # Update the tone generator if we have a reference to it
            if hasattr(self, 'tone_generators'):
                self.tone_generators[self.selected_index].set_frequency(new_freq)

    def toggle_statue(self):
        """Toggle the selected statue on/off."""
        self.tone_enabled[self.selected_index] = not self.tone_enabled[self.selected_index]

        # Update the audio playback if we have a reference to it
        if hasattr(self, 'playback'):
            self.playback.set_tone_channel(self.selected_index, self.tone_enabled[self.selected_index])

    def run(self, playback, tone_generators):
        """Run the interactive interface."""
        # Store references for real-time updates
        self.playback = playback
        self.tone_generators = tone_generators

        self.setup_terminal()
        self.hide_cursor()

        try:
            # If no terminal input available, just run tones for 10 seconds
            if self.old_settings is None:
                print("Running tone generators for 10 seconds...")
                time.sleep(10)
                self.running = False
            else:
                # Interactive mode
                while self.running:
                    self.draw_ui()

                    # Non-blocking key input with timeout
                    if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        if not handle_key_input(key, self):
                            self.running = False

                    time.sleep(0.05)  # Small delay to reduce CPU usage

        finally:
            self.restore_terminal()
            self.show_cursor()
            self.clear_screen()


def main():
    """Main function for interactive tone generator."""
    print("=== Interactive Tone Generator ===")
    print()

    # Configure USB audio devices
    print("Configuring USB audio devices...")
    devices = configure_devices(max_devices=5)

    if not devices:
        print("ERROR: No USB audio devices found!")
        print("Make sure USB audio adapters are connected.")
        return 1

    print(f"✓ Configured {len(devices)} device(s)")

    # Show configured statues
    statue_names = [device['statue'].value for device in devices]
    print(f"Configured statues: {statue_names}")

    # Show default frequencies
    print()
    print("Default frequencies:")
    for device in devices:
        statue = device['statue']
        freq = TONE_FREQUENCIES.get(statue, "Unknown")
        print(f"  {statue.value.upper()}: {freq}Hz")

    # Initialize audio playback with tone generators
    print()
    print("Initializing audio playback...")

    # Create tone generators for each device using the working implementation
    tone_generators = {}
    for i, device in enumerate(devices):
        statue = device['statue']
        freq = TONE_FREQUENCIES[statue]
        # Use DynamicToneGenerator which wraps the working create_tone_generator
        tone_generators[i] = DynamicToneGenerator(freq, device['sample_rate'])
        print(f"  Created tone generator for {statue.value}: {freq}Hz")

    # Create dummy audio data (we only use tone generators)
    # Use 1 second of audio per channel for smooth looping
    sample_rate = devices[0]['sample_rate']
    audio_duration_seconds = 1.0
    dummy_audio = np.zeros((int(sample_rate * audio_duration_seconds), len(devices)))

    # Create and start playback with looping enabled
    playback = ToggleableMultiChannelPlayback(
        dummy_audio, sample_rate, devices,
        right_channel_callbacks=tone_generators,
        loop=True  # Enable looping for continuous tone generation
    )
    playback.start()

    # Enable all tone channels initially
    for i in range(len(devices)):
        playback.set_tone_channel(i, True)

    print("✓ Audio playback started")
    print()
    print("Starting interactive interface...")

    # Create and run interactive UI
    ui = InteractiveUI(devices, TONE_FREQUENCIES)

    try:
        ui.run(playback, tone_generators)
    finally:
        # Clean shutdown
        print("\nStopping audio...")
        playback.stop()

    print("\n🎵 Interactive Tone Generator Complete! 🎵")
    print("Controls used:")
    print("  ✓ W/S keys to select statues")
    print("  ✓ A/D keys to adjust frequencies by ±500Hz")
    print("  ✓ SPACE to toggle individual statues on/off")
    print("  ✓ Q/ESC to quit")
    print("  ✓ 1-9 for direct statue selection")
    return 0


if __name__ == "__main__":
    sys.exit(main())
