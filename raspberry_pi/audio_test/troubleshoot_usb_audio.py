#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice"]
# ///

# Troubleshoot USB audio devices on Raspberry Pi

import json
import subprocess
import sounddevice as sd

print("USB Audio Device Troubleshooting")
print("=" * 40)

# 1. Check system USB devices
print("\n1. Checking USB devices (lsusb):")
print("-" * 30)
try:
    result = subprocess.run(['lsusb'], capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"Error running lsusb: {e}")

# 2. Check ALSA cards
print("\n2. Checking ALSA sound cards (aplay -l):")
print("-" * 30)
try:
    result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"Error running aplay -l: {e}")

# 3. Check ALSA PCMs
print("\n3. Checking ALSA PCMs (aplay -L):")
print("-" * 30)
try:
    result = subprocess.run(['aplay', '-L'], capture_output=True, text=True, env={'LANG': 'C'})
    # Only show hw: devices to reduce clutter
    lines = result.stdout.split('\n')
    for line in lines:
        if line.startswith('hw:') or line.strip() == '':
            print(line)
except Exception as e:
    print(f"Error running aplay -L: {e}")

# 4. Check /proc/asound/cards
print("\n4. Checking /proc/asound/cards:")
print("-" * 30)
try:
    with open('/proc/asound/cards', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading /proc/asound/cards: {e}")

# 5. Check sounddevice devices
print("\n5. Checking sounddevice devices:")
print("-" * 30)
devices = sd.query_devices()
print(json.dumps(devices, indent=2))

# 6. Look for hw: devices specifically
print("\n6. Looking for hardware devices:")
print("-" * 30)
for i, device in enumerate(devices):
    name = device.get('name', '')
    if 'hw:' in name or 'usb' in name.lower() or 'USB' in name:
        print(f"Device {i}: {name}")
        print(f"  Input channels: {device['max_input_channels']}")
        print(f"  Output channels: {device['max_output_channels']}")

# 7. Check audio group membership
print("\n7. Checking audio group membership:")
print("-" * 30)
try:
    result = subprocess.run(['id'], capture_output=True, text=True)
    print(result.stdout)
    if 'audio' not in result.stdout:
        print("WARNING: User is not in 'audio' group!")
        print("Run: sudo usermod -a -G audio $USER")
        print("Then logout and login again.")
except Exception as e:
    print(f"Error checking groups: {e}")

print("\n" + "=" * 40)
print("Troubleshooting complete.") 