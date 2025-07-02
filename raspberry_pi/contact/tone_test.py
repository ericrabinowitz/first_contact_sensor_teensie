#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice"]
# ///

# Play test tones on detected USB audio devices
# Execute: ./tone_test.py

import re
import time

import numpy as np
import sounddevice as sd


def find_usb_audio_devices():
    """Find all USB audio output devices."""
    devices = sd.query_devices()
    usb_devices = []

    # Pattern for format: "C-Media USB Headphone Set: Audio (hw:2,0)"
    pattern = r'^([^:]*): ([^(]*) \((hw:\d+,\d+)\)$'

    for device in devices:
        match = re.search(pattern, device["name"])
        if match and device["max_output_channels"] > 0:
            device_name = match.group(1).lower()
            match.group(2).lower()
            device_id = match.group(3)

            # Check if it's a USB device
            if "usb" in device_name or "c-media" in device_name:
                usb_devices.append({
                    "index": device["index"],
                    "name": device["name"],
                    "device_id": device_id,
                    "channels": device["max_output_channels"],
                    "sample_rate": int(device["default_samplerate"])
                })

    return usb_devices


def play_tone(device_index, frequency=440, duration=3, sample_rate=44100):
    """Play a sine wave tone on the specified device."""
    print(f"Playing {frequency}Hz tone for {duration} seconds...")

    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Play the tone
    sd.play(tone, samplerate=sample_rate, device=device_index)
    sd.wait()  # Wait until playback is finished


def main():
    print("Detecting USB audio devices...")
    usb_devices = find_usb_audio_devices()

    if not usb_devices:
        print("No USB audio devices found!")
        print("\nAll available devices:")
        print(sd.query_devices())
        return

    print(f"\nFound {len(usb_devices)} USB audio device(s):")
    for i, device in enumerate(usb_devices):
        print(f"{i+1}. {device['name']} (index: {device['index']})")

    # Play test tone on each device
    for device in usb_devices:
        print(f"\nTesting device: {device['name']}")
        try:
            play_tone(
                device_index=device['index'],
                frequency=440,
                duration=2,
                sample_rate=device['sample_rate']
            )
            print("✓ Tone played successfully")
        except Exception as e:
            print(f"✗ Error playing tone: {e}")

        time.sleep(1)  # Brief pause between devices


if __name__ == "__main__":
    main()
