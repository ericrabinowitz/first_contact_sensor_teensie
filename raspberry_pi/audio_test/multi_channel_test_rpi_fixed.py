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
# ./multi_channel_test_rpi_fixed.py

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
    """Get USB audio devices directly from ALSA - Fixed version."""
    usb_devices = []
    
    try:
        # Get card info from /proc/asound/cards
        with open('/proc/asound/cards', 'r') as f:
            cards_info = f.read()
        
        if DEBUG:
            print("Raw /proc/asound/cards content:")
            print(cards_info)
            print("-" * 40)
        
        # Split into card blocks (each card is 2 lines)
        lines = cards_info.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line and line[0].isdigit():
                # This is a card header line
                # Try multiple regex patterns
                card_match = None
                patterns = [
                    r'^\s*(\d+)\s+\[([^\]]+)\s*\]:\s*(.*)',  # Original pattern
                    r'^(\d+)\s+\[([^\]]+)\]:\s*(.*)',        # Without extra spaces
                    r'^(\d+)\s+\[(\w+)\s*\].*',              # Simplified
                ]
                
                for pattern in patterns:
                    card_match = re.match(pattern, line)
                    if card_match:
                        break
                
                if card_match:
                    card_num = int(card_match.group(1))
                    card_id = card_match.group(2).strip()
                    card_driver = card_match.group(3) if len(card_match.groups()) >= 3 else ""
                    
                    # Get the description from the next line
                    description = ""
                    if i + 1 < len(lines):
                        description = lines[i + 1].strip()
                    
                    # Check if it's a USB device
                    is_usb = False
                    if 'USB-Audio' in card_driver or 'USB-Audio' in description:
                        is_usb = True
                    elif 'usb' in card_driver.lower() or 'usb' in description.lower():
                        is_usb = True
                    elif card_id not in ['b1', 'Headphones']:  # Exclude known non-USB cards
                        # Might be USB if it's not a known built-in card
                        is_usb = True
                    
                    if is_usb:
                        usb_device = {
                            'card_num': card_num,
                            'card_id': card_id,
                            'driver': card_driver,
                            'description': description
                        }
                        usb_devices.append(usb_device)
                        if DEBUG:
                            print(f"Found USB device: Card {card_num} [{card_id}] - {description}")
                    
                    i += 2  # Skip to next card (2 lines per card)
                else:
                    i += 1
            else:
                i += 1
    
    except Exception as e:
        print(f"Error reading ALSA cards: {e}")
    
    # Alternative method: Use aplay -l to double-check
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            # Look for USB devices in aplay output
            for line in result.stdout.split('\n'):
                if 'USB' in line or 'C-Media' in line:
                    # Extract card number
                    card_match = re.search(r'card (\d+):', line)
                    if card_match:
                        card_num = int(card_match.group(1))
                        # Check if we already have this card
                        if not any(d['card_num'] == card_num for d in usb_devices):
                            # Extract card name
                            name_match = re.search(r'card \d+: ([^\[]+)\[([^\]]+)\]', line)
                            if name_match:
                                card_id = name_match.group(1).strip()
                                usb_devices.append({
                                    'card_num': card_num,
                                    'card_id': card_id,
                                    'driver': 'USB-Audio',
                                    'description': line.strip()
                                })
                                if DEBUG:
                                    print(f"Found USB device via aplay: Card {card_num}")
    except Exception as e:
        if DEBUG:
            print(f"Could not run aplay -l: {e}")
    
    return usb_devices


def configure_devices():
    """Detect and configure USB audio output devices for Raspberry Pi."""
    global usb_output_devices
    usb_output_devices = []  # Reset the list
    
    # First, try to get USB devices from ALSA
    print("Detecting USB audio devices from ALSA...")
    alsa_usb_devices = get_alsa_usb_devices()
    
    print(f"\nFound {len(alsa_usb_devices)} USB audio devices in ALSA:")
    for dev in alsa_usb_devices:
        print(f"  Card {dev['card_num']}: {dev['card_id']} - {dev['description']}")
    
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
        device_added = False
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
                    print(f"✓ Successfully configured USB device: {device_spec} - {alsa_dev['description']}")
                    device_added = True
                    break
            except Exception as e:
                if DEBUG:
                    print(f"  Failed to query device {device_spec}: {e}")
                continue
        
        if not device_added:
            print(f"✗ Could not configure Card {card_num} with any device specification")
    
    # If we couldn't configure some devices, try direct hw: addressing
    if len(usb_output_devices) < len(alsa_usb_devices):
        print("\nTrying direct hardware addressing for remaining devices...")
        for card_num in [2, 3, 4, 5]:  # Try a few card numbers
            if any(d['card_num'] == card_num for d in usb_output_devices):
                continue  # Already configured
            
            try:
                device_spec = f"hw:{card_num},0"
                info = sd.query_devices(device_spec)
                if info and info['max_output_channels'] > 0:
                    device_info = {
                        "device_id": device_spec,
                        "device_spec": device_spec,
                        "card_num": card_num,
                        "card_id": f"Card{card_num}",
                        "device_name": f"Hardware Device {card_num}",
                        "sample_rate": int(info.get('default_samplerate', 44100)),
                        "channels": int(info['max_output_channels'])
                    }
                    usb_output_devices.append(device_info)
                    print(f"✓ Found additional device via direct addressing: {device_spec}")
            except:
                pass
    
    print(f"\nTotal USB output devices configured: {len(usb_output_devices)}")
    if DEBUG:
        print("USB output devices configuration:")
        for dev in usb_output_devices:
            print(f"  {dev['device_spec']}: {dev['device_name']} ({dev['channels']} channels @ {dev['sample_rate']}Hz)")


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
        print("\nOnly one USB device found. Playing all channels mixed...")
        device = usb_output_devices[0]
        print(f"Playing on device: {device['device_spec']} - {device['device_name']}")
        try:
            # Mix all channels to mono
            mixed_data = np.mean(data, axis=1, keepdims=True)
            sd.play(mixed_data, samplerate=sample_rate, device=device['device_spec'])
            sd.wait()
            print("Single device playback completed.")
            return
        except Exception as e:
            print(f"Error in single device playback: {e}")
            return
    
    # Multi-device synchronized playback
    print("\nSetting up multi-device synchronized playback...")
    for i in range(channels_to_play):
        device = usb_output_devices[i]
        print(f"  Channel {i+1} → {device['device_spec']} ({device['device_name']})")
    
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
            print(f"Creating stream for channel {i + 1} on {device_info['device_spec']}")
            
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
        print(f"Error details: {type(e).__name__}: {str(e)}")
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
    print("Multi-Channel Audio Test (Raspberry Pi) - Fixed")
    print("=" * 50)
    
    # Configure devices
    configure_devices()
    
    if not usb_output_devices:
        print("\nNo USB audio output devices found!")
        print("\nTroubleshooting tips:")
        print("1. Check USB connection: lsusb")
        print("2. Check ALSA cards: aplay -l")
        print("3. Try a powered USB hub")
        print("4. Check dmesg for USB errors: dmesg | grep -i usb")
        print("5. Run the test_usb_devices.py script")
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