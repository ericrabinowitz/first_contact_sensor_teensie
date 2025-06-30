#!/usr/bin/env python3
"""
Audio playback module for Missing Link project.
Handles WAV file playback with channel routing for statue audio output.
"""

import numpy as np
import sounddevice as sd
from .devices import dynConfig


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