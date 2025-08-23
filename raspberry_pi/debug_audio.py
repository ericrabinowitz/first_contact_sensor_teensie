#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice"]
# ///

"""Debug script to check audio device detection."""

import re
import sounddevice as sd

print("Available audio devices:")
devices = sd.query_devices()
print(f"Total devices: {len(devices)}\n")

# Pattern for parsing device names
pattern = r'^([^:]*): ([^(]*) \((hw:\d+,\d+)\)$'

usb_devices = []
for i, d in enumerate(devices):
    print(f"  {i}: {d['name']}")
    print(f"     Inputs: {d['max_input_channels']}, Outputs: {d['max_output_channels']}")
    print(f"     Sample rate: {d['default_samplerate']} Hz")
    
    # Check if it's a USB device
    match = re.search(pattern, d['name'])
    if match and 'usb' in d['name'].lower():
        hw_id = match.group(3)
        usb_devices.append({
            'index': i,
            'name': d['name'],
            'hw_id': hw_id,
            'outputs': d['max_output_channels']
        })
        print(f"     -> USB device detected: {hw_id}")
    print()

print(f"\nFound {len(usb_devices)} USB audio devices:")
for dev in usb_devices:
    print(f"  Device {dev['index']}: {dev['hw_id']} - {dev['name']}")

print("\nExpected mappings:")
expected = {
    "hw:2,0": "EROS",
    "hw:3,0": "ELEKTRA", 
    "hw:4,0": "ARIEL",
    "hw:5,0": "SOPHIA",
    "hw:6,0": "ULTIMO"
}

for hw_id, statue in expected.items():
    found = any(d['hw_id'] == hw_id for d in usb_devices)
    status = "✓" if found else "✗"
    print(f"  {status} {statue}: {hw_id}")