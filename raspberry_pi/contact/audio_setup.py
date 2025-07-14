"""Audio initialization for multi-channel playback with tone generation.

This module handles loading audio files and setting up multi-channel
playback with integrated tone generators for contact detection.
"""

import os
import threading

import numpy as np
import soundfile as sf

from audio.music import ToggleableMultiChannelPlayback

from .config import DEFAULT_AUDIO_FILE, TONE_FREQUENCIES
from .tone_detect import create_tone_generator


class DynamicToneGenerator:
    """Dynamic tone generator with real-time frequency updates."""
    
    def __init__(self, initial_frequency: float, sample_rate: int):
        # Store the working tone generator closure
        self.base_generator = create_tone_generator(initial_frequency, sample_rate)
        self.frequency = initial_frequency
        self.sample_rate = sample_rate
        self.lock = threading.Lock()
    
    def set_frequency(self, new_frequency: float):
        """Update frequency by creating a new generator."""
        with self.lock:
            self.frequency = max(500, new_frequency)  # Enforce minimum
            # Create new generator with updated frequency
            self.base_generator = create_tone_generator(self.frequency, self.sample_rate)
    
    def get_frequency(self):
        """Get current frequency."""
        with self.lock:
            return self.frequency
    
    def __call__(self, frames):
        """Generate tone samples using the working generator."""
        with self.lock:
            return self.base_generator(frames)


def initialize_audio_playback(devices, audio_file=None, loop=False):
    """Initialize 6-channel audio playback for link detection with tone generation.

    Args:
        devices: List of device configurations from configure_devices()
        audio_file: Optional path to audio file (defaults to DEFAULT_AUDIO_FILE)
        loop: Whether to loop audio playback (defaults to False)

    Returns:
        tuple: (ToggleableMultiChannelPlayback instance, dict of DynamicToneGenerators)
               Returns (None, {}) if initialization fails
    """
    if audio_file is None:
        audio_file = DEFAULT_AUDIO_FILE

    if not os.path.exists(audio_file):
        print(f"\nAudio file not found: {audio_file}")
        print("Continuing without audio playback")
        return None, {}

    try:
        print(f"\nLoading audio: {os.path.basename(audio_file)}")
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"  Duration: {len(audio_data) / sample_rate:.1f} seconds")
        print(f"  Channels: {audio_data.shape[1]}")

        # Create dynamic tone generators for right channel of each device
        right_channel_callbacks = {}
        dynamic_tone_generators = {}
        for i, device in enumerate(devices):
            statue = device['statue']
            if statue in TONE_FREQUENCIES:
                freq = TONE_FREQUENCIES[statue]
                device_sample_rate = device.get('sample_rate', sample_rate)
                # Create dynamic tone generator
                dynamic_generator = DynamicToneGenerator(freq, device_sample_rate)
                right_channel_callbacks[i] = dynamic_generator
                dynamic_tone_generators[statue] = dynamic_generator
                print(f"  Created dynamic tone generator for {statue.value}: {freq}Hz")

        # Create toggleable playback instance with tone generators
        playback = ToggleableMultiChannelPlayback(
            audio_data, sample_rate, devices,
            right_channel_callbacks=right_channel_callbacks,
            loop=loop
        )
        playback.start()
        print("  ✓ Audio playback initialized with dynamic tone generators")

        return playback, dynamic_tone_generators

    except Exception as e:
        print(f"Warning: Could not load audio file: {e}")
        print("Continuing without audio playback")
        return None, {}
