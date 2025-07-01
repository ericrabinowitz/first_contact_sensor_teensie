#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

"""Missing Link Tone Detection Demo

This script demonstrates the tone-based contact detection system,
showing real-time connection status and audio playback control.
"""

import threading
import time
import sys

# Add parent directory to path for imports
sys.path.append('../')

from audio.devices import dynConfig, configure_devices

# Import from our contact module
from contact import (
    TONE_FREQUENCIES,
    LinkStateTracker,
    StatusDisplay,
    initialize_audio_playback,
    detect_tone
)


def play_and_detect_tones(devices, link_tracker, status_display=None):
    """
    Start tone generation and detection for all configured statues.
    Each statue plays its unique tone and detects all other statue tones.
    """
    if not link_tracker.quiet:
        print("\nStarting tone generation and detection...")
        print(f"Configured statues: {[dev['statue'].value for dev in devices]}")

    # Get list of configured statues
    configured_statues = [dev['statue'] for dev in devices]

    # Tone generation now handled through audio playback system
    if not link_tracker.quiet:
        print("\nTone generators integrated with audio playback")

    # Small delay to ensure all tones are playing
    time.sleep(0.5)

    # Start detection threads for statues with input capability
    if not link_tracker.quiet:
        print("\nStarting detection threads:")
    detection_threads = []

    for statue in configured_statues:
        if dynConfig[statue.value]["detect"]["device_index"] != -1:
            # Each statue detects all other statues
            other_statues = [s for s in configured_statues if s != statue]
            if other_statues:
                thread = threading.Thread(
                    target=detect_tone,
                    args=(statue, other_statues, link_tracker, status_display),
                    daemon=True,
                    name=f"detect_{statue.value}"
                )
                detection_threads.append(thread)
                thread.start()

    if not link_tracker.quiet:
        print(f"\n{len(detection_threads)} detection thread(s) started")
        print("\nMonitoring for connections... Press Ctrl+C to stop")

        # Print initial status
        time.sleep(1)
        print("\n" + link_tracker.get_link_summary())


def main():
    """Main function for tone detection demo."""
    import argparse

    parser = argparse.ArgumentParser(description='Missing Link Tone Detection Demo')
    parser.add_argument('--timeout', type=int, default=0,
                        help='Auto-exit after N seconds (0 = run forever)')
    args = parser.parse_args()

    print("=== Missing Link Tone Detection Demo ===")
    if args.timeout > 0:
        print(f"Will exit after {args.timeout} seconds")
    else:
        print("Press Ctrl+C to stop")
    print()

    devices = configure_devices(max_devices=5)  # Configure up to 5 devices for all statues
    if not devices:
        print("Device configuration failed!")
        return 1

    # Set tone frequencies for all configured devices
    for device in devices:
        statue = device['statue']
        if statue in TONE_FREQUENCIES:
            dynConfig[statue.value]["tone_freq"] = TONE_FREQUENCIES[statue]

    if dynConfig["debug"]:
        print("\nTone frequencies configured:")
        for device in devices:
            statue = device['statue']
            freq = dynConfig[statue.value].get('tone_freq', -1)
            if freq > 0:
                print(f"  {statue.value.upper()}: {freq}Hz")

    # Initialize audio playback
    audio_playback = initialize_audio_playback(devices)

    # Initialize link tracker with audio playback in quiet mode
    link_tracker = LinkStateTracker(audio_playback, quiet=True)

    # Create status display
    status_display = StatusDisplay(link_tracker, devices)

    # Start display thread
    display_thread = threading.Thread(target=status_display.run, daemon=True)
    display_thread.start()

    play_and_detect_tones(devices, link_tracker, status_display)

    try:
        start_time = time.time()
        while True:
            time.sleep(1)
            # Check timeout
            if args.timeout > 0 and (time.time() - start_time) >= args.timeout:
                print("\nTimeout reached, shutting down...")
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user...")

    # Cleanup
    status_display.stop()
    print("\nShutting down...")
    # Stop audio playback
    if audio_playback:
        audio_playback.stop()
        print("Audio playback stopped")
    time.sleep(0.5)
    print("Done")

    return 0


if __name__ == "__main__":
    sys.exit(main())