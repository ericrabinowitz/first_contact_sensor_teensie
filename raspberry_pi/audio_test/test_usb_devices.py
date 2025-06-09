#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy"]
# ///

# Test USB audio devices on Raspberry Pi

import numpy as np
import sounddevice as sd
import time

print("Testing USB Audio Devices")
print("=" * 40)

# Generate a test tone
duration = 2.0
sample_rate = 44100
frequency = 440  # A4 note

t = np.linspace(0, duration, int(sample_rate * duration), False)
tone = 0.5 * np.sin(2 * np.pi * frequency * t)

# Test specific hardware devices
test_devices = [
    ("hw:2,0", "C-Media USB Headphone Set"),
    ("hw:3,0", "USB Audio Device"),
    (2, "Card 2 by index"),
    (3, "Card 3 by index"),
    ("plughw:2,0", "C-Media USB Headphone Set (plug)"),
    ("plughw:3,0", "USB Audio Device (plug)")
]

for device_spec, description in test_devices:
    print(f"\nTesting: {description} ({device_spec})")
    try:
        # Query device info
        info = sd.query_devices(device_spec)
        print(f"  Channels: {info['max_output_channels']}")
        print(f"  Sample rate: {info['default_samplerate']}")
        
        # Play test tone
        print(f"  Playing {frequency}Hz tone for {duration} seconds...")
        sd.play(tone, samplerate=sample_rate, device=device_spec)
        sd.wait()
        print("  Success!")
        
        time.sleep(0.5)  # Brief pause between devices
        
    except Exception as e:
        print(f"  Failed: {e}")

print("\nTest complete!") 