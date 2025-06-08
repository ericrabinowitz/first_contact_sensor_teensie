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


USB_ADAPTER = "usb audio device"
AUDIO_JACK = "bcm2835 headphones"

# Audio tones, in Hz
tones_hz = [
    7902,  # B
    7040,  # A
    6272,  # G
    5588,  # F
    4699,  # D
    4186,  # C
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
        "audio": {
            "device_id": "hw:1,0",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone": {
            "device_id": "hw:1,0",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "detect": {
            "device_id": "hw:1,0",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone_freq": -1,  # Hz
    },
    Statue.ELEKTRA.value: {
        "audio": {
            "device_id": "hw:2,0",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "tone": {
            "device_id": "hw:2,0",
            "device_index": -1,
            "channel": -1,
            "sample_rate": -1,
            "device_type": "",
        },
        "detect": {
            "device_id": "hw:2,0",
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
        print(json.dumps(devices, indent=2))

    pattern = r"^([^:]*): - \((hw:\d+,\d+)\)$"
    statues = [s.value for s in Statue]
    curr_statue_i = 0
    curr_ch_type = "audio"

    print("Processing output channels...")
    for device in devices:
        match = re.search(pattern, device["name"])
        if not match:
            continue
        device_type = match.group(1).lower()
        device_id = match.group(2)
        if dynConfig["debug"]:
            print(f"Device: {device_type}, ID: {device_id}")

        if device_type != USB_ADAPTER:
            # Only allow USB external sound cards for now
            continue

        for ch in range(1, int(device["max_output_channels"]) + 1):
            if curr_statue_i >= len(statues):
                break

            statue = statues[curr_statue_i]
            dynConfig[statue][curr_ch_type]["device_id"] = device_id
            dynConfig[statue][curr_ch_type]["device_index"] = int(device["index"])
            dynConfig[statue][curr_ch_type]["channel"] = ch
            dynConfig[statue][curr_ch_type]["sample_rate"] = int(
                device["default_samplerate"]
            )
            dynConfig[statue][curr_ch_type]["device_type"] = device_type

            if curr_ch_type == "audio":
                curr_ch_type = "tone"
                dynConfig[statue]["tone_freq"] = tones_hz[curr_statue_i]
            else:
                curr_ch_type = "audio"
                curr_statue_i += 1

    print("Processing input channels...")
    curr_ch_type = "detect"
    curr_statue_i = 0
    for device in devices:
        match = re.search(pattern, device["name"])
        if not match:
            continue
        device_type = match.group(1).lower()
        device_id = match.group(2)

        if device_type != USB_ADAPTER:
            # Only allow USB external sound cards for now
            continue

        for ch in range(1, int(device["max_input_channels"]) + 1):
            if curr_statue_i >= len(statues):
                break

            statue = statues[curr_statue_i]
            dynConfig[statue][curr_ch_type]["device_id"] = device_id
            dynConfig[statue][curr_ch_type]["device_index"] = int(device["index"])
            dynConfig[statue][curr_ch_type]["channel"] = ch
            dynConfig[statue][curr_ch_type]["sample_rate"] = int(
                device["default_samplerate"]
            )
            dynConfig[statue][curr_ch_type]["device_type"] = device_type
            curr_statue_i += 1

    if dynConfig["debug"]:
        print("Final dynamic configuration:")
        print(json.dumps(dynConfig, indent=2))


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
    print(f"Playing a {freq} Hz tone for the {statue.value} statue")

    def callback(outdata, frames, time_info, status):
        t = (np.arange(frames) + callback.offset) / config["sample_rate"]
        outdata[:] = 0.5 * np.sin(2 * np.pi * freq * t).reshape(-1, 1)
        callback.offset += frames

    callback.offset = 0

    # Play the tone, non-blocking
    tone_streams[statue.value] = sd.OutputStream(
        device=config["device_id"],
        channels=config["channel"],
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
        # latency="high",
        # dtype="float32",
    )


def detect_tone(statue, other_statues):
    config = dynConfig[statue.value]["tone"]
    freqs = [dynConfig[s.value]["tone_freq"] for s in other_statues]
    print(f"At {statue.value} statue, detect the following tones: {freqs}")

    stream = sd.InputStream(
        device=config["device_id"],
        channels=config["channel"],
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
        # latency="low",
        # dtype="float32",
    )
    stream.start()
    # Detect the tone using the Goertzel algorithm, blocking
    while True:
        try:
            audio, _ = stream.read(dynConfig["block_size"])
            channel1 = audio[:, 0].astype(np.float64)
            # Goertzel is cheap for single‑tone detection
            # level = sig.goertzel(audio[:, 0], TONE_FREQ, sample_rate)
            for s in other_statues:
                freq = dynConfig[s.value]["tone_freq"]
                level, _ = G.goertzel(channel1, freq / config["sample_rate"])
                if level > dynConfig["touch_threshold"]:
                    if dynConfig["debug"]:
                        print(f"Tone ${freq} detected at {level:.2f}")
                    print(f"Connection detected: {statue.value} - {s.value}")
                    time.sleep(0.1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)
            break

    stream.stop()
    tone_streams[statue.value].stop()
    stream.close()
    tone_streams[statue.value].close()
    print(f"Tone detection and playing stopped for {statue.value}")


# Play a tone for each statue and detect tones from other statues.
# Connections are pairwise, self detection is not possible.
def play_and_detect_tones():
    statues = [s for s in Statue]

    # The first statue detects all other tones, doesn't need to play one
    for i in range(1, len(statues)):
        play_tone(statues[i])

    # The last statue is detected by the other statues, doesn't need to detect
    for i in range(len(statues) - 1):
        other_statues = statues[(i + 1) :]
        thread = threading.Thread(
            target=detect_tone, args=(statues[i], other_statues), daemon=True
        )
        thread.start()


if __name__ == "__main__":
    configure_devices()

    play_and_detect_tones()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        time.sleep(0.5)
        print("Done")
