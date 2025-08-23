#!/usr/bin/env python3
"""Audio channel configuration for Missing Link installation.

This module provides flexible channel mapping configurations to support
different hardware setups, including boards with fewer working channels.

Configuration modes:
- ORIGINAL: Standard 5-channel setup (channels 0-4)
- SPARE_DAC8X: For spare board with channels 0,1,4,5 working
- SINGLE_SPEAKER: All statues on one channel for testing
"""

import os
from typing import Dict
import ultraimport as ui

Statue = ui.ultraimport("__dir__/constants.py", "Statue")


# Channel mapping presets
CHANNEL_MAPPINGS = {
    "ORIGINAL": {
        Statue.EROS: 0,
        Statue.ELEKTRA: 1,
        Statue.SOPHIA: 2,
        Statue.ULTIMO: 3,
        Statue.ARIEL: 4,
    },
    "SPARE_DAC8X": {
        # For spare DAC8x with only channels 0,1,4,5 working
        Statue.EROS: 0,      # Share channel 0
        Statue.ELEKTRA: 0,   # Share channel 0
        Statue.SOPHIA: 1,    # Channel 1
        Statue.ULTIMO: 4,    # Channel 4
        Statue.ARIEL: 5,     # Channel 5
    },
    "SINGLE_SPEAKER": {
        # All statues on channel 0 for testing
        Statue.EROS: 0,
        Statue.ELEKTRA: 0,
        Statue.SOPHIA: 0,
        Statue.ULTIMO: 0,
        Statue.ARIEL: 0,
    }
}


def get_channel_mapping(mode: str = None) -> Dict[Statue, int]:
    """Get the audio channel mapping configuration.
    
    Args:
        mode: Optional mode override. If not provided, reads from
              AUDIO_CHANNEL_MODE environment variable, defaults to "ORIGINAL"
    
    Returns:
        Dictionary mapping Statue enum to physical output channel number
    
    Raises:
        ValueError: If mode is not recognized
    """
    if mode is None:
        mode = os.environ.get("AUDIO_CHANNEL_MODE", "ORIGINAL")
    
    mode = mode.upper()
    if mode not in CHANNEL_MAPPINGS:
        raise ValueError(
            f"Unknown channel mode: {mode}. "
            f"Valid modes: {', '.join(CHANNEL_MAPPINGS.keys())}"
        )
    
    return CHANNEL_MAPPINGS[mode]


def get_channels_for_output(output_channel: int, mode: str = None) -> list[Statue]:
    """Get all statues mapped to a specific output channel.
    
    Args:
        output_channel: Physical output channel number
        mode: Optional mode override
    
    Returns:
        List of Statue enums mapped to this output channel
    """
    mapping = get_channel_mapping(mode)
    return [
        statue for statue, channel in mapping.items()
        if channel == output_channel
    ]


def requires_mixing(mode: str = None) -> bool:
    """Check if the current mode requires audio mixing.
    
    Args:
        mode: Optional mode override
    
    Returns:
        True if any output channel has multiple inputs
    """
    mapping = get_channel_mapping(mode)
    channel_counts = {}
    for channel in mapping.values():
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
    return any(count > 1 for count in channel_counts.values())


def get_mixing_gain(mode: str = None) -> float:
    """Get the gain adjustment for mixing multiple channels.
    
    Args:
        mode: Optional mode override
        
    Returns:
        Gain value to apply when mixing (0.0 to 1.0)
    """
    if not requires_mixing(mode):
        return 1.0
    
    # Use 0.7 gain per channel to prevent clipping when mixing
    return 0.7


def print_configuration(mode: str = None):
    """Print the current channel configuration for debugging."""
    mapping = get_channel_mapping(mode)
    mode_name = mode or os.environ.get("AUDIO_CHANNEL_MODE", "ORIGINAL")
    
    print(f"\nAudio Channel Configuration: {mode_name}")
    print("-" * 40)
    
    # Group by output channel
    outputs = {}
    for statue, channel in mapping.items():
        if channel not in outputs:
            outputs[channel] = []
        outputs[channel].append(statue.value.upper())
    
    for channel in sorted(outputs.keys()):
        statues = outputs[channel]
        if len(statues) > 1:
            print(f"Channel {channel}: {', '.join(statues)} (SHARED)")
        else:
            print(f"Channel {channel}: {statues[0]}")
    
    if requires_mixing(mode):
        print(f"\nMixing enabled with gain: {get_mixing_gain(mode)}")