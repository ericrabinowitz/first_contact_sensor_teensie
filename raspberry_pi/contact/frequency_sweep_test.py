#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile", "matplotlib"]
# ///

"""
Frequency sweep test to empirically determine optimal tone frequencies.
Tests frequencies from 2kHz to 20kHz with emphasis on higher frequencies.
Based on production experience showing 10kHz works well with long cables.
"""

import sys
import time
from collections import defaultdict
from datetime import datetime

import numpy as np

# Add parent directory to path for imports
sys.path.append('../')

import fastgoertzel as G
import sounddevice as sd

# Import device configuration from audio module
from audio.devices import Statue, configure_devices, dynConfig

# Test frequency ranges focused on higher frequencies
# Based on production statue success at 10kHz with long cables
TEST_FREQUENCIES = [
    # Lower range (2-5kHz) - may have issues with long cables
    2000, 2357, 2700, 3000, 3181, 3500, 3889, 4000, 4231, 4500, 4699, 5000,

    # Mid range (5-8kHz) - transitional zone
    5500, 5639,  # 5639 was problematic
    6000, 6500, 7000, 7040,  # 7040 works well
    7500, 8000, 8192, 8500,

    # Upper range (9-12kHz) - production sweet spot
    9000, 9500, 9871,
    10000, 10079, 10301, 10531, 10789,  # Dense sampling around 10kHz
    11000, 11311, 11500, 12000,

    # High range (12-20kHz) - testing upper limits
    12500, 13000, 13500, 14000, 14500,
    15000, 15500, 16000, 16500, 17000,
    17500, 18000, 18500, 19000, 19500, 20000
]

# Configuration
TONE_DURATION = 3.0  # seconds per frequency
AMPLITUDE = 0.5
SAMPLE_RATE = 48000  # Increased for better high frequency response
BLOCK_SIZE = 1024
DETECTION_THRESHOLD = 0.1

# Results storage
test_results = defaultdict(dict)


