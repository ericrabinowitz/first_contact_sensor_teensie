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
BLOCK_SIZE = 1024  # Frames per block

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
        
        # Convert to float32 for sounddevice
        data = data.astype(np.float32)
        
    except Exception as e:
        print(f"Error loading audio file: {e}")
        return
    
    # Determine how many channels we can play
    channels_to_play = min(num_channels, len(usb_output_devices))
    if channels_to_play == 0:
        print("No USB audio devices available for playback!")
        return
    
    print(f"\nPlaying {channels_to_play} channels on {channels_to_play} devices")
    
    # Create a shared playback state
    class PlaybackState:
        def __init__(self):
            self.position = 0
            self.finished = False
    
    state = PlaybackState()
    
    # Create output streams for each channel/device
    streams = []
    
    def create_callback(channel_idx):
        """Create a callback function for a specific channel."""
        def callback(outdata, frames, time_info, status):
            if status:
                print(f"Stream {channel_idx + 1} status: {status}")
            
            # Calculate the range of samples to read
            start = state.position
            end = min(start + frames, num_samples)
            actual_frames = end - start
            
            if actual_frames > 0:
                # Extract the channel data for this range
                outdata[:actual_frames, 0] = data[start:end, channel_idx]
                
                # Fill any remaining frames with silence
                if actual_frames < frames:
                    outdata[actual_frames:, 0] = 0
                    
                # Update position (only one callback should do this)
                if channel_idx == 0:
                    state.position = end
                    if end >= num_samples:
                        state.finished = True
            else:
                # No more data, fill with silence
                outdata[:] = 0
                state.finished = True
                
        return callback
    
    # Create streams for each channel
    try:
        for i in range(channels_to_play):
            device_info = usb_output_devices[i]
            print(f"Creating stream for channel {i + 1} on {device_info['device_id']}")
            
            stream = sd.OutputStream(
                device=device_info['device_index'],
                channels=1,
                samplerate=sample_rate,
                blocksize=BLOCK_SIZE,
                callback=create_callback(i),
                finished_callback=lambda: print(f"Stream {i + 1} finished")
            )
            streams.append(stream)
            
    except Exception as e:
        print(f"Error creating streams: {e}")
        # Close any streams that were created
        for stream in streams:
            stream.close()
        return
    
    # Start all streams simultaneously
    print("\nStarting synchronized playback...")
    start_time = time.time()
    
    try:
        # Start all streams
        for i, stream in enumerate(streams):
            stream.start()
            print(f"Started stream {i + 1}")
        
        print("All streams started. Playing...")
        
        # Wait for playback to complete
        while not state.finished:
            time.sleep(0.1)
            # Print progress
            progress = (state.position / num_samples) * 100
            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print("\n\nWaiting for streams to finish...")
        time.sleep(0.5)  # Give streams time to flush buffers
        
    except KeyboardInterrupt:
        print("\n\nPlayback interrupted by user")
    except Exception as e:
        print(f"\nError during playback: {e}")
    finally:
        # Stop and close all streams
        for i, stream in enumerate(streams):
            stream.stop()
            stream.close()
            print(f"Closed stream {i + 1}")
    
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
