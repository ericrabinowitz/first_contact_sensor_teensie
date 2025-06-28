#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./tone_detect_test.py

from enum import Enum
import json
import re
import threading
import time

import fastgoertzel as G
import numpy as np
import sounddevice as sd


# TODOs
# How to support multiple detection channels? goertzel is only efficient for a
# limited number of frequencies. The Pi is limited to 4 cores, 1 thread/core.

# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://docs.scipy.org/doc/scipy/reference/signal.html
# https://pypi.org/project/fastgoertzel/
# https://arlpy.readthedocs.io/en/latest/signal.html


USB_ADAPTER = "usb"  # Match any USB device
AUDIO_JACK = "bcm2835 headphones"

# Audio tones, in Hz (using only first two for EROS and ELEKTRA)
tones_hz = [
    7040,  # A - for EROS
    4699,  # D - for ELEKTRA
]
tone_streams = {}


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
    
    # First USB device - use its INPUT for EROS detection
    eros_device = usb_devices[0]
    if eros_device["max_input"] > 0:
        print(f"  EROS (detect): {eros_device['name']} [device {eros_device['index']}]")
        dynConfig[Statue.EROS.value]["detect"]["device_index"] = eros_device["index"]
        dynConfig[Statue.EROS.value]["detect"]["device_id"] = eros_device["device_id"]
        dynConfig[Statue.EROS.value]["detect"]["sample_rate"] = eros_device["sample_rate"]
        dynConfig[Statue.EROS.value]["detect"]["device_type"] = eros_device["name"]
        # Set channel to 1 for mono input (actual channel count set when creating stream)
        dynConfig[Statue.EROS.value]["detect"]["channel"] = 1
    
    # Second USB device - use its OUTPUT for ELEKTRA tone
    elektra_device = usb_devices[1]
    if elektra_device["max_output"] > 0:
        print(f"  ELEKTRA (tone): {elektra_device['name']} [device {elektra_device['index']}]")
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_index"] = elektra_device["index"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_id"] = elektra_device["device_id"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["sample_rate"] = elektra_device["sample_rate"]
        dynConfig[Statue.ELEKTRA.value]["tone"]["device_type"] = elektra_device["name"]
        # Set channel to 2 for stereo output (actual channel count set when creating stream)
        dynConfig[Statue.ELEKTRA.value]["tone"]["channel"] = 2
    
    # Set tone frequencies
    dynConfig[Statue.EROS.value]["tone_freq"] = tones_hz[0]  # 7040 Hz
    dynConfig[Statue.ELEKTRA.value]["tone_freq"] = tones_hz[1]  # 4699 Hz
    
    if dynConfig["debug"]:
        print("\nConfiguration summary:")
        print(f"  EROS will detect {dynConfig[Statue.ELEKTRA.value]['tone_freq']}Hz on device {eros_device['index']}")
        print(f"  ELEKTRA will play {dynConfig[Statue.ELEKTRA.value]['tone_freq']}Hz on device {elektra_device['index']}")
    
    return True


# def play_tone(statue):
#     config = dynConfig[statue.value]["tone"]
#     freq = dynConfig[statue.value]["tone_freq"]
#     print(f"Playing a {freq} Hz tone for the {statue.value} statue")

#     # Generate a time array and sine wave
#     duration = 60  # seconds
#     t = np.linspace(0, duration, int(config["sample_rate"] * duration), False)
#     tone = np.sin(2 * np.pi * freq * t)
#     tone = tone.astype(np.float32)

#     try:
#         sd.play(
#             device=config["device_id"],
#             data=tone,
#             samplerate=config["sample_rate"],
#             mapping=[config["channel"]],
#             blocking=True,
#             loop=True,
#         )
#     except KeyboardInterrupt:
#         sd.stop()
#         print("Playback stopped")
#     except Exception as e:
#         print(e)


def play_tone(statue):
    config = dynConfig[statue.value]["tone"]
    freq = dynConfig[statue.value]["tone_freq"]
    
    if config["device_index"] == -1:
        print(f"WARNING: No output device configured for {statue.value}")
        return
    
    print(f"Playing {freq}Hz tone for {statue.value} on device {config['device_index']}")
    
    def callback(outdata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        t = (np.arange(frames) + callback.phase) / config["sample_rate"]
        # Generate stereo sine wave (same signal on both channels)
        sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)
        outdata[:, 0] = sine_wave  # Left channel
        outdata[:, 1] = sine_wave  # Right channel
        callback.phase = (callback.phase + frames) % config["sample_rate"]
    
    callback.phase = 0
    
    # Create and start the output stream
    stream = sd.OutputStream(
        device=config["device_index"],
        channels=2,  # Stereo output
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
        callback=callback
    )
    
    tone_streams[statue.value] = stream
    stream.start()
    print(f"✓ Tone stream started for {statue.value}")


def detect_tone(statue, other_statues):
    config = dynConfig[statue.value]["detect"]  # Use detect config, not tone
    
    if config["device_index"] == -1:
        print(f"WARNING: No input device configured for {statue.value}")
        return
    
    freqs = [dynConfig[s.value]["tone_freq"] for s in other_statues]
    print(f"{statue.value} listening for tones {freqs}Hz on device {config['device_index']}")
    
    stream = sd.InputStream(
        device=config["device_index"],
        channels=1,  # Mono input
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
    )
    
    stream.start()
    print(f"✓ Detection started for {statue.value}")
    
    # Detect tones using the Goertzel algorithm
    while True:
        try:
            audio, overflowed = stream.read(dynConfig["block_size"])
            if overflowed:
                print("Input overflow!")
            
            # Convert to float64 for Goertzel
            audio_data = audio[:, 0].astype(np.float64)
            
            # Check for each other statue's tone
            for s in other_statues:
                freq = dynConfig[s.value]["tone_freq"]
                normalized_freq = freq / config["sample_rate"]
                level, _ = G.goertzel(audio_data, normalized_freq)
                
                if level > dynConfig["touch_threshold"]:
                    print(f"🔗 Connection detected: {statue.value} ← {s.value} (level: {level:.2f})")
                    time.sleep(0.5)  # Debounce
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in detection: {e}")
            break
    
    stream.stop()
    stream.close()
    print(f"Detection stopped for {statue.value}")


# Play a tone for each statue and detect tones from other statues.
# Based on wiring: ELEKTRA output → EROS input
def play_and_detect_tones():
    print("\nStarting tone generation and detection...")
    print("Wiring: ELEKTRA output → EROS input")
    
    # ELEKTRA plays its tone
    play_tone(Statue.ELEKTRA)
    
    # Small delay to ensure tone is playing
    time.sleep(0.5)
    
    # EROS detects ELEKTRA's tone
    detect_thread = threading.Thread(
        target=detect_tone, 
        args=(Statue.EROS, [Statue.ELEKTRA]), 
        daemon=True
    )
    detect_thread.start()


if __name__ == "__main__":
    print("=== Missing Link Tone Detection Test ===")
    print("Press Ctrl+C to stop\n")
    
    if not configure_devices():
        print("Device configuration failed!")
        exit(1)
    
    play_and_detect_tones()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        # Close all tone streams
        for stream in tone_streams.values():
            stream.stop()
            stream.close()
        time.sleep(0.5)
        print("Done")
