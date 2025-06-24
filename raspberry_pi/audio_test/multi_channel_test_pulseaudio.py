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
# ./multi_channel_test_pulseaudio.py

import json
import subprocess
import time
import re

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


def get_pulseaudio_usb_sinks():
    """Get USB audio devices from PulseAudio."""
    usb_devices = []
    
    try:
        # Get PulseAudio sinks
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running pactl: {result.stderr}")
            return usb_devices
        
        if DEBUG:
            print("PulseAudio sinks:")
            print(result.stdout)
        
        # Parse sink output
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                sink_id = int(parts[0])
                sink_name = parts[1]
                
                # Look for USB devices
                if 'usb' in sink_name.lower() and 'analog-stereo' in sink_name:
                    # Extract device info from sink name
                    device_info = {
                        'sink_id': sink_id,
                        'sink_name': sink_name,
                        'device_name': sink_name.split('.')[-1],
                        'sample_rate': 44100,  # Default for most USB devices
                        'channels': 2  # Stereo output
                    }
                    
                    # Try to get a friendlier name
                    if 'C-Media_Electronics_Inc._USB_Audio_Device' in sink_name:
                        device_info['friendly_name'] = 'USB Audio Device'
                    elif 'C-Media_USB_Headphone_Set' in sink_name:
                        device_info['friendly_name'] = 'USB Headphone Set'
                    else:
                        device_info['friendly_name'] = f'USB Device {sink_id}'
                    
                    usb_devices.append(device_info)
                    if DEBUG:
                        print(f"Found USB sink {sink_id}: {device_info['friendly_name']}")
    
    except Exception as e:
        print(f"Error getting PulseAudio sinks: {e}")
    
    return usb_devices


def configure_devices():
    """Detect and configure USB audio output devices via PulseAudio."""
    global usb_output_devices
    usb_output_devices = []  # Reset the list
    
    print("Detecting USB audio devices from PulseAudio...")
    pulse_usb_devices = get_pulseaudio_usb_sinks()
    
    print(f"\nFound {len(pulse_usb_devices)} USB audio devices in PulseAudio:")
    for dev in pulse_usb_devices:
        print(f"  Sink {dev['sink_id']}: {dev['friendly_name']}")
    
    # Test each USB device
    for pulse_dev in pulse_usb_devices:
        sink_id = pulse_dev['sink_id']
        
        try:
            # Test if sounddevice can access this sink
            info = sd.query_devices(sink_id)
            if info and info['max_output_channels'] > 0:
                device_info = {
                    "device_id": sink_id,
                    "device_spec": sink_id,
                    "sink_id": sink_id,
                    "sink_name": pulse_dev['sink_name'],
                    "device_name": pulse_dev['friendly_name'],
                    "sample_rate": int(info.get('default_samplerate', 44100)),
                    "channels": min(int(info['max_output_channels']), 2)  # Limit to stereo
                }
                usb_output_devices.append(device_info)
                print(f"✓ Successfully configured USB device: Sink {sink_id} - {pulse_dev['friendly_name']}")
            else:
                print(f"✗ Sink {sink_id} has no output channels")
                
        except Exception as e:
            print(f"✗ Could not configure Sink {sink_id}: {e}")
    
    print(f"\nTotal USB output devices configured: {len(usb_output_devices)}")
    if DEBUG:
        print("USB output devices configuration:")
        for dev in usb_output_devices:
            print(f"  Sink {dev['sink_id']}: {dev['device_name']} ({dev['channels']} channels @ {dev['sample_rate']}Hz)")


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
    
    print(f"\nPlaying {channels_to_play} channels on {channels_to_play} USB devices")
    
    # Test single device first if only one device available
    if len(usb_output_devices) == 1:
        print("\nOnly one USB device found. Playing all channels mixed...")
        device = usb_output_devices[0]
        print(f"Playing on: Sink {device['sink_id']} - {device['device_name']}")
        try:
            # Mix all channels to stereo
            if num_channels == 1:
                # Mono to stereo
                mixed_data = np.column_stack([data[:, 0], data[:, 0]])
            elif num_channels >= 2:
                # Mix all channels down to stereo
                left_mix = np.mean(data[:, ::2], axis=1)  # Mix odd channels to left
                right_mix = np.mean(data[:, 1::2], axis=1)  # Mix even channels to right
                mixed_data = np.column_stack([left_mix, right_mix])
            
            sd.play(mixed_data, samplerate=sample_rate, device=device['sink_id'])
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
        print(f"  Channel {i+1} → Sink {device['sink_id']} ({device['device_name']})")
    
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
                # Extract the channel data for this range and duplicate to stereo
                channel_data = data[start:end, channel_idx]
                outdata[:actual_frames, 0] = channel_data  # Left
                outdata[:actual_frames, 1] = channel_data  # Right (duplicate for stereo)
                
                # Fill any remaining frames with silence
                if actual_frames < frames:
                    outdata[actual_frames:, :] = 0
                    
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
            print(f"Creating stream for channel {i + 1} on Sink {device_info['sink_id']}")
            
            stream = sd.OutputStream(
                device=device_info['sink_id'],
                channels=2,  # Stereo output
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
    print("Multi-Channel Audio Test (PulseAudio)")
    print("=" * 50)
    
    # Configure devices
    configure_devices()
    
    if not usb_output_devices:
        print("\nNo USB audio output devices found!")
        print("\nTroubleshooting tips:")
        print("1. Check USB connection: lsusb")
        print("2. Check PulseAudio sinks: pactl list short sinks")
        print("3. Try a powered USB hub")
        print("4. Check dmesg for USB errors: dmesg | grep -i usb")
        print("5. Restart PulseAudio: pulseaudio --kill && pulseaudio --start")
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