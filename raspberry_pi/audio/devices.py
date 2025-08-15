#!/usr/bin/env python3
"""Audio device configuration for Missing Link statues.

This module handles the detection and configuration of USB audio devices
for the Missing Link art installation. Each statue has a dedicated USB
audio device that handles both audio playback and tone generation.

The Missing Link installation consists of 5 life-sized statues that light up
and play music when humans form a chain between them. Each statue requires:
- USB audio device for sound input/output
- Contact detection via sine wave tones
- Synchronized multi-channel audio playback

Device Configuration:
- Each statue gets one USB audio device (C-Media USB Headphone Set)
- Devices are assigned in enumeration order (first device = EROS, etc.)
- Stereo output channels are split:
  - Left channel (Tip): Audio playback (music)
  - Right channel (Ring): Tone generation for contact detection
- Mono input channel: Tone detection from other statues

Example:
    >>> from audio.devices import configure_devices, Statue
    >>> devices = configure_devices()
    >>> for d in devices:
    ...     print(f"{d['statue'].value}: device {d['device_index']}")
    eros: device 0
    elektra: device 1
    sophia: device 2
    ultimo: device 3
    ariel: device 4
"""

import re
from enum import Enum
from typing import Any, Optional

import sounddevice as sd

USB_ADAPTER: str = "usb"  # Match any USB device


class Statue(Enum):
    """Enumeration of the five Missing Link statues.

    Each statue represents a figure in the art installation and requires
    its own USB audio device for contact sensing and audio playback.
    """

    EROS = "eros"
    ELEKTRA = "elektra"
    SOPHIA = "sophia"
    ULTIMO = "ultimo"
    ARIEL = "ariel"
    CH6 = "ch6"


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
dynConfig: dict[str, Any] = {
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


def configure_hifiberry(device: dict[str, Any]) -> list[dict[str, Any]]:
    """Configure HiFiBerry DAC8x for all 5 statues.
    
    The HiFiBerry DAC8x has 8 output channels, allowing us to assign
    one channel per statue for music playback.
    
    Args:
        device: The HiFiBerry device dictionary from sounddevice
        
    Returns:
        list: Configured devices for all 5 statues
    """
    statue_list = [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, 
                   Statue.ULTIMO, Statue.ARIEL]
    
    configured_devices = []
    sample_rate = int(device["default_samplerate"])
    
    print(f"\nConfiguring HiFiBerry DAC8x with 8 channels")
    print(f"Device: {device['name']}")
    print(f"Sample rate: {sample_rate} Hz")
    print("Channel assignments:")
    
    for i, statue in enumerate(statue_list):
        print(f"  Channel {i}: {statue.value.upper()}")
        
        # Update dynConfig for compatibility
        dynConfig[statue.value]["audio"]["device_index"] = device["index"]
        dynConfig[statue.value]["audio"]["sample_rate"] = sample_rate
        dynConfig[statue.value]["audio"]["channel"] = i
        
        configured_devices.append({
            "statue": statue,
            "device_index": device["index"],
            "sample_rate": sample_rate,
            "channel_index": i,  # Audio file channel (0-4)
            "output_channel": i,  # HiFiBerry output channel (0-4)  
            "device_type": "multi_channel"
        })
    
    return configured_devices


def configure_devices(max_devices: Optional[int] = None) -> list[dict[str, Any]]:
    """Configure audio devices for statue assignments.

    This is the main entry point for device configuration. It:
    1. Enumerates all available audio devices
    2. First checks for HiFiBerry DAC8x (8-channel device)
    3. Falls back to USB audio devices if no HiFiBerry found
    4. Assigns devices/channels to statues

    Music-only configuration (no tone generation):
    - HiFiBerry: Each statue gets one channel (0-4)
    - USB devices: Each statue gets one stereo device

    Args:
        max_devices (int, optional): Limit number of devices configured.
            Useful for testing with fewer than 5 devices.

    Returns:
        list: Configured device dictionaries containing:
            - statue (Statue): The statue enum value
            - device_index (int): PortAudio device index
            - sample_rate (int): Sample rate in Hz
            - channel_index (int): Input audio channel
            - output_channel (int): Output channel (for multi-channel devices)
            - device_type (str): "multi_channel" or "stereo"

    Side Effects:
        Updates the global dynConfig with device assignments
    """
    devices = sd.query_devices()
    if dynConfig["debug"]:
        print("Available audio devices:")
        for d in devices:
            print(
                f"  {d['index']}: {d['name']} ({d['max_input_channels']} in, {d['max_output_channels']} out)"  # noqa: E501
            )

    # First check for HiFiBerry DAC8x
    for device in devices:
        if "hifiberry" in device["name"].lower() and device["max_output_channels"] >= 8:
            print("\nFound HiFiBerry DAC8x!")
            return configure_hifiberry(device)
    
    # Fallback to USB devices
    print("\nNo HiFiBerry DAC8x found, falling back to USB devices...")
    
    # Updated pattern for "USB PnP Sound Device: Audio (hw:2,0)" format
    pattern = r"^([^:]*): ([^(]*) \((hw:\d+,\d+)\)$"

    usb_devices = []
    for device in devices:
        match = re.search(pattern, device["name"])
        if match and USB_ADAPTER in device["name"].lower():
            usb_devices.append(
                {
                    "index": device["index"],
                    "name": device["name"],
                    "device_id": match.group(3),
                    "max_input": device["max_input_channels"],
                    "max_output": device["max_output_channels"],
                    "sample_rate": int(device["default_samplerate"]),
                }
            )

    if len(usb_devices) == 0:
        print("ERROR: No USB audio devices found")
        return []

    # Limit devices to max_devices if specified
    if max_devices is not None:
        usb_devices = usb_devices[:max_devices]

    print(f"\nFound {len(usb_devices)} USB audio devices")
    print("Music-only mode (no tone generation)")

    # Get list of available statues
    statue_list = list(Statue)[:5]  # Only use first 5 statues
    configured_devices = []

    # Configure each USB device with a statue
    for i, usb_device in enumerate(usb_devices):
        if i >= len(statue_list):
            print(
                f"WARNING: More USB devices than defined statues. Device {i} skipped."
            )
            break

        statue = statue_list[i]
        print(
            f"\nConfiguring {statue.value.upper()} with device {usb_device['index']}: {usb_device['name']}"  # noqa: E501
        )

        # Configure output for music only
        if usb_device["max_output"] > 0:
            print(f"  {statue.value}: stereo music output")

            # Update dynConfig for compatibility
            dynConfig[statue.value]["audio"]["device_index"] = usb_device["index"]
            dynConfig[statue.value]["audio"]["device_id"] = usb_device["device_id"]
            dynConfig[statue.value]["audio"]["sample_rate"] = usb_device["sample_rate"]
            dynConfig[statue.value]["audio"]["device_type"] = usb_device["name"]
            dynConfig[statue.value]["audio"]["channel"] = 0  # left channel

            configured_devices.append(
                {
                    "statue": statue,
                    "device_index": usb_device["index"],
                    "sample_rate": usb_device["sample_rate"],
                    "channel_index": i,  # Audio file channel
                    "device_type": "stereo"
                }
            )

    if dynConfig["debug"]:
        print("\nConfiguration summary:")
        print(f"  {len(configured_devices)} devices configured successfully")
        for dev in configured_devices:
            print(f"  {dev['statue'].value}: device {dev['device_index']}")

    return configured_devices


def get_audio_devices() -> list[dict[str, Any]]:
    """Return a list of configured audio devices with their statue assignments.

    This function reads from the global dynConfig to get device assignments
    that were configured by configure_devices().

    Returns:
        list: Audio device configurations, each containing:
            - statue (Statue): The statue enum
            - device_index (int): PortAudio device index
            - sample_rate (int): Sample rate in Hz
            - channel (int): Audio output channel (0=left)

    Note:
        Returns empty list if configure_devices() hasn't been called.
    """
    audio_devices = []

    for statue in Statue:
        statue_config = dynConfig.get(statue.value, {})
        if isinstance(statue_config, dict):
            audio_config = statue_config.get("audio", {})
            if (
                isinstance(audio_config, dict)
                and audio_config.get("device_index", -1) != -1
            ):
                audio_devices.append(
                    {
                        "statue": statue,
                        "device_index": audio_config["device_index"],
                        "sample_rate": audio_config["sample_rate"],
                        "channel": audio_config["channel"],
                    }
                )

    return audio_devices
