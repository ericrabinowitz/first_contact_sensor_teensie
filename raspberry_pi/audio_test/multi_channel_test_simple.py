#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "soundfile", "numpy"]
# ///

# Simple multi-channel test using card indices directly

import numpy as np
import sounddevice as sd
import soundfile as sf
import time
import sys
import os

# Setup logging
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'multi_channel_test_simple.log')

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger(log_file)

AUDIO_FILE = "Missing Link Playa 1 - 6 Channel 6-7.wav"
AUDIO_DIR = "/run/audio_files"
BLOCK_SIZE = 1024

print("Multi-Channel Audio Test - Simple Version")
print("=" * 50)

# Known USB audio card indices on Raspberry Pi
USB_CARD_INDICES = [2, 3, 4, 5]

# Test which USB cards are available
print("\nTesting USB audio cards...")
available_usb_cards = []

for card_idx in USB_CARD_INDICES:
    try:
        info = sd.query_devices(card_idx)
        if info and info['max_output_channels'] > 0:
            available_usb_cards.append({
                'index': card_idx,
                'name': info['name'],
                'channels': info['max_output_channels'],
                'sample_rate': info['default_samplerate']
            })
            print(f"✓ Card {card_idx}: {info['name']} ({info['max_output_channels']} channels)")
    except:
        pass

print(f"\nFound {len(available_usb_cards)} USB audio cards")

if len(available_usb_cards) == 0:
    print("No USB audio devices found!")
    exit(1)

# Load audio file
print(f"\nLoading audio file: {AUDIO_DIR}/{AUDIO_FILE}")
try:
    data, sample_rate = sf.read(f"{AUDIO_DIR}/{AUDIO_FILE}", always_2d=True)
    num_samples, num_channels = data.shape
    duration = num_samples / sample_rate
    
    print(f"Audio file loaded:")
    print(f"  Channels: {num_channels}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration:.2f} seconds")
    
    data = data.astype(np.float32)
except Exception as e:
    print(f"Error loading audio file: {e}")
    exit(1)

# Determine how many channels to play
channels_to_play = min(num_channels, len(available_usb_cards))
print(f"\nWill play {channels_to_play} channels on {channels_to_play} devices")

if channels_to_play == 1:
    # Single device - play mixed audio
    print("\nOnly one USB device - playing mixed audio...")
    mixed_data = np.mean(data, axis=1, keepdims=True)
    sd.play(mixed_data, samplerate=sample_rate, device=available_usb_cards[0]['index'])
    sd.wait()
    print("Done!")
else:
    # Multi-device playback
    print("\nChannel to device mapping:")
    for i in range(channels_to_play):
        print(f"  Channel {i+1} → Card {available_usb_cards[i]['index']}")
    
    # Shared state
    class State:
        position = 0
        finished = False
    
    state = State()
    streams = []
    
    def create_callback(channel_idx):
        def callback(outdata, frames, time_info, status):
            if status:
                print(f"Stream {channel_idx + 1} status: {status}")
            
            start = state.position
            end = min(start + frames, num_samples)
            actual_frames = end - start
            
            if actual_frames > 0:
                outdata[:actual_frames, 0] = data[start:end, channel_idx]
                if actual_frames < frames:
                    outdata[actual_frames:, 0] = 0
                
                if channel_idx == 0:  # Only first stream updates position
                    state.position = end
                    if end >= num_samples:
                        state.finished = True
            else:
                outdata[:] = 0
                state.finished = True
        
        return callback
    
    # Create streams
    print("\nCreating streams...")
    try:
        for i in range(channels_to_play):
            card = available_usb_cards[i]
            print(f"Creating stream {i+1} for card {card['index']}")
            
            stream = sd.OutputStream(
                device=card['index'],
                channels=1,
                samplerate=sample_rate,
                blocksize=BLOCK_SIZE,
                callback=create_callback(i)
            )
            streams.append(stream)
    except Exception as e:
        print(f"Error creating streams: {e}")
        for s in streams:
            s.close()
        exit(1)
    
    # Start playback
    print("\nStarting playback...")
    try:
        for i, stream in enumerate(streams):
            stream.start()
            print(f"Started stream {i+1}")
        
        print("Playing... Press Ctrl+C to stop")
        
        while not state.finished:
            time.sleep(0.1)
            progress = (state.position / num_samples) * 100
            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print("\n\nPlayback complete!")
        
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        for stream in streams:
            stream.stop()
            stream.close()
        print("All streams closed")

print(f"\nLog saved to: {log_file}") 