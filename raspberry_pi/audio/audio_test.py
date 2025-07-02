#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile"]
# ///

# Execute
# ./audio_test.py

import os
import sys
import time

# Add parent directory to path for imports
sys.path.append('../')

from audio.devices import configure_devices
from audio.music import play_multichannel_audio


def main():
    print("=== Missing Link Multi-Channel Audio Test ===\n")

    # Configure all available USB devices (up to 6)
    devices = configure_devices(max_devices=6)
    if not devices:
        print("No USB audio devices found!")
        return

    print(f"\nConfigured {len(devices)} devices for multi-channel playback")

    # Default to 6-channel test file
    audio_file = "../../audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"

    # Check if file exists, otherwise use a different one
    if not os.path.exists(audio_file):
        print("6-channel file not found, trying stereo file...")
        audio_file = "../../audio_files/Missing Link unSCruz active 01 Remi Wolf Polo Pan Hello.wav"
        if not os.path.exists(audio_file):
            print("ERROR: No test audio files found")
            return

    print(f"\nPlaying: {os.path.basename(audio_file)}")

    # Play multi-channel audio
    playback = play_multichannel_audio(audio_file, devices)
    if not playback:
        return

    # Control playback demonstration
    print("\nPlayback controls demonstration:")
    print("  Playing for 5 seconds...")
    time.sleep(5)

    playback.pause()
    print("  Paused for 2 seconds...")
    time.sleep(2)

    playback.resume()
    print("  Resumed for 5 seconds...")
    time.sleep(5)

    # Check if still playing
    if playback.is_active():
        print("  Stopping playback...")
        playback.stop()
    else:
        print("  Playback completed")
        playback.stop()

    print("\nTest complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
