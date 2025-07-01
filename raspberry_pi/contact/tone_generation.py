"""Tone generation utilities for contact detection.

This module provides functions for generating sine wave tones
used in the contact detection system.
"""

import numpy as np


def create_tone_generator(frequency, sample_rate):
    """Create a tone generator closure for the given frequency.
    
    Args:
        frequency: Frequency in Hz of the tone to generate
        sample_rate: Sample rate in Hz for audio generation
        
    Returns:
        A function that generates tone samples when called with frame count
    """
    phase = 0

    def generate_tone(frames):
        nonlocal phase
        t = (np.arange(frames) + phase) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        # Update phase for continuity
        phase = (phase + frames) % int(sample_rate / frequency)
        return tone

    return generate_tone