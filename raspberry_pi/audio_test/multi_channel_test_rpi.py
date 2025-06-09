#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "soundfile", "numpy"]
# ///

# System Prerequisites (Raspberry Pi):
# sudo apt-get update
# sudo apt-get install -y portaudio19-dev python3-pyaudio
# sudo apt-get install -y libsndfile1

# Install Python environment:
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute:
# ./multi_channel_test_rpi.py

import json
import re
import subprocess
import time

import numpy as np
import sounddevice as sd
import soundfile as sf


# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://python-soundfile.readthedocs.io/en/latest/


AUDIO_FILE = "Missing Link Playa 1 - 6 Channel 6-7.wav"
AUDIO_DIR = "/run/audio_files"
DEBUG = True
BLOCK_SIZE = 1024  # Frames per block

# Store detected USB audio output devices
usb_output_devices = []


def get_alsa_usb_devices():
    """Get USB audio devices directly from ALSA."""
    usb_devices = []
    
    try:
        # Get card info from /proc/asound/cards
        with open('/proc/asound/cards', 'r') as f:
            cards_info = f.read()
        
        # Parse the cards info
        lines = cards_info.strip().split('\n')
        current_card = None
        
        for line in lines:
            # Card number line
            if line and line[0].isdigit():
                card_match = re.match(r'\s*(\d+)\s+\[(\w+)\s*\]:\s+(.*)', line)
                if card_match:
                    card_num = int(card_match.group(1))
                    card_id = card_match.group(2)
                    card_driver = card_match.group(3)
                    current_card = {
                        'card_num': card_num,
                        'card_id': card_id,
                        'driver': card_driver,
                        'description': ''
                    }
            # Description line (contains USB info)
            elif current_card and line.strip():
                current_card['description'] = line.strip()
                # Check if it's a USB device
                if 'usb' in current_card['driver'].lower() or 'usb' in current_card['description'].lower():
                    usb_devices.append(current_card)
                current_card = None
    
    except Exception as e:
        print(f"Error reading ALSA cards: {e}")
    
    return usb_devices


def configure_devices():
    """Detect and configure USB audio output devices for Raspberry Pi."""
    
    # First, try to get USB devices from ALSA
    print("Detecting USB audio devices from ALSA...")
    alsa_usb_devices = get_alsa_usb_devices()
    
    if DEBUG:
        print(f"Found {len(alsa_usb_devices)} USB audio devices in ALSA:")
        for dev in alsa_usb_devices:
            print(f"  Card {dev['card_num']}: {dev['card_id']} - {dev['description']}")
    
    # Get sounddevice info for reference
    sd_devices = sd.query_devices()
    if DEBUG:
        print("\nSounddevice devices (for reference):")
        print(json.dumps(sd_devices, indent=2))
    
    # For each USB device found in ALSA, create device info
    for alsa_dev in alsa_usb_devices:
        card_num = alsa_dev['card_num']
        
        # Try different device specifications
        device_specs = [
            f"hw:{card_num},0",           # Standard hardware device
            f"plughw:{card_num},0",        # Plugin hardware device (does format conversion)
            card_num,                      # Just the card number
            f"hw:CARD={alsa_dev['card_id']},DEV=0"  # By card ID
        ]
        
        # Test which specification works with sounddevice
        for device_spec in device_specs:
            try:
                # Query this specific device
                info = sd.query_devices(device_spec)
                if info and info['max_output_channels'] > 0:
                    device_info = {
                        "device_id": device_spec,
                        "device_spec": device_spec,
                        "card_num": card_num,
                        "card_id": alsa_dev['card_id'],
                        "device_name": alsa_dev['description'],
                        "sample_rate": int(info.get('default_samplerate', 44100)),
                        "channels": int(info['max_output_channels'])
                    }
                    usb_output_devices.append(device_info)
                    print(f"Successfully configured USB device: {device_spec} - {alsa_dev['description']}")
                    break
            except Exception as e:
                if DEBUG:
                    print(f"  Failed to query device {device_spec}: {e}")
                continue
    
    # Fallback: If no USB devices found, try to use any available output device
    if not usb_output_devices and len(sd_devices) > 0:
        print("\nNo USB devices found via ALSA, trying fallback detection...")
        # Look for the C-Media device or any device with output channels
        for i, device in enumerate(sd_devices):
            if device['max_output_channels'] > 0 and i > 7:  # Skip the first virtual devices
                device_info = {
                    "device_id": i,
                    "device_spec": i,
                    "card_num": -1,
                    "card_id": "unknown",
                    "device_name": device['name'],
                    "sample_rate": int(device['default_samplerate']),
                    "channels": int(device['max_output_channels'])
                }
                usb_output_devices.append(device_info)
                print(f"Added fallback device {i}: {device['name']}")
    
    print(f"\nTotal USB output devices configured: {len(usb_output_devices)}")
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
    
    # Test single device first if only one channel to play
    if channels_to_play == 1:
        print("\nTesting single device playback...")
        device = usb_output_devices[0]
        print(f"Playing all channels mixed on device: {device['device_spec']}")
        try:
            # Mix all channels to mono
            mixed_data = np.mean(data, axis=1, keepdims=True)
            sd.play(mixed_data, samplerate=sample_rate, device=device['device_spec'])
            sd.wait()
            print("Single device test completed.")
            return
        except Exception as e:
            print(f"Error in single device playback: {e}")
            return
    
    # Multi-device synchronized playback
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
            print(f"Creating stream for channel {i + 1} on {device_info['device_spec']} ({device_info['device_name']})")
            
            stream = sd.OutputStream(
                device=device_info['device_spec'],
                channels=1,
                samplerate=sample_rate,
                blocksize=BLOCK_SIZE,
                callback=create_callback(i),
                finished_callback=lambda idx=i: print(f"Stream {idx + 1} finished")
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
    print("Multi-Channel Audio Test (Raspberry Pi)")
    print("=" * 40)
    
    # Configure devices
    configure_devices()
    
    if not usb_output_devices:
        print("\nNo USB audio output devices found!")
        print("\nTroubleshooting tips:")
        print("1. Check USB connection: lsusb")
        print("2. Check ALSA cards: aplay -l")
        print("3. Try a powered USB hub")
        print("4. Check dmesg for USB errors: dmesg | grep -i usb")
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