#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile"]
# ///

# Execute
# ./audio_test.py

import os
import time

from audio.devices import configure_devices
from audio.music import ToggleableMultiChannelPlayback
from .devices import get_audio_devices

import soundfile as sf


def play_multichannel_audio(audio_file, devices=None):
    """
    Play a multi-channel audio file across multiple devices.

    Args:
        audio_file: Path to the multi-channel WAV file
        devices: List of device configurations. If None, uses all configured audio devices.

    Returns:
        ToggleableMultiChannelPlayback instance for control, or None on error
    """
    try:
        # Load the audio file
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D (samples x channels)
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"Loaded audio file: {audio_file}")
        print(f"  Sample rate: {sample_rate} Hz")
        print(f"  Duration: {len(audio_data) / sample_rate:.2f} seconds")
        print(f"  Channels: {audio_data.shape[1]}")

        # Get devices if not provided
        if devices is None:
            devices = get_audio_devices()

        if not devices:
            print("ERROR: No audio devices configured")
            return None

        # Limit to available channels
        num_channels = min(len(devices), audio_data.shape[1])
        devices = devices[:num_channels]

        print(f"\nMapping {num_channels} audio channels to devices:")
        for i, device in enumerate(devices):
            statue_name = (
                device["statue"].value
                if hasattr(device["statue"], "value")
                else str(device["statue"])
            )
            print(f"  Channel {i} → {statue_name} (device {device['device_index']})")

        # Create and start playback
        playback = ToggleableMultiChannelPlayback(audio_data, sample_rate, devices)
        playback.start()

        return playback

    except ImportError:
        print("ERROR: soundfile library not available")
        print("Install with: pip install soundfile")
        return None
    except Exception as e:
        print(f"Error loading audio file {audio_file}: {e}")
        return None


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
    playback.enable_all_music_channels()
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
