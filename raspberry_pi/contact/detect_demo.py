#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

"""Missing Link Tone Detection Demo (Detection Only)

This script demonstrates only the tone detection system without generation,
showing real-time detection status in a simple table format.
Perfect for testing against external tone sources.
"""

import sys
import threading
import time
from datetime import datetime
from typing import Any, Optional

import fastgoertzel as G
import numpy as np
import sounddevice as sd

from audio.devices import Statue, configure_devices, dynConfig

# Default tone frequencies (copied to avoid import chain)
TONE_FREQUENCIES = {
    Statue.EROS: 3000,
    Statue.ELEKTRA: 17000,
    Statue.SOPHIA: 9500,
    Statue.ULTIMO: 13500,
    Statue.ARIEL: 19500,
}


class SimpleDetectionTracker:
    """Simple tracker for detection metrics without audio control."""

    def __init__(self):
        """Initialize detection tracking."""
        # Track detection levels and SNR for each detector-target pair
        self.detection_metrics = {}
        self.lock = threading.Lock()

        # Initialize metrics for all statue pairs
        for detector in Statue:
            self.detection_metrics[detector] = {}
            for target in Statue:
                if detector != target:
                    self.detection_metrics[detector][target] = {
                        'level': 0.0,
                        'snr': 0.0,
                        'freq': TONE_FREQUENCIES.get(target, 0),
                        'linked': False
                    }

    def update_metrics(self, detector: Statue, target: Statue, level: float, snr: float = 0.0):
        """Update detection metrics for a detector-target pair."""
        with self.lock:
            if detector in self.detection_metrics and target in self.detection_metrics[detector]:
                metrics = self.detection_metrics[detector][target]
                metrics['level'] = level
                metrics['snr'] = snr
                metrics['linked'] = level > dynConfig["touch_threshold"]

    def get_metrics_snapshot(self):
        """Get a thread-safe snapshot of current metrics."""
        with self.lock:
            return {
                detector: {
                    target: metrics.copy()
                    for target, metrics in targets.items()
                }
                for detector, targets in self.detection_metrics.items()
            }


