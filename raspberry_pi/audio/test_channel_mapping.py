#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "numpy", "sounddevice", "ultraimport"
# ]
# ///
"""Test utility for verifying audio channel mapping configurations.

This script allows testing different channel mapping modes to ensure
audio is routed correctly to physical outputs. It plays test tones
on each statue channel and reports which physical output is active.

Usage:
    ./test_channel_mapping.py                  # Use default/env mode
    ./test_channel_mapping.py --mode SPARE_DAC8X  # Test specific mode
    ./test_channel_mapping.py --list          # List available modes
"""

import argparse
import os
import sys
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import ultraimport as ui

# Import configuration modules
Statue = ui.ultraimport("__dir__/../config/constants.py", "Statue")
(
    get_channel_mapping,
    print_configuration,
    CHANNEL_MAPPINGS,
    get_mixing_gain,
) = ui.ultraimport(
    "__dir__/../config/audio_config.py",
    ["get_channel_mapping", "print_configuration", "CHANNEL_MAPPINGS", "get_mixing_gain"],
)
configure_devices = ui.ultraimport("__dir__/../audio/devices.py", "configure_devices")


def generate_test_tone(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    """Generate a sine wave test tone.
    
    Args:
        frequency: Tone frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Numpy array containing the tone
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * frequency * t)
    # Apply fade in/out to avoid clicks
    fade_samples = int(0.01 * sample_rate)  # 10ms fade
    tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
    tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return tone * 0.5  # Reduce volume


def test_channel_mapping(mode: Optional[str] = None, duration: float = 2.0):
    """Test audio channel mapping with test tones.
    
    Args:
        mode: Channel mapping mode to test
        duration: Duration of each test tone in seconds
    """
    print("\n" + "=" * 60)
    print("Audio Channel Mapping Test")
    print("=" * 60)
    
    # Print configuration
    print_configuration(mode)
    
    # Configure devices
    print("\nConfiguring audio devices...")
    devices = configure_devices(channel_mode=mode, debug=False)
    
    if not devices:
        print("ERROR: No audio devices found!")
        return 1
    
    # Get device info
    device_index = devices[0]["device_index"]
    sample_rate = devices[0]["sample_rate"]
    device_type = devices[0]["device_type"]
    
    print(f"\nUsing device {device_index} at {sample_rate} Hz")
    print(f"Device type: {device_type}")
    
    # Get channel mapping
    channel_mapping = get_channel_mapping(mode)
    mixing_gain = get_mixing_gain(mode)
    
    # Test tones for each statue
    tone_frequencies = {
        Statue.EROS: 440,      # A4
        Statue.ELEKTRA: 523,   # C5
        Statue.SOPHIA: 659,    # E5
        Statue.ULTIMO: 784,    # G5
        Statue.ARIEL: 880,     # A5
    }
    
    print("\n" + "-" * 60)
    print("Playing test tones for each statue...")
    print("Listen for which physical output is active")
    print("-" * 60)
    
    for statue in [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL]:
        output_channel = channel_mapping[statue]
        frequency = tone_frequencies[statue]
        
        print(f"\n{statue.value.upper()}: Channel {output_channel} - {frequency} Hz tone")
        
        # Check if this channel is shared
        shared_with = [
            s.value.upper() for s, ch in channel_mapping.items()
            if ch == output_channel and s != statue
        ]
        if shared_with:
            print(f"  (Shared with: {', '.join(shared_with)})")
        
        # Generate test tone
        tone = generate_test_tone(frequency, duration, sample_rate)
        
        if device_type == "multi_channel":
            # Multi-channel output (HiFiBerry)
            max_channel = max(channel_mapping.values())
            num_channels = max(8, max_channel + 1)
            
            # Create multi-channel array
            audio = np.zeros((len(tone), num_channels))
            audio[:, output_channel] = tone
            
            # Apply mixing gain if needed
            if shared_with:
                audio[:, output_channel] *= mixing_gain
                print(f"  Applied mixing gain: {mixing_gain}")
        else:
            # Stereo output (USB devices)
            audio = np.zeros((len(tone), 2))
            audio[:, 0] = tone  # Left channel only
        
        # Play the tone
        print("  Playing...", end="", flush=True)
        sd.play(audio, sample_rate, device=device_index)
        sd.wait()
        print(" done")
        
        # Short pause between tones
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
    
    # Test mixed channels if applicable
    mixed_channels = {}
    for statue, channel in channel_mapping.items():
        if channel not in mixed_channels:
            mixed_channels[channel] = []
        mixed_channels[channel].append(statue)
    
    mixed_channels = {ch: statues for ch, statues in mixed_channels.items() if len(statues) > 1}
    
    if mixed_channels:
        print("\nTesting mixed channels...")
        print("-" * 60)
        
        for channel, statues in mixed_channels.items():
            print(f"\nChannel {channel}: Playing all statues simultaneously")
            print(f"  Statues: {', '.join(s.value.upper() for s in statues)}")
            
            # Generate mixed tone
            mixed_tone = np.zeros(int(sample_rate * duration))
            for statue in statues:
                frequency = tone_frequencies[statue]
                tone = generate_test_tone(frequency, duration, sample_rate)
                mixed_tone += tone * mixing_gain
            
            if device_type == "multi_channel":
                audio = np.zeros((len(mixed_tone), num_channels))
                audio[:, channel] = mixed_tone
            else:
                audio = np.zeros((len(mixed_tone), 2))
                audio[:, 0] = mixed_tone
            
            print("  Playing mixed audio...", end="", flush=True)
            sd.play(audio, sample_rate, device=device_index)
            sd.wait()
            print(" done")
    
    return 0


def list_modes():
    """List all available channel mapping modes."""
    print("\nAvailable channel mapping modes:")
    print("-" * 40)
    for mode_name in CHANNEL_MAPPINGS.keys():
        print(f"  {mode_name}")
        if mode_name == "ORIGINAL":
            print("    Standard 5-channel setup (default)")
        elif mode_name == "SPARE_DAC8X":
            print("    For spare board with channels 0,1,4,5")
        elif mode_name == "SINGLE_SPEAKER":
            print("    All statues on channel 0")
    print("\nSet mode with: AUDIO_CHANNEL_MODE=<mode> ./controller.py")


def main():
    parser = argparse.ArgumentParser(
        description="Test audio channel mapping configurations"
    )
    parser.add_argument(
        "--mode",
        choices=list(CHANNEL_MAPPINGS.keys()),
        help="Channel mapping mode to test",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Duration of each test tone in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available channel mapping modes",
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_modes()
        return 0
    
    # Use mode from args or environment
    mode = args.mode
    if mode is None and "AUDIO_CHANNEL_MODE" in os.environ:
        mode = os.environ["AUDIO_CHANNEL_MODE"]
        print(f"Using mode from environment: {mode}")
    
    return test_channel_mapping(mode, args.duration)


if __name__ == "__main__":
    sys.exit(main())