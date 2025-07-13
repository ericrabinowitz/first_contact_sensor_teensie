#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

"""Unit tests for basic transmission/detection functionality.

Tests the fundamental tone transmission and detection between connected
EROS and ELEKTRA statues, bypassing coordinator complexity.
"""

import time
import unittest
import numpy as np
import sounddevice as sd
import fastgoertzel as G

from audio.devices import configure_devices, dynConfig, Statue
from contact.audio_setup import initialize_audio_playback
from contact.config import TONE_FREQUENCIES


class TestBasicTransmission(unittest.TestCase):
    """Test basic transmission and detection functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        print("\n=== Setting up Basic Transmission Tests ===")
        
        # Configure devices for 2-statue test
        cls.devices = configure_devices(max_devices=2)
        if len(cls.devices) < 2:
            raise unittest.SkipTest("Need at least 2 devices configured")
        
        print(f"Configured devices: {[dev['statue'].value for dev in cls.devices]}")
        
        # Initialize audio playback (creates tone generators)
        cls.audio_playback = initialize_audio_playback(cls.devices)
        if not cls.audio_playback:
            raise unittest.SkipTest("Failed to initialize audio playback")
        
        # Configure tone frequencies for detection
        for device in cls.devices:
            statue = device['statue']
            if statue in TONE_FREQUENCIES:
                dynConfig[statue.value]["tone_freq"] = TONE_FREQUENCIES[statue]
        
        # Let audio system initialize
        time.sleep(1.0)
        print("✓ Test setup complete\n")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        if hasattr(cls, 'audio_playback') and cls.audio_playback:
            cls.audio_playback.stop()
        print("\n✓ Test cleanup complete")

    def setUp(self):
        """Reset transmission state before each test."""
        # Disable all tone channels for clean test start
        if self.__class__.audio_playback:
            for i in range(len(self.__class__.devices)):
                self.__class__.audio_playback.set_tone_channel(i, False)
        time.sleep(0.1)  # Let system settle

    def test_eros_to_elektra_transmission(self):
        """Test EROS transmitting tone detected by ELEKTRA."""
        print("Testing EROS → ELEKTRA transmission")
        
        result = self._test_single_direction(
            transmitter=Statue.EROS,
            detector=Statue.ELEKTRA
        )
        
        self.assertTrue(result['detected_when_on'], 
                       f"ELEKTRA should detect EROS transmission (level: {result['level_on']:.3f})")
        self.assertFalse(result['false_positive'],
                        f"ELEKTRA should not detect when EROS not transmitting (level: {result['level_off']:.3f})")

    def test_elektra_to_eros_transmission(self):
        """Test ELEKTRA transmitting tone detected by EROS."""
        print("Testing ELEKTRA → EROS transmission")
        
        result = self._test_single_direction(
            transmitter=Statue.ELEKTRA,
            detector=Statue.EROS
        )
        
        self.assertTrue(result['detected_when_on'],
                       f"EROS should detect ELEKTRA transmission (level: {result['level_on']:.3f})")
        self.assertFalse(result['false_positive'],
                        f"EROS should not detect when ELEKTRA not transmitting (level: {result['level_off']:.3f})")

    def test_no_transmission_baseline(self):
        """Test that no signals are detected when nothing transmits."""
        print("Testing baseline with no transmission")
        
        # Explicitly disable all tone channels
        if self.__class__.audio_playback:
            for i in range(len(self.__class__.devices)):
                self.__class__.audio_playback.set_tone_channel(i, False)
        time.sleep(0.1)  # Let system settle
        
        threshold = dynConfig["touch_threshold"]
        
        for device in self.__class__.devices:
            statue = device['statue']
            config = dynConfig[statue.value]["detect"]
            
            if config["device_index"] == -1:
                continue
            
            with self._create_input_stream(config) as stream:
                # Test detection of all frequencies
                for target_statue in [Statue.EROS, Statue.ELEKTRA]:
                    level = self._measure_detection_level(stream, target_statue, config)
                    
                    self.assertLess(level, threshold,
                                   f"{statue.value} should not detect {target_statue.value} "
                                   f"when not transmitting (level: {level:.3f}, threshold: {threshold:.3f})")

    def test_audio_stream_timing(self):
        """Test that audio stream reads take expected time."""
        print("Testing audio stream timing")
        
        # Expected duration for 1024 samples at 48kHz
        expected_duration_ms = (dynConfig["block_size"] / 48000) * 1000  # ~21.33ms
        tolerance_ms = 10.0  # Allow some variation
        
        for device in self.__class__.devices:
            statue = device['statue']
            config = dynConfig[statue.value]["detect"]
            
            if config["device_index"] == -1:
                continue
            
            with self._create_input_stream(config) as stream:
                # Measure several reads to get average timing
                durations = []
                for _ in range(5):
                    start_time = time.time()
                    _audio, overflowed = stream.read(dynConfig["block_size"])
                    duration_ms = (time.time() - start_time) * 1000
                    durations.append(duration_ms)
                    
                    self.assertFalse(overflowed, f"Audio overflow in {statue.value}")
                
                avg_duration = sum(durations) / len(durations)
                print(f"  {statue.value} average read time: {avg_duration:.1f}ms (expected: {expected_duration_ms:.1f}ms)")
                
                # Allow for some timing variation but catch obvious problems
                self.assertGreater(avg_duration, 5.0, 
                                  f"{statue.value} audio reads too fast (avg: {avg_duration:.1f}ms)")
                self.assertLess(avg_duration, expected_duration_ms + tolerance_ms,
                               f"{statue.value} audio reads too slow (avg: {avg_duration:.1f}ms)")

    def _test_single_direction(self, transmitter: Statue, detector: Statue):
        """Test transmission from one statue to another."""
        # Check audio playback is available
        if not self.__class__.audio_playback:
            self.skipTest("Audio playback not available")
        
        # Find detector device config
        detector_device = None
        for dev in self.__class__.devices:
            if dev['statue'] == detector:
                detector_device = dev
                break
        
        self.assertIsNotNone(detector_device, f"Detector {detector.value} not found")
        
        config = dynConfig[detector.value]["detect"]
        self.assertNotEqual(config["device_index"], -1, 
                           f"No input device configured for {detector.value}")
        
        with self._create_input_stream(config) as stream:
            # Get transmitter channel index
            transmitter_channel = self._get_channel_index(transmitter)
            self.assertIsNotNone(transmitter_channel, f"Transmitter {transmitter.value} not found")
            
            # Measure detection with transmission OFF
            print(f"  Phase 1: {transmitter.value} transmission OFF")
            self.__class__.audio_playback.set_tone_channel(transmitter_channel, False)
            time.sleep(0.1)
            
            level_off = self._measure_detection_level(stream, transmitter, config)
            print(f"    Detection level: {level_off:.3f}")
            
            # Measure detection with transmission ON
            print(f"  Phase 2: {transmitter.value} transmission ON")
            self.__class__.audio_playback.set_tone_channel(transmitter_channel, True)
            time.sleep(0.1)
            
            level_on = self._measure_detection_level(stream, transmitter, config)
            print(f"    Detection level: {level_on:.3f}")
            
            # Turn off transmission
            self.__class__.audio_playback.set_tone_channel(transmitter_channel, False)
            
            # Evaluate results
            threshold = dynConfig["touch_threshold"]
            detected_when_on = level_on > threshold
            false_positive = level_off > threshold
            
            print(f"    Threshold: {threshold:.3f}")
            print(f"    Detected when ON: {detected_when_on}")
            print(f"    False positive: {false_positive}")
            
            return {
                'level_on': level_on,
                'level_off': level_off,
                'detected_when_on': detected_when_on,
                'false_positive': false_positive
            }

    def _create_input_stream(self, config):
        """Create and return an input stream for the given config."""
        return sd.InputStream(
            device=config["device_index"],
            channels=1,
            samplerate=config["sample_rate"],
            blocksize=dynConfig["block_size"],
        )

    def _measure_detection_level(self, stream, target_statue: Statue, config):
        """Measure detection level for target statue's frequency."""
        # Read audio
        start_time = time.time()
        audio, overflowed = stream.read(dynConfig["block_size"])
        duration_ms = (time.time() - start_time) * 1000
        
        if overflowed:
            print(f"    WARNING: Audio overflow")
        
        print(f"    Audio read took {duration_ms:.1f}ms")
        
        # Convert to float64 for Goertzel
        audio_data = audio[:, 0].astype(np.float64)
        
        # Get target frequency and perform detection
        freq = dynConfig[target_statue.value]["tone_freq"]
        normalized_freq = freq / config["sample_rate"]
        level, _ = G.goertzel(audio_data, normalized_freq)
        
        return level

    def _get_channel_index(self, statue: Statue):
        """Get the channel index for a given statue."""
        for i, device in enumerate(self.__class__.devices):
            if device['statue'] == statue:
                return i
        return None


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)