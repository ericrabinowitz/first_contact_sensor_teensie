#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile", "ultraimport"]
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

# List of available songs
SONG_LIST = [
    "../../audio_files/Missing Link Playa 1 - 5 channel.wav",
    "../../audio_files/Missing Link Playa 2 - 5 Channel.wav",
    "../../audio_files/Missing Link Playa 3 - Five Channel.wav",
    "../../audio_files/Missing Link Playa Dormant - 5 channel deux.wav",
    # Fallback songs if the main ones aren't found
    #"../../audio_files/Missing Link unSCruz active 01 Remi Wolf Polo Pan Hello.wav",
]


class ChannelToggleInterface:
    """Interactive interface for toggling audio channels."""

    def __init__(self, playback, devices, song_name, song_index, total_songs, song_switcher):
        self.playback = playback
        self.devices = devices
        self.song_name = song_name
        self.song_index = song_index
        self.total_songs = total_songs
        self.song_switcher = song_switcher
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
        print(f"Current Song: {os.path.basename(self.song_name)}\r")
        print(f"Song {self.song_index + 1} of {self.total_songs}\r\n")
        print("Channel Status:\r")

        statue_names = ["EROS", "ELEKTRA", "ARIEL", "SOPHIA", "ULTIMO", "---"]

        for i in range(len(self.devices)):
            statue_name = statue_names[i] if i < len(statue_names) else f"CH{i+1}"
            status = "ON " if states[i] else "OFF"
            bar = "█" * 12 if states[i] else "─" * 12

            print(f"[{i+1}] {statue_name:8s} [{status}]  {bar}\r")

        print(f"\r\nActive channels: {self.playback.active_count}/{len(self.devices)}\r")
        print(f"Playback: {'Stopped' if self.playback.is_stopped else 'Playing'} ({progress}%)\r")
        print("\r\nControls:\r")
        print("  1-6: Toggle channels | A: Previous song | D: Next song | Q: Quit\r")

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
                            self.playback.toggle_music_channel(channel)
                    elif key == 'a' or key == 'A':
                        # Previous song
                        self.song_switcher(-1)
                        self.running = False  # Exit interface to switch songs
                    elif key == 'd' or key == 'D':
                        # Next song
                        self.song_switcher(1)
                        self.running = False  # Exit interface to switch songs

                time.sleep(0.05)  # Small delay to reduce CPU usage

        finally:
            self.restore_terminal()
            self.clear_screen()
            print("Demo ended.")


def load_song(song_path):
    """Load a song file and return audio data and sample rate."""
    if not os.path.exists(song_path):
        return None, None

    try:
        audio_data, sample_rate = sf.read(song_path)
        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)
        return audio_data, sample_rate
    except Exception as e:
        print(f"Error loading audio file {song_path}: {e}")
        return None, None


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

    # Track current song index
    current_song_index = 0
    song_change_direction = 0  # -1 for previous, 0 for none, 1 for next
    channel_states = None  # To preserve channel states between songs

    # Find available songs
    available_songs = []
    for song in SONG_LIST:
        if os.path.exists(song):
            available_songs.append(song)
        else:
            print(f"Couldn't find song {song}")

    if not available_songs:
        print("ERROR: No audio files found!")
        return

    print(f"Found {len(available_songs)} songs")

    def switch_song(direction):
        """Callback to switch songs."""
        nonlocal song_change_direction
        song_change_direction = direction

    # Main loop for song switching
    while True:
        # Load current song
        audio_file = available_songs[current_song_index]
        audio_data, sample_rate = load_song(audio_file)

        if audio_data is None:
            print(f"Failed to load {audio_file}, trying next song...")
            current_song_index = (current_song_index + 1) % len(available_songs)
            continue

        print(f"\nLoaded: {os.path.basename(audio_file)}")
        print(f"Duration: {len(audio_data) / sample_rate:.1f} seconds")
        print(f"Channels: {audio_data.shape[1]}")

        # Create toggleable playback instance
        playback = ToggleableMultiChannelPlayback(audio_data, sample_rate, devices)

        # Restore channel states if we have them
        if channel_states is not None:
            for i, state in enumerate(channel_states):
                if i < len(devices):
                    playback.set_music_channel(i, state)

        # Start all output streams
        playback.start()

        # Reset song change direction
        song_change_direction = 0

        # Run the interactive interface
        interface = ChannelToggleInterface(
            playback,
            devices,
            audio_file,
            current_song_index,
            len(available_songs),
            switch_song
        )

        try:
            interface.run()
        except KeyboardInterrupt:
            playback.stop()
            print("\nExiting...")
            break

        # Save channel states before stopping
        channel_states = playback.get_channel_states()

        # Clean up current playback
        playback.stop()

        # Check if we should switch songs or quit
        if song_change_direction != 0:
            # Switch to next/previous song
            current_song_index = (current_song_index + song_change_direction) % len(available_songs)
            print(f"\nSwitching to song {current_song_index + 1} of {len(available_songs)}...")
        else:
            # User pressed 'q', exit
            print("\nPlayback stopped.")
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
