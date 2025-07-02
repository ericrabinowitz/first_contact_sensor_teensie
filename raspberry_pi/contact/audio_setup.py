"""Audio initialization for multi-channel playback with tone generation.

This module handles loading audio files and setting up multi-channel
playback with integrated tone generators for contact detection.
"""

import os
import sys

import soundfile as sf

sys.path.append('../')

from audio.music import ToggleableMultiChannelPlayback

from .config import DEFAULT_AUDIO_FILE, TONE_FREQUENCIES
from .tone_detect import create_tone_generator


def initialize_audio_playback(devices, audio_file=None):
    """Initialize 6-channel audio playback for link detection with tone generation.

    Args:
        devices: List of device configurations from configure_devices()
        audio_file: Optional path to audio file (defaults to DEFAULT_AUDIO_FILE)

    Returns:
        ToggleableMultiChannelPlayback instance or None if initialization fails
    """
    if audio_file is None:
        audio_file = DEFAULT_AUDIO_FILE

    if not os.path.exists(audio_file):
        print(f"\nAudio file not found: {audio_file}")
        print("Continuing without audio playback")
        return None

    try:
        print(f"\nLoading audio: {os.path.basename(audio_file)}")
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"  Duration: {len(audio_data) / sample_rate:.1f} seconds")
        print(f"  Channels: {audio_data.shape[1]}")

        # Create tone generators for right channel of each device
        right_channel_callbacks = {}
        for i, device in enumerate(devices):
            statue = device['statue']
            if statue in TONE_FREQUENCIES:
                freq = TONE_FREQUENCIES[statue]
                device_sample_rate = device.get('sample_rate', sample_rate)
                right_channel_callbacks[i] = create_tone_generator(freq, device_sample_rate)
                print(f"  Created tone generator for {statue.value}: {freq}Hz")

        # Create toggleable playback instance with tone generators
        playback = ToggleableMultiChannelPlayback(
            audio_data, sample_rate, devices,
            right_channel_callbacks=right_channel_callbacks
        )
        playback.start()
        print("  ✓ Audio playback initialized with tone generators")

        return playback

    except Exception as e:
        print(f"Warning: Could not load audio file: {e}")
        print("Continuing without audio playback")
        return None
