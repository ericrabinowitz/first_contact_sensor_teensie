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
    SOPHIA = "sophia"
    ULTIMO = "ultimo"
    ARIEL = "ariel"


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
# Initialize dynConfig with all statues
dynConfig = {
    "debug": True,
    "block_size": 1024,
    "touch_threshold": 0.1,
}

# Add configuration for each statue
for statue in Statue:
    dynConfig[statue.value] = {
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
    }


def configure_devices(max_devices=None):
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

    if len(usb_devices) == 0:
        print("ERROR: No USB audio devices found")
        return []

    # Limit devices to max_devices if specified
    if max_devices is not None:
        usb_devices = usb_devices[:max_devices]

    print(f"\nFound {len(usb_devices)} USB audio devices")
    print("Channel assignment: Left=Audio, Right=Tone")
    print("TRS Jack mapping: Tip=Left (Ch 0), Ring=Right (Ch 1)")

    # Get list of available statues
    statue_list = list(Statue)
    configured_devices = []

    # Configure each USB device with a statue
    for i, usb_device in enumerate(usb_devices):
        if i >= len(statue_list):
            print(f"WARNING: More USB devices than defined statues. Device {i} skipped.")
            break

        statue = statue_list[i]
        print(f"\nConfiguring {statue.value.upper()} with device {usb_device['index']}: {usb_device['name']}")

        # Configure input if available
        if usb_device["max_input"] > 0:  # Configure input for all devices with input capability
            print(f"  {statue.value} (detect): input channel")
            dynConfig[statue.value]["detect"]["device_index"] = usb_device["index"]
            dynConfig[statue.value]["detect"]["device_id"] = usb_device["device_id"]
            dynConfig[statue.value]["detect"]["sample_rate"] = usb_device["sample_rate"]
            dynConfig[statue.value]["detect"]["device_type"] = usb_device["name"]
            dynConfig[statue.value]["detect"]["channel"] = 1  # mono input

        # Configure output channels
        if usb_device["max_output"] > 0:
            print(f"  {statue.value} (audio): left channel")
            print(f"  {statue.value} (tone): right channel")

            # Audio on left channel (0) - TRS Tip
            dynConfig[statue.value]["audio"]["device_index"] = usb_device["index"]
            dynConfig[statue.value]["audio"]["device_id"] = usb_device["device_id"]
            dynConfig[statue.value]["audio"]["sample_rate"] = usb_device["sample_rate"]
            dynConfig[statue.value]["audio"]["device_type"] = usb_device["name"]
            dynConfig[statue.value]["audio"]["channel"] = 0  # left channel (TRS tip)

            # Tone on right channel (1) - TRS Ring
            dynConfig[statue.value]["tone"]["device_index"] = usb_device["index"]
            dynConfig[statue.value]["tone"]["device_id"] = usb_device["device_id"]
            dynConfig[statue.value]["tone"]["sample_rate"] = usb_device["sample_rate"]
            dynConfig[statue.value]["tone"]["device_type"] = usb_device["name"]
            dynConfig[statue.value]["tone"]["channel"] = 1  # right channel (TRS ring)

            configured_devices.append({
                "statue": statue,
                "device_index": usb_device["index"],
                "sample_rate": usb_device["sample_rate"]
            })

    if dynConfig["debug"]:
        print(f"\nConfiguration summary:")
        print(f"  {len(configured_devices)} devices configured successfully")
        for dev in configured_devices:
            print(f"  {dev['statue'].value}: device {dev['device_index']}")

    return configured_devices


def get_audio_devices():
    """Return a list of configured audio devices with their statue assignments."""
    audio_devices = []

    for statue in Statue:
        config = dynConfig.get(statue.value, {}).get("audio", {})
        if config.get("device_index", -1) != -1:
            audio_devices.append({
                "statue": statue,
                "device_index": config["device_index"],
                "sample_rate": config["sample_rate"],
                "channel": config["channel"]
            })

    return audio_devices