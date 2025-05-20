#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./tone_detect_test.py

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


BLOCK_SIZE = 1024
TONE_FREQ = 10000
TOUCH_THRESHOLD = 0.1
USB_ADAPTER = "usb audio device"
AUDIO_JACK = "bcm2835 headphones"

dynConfig = {
    "audio": {
        "device": None,
        "num_channels": None,
        "sample_rate": None,
        "index": None,
    },
    "tone": {
        "device": None,
        "num_channels": None,
        "sample_rate": None,
        "index": None,
    },
    "receive": {
        "device": None,
        "num_channels": None,
        "sample_rate": None,
        "index": None,
    },
}


def detect_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    print(json.dumps(devices, indent=2))

    pattern = r"^([^:]*): - \(hw:(\d+),(\d+)\)$"
    for device in devices:
        match = re.search(pattern, device["name"])
        if not match:
            continue
        device_name = match.group(1)
        device_id = f"hw:{match.group(2)}"
        print(f"Device: {device_name}, ID: {device_id}")

        if device_name.lower() == AUDIO_JACK:
            dynConfig["audio"]["device"] = device_id
            dynConfig["audio"]["num_channels"] = int(device["max_output_channels"])
            dynConfig["audio"]["sample_rate"] = int(device["default_samplerate"])
            dynConfig["audio"]["index"] = int(device["index"])

        if device_name.lower() == USB_ADAPTER:
            dynConfig["tone"]["device"] = device_id
            dynConfig["tone"]["num_channels"] = int(device["max_output_channels"])
            dynConfig["tone"]["sample_rate"] = int(device["default_samplerate"])
            dynConfig["tone"]["index"] = int(device["index"])

        if device_name.lower() == USB_ADAPTER:
            dynConfig["receive"]["device"] = device_id
            dynConfig["receive"]["num_channels"] = int(device["max_input_channels"])
            dynConfig["receive"]["sample_rate"] = int(device["default_samplerate"])
            dynConfig["receive"]["index"] = int(device["index"])


def play_tone():
    print(f"Playing a {TONE_FREQ} Hz tone")

    # Generate a time array and sine wave
    duration = 60  # seconds
    sample_rate = dynConfig["tone"]["sample_rate"]
    device = dynConfig["tone"]["device"]
    # channels = np.arange(1, dynConfig["tone"]["num_channels"] + 1)

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * TONE_FREQ * t)
    tone = tone.astype(np.float32)

    try:
        sd.play(
            device=device,
            data=tone,
            samplerate=sample_rate,
            # mapping=[1],
            blocking=True,
            loop=True,
        )
    except KeyboardInterrupt:
        sd.stop()
        print("Playback stopped")
    except Exception as e:
        print(e)


# def play_tone2():
#     # Generate a 10kHz sine wave
#     t = np.arange(BLOCK_SIZE) / SAMPLE_RATE
#     tone = 0.5 * np.sin(2 * np.pi * TONE_FREQ * t)

#     # Play the tone
#     stream = sd.OutputStream(
#         device=f"hw:{SEND_CHANNEL}",
#         channels=1,
#         samplerate=SAMPLE_RATE,
#         blocksize=BLOCK_SIZE,
#     )
#     stream.start()
#     for _ in range(10):
#         stream.write(tone)
#         time.sleep(BLOCK_SIZE / SAMPLE_RATE)
#     stream.stop()


def detect_tone():
    device = dynConfig["receive"]["device"]
    sample_rate = dynConfig["receive"]["sample_rate"]
    # channels = dynConfig["receive"]["num_channels"]

    stream = sd.InputStream(
        device=device,
        channels=1,
        samplerate=sample_rate,
        blocksize=BLOCK_SIZE,
        latency="low",
        # dtype="float32",
    )
    stream.start()
    while True:
        try:
            audio, _ = stream.read(BLOCK_SIZE)
            channel1 = audio[:, 0].astype(np.float64)
            # Goertzel is cheap for single‑tone detection
            # level = sig.goertzel(audio[:, 0], TONE_FREQ, sample_rate)
            level, _ = G.goertzel(channel1, TONE_FREQ / sample_rate)
            if level > TOUCH_THRESHOLD:
                print(f"Tone detected at {level:.2f}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Tone detection stopped")
            break
        except Exception as e:
            print(e)
            break

    stream.stop()
    stream.close()
    print("Stream stopped")


if __name__ == "__main__":
    detect_devices()

    thread = threading.Thread(target=play_tone, args=(), daemon=True)
    thread.start()

    detect_tone()
