#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile", "fastgoertzel"]
# ///

"""Test the new audio_file=None behavior."""

from audio.devices import Statue, configure_devices
from contact.audio_setup import initialize_audio_playback

print("Testing initialize_audio_playback with audio_file=None...")
print("=" * 60)

# Configure real devices
devices = configure_devices(max_devices=2)
if not devices:
    print("No devices found, using mock devices")
    devices = [
        {'statue': Statue.EROS, 'device_index': 0, 'sample_rate': 44100},
        {'statue': Statue.ELEKTRA, 'device_index': 1, 'sample_rate': 44100}
    ]

# Test with None - should create silent audio
print("\nTest 1: audio_file=None (should create silent audio)")
playback, generators = initialize_audio_playback(devices, audio_file=None, duration_seconds=10)

if playback:
    print("\n✓ Success! Playback object created with silent audio")
    print(f"  Generators created: {list(generators.keys())}")
    playback.stop()
else:
    print("\n✗ Failed to create playback object")

print("\n" + "=" * 60)
print("\nTest 2: Non-existent file (should return None)")
playback2, generators2 = initialize_audio_playback(devices, audio_file="/tmp/nonexistent.wav")

if playback2 is None and generators2 == {}:
    print("✓ Correctly returned (None, {}) for missing file")
else:
    print("✗ Should have returned (None, {}) for missing file")
    if playback2:
        playback2.stop()
        
print("\nTests complete!")