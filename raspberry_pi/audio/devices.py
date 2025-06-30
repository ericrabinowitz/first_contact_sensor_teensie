#!/usr/bin/env python3
"""
Audio device configuration module for Missing Link project.
Handles USB audio device detection and configuration for statue connections.
"""

from enum import Enum
import re
import sounddevice as sd


USB_ADAPTER = "usb"  # Match any USB device


class Statue(Enum):
    EROS = "eros"
    ELEKTRA = "elektra"


# ALSA system has a default limit of 32 cards
# A USB host controller can support up to 127 devices, including hubs
# Daisy-chaining can also introduce latency, especially for low-latency devices
# Example channel config:
# {
#     "device_id": "hw:3,0",  # Should map to a particular USB port
#     "device_index": 1,
#     "channel": 0,
#     "sample_rate": 44100.0,
#     "device_type": "usb audio device",
# }
dynConfig = {
    "debug": True,
    "block_size": 1024,
    "touch_threshold": 0.1,
    Statue.EROS.value: {
        "audio": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "detect": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone_freq": -1,  # Hz
    },
    Statue.ELEKTRA.value: {
        "audio": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "detect": {
            "device_id": "",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone_freq": -1,  # Hz
    },
}


def configure_devices():
    devices = sd.query_devices()
    if dynConfig["debug"]:
        print("Available audio devices:")
        for d in devices:
            print(f"  {d['index']}: {d['name']} ({d['max_input_channels']} in, {d['max_output_channels']} out)")

    # Updated pattern for "USB PnP Sound Device: Audio (hw:2,0)" format
    pattern = r'^([^:]*): ([^(]*) \((hw:\d+,\d+)\)$'

    usb_devices = []
    for device in devices:
        match = re.search(pattern, device["name"])
        if match and USB_ADAPTER in device["name"].lower():
            usb_devices.append({
                "index": device["index"],
                "name": device["name"],
                "device_id": match.group(3),
                "max_input": device["max_input_channels"],
                "max_output": device["max_output_channels"],
                "sample_rate": int(device["default_samplerate"])
            })

    if len(usb_devices) < 2:
        print(f"ERROR: Need at least 2 USB devices, found {len(usb_devices)}")
        return False

    print(f"\nFound {len(usb_devices)} USB audio devices")
    print("Configuring devices based on wiring: ELEKTRA output → EROS input")
    print("Channel assignment: Left=Audio, Right=Tone")
    print("TRS Jack mapping: Tip=Left (Ch 0), Ring=Right (Ch 1)")

    # First USB device - EROS uses INPUT for detection, OUTPUT for audio+tone
    eros_device = usb_devices[0]
    if eros_device["max_input"] > 0:
        print(f"  EROS (detect): {eros_device['name']} [device {eros_device['index']}] input")
        dynConfig[Statue.EROS.value]["detect"]["device_index"] = eros_device["index"]
        dynConfig[Statue.EROS.value]["detect"]["device_id"] = eros_device["device_id"]
        dynConfig[Statue.EROS.value]["detect"]["sample_rate"] = eros_device["sample_rate"]
        dynConfig[Statue.EROS.value]["detect"]["device_type"] = eros_device["name"]
        dynConfig[Statue.EROS.value]["detect"]["channel"] = 1  # mono input

    if eros_device["max_output"] > 0:
        print(f"  EROS (audio): {eros_device['name']} [device {eros_device['index']}] left channel")
        print(f"  EROS (tone): {eros_device['name']} [device {eros_device['index']}] right channel")
        # Audio on left channel (0) - TRS Tip
        dynConfig[Statue.EROS.value]["audio"]["device_index"] = eros_device["index"]
        dynConfig[Statue.EROS.value]["audio"]["device_id"] = eros_device["device_id"]
        dynConfig[Statue.EROS.value]["audio"]["sample_rate"] = eros_device["sample_rate"]
        dynConfig[Statue.EROS.value]["audio"]["device_type"] = eros_device["name"]
        dynConfig[Statue.EROS.value]["audio"]["channel"] = 0  # left channel (TRS tip)

        # Tone on right channel (1) - TRS Ring
        dynConfig[Statue.EROS.value]["tone"]["device_index"] = eros_device["index"]
        dynConfig[Statue.EROS.value]["tone"]["device_id"] = eros_device["device_id"]
        dynConfig[Statue.EROS.value]["tone"]["sample_rate"] = eros_device["sample_rate"]
        dynConfig[Statue.EROS.value]["tone"]["device_type"] = eros_device["name"]
        dynConfig[Statue.EROS.value]["tone"]["channel"] = 1  # right channel (TRS ring)

    # Second USB device - ELEKTRA uses OUTPUT for audio+tone
    elektra_device = usb_devices[1]
    if elektra_device["max_output"] > 0:
        print(f"  ELEKTRA (audio): {elektra_device['name']} [device {elektra_device['index']}] left channel")
        print(f"  ELEKTRA (tone): {elektra_device['name']} [device {elektra_device['index']}] right channel")
        # Audio on left channel (0) - TRS Tip
        dynConfig[Statue.ELEKTRA.value]["audio"]["device_index"] = elektra_device["index"]
        dynConfig[Statue.ELEKTRA.value]["audio"]["device_id"] = elektra_device["device_id"]
        dynConfig[Statue.ELEKTRA.value]["audio"]["sample_rate"] = elektra_device["sample_rate"]
        dynConfig[Statue.ELEKTRA.value]["audio"]["device_type"] = elektra_device["name"]
        dynConfig[Statue.ELEKTRA.value]["audio"]["channel"] = 0  # left channel (TRS tip)

        # Tone on right channel (1) - TRS Ring
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_index"] = elektra_device["index"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_id"] = elektra_device["device_id"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["sample_rate"] = elektra_device["sample_rate"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_type"] = elektra_device["name"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["channel"] = 1  # right channel (TRS ring)

    # Note: tone frequencies are set by the calling script
    if dynConfig["debug"]:
        print("\nConfiguration summary:")
        print(f"  Devices configured successfully")
        print(f"  EROS device: {eros_device['index']}")
        print(f"  ELEKTRA device: {elektra_device['index']}")

    return True