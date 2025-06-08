#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "soundfile", "numpy"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./multi_channel_test.py

import json
import re
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf


# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://python-soundfile.readthedocs.io/en/latest/


USB_ADAPTER = "usb audio device"
AUDIO_FILE = "Missing Link Playa 1 - 6 Channel 6-7.wav"
AUDIO_DIR = "/run/audio_files"
DEBUG = True

# Store detected USB audio output devices
usb_output_devices = []


def configure_devices():
    """Detect and configure USB audio output devices."""
    devices = sd.query_devices()
    if DEBUG:
        print("Available audio devices:")
        print(json.dumps(devices, indent=2))

    pattern = r"^([^:]*): - \((hw:\d+,\d+)\)$"
    
    print("\nDetecting USB audio output devices...")
    for device in devices:
        match = re.search(pattern, device["name"])
        if not match:
            continue
        device_type = match.group(1).lower()
        device_id = match.group(2)
        
        # Only process USB audio devices with output channels
        if device_type == USB_ADAPTER and device["max_output_channels"] > 0:
            device_info = {
                "device_id": device_id,
                "device_index": int(device["index"]),
                "device_name": device["name"],
                "sample_rate": int(device["default_samplerate"]),
                "channels": int(device["max_output_channels"])
            }
            usb_output_devices.append(device_info)
            print(f"Found USB output device: {device_id} - {device['name']}")

    print(f"\nTotal USB output devices found: {len(usb_output_devices)}")
    if DEBUG:
        print("USB output devices configuration:")
        print(json.dumps(usb_output_devices, indent=2))


def play_multi_channel_audio():
    """Load multi-channel audio file and play each channel on a separate USB device."""
    
    # Load the audio file
    audio_path = f"{AUDIO_DIR}/{AUDIO_FILE}"
    print(f"\nLoading audio file: {audio_path}")
    
    try:
        data, sample_rate = sf.read(audio_path, always_2d=True)
        num_samples, num_channels = data.shape
        duration = num_samples / sample_rate
        
        print(f"Audio file loaded:")
        print(f"  Channels: {num_channels}")
        print(f"  Sample rate: {sample_rate} Hz")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Shape: {data.shape}")
        
    except Exception as e:
        print(f"Error loading audio file: {e}")
        return
    
    # Determine how many channels we can play
    channels_to_play = min(num_channels, len(usb_output_devices))
    if channels_to_play == 0:
        print("No USB audio devices available for playback!")
        return
    
    print(f"\nPlaying {channels_to_play} channels on {channels_to_play} devices")
    
    # Create output streams for each channel/device
    streams = []
    stream_threads = []
    
    def play_channel(channel_idx, device_info, channel_data):
        """Play a single channel on a specific device."""
        try:
            print(f"Starting playback of channel {channel_idx + 1} on {device_info['device_id']}")
            
            # Ensure the audio data is in the correct format (float32)
            audio_data = channel_data.astype(np.float32)
            
            # Play the audio blocking on this thread
            sd.play(
                data=audio_data,
                samplerate=sample_rate,
                device=device_info['device_index'],
                blocking=True
            )
            
        except Exception as e:
            print(f"Error playing channel {channel_idx + 1}: {e}")
    
    # Start playback threads for each channel
    print("\nStarting synchronized playback...")
    start_time = time.time()
    
    for i in range(channels_to_play):
        # Extract single channel data
        channel_data = data[:, i].reshape(-1, 1)
        
        # Create and start thread for this channel
        thread = threading.Thread(
            target=play_channel,
            args=(i, usb_output_devices[i], channel_data),
            daemon=True
        )
        stream_threads.append(thread)
        thread.start()
        
        # Very small delay to ensure threads start in order
        time.sleep(0.001)
    
    print("All channels started. Playing...")
    
    # Wait for all threads to complete
    for thread in stream_threads:
        thread.join()
    
    elapsed = time.time() - start_time
    print(f"\nPlayback completed. Total time: {elapsed:.2f} seconds")


def main():
    """Main function to run the multi-channel audio test."""
    print("Multi-Channel Audio Test")
    print("========================")
    
    # Configure devices
    configure_devices()
    
    if not usb_output_devices:
        print("\nNo USB audio output devices found!")
        return
    
    # Play multi-channel audio
    play_multi_channel_audio()
    
    print("\nTest completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sd.stop()  # Stop all playback