class SimpleTableDisplay:
    """Simple table display for detection metrics."""

    def __init__(self, devices, tracker):
        """Initialize table display."""
        self.devices = devices
        self.tracker = tracker
        self.configured_statues = [dev['statue'] for dev in devices]

    def print_table(self):
        """Print detection status table."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n=== Tone Detection Status ({timestamp}) ===")

        # Header
        print(f"{'DETECTOR':<12} {'TARGET':<12} {'FREQ':<8} {'LEVEL':<8} {'SNR':<10} {'STATUS':<8}")
        print("-" * 70)

        metrics = self.tracker.get_metrics_snapshot()
        active_links = []

        # Print detection data
        for detector_device in self.devices:
            detector = detector_device['statue']

            if detector not in metrics:
                continue

            for target_device in self.devices:
                target = target_device['statue']

                if detector == target:
                    continue

                if target in metrics[detector]:
                    m = metrics[detector][target]
                    status = "LINKED" if m['linked'] else "----"

                    if m['linked']:
                        active_links.append(f"{detector.value} ↔ {target.value}")

                    print(f"{detector.value:<12} {target.value:<12} {m['freq']:<8} "
                          f"{m['level']:<8.3f} {m['snr']:<10.1f}dB {status:<8}")

        # Summary
        threshold = dynConfig["touch_threshold"]
        if active_links:
            print(f"\nActive Links: {', '.join(set(active_links))}")
        else:
            print(f"\nActive Links: None")

        print(f"Threshold: {threshold:.3f}")
        print(f"Total Detections: {len(set(active_links))}")


def detect_tone_simple(statue: Statue, other_statues: list[Statue], tracker: SimpleDetectionTracker,
                      shutdown_event: Optional[threading.Event] = None) -> None:
    """Simplified tone detection function for detection-only demo."""
    config = dynConfig[statue.value]["detect"]

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
        # Check for shutdown signal
        if shutdown_event and shutdown_event.is_set():
            break

        try:
            audio, overflowed = stream.read(dynConfig["block_size"])
            if overflowed:
                print("Input overflow!")

            # Convert to float64 for Goertzel
            audio_data = audio[:, 0].astype(np.float64)

            # Calculate overall signal power for noise estimation
            total_power = np.mean(audio_data ** 2)

            # Check for each other statue's tone
            for s in other_statues:
                freq = dynConfig[s.value]["tone_freq"]
                normalized_freq = freq / config["sample_rate"]
                level, _ = G.goertzel(audio_data, normalized_freq)

                # Simple SNR calculation
                if total_power > 0:
                    snr_db = 10 * np.log10(level / total_power) if level > 0 else -20
                else:
                    snr_db = 0

                # Update tracker
                tracker.update_metrics(statue, s, level, snr_db)

        except KeyboardInterrupt:
            break
        except Exception as e:
            if shutdown_event and shutdown_event.is_set():
                break
            print(f"Error in detection: {e}")

    stream.stop()
    stream.close()


def main() -> int:
    """Main function for detection-only demo."""
    import argparse

    parser = argparse.ArgumentParser(description='Missing Link Tone Detection Demo (Detection Only)')
    parser.add_argument('--timeout', type=int, default=0,
                        help='Auto-exit after N seconds (0 = run forever)')
    parser.add_argument('--interval', type=int, default=0.5,
                        help='Table update interval in seconds (default: 0.5)')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimal output')
    args = parser.parse_args()

    print("=== Missing Link Tone Detection Demo (Detection Only) ===")
    if args.timeout > 0:
        print(f"Will exit after {args.timeout} seconds")
    else:
        print("Press Ctrl+C to stop")
    print(f"Table update interval: {args.interval} seconds")
    print()

    # Configure devices - for detection-only we need input devices
    devices = configure_devices(max_devices=5)

    # For detection demo, we care about detection capability, not output
    # Check which devices have detection configured
    detection_devices = []
    for statue in [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL]:
        if statue.value in dynConfig and dynConfig[statue.value]["detect"]["device_index"] != -1:
            detection_devices.append({
                "statue": statue,
                "device_index": dynConfig[statue.value]["detect"]["device_index"],
                "sample_rate": dynConfig[statue.value]["detect"]["sample_rate"]
            })

    if not detection_devices:
        print("No detection devices configured! Need input-capable USB devices.")
        return 1

    # Use detection devices instead of output devices
    devices = detection_devices

    # Set tone frequencies for all configured devices
    for device in devices:
        statue = device['statue']
        if statue in TONE_FREQUENCIES:
            dynConfig[statue.value]["tone_freq"] = TONE_FREQUENCIES[statue]

    if not args.quiet:
        print("Tone frequencies configured:")
        for device in devices:
            statue = device['statue']
            freq = dynConfig[statue.value].get('tone_freq', -1)
            if freq > 0:
                print(f"  {statue.value.upper()}: {freq}Hz")

    # Create detection tracker and display
    tracker = SimpleDetectionTracker()
    display = SimpleTableDisplay(devices, tracker)

    # Create shutdown event for coordinating thread shutdown
    shutdown_event = threading.Event()

    # Start detection threads
    detection_threads = []
    configured_statues = [dev['statue'] for dev in devices]

    for statue in configured_statues:
        if dynConfig[statue.value]["detect"]["device_index"] != -1:
            # Each statue detects all other statues
            other_statues = [s for s in configured_statues if s != statue]
            if other_statues:
                thread = threading.Thread(
                    target=detect_tone_simple,
                    args=(statue, other_statues, tracker, shutdown_event),
                    daemon=True,
                    name=f"detect_{statue.value}"
                )
                detection_threads.append(thread)
                thread.start()

    print(f"\n{len(detection_threads)} detection thread(s) started")
    print("\nMonitoring for tones from external sources...")

    try:
        start_time = time.time()
        last_update = time.time()

        while True:
            # Print table at specified interval
            if time.time() - last_update >= args.interval:
                display.print_table()
                last_update = time.time()

            # Check timeout
            if args.timeout > 0 and (time.time() - start_time) >= args.timeout:
                print("\nTimeout reached, shutting down...")
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nInterrupted by user...")

    # Cleanup
    print("\nShutting down...")

    # Signal all detection threads to stop
    shutdown_event.set()

    # Wait for detection threads to finish
    for thread in detection_threads:
        thread.join(timeout=1.0)

    time.sleep(0.2)
    print("Done")

    return 0


if __name__ == "__main__":
    sys.exit(main())