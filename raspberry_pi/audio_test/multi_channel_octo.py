#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "soundfile", "numpy"]
# ///

# Multi-channel playback for Audio Injector OCTO

import numpy as np
import sounddevice as sd
import soundfile as sf
import sys
import os

AUDIO_FILE = "Missing Link Playa 1 - 6 Channel 6-7.wav"
AUDIO_DIRS = [
    "/home/pi/first_contact/audio_files",
    "/run/audio_files",
    "~/workspace/first_contact_sensor_teensie/audio_files"
]
OCTO_DEVICE = 2  # OCTO is card 2
BLOCK_SIZE = 2048

print("Multi-Channel Playback on Audio Injector OCTO")
print("=" * 50)

# Find the audio file
audio_path = None
for dir_path in AUDIO_DIRS:
    full_path = os.path.expanduser(os.path.join(dir_path, AUDIO_FILE))
    if os.path.exists(full_path):
        audio_path = full_path
        break

if not audio_path:
    print(f"ERROR: Could not find {AUDIO_FILE}")
    print("Searched in:", AUDIO_DIRS)
    sys.exit(1)

# Check OCTO device
print("\nChecking Audio Injector OCTO...")
try:
    info = sd.query_devices(OCTO_DEVICE)
    print(f"✓ Found: {info['name']}")
    print(f"  Output channels: {info['max_output_channels']}")
    print(f"  Sample rate: {info['default_samplerate']} Hz")
except Exception as e:
    print(f"✗ OCTO not found at device index {OCTO_DEVICE}")
    print(f"Error: {e}")
    print("\nAvailable devices:")
    print(sd.query_devices())
    sys.exit(1)

# Load audio file
print(f"\nLoading: {audio_path}")
try:
    data, sample_rate = sf.read(audio_path, always_2d=True)
    num_samples, num_channels = data.shape
    duration = num_samples / sample_rate
    
    print(f"✓ Loaded successfully:")
    print(f"  Channels: {num_channels}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration:.2f} seconds")
    
except Exception as e:
    print(f"Error loading audio: {e}")
    sys.exit(1)

# Prepare 8-channel output (pad with zeros if needed)
if num_channels < 8:
    print(f"\nPadding {num_channels} channels to 8 channels...")
    padding = np.zeros((num_samples, 8 - num_channels))
    data = np.hstack([data, padding])
elif num_channels > 8:
    print(f"\nTrimming {num_channels} channels to 8 channels...")
    data = data[:, :8]

# Convert to float32
data = data.astype(np.float32)

# Option 1: Simple blocking playback
print("\nPlaying on OCTO (blocking)...")
print("Press Ctrl+C to stop")
try:
    sd.play(data, samplerate=sample_rate, device=OCTO_DEVICE)
    sd.wait()
    print("\nPlayback complete!")
except KeyboardInterrupt:
    print("\nStopped by user")
    sd.stop()
except Exception as e:
    print(f"Playback error: {e}")

# Option 2: Non-blocking with callback (commented out)
"""
# For non-blocking playback with progress
class PlaybackState:
    def __init__(self):
        self.position = 0
        self.finished = False

state = PlaybackState()

def callback(outdata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    
    start = state.position
    end = min(start + frames, num_samples)
    actual_frames = end - start
    
    if actual_frames > 0:
        outdata[:actual_frames] = data[start:end]
        if actual_frames < frames:
            outdata[actual_frames:] = 0
        state.position = end
    else:
        outdata[:] = 0
        state.finished = True

print("\nStarting non-blocking playback...")
stream = sd.OutputStream(
    device=OCTO_DEVICE,
    channels=8,
    samplerate=sample_rate,
    blocksize=BLOCK_SIZE,
    callback=callback
)

with stream:
    while not state.finished:
        progress = (state.position / num_samples) * 100
        print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        sd.sleep(100)
    print("\n\nPlayback complete!")
""" 