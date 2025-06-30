#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./tone_detect_test.py

import threading
import time
import sys

# Add parent directory to path for imports
sys.path.append('../')

import fastgoertzel as G
import numpy as np
import sounddevice as sd

# Import device configuration from audio module
from audio.devices import USB_ADAPTER, Statue, dynConfig, configure_devices


# TODOs
# How to support multiple detection channels? goertzel is only efficient for a
# limited number of frequencies. The Pi is limited to 4 cores, 1 thread/core.

# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://docs.scipy.org/doc/scipy/reference/signal.html
# https://pypi.org/project/fastgoertzel/
# https://arlpy.readthedocs.io/en/latest/signal.html


AUDIO_JACK = "bcm2835 headphones"

# Audio tones, in Hz (using only first two for EROS and ELEKTRA)
tones_hz = [
    7040,  # A - for EROS
    4699,  # D - for ELEKTRA
]
tone_streams = {}


# Device configuration is now imported from audio.devices module


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

    channel_name = "left" if config["channel"] == 0 else "right"
    print(f"Playing {freq}Hz tone for {statue.value} on device {config['device_index']} ({channel_name} channel)")

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        t = (np.arange(frames) + callback.phase) / config["sample_rate"]
        # Generate sine wave for stereo output with specific channel
        sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)

        # Route to specific channel: 0=left (tip), 1=right (ring)
        if config["channel"] == 0:  # Left channel (TRS tip)
            outdata[:, 0] = sine_wave
            outdata[:, 1] = 0  # Silence right channel
        else:  # Right channel (TRS ring)
            outdata[:, 0] = 0  # Silence left channel
            outdata[:, 1] = sine_wave

        callback.phase = (callback.phase + frames) % config["sample_rate"]

    callback.phase = 0

    # Create and start the output stream
    stream = sd.OutputStream(
        device=config["device_index"],
        channels=2,  # Stereo output (required to route to specific channel)
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
        callback=callback
    )

    tone_streams[statue.value] = stream
    stream.start()
    print(f"✓ Tone stream started for {statue.value} on channel {config['channel']}")


def play_audio(statue, audio_file):
    """Play a WAV file on the audio channel for the specified statue."""
    config = dynConfig[statue.value]["audio"]

    if config["device_index"] == -1:
        print(f"WARNING: No audio device configured for {statue.value}")
        return

    channel_name = "left" if config["channel"] == 0 else "right"
    print(f"Playing audio file for {statue.value} on device {config['device_index']} ({channel_name} channel)")

    try:
        # Load the audio file
        import soundfile as sf
        data, samplerate = sf.read(audio_file)

        # Handle multi-channel files - extract first channel if needed
        if len(data.shape) > 1:
            data = data[:, 0]  # Use first channel

        # Convert to stereo and route to specific channel
        if config["channel"] == 0:  # Left channel (TRS tip)
            stereo_data = np.column_stack([data, np.zeros_like(data)])
        else:  # Right channel (TRS ring)
            stereo_data = np.column_stack([np.zeros_like(data), data])

        # Play with specific channel routing
        sd.play(
            stereo_data,
            samplerate=samplerate,
            device=config["device_index"]
        )
        print(f"✓ Audio playback started for {statue.value} on channel {config['channel']}")

    except ImportError:
        print("WARNING: soundfile library not available, falling back to simple method")
        # Fallback: use sd.play without soundfile (limited format support)
        try:
            # This is a simple fallback - won't work with all file formats
            print("Please install soundfile: pip install soundfile")
        except Exception as e:
            print(f"Error playing audio: {e}")
    except Exception as e:
        print(f"Error playing audio file {audio_file}: {e}")


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
    print("\nStarting audio playback, tone generation and detection...")
    print("Wiring: ELEKTRA output → EROS input")

    # First, play audio on EROS (left channel)
    # Use a sample audio file from the project
    import os
    audio_file = "../../audio_files/Missing Link unSCruz active 01 Remi Wolf Polo Pan Hello.wav"
    if os.path.exists(audio_file):
        print("Starting EROS audio playback...")
        play_audio(Statue.EROS, audio_file)
        time.sleep(1)  # Give audio time to start

    # ELEKTRA plays its tone (right channel)
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
    
    # Set tone frequencies after device configuration
    dynConfig[Statue.EROS.value]["tone_freq"] = tones_hz[0]  # 7040 Hz
    dynConfig[Statue.ELEKTRA.value]["tone_freq"] = tones_hz[1]  # 4699 Hz
    
    if dynConfig["debug"]:
        print(f"\nTone frequencies configured:")
        print(f"  EROS: {dynConfig[Statue.EROS.value]['tone_freq']}Hz")
        print(f"  ELEKTRA: {dynConfig[Statue.ELEKTRA.value]['tone_freq']}Hz")

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
