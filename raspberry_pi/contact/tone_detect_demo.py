#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

"""Missing Link Tone Detection Demo

This script demonstrates the tone-based contact detection system,
showing real-time connection status and audio playback control.
"""

import select
import sys
import termios
import threading
import time
import tty
from typing import Any, Optional

from audio.devices import Statue, configure_devices, dynConfig

# Import from our contact module
from contact import (
    TONE_FREQUENCIES,
    LinkStateTracker,
    StatusDisplay,
    detect_tone,
    initialize_audio_playback,
)


class FrequencyController:
    """Manages dynamic frequency updates for tone generation and detection."""
    
    def __init__(self, devices, dynamic_tone_generators):
        """Initialize frequency controller."""
        self.devices = devices
        self.dynamic_tone_generators = dynamic_tone_generators
        self.selected_statue_index = 0
        self.lock = threading.RLock()
        
        # Initialize current frequencies from tone generators
        self.current_frequencies = {}
        for statue, generator in dynamic_tone_generators.items():
            self.current_frequencies[statue] = generator.get_frequency()
    
    def get_selected_statue(self):
        """Get currently selected statue."""
        with self.lock:
            if 0 <= self.selected_statue_index < len(self.devices):
                return self.devices[self.selected_statue_index]['statue']
            return None
    
    def navigate_up(self):
        """Move selection up to previous statue."""
        with self.lock:
            if self.selected_statue_index > 0:
                self.selected_statue_index -= 1
    
    def navigate_down(self):
        """Move selection down to next statue."""
        with self.lock:
            if self.selected_statue_index < len(self.devices) - 1:
                self.selected_statue_index += 1
    
    def adjust_frequency(self, delta):
        """Adjust frequency of selected statue by delta Hz."""
        selected_statue = self.get_selected_statue()
        if not selected_statue or selected_statue not in self.dynamic_tone_generators:
            return
            
        with self.lock:
            current_freq = self.current_frequencies[selected_statue]
            new_freq = max(500, min(20000, current_freq + delta))  # Enforce 500-20000Hz range
            
            if new_freq != current_freq:
                # Update tone generator for real-time frequency change
                self.dynamic_tone_generators[selected_statue].set_frequency(new_freq)
                self.current_frequencies[selected_statue] = new_freq
                
                # Update detection frequencies in dynConfig (affects detection threads)
                dynConfig[selected_statue.value]["tone_freq"] = new_freq
    
    def get_current_frequency(self, statue):
        """Get current frequency for a statue."""
        with self.lock:
            return self.current_frequencies.get(statue, 0)


def handle_key_input(key, freq_controller):
    """Handle keyboard input for frequency control."""
    if key == 'q' or key == 'Q' or key == '\x1b':  # ESC key
        return False  # Signal to exit
    elif key == 'w' or key == 'W':  # Up (w key)
        freq_controller.navigate_up()
    elif key == 's' or key == 'S':  # Down (s key)
        freq_controller.navigate_down()
    elif key == 'a' or key == 'A':  # Left (a key)
        freq_controller.adjust_frequency(-500)
    elif key == 'd' or key == 'D':  # Right (d key)
        freq_controller.adjust_frequency(+500)
    return True  # Continue running


def play_and_detect_tones(devices: list[dict[str, Any]], link_tracker: LinkStateTracker,
                          status_display: Optional[StatusDisplay] = None,
                          shutdown_event: Optional[threading.Event] = None) -> list[threading.Thread]:
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
                    args=(statue, other_statues, link_tracker, status_display, shutdown_event),
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

    return detection_threads


def main() -> int:
    """Main function for tone detection demo.

    This function orchestrates the complete demo:
    1. Parse command line arguments
    2. Configure USB audio devices (up to 5 for full installation)
    3. Set up tone frequencies for each statue
    4. Initialize multi-channel audio playback with tone generators
    5. Create link state tracker and status display
    6. Start detection threads for all statues
    7. Run until interrupted or timeout expires
    8. Perform clean shutdown of all components

    The demo requires at least one USB audio device to function.
    With 5 devices, it demonstrates the full 5-statue installation.

    Exit codes:
        0: Success
        1: Configuration or initialization failure
    """
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

    # Initialize audio playback with dynamic tone generators
    audio_playback, dynamic_tone_generators = initialize_audio_playback(devices)

    # Initialize link tracker with audio playback in quiet mode
    link_tracker = LinkStateTracker(audio_playback, quiet=True)

    # Create shutdown event for coordinating thread shutdown
    shutdown_event = threading.Event()

    # Create frequency controller
    freq_controller = FrequencyController(devices, dynamic_tone_generators)
    
    # Create status display with frequency controller
    status_display = StatusDisplay(link_tracker, devices, freq_controller)

    # Start display thread
    display_thread = threading.Thread(target=status_display.run, daemon=True)
    display_thread.start()

    detection_threads = play_and_detect_tones(devices, link_tracker, status_display, shutdown_event)
    
    # Set up terminal for non-blocking input
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        
        print("\n=== Interactive Controls ===")
        print("W/S: Navigate statues | A/D: Adjust frequency (-/+500Hz) | Q/ESC: Quit")
        print("Currently controlling frequencies in real-time...")
        
        start_time = time.time()
        while True:
            # Check for keyboard input (non-blocking)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                if not handle_key_input(key, freq_controller):
                    print("\nExiting due to user input...")
                    break
            
            # Check timeout
            if args.timeout > 0 and (time.time() - start_time) >= args.timeout:
                print("\nTimeout reached, shutting down...")
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user...")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    # Cleanup
    status_display.stop()
    print("\nShutting down...")

    # Signal all detection threads to stop
    shutdown_event.set()

    # Wait for detection threads to finish
    for thread in detection_threads:
        thread.join(timeout=1.0)

    # Now safe to stop audio playback
    if audio_playback:
        audio_playback.stop()
        print("Audio playback stopped")

    time.sleep(0.2)
    print("Done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
