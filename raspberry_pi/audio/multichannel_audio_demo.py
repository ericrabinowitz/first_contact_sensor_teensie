#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile"]
# ///

"""
Interactive multi-channel audio demo with channel toggle controls.
Allows real-time muting/unmuting of individual channels while playing.
"""

import os
import select
import sys
import termios
import time
import tty

import soundfile as sf

from audio.devices import configure_devices
from audio.music import ToggleableMultiChannelPlayback


class ChannelToggleInterface:
    """Interactive interface for toggling audio channels."""

    def __init__(self, playback, devices):
        self.playback = playback
        self.devices = devices
        self.running = True
        self.old_settings = None

    def setup_terminal(self):
        """Set terminal to raw mode for immediate key capture."""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    def restore_terminal(self):
        """Restore terminal to normal mode."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def clear_screen(self):
        """Clear terminal screen."""
        print("\033[2J\033[H", end='')

    def draw_interface(self):
        """Draw the channel toggle interface."""
        self.clear_screen()

        states = self.playback.get_channel_states()
        progress = self.playback.get_progress()

        # In raw mode, we need explicit \r\n for proper line endings
        print("=== Multi-Channel Audio Demo ===\r\n\r")
        print("Channel Status:\r")

        statue_names = ["EROS", "ELEKTRA", "SOPHIA", "ULTIMO", "ARIEL", "---"]

        for i in range(len(self.devices)):
            statue_name = statue_names[i] if i < len(statue_names) else f"CH{i+1}"
            status = "ON " if states[i] else "OFF"
            bar = "█" * 12 if states[i] else "─" * 12

            print(f"[{i+1}] {statue_name:8s} [{status}]  {bar}\r")

        print(f"\r\nActive channels: {self.playback.active_count}/{len(self.devices)}\r")
        print(f"Playback: {'Playing' if self.playback.is_playing else 'Stopped'} ({progress}%)\r")
        print("\r\nPress 1-6 to toggle channels, 'q' to quit\r")

    def run(self):
        """Run the interactive interface."""
        self.setup_terminal()

        try:
            while self.running:
                self.draw_interface()

                # Non-blocking key input with timeout
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)

                    if key == 'q' or key == 'Q':
                        self.running = False
                    elif key.isdigit():
                        channel = int(key) - 1
                        if 0 <= channel < len(self.devices):
                            self.playback.toggle_channel(channel)

                time.sleep(0.05)  # Small delay to reduce CPU usage

        finally:
            self.restore_terminal()
            self.clear_screen()
            print("Demo ended.")


def main():
    """Run the multi-channel audio demo."""
    print("=== Multi-Channel Audio Demo ===")
    print("Initializing...")

    # Configure all available USB devices (up to 6)
    devices = configure_devices(max_devices=6)
    if not devices:
        print("No USB audio devices found!")
        return

    print(f"Configured {len(devices)} devices")

    # Load the 6-channel audio file
    audio_file = "../../audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"

    if not os.path.exists(audio_file):
        print("6-channel file not found, trying stereo file...")
        audio_file = "../../audio_files/Missing Link unSCruz active 01 Remi Wolf Polo Pan Hello.wav"
        if not os.path.exists(audio_file):
            print("ERROR: No test audio files found")
            return

    try:
        # Load audio data
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"\nLoaded: {os.path.basename(audio_file)}")
        print(f"Duration: {len(audio_data) / sample_rate:.1f} seconds")
        print(f"Channels: {audio_data.shape[1]}")

    except Exception as e:
        print(f"Error loading audio file: {e}")
        return

    # Create toggleable playback instance
    playback = ToggleableMultiChannelPlayback(audio_data, sample_rate, devices)

    # Start all output streams (but with channels muted)
    playback.start()

    # Run the interactive interface
    interface = ChannelToggleInterface(playback, devices)

    try:
        interface.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        playback.stop()
        print("\nPlayback stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