class FrequencySweeper:
    """Performs frequency sweep testing with cable length considerations."""

    def __init__(self, output_device, input_device):
        self.output_device = output_device
        self.input_device = input_device
        self.current_freq = None
        self.is_playing = False
        self.phase = 0
        self.results_file = open(f"frequency_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 'w')  # noqa: SIM115

    def log(self, message):
        """Log to console and file."""
        print(message)
        self.results_file.write(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {message}\n")
        self.results_file.flush()

    def play_callback(self, outdata, frames, time_info, status):
        """Audio callback for tone generation."""
        if status:
            self.log(f"Output stream status: {status}")

        if not self.is_playing or self.current_freq is None:
            outdata.fill(0)
            return

        # Generate tone
        t = (np.arange(frames) + self.phase) / SAMPLE_RATE
        sine_wave = AMPLITUDE * np.sin(2 * np.pi * self.current_freq * t)

        # Output to right channel (ring) for tone
        outdata[:, 0] = 0  # Left channel silent
        outdata[:, 1] = sine_wave  # Right channel tone

        self.phase = (self.phase + frames) % SAMPLE_RATE

    def analyze_signal(self, audio_data, freq):
        """Analyze signal quality for a given frequency."""
        # Goertzel detection
        normalized_freq = freq / SAMPLE_RATE
        goertzel_level, _ = G.goertzel(audio_data, normalized_freq)

        # FFT analysis for additional metrics
        fft_data = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/SAMPLE_RATE)
        magnitudes = np.abs(fft_data)

        # Find peak near target frequency
        target_idx = np.argmin(np.abs(freqs - freq))
        window = 10  # bins
        start = max(0, target_idx - window)
        end = min(len(magnitudes), target_idx + window + 1)

        peak_mag = np.max(magnitudes[start:end])
        peak_idx = start + np.argmax(magnitudes[start:end])
        peak_freq = freqs[peak_idx]

        # Calculate SNR (signal-to-noise ratio)
        signal_power = peak_mag ** 2
        # Noise is everything outside the window
        noise_mask = np.ones(len(magnitudes), dtype=bool)
        noise_mask[start:end] = False
        noise_power = np.mean(magnitudes[noise_mask] ** 2)
        snr_db = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 0

        # Calculate frequency accuracy
        freq_error = abs(peak_freq - freq)
        freq_error_percent = (freq_error / freq) * 100

        # Cable attenuation estimate (simplified model)
        # Higher frequencies attenuate more with cable length
        cable_attenuation_db = (freq / 1000) * 0.5  # ~0.5dB per kHz (simplified)

        return {
            'goertzel_level': goertzel_level,
            'peak_magnitude': peak_mag,
            'peak_frequency': peak_freq,
            'frequency_error': freq_error,
            'frequency_error_percent': freq_error_percent,
            'snr_db': snr_db,
            'cable_attenuation_estimate': cable_attenuation_db,
            'detected': goertzel_level > DETECTION_THRESHOLD
        }

    def test_frequency(self, freq):
        """Test a single frequency."""
        self.log(f"\n--- Testing {freq} Hz ---")

        # Start playing tone
        self.current_freq = freq
        self.phase = 0
        self.is_playing = True

        # Wait for tone to stabilize
        time.sleep(0.5)

        # Collect multiple samples
        samples = []
        sample_count = int((TONE_DURATION - 0.5) * SAMPLE_RATE / BLOCK_SIZE)

        with sd.InputStream(device=self.input_device, channels=1,
                           samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE) as stream:
            for i in range(sample_count):
                audio, overflowed = stream.read(BLOCK_SIZE)
                if overflowed:
                    self.log(f"  Input overflow at sample {i}")

                audio_data = audio[:, 0].astype(np.float64)
                result = self.analyze_signal(audio_data, freq)
                samples.append(result)

                # Log every 10th sample
                if i % 10 == 0:
                    self.log(f"  Sample {i}: Goertzel={result['goertzel_level']:.4f}, "
                           f"SNR={result['snr_db']:.1f}dB, "
                           f"Detected={'YES' if result['detected'] else 'NO'}")

        # Stop tone
        self.is_playing = False

        # Aggregate results
        detection_rate = sum(1 for s in samples if s['detected']) / len(samples) * 100
        avg_goertzel = np.mean([s['goertzel_level'] for s in samples])
        avg_snr = np.mean([s['snr_db'] for s in samples])
        avg_freq_error = np.mean([s['frequency_error_percent'] for s in samples])
        avg_cable_atten = np.mean([s['cable_attenuation_estimate'] for s in samples])

        # Store results
        test_results[freq] = {
            'detection_rate': detection_rate,
            'avg_goertzel_level': avg_goertzel,
            'avg_snr_db': avg_snr,
            'avg_freq_error_percent': avg_freq_error,
            'est_cable_attenuation_db': avg_cable_atten,
            'samples': len(samples)
        }

        self.log(f"  Results: Detection={detection_rate:.1f}%, "
               f"Avg Level={avg_goertzel:.4f}, "
               f"Avg SNR={avg_snr:.1f}dB, "
               f"Freq Error={avg_freq_error:.2f}%, "
               f"Est Cable Loss={avg_cable_atten:.1f}dB")

        return test_results[freq]

    def run_sweep(self):
        """Run the complete frequency sweep."""
        self.log("=== Frequency Sweep Test (2-20kHz) ===")
        self.log(f"Testing {len(TEST_FREQUENCIES)} frequencies from {min(TEST_FREQUENCIES)}Hz to {max(TEST_FREQUENCIES)}Hz")
        self.log(f"Sample rate: {SAMPLE_RATE}Hz (Nyquist: {SAMPLE_RATE/2}Hz)")
        self.log(f"Output device: {self.output_device}")
        self.log(f"Input device: {self.input_device}")
        self.log("Physical connection: Ariel (device 5) → Eros (device 1)")
        self.log("Note: Production statues with long cables work best at ~10kHz")

        # Create output stream
        with sd.OutputStream(device=self.output_device, channels=2,
                           samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                           callback=self.play_callback):

            # Test each frequency
            for freq in TEST_FREQUENCIES:
                self.test_frequency(freq)
                time.sleep(0.2)  # Brief pause between frequencies

        self.log("\n=== Sweep Complete ===")
        self.print_summary()

    def print_summary(self):
        """Print summary of results."""
        self.log("\n=== SUMMARY OF RESULTS ===")

        # Sort by detection rate
        sorted_freqs = sorted(test_results.keys(),
                            key=lambda f: test_results[f]['detection_rate'],
                            reverse=True)

        self.log("\nTop 25 frequencies by detection rate:")
        self.log("Freq(Hz)  Detection%  Avg Level   SNR(dB)  Freq Error%  Cable Loss(dB)")
        self.log("-" * 75)

        for _i, freq in enumerate(sorted_freqs[:25]):
            r = test_results[freq]
            self.log(f"{freq:7d}  {r['detection_rate']:9.1f}%  {r['avg_goertzel_level']:9.4f}  "
                   f"{r['avg_snr_db']:7.1f}  {r['avg_freq_error_percent']:10.2f}  "
                   f"{r['est_cable_attenuation_db']:13.1f}")

        # Analyze by frequency ranges
        self.log("\nAnalysis by frequency range:")
        ranges = [
            (2000, 5000, "Low (2-5kHz)"),
            (5000, 8000, "Mid (5-8kHz)"),
            (8000, 12000, "Upper (8-12kHz)"),
            (12000, 20000, "High (12-20kHz)")
        ]

        for start, end, name in ranges:
            range_freqs = [f for f in sorted_freqs if start <= f < end]
            if range_freqs:
                avg_detection = np.mean([test_results[f]['detection_rate'] for f in range_freqs])
                avg_snr = np.mean([test_results[f]['avg_snr_db'] for f in range_freqs])
                self.log(f"  {name}: Avg detection={avg_detection:.1f}%, Avg SNR={avg_snr:.1f}dB")

        # Special frequencies
        self.log("\nKey frequencies:")
        special_freqs = [5639, 7040, 10000, 10079, 10301, 10531, 10789]
        for freq in special_freqs:
            if freq in test_results:
                r = test_results[freq]
                note = ""
                if freq == 5639:
                    note = " (original problematic Ariel)"
                elif freq == 7040:
                    note = " (current working Ariel)"
                elif freq == 10000:
                    note = " (production statue frequency)"
                self.log(f"  {freq}Hz{note}: {r['detection_rate']:.1f}% detection, "
                       f"{r['avg_snr_db']:.1f}dB SNR")

        # Recommended frequencies for 5 statues
        self.log("\nRecommended frequencies for 5 statues (distributed across spectrum):")
        recommended = self.find_optimal_frequencies(5, prefer_high=True)
        statue_names = ["EROS", "ELEKTRA", "SOPHIA", "ULTIMO", "ARIEL"]

        for i, (freq, _score) in enumerate(recommended):
            r = test_results[freq]
            self.log(f"  {statue_names[i]}: {freq}Hz (detection={r['detection_rate']:.1f}%, "
                   f"SNR={r['avg_snr_db']:.1f}dB, cable loss={r['est_cable_attenuation_db']:.1f}dB)")

        # Show frequency separation analysis
        if len(recommended) > 1:
            self.log("\nFrequency separation analysis:")
            freqs = [f for f, _ in recommended]
            for i in range(len(freqs) - 1):
                for j in range(i + 1, len(freqs)):
                    ratio = freqs[j] / freqs[i]
                    separation_percent = (freqs[j] - freqs[i]) / freqs[i] * 100
                    self.log(f"  {freqs[i]}Hz → {freqs[j]}Hz: ratio={ratio:.2f}:1, "
                           f"separation={separation_percent:.1f}%")

    def find_optimal_frequencies(self, count, prefer_high=True):
        """Find optimal non-harmonic frequencies distributed across spectrum."""
        # Filter frequencies with excellent detection and SNR
        excellent_freqs = [(f, test_results[f]) for f in test_results
                          if test_results[f]['detection_rate'] >= 98 and
                          test_results[f]['avg_snr_db'] >= 25]

        # Define zones to ensure frequency distribution
        zones = [
            (2000, 4000, "Low"),
            (4000, 7000, "Mid-Low"),
            (7000, 10000, "Mid"),
            (10000, 14000, "Mid-High"),
            (14000, 20000, "High")
        ]

        selected = []
        zone_counts = {i: 0 for i in range(len(zones))}

        # First pass: Try to get one frequency from each zone
        for zone_idx, (zone_min, zone_max, _zone_name) in enumerate(zones):
            zone_candidates = [(f, r) for f, r in excellent_freqs
                             if zone_min <= f < zone_max]

            if not zone_candidates:
                continue

            # Score candidates (prefer middle of zone and good metrics)
            zone_center = (zone_min + zone_max) / 2
            scored_candidates = []
            for f, r in zone_candidates:
                score = r['detection_rate'] + r['avg_snr_db']
                # Bonus for being near zone center
                center_distance = abs(f - zone_center) / (zone_max - zone_min)
                score += (1 - center_distance) * 10
                # Special bonus for proven frequencies
                if f in [7040, 10000, 10079]:
                    score += 5
                scored_candidates.append((f, score))

            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            # Try candidates until we find one that's non-harmonic
            for freq, score in scored_candidates:
                is_valid = True

                for sel_freq, _ in selected:
                    ratio = max(freq, sel_freq) / min(freq, sel_freq)
                    # Check harmonic ratios and minimum separation
                    if ratio < 1.2 or any(abs(ratio - r) < 0.05
                                         for r in [2.0, 1.5, 1.33, 1.25, 3.0, 4.0, 5.0]):
                        is_valid = False
                        break

                if is_valid:
                    selected.append((freq, score))
                    zone_counts[zone_idx] += 1
                    break

        # Second pass: Fill remaining slots with best frequencies
        if len(selected) < count:
            # Get all candidates not yet selected
            remaining = [(f, r['detection_rate'] + r['avg_snr_db'])
                        for f, r in excellent_freqs
                        if not any(f == sel_f for sel_f, _ in selected)]
            remaining.sort(key=lambda x: x[1], reverse=True)

            for freq, score in remaining:
                is_valid = True

                for sel_freq, _ in selected:
                    ratio = max(freq, sel_freq) / min(freq, sel_freq)
                    if ratio < 1.2 or any(abs(ratio - r) < 0.05
                                         for r in [2.0, 1.5, 1.33, 1.25, 3.0, 4.0, 5.0]):
                        is_valid = False
                        break

                if is_valid:
                    selected.append((freq, score))
                    if len(selected) >= count:
                        break

        # Sort by frequency for consistent assignment
        selected.sort(key=lambda x: x[0])

        return selected

    def close(self):
        """Clean up resources."""
        self.results_file.close()


def main():
    """Run the frequency sweep test."""
    print("=== Frequency Sweep Configuration (2-20kHz) ===")
    print("This test will sweep frequencies from 2kHz to 20kHz")
    print("with emphasis on higher frequencies that work better with long cables")
    print("\nPhysical setup: Ariel (device 5) output → Eros (device 1) input")
    print("\nPress Enter to start the sweep or Ctrl+C to abort...")

    try:
        input()
    except KeyboardInterrupt:
        print("\nAborted")
        return

    # Configure devices
    devices = configure_devices(max_devices=5)
    if len(devices) < 5:
        print(f"ERROR: Need 5 devices configured, found {len(devices)}")
        return

    # Get Ariel output and Eros input devices
    ariel_config = dynConfig[Statue.ARIEL.value]["tone"]
    eros_config = dynConfig[Statue.EROS.value]["detect"]

    if ariel_config["device_index"] == -1:
        print("ERROR: Ariel tone output not configured")
        return
    if eros_config["device_index"] == -1:
        print("ERROR: Eros detection input not configured")
        return

    print("\nUsing devices:")
    print(f"  Output: Ariel on device {ariel_config['device_index']}")
    print(f"  Input: Eros on device {eros_config['device_index']}")

    # Create and run sweeper
    sweeper = FrequencySweeper(
        output_device=ariel_config["device_index"],
        input_device=eros_config["device_index"]
    )

    try:
        sweeper.run_sweep()
    except KeyboardInterrupt:
        print("\n\nSweep interrupted")
        sweeper.print_summary()
    finally:
        sweeper.close()
        print("\nResults saved to frequency_sweep_*.log")


if __name__ == "__main__":
    main()
