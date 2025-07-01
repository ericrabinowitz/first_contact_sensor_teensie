"""Tone detection and generation for statue contact sensing.

This module implements the core contact detection system for the Missing Link
installation. Each statue generates a unique sine wave tone and listens for
tones from other statues to detect when humans form a chain between them.

Key Components:
- Tone Generation: Creates continuous sine waves at specific frequencies
- Tone Detection: Uses Goertzel algorithm for efficient frequency detection
- Link Tracking: Updates connection states based on detected tones

The Goertzel Algorithm:
The Goertzel algorithm is a digital signal processing technique that efficiently
detects the presence of a specific frequency in a signal. Unlike FFT which
calculates all frequencies, Goertzel only computes the frequencies of interest,
making it ideal for our single-tone detection needs.

Frequency Selection:
Tones are carefully chosen to be non-harmonic to avoid interference:
- EROS: 3000 Hz
- ELEKTRA: 7000 Hz
- SOPHIA: 9500 Hz
- ULTIMO: 13500 Hz
- ARIEL: 19500 Hz

Detection Thresholds:
- Link established: Signal level > 0.1 (10% of max)
- Link broken: Signal level < 0.1
- SNR typically > 30dB for reliable detection
"""

import sys
import threading
from typing import List, Optional, Callable, TYPE_CHECKING
import numpy as np
import sounddevice as sd
import fastgoertzel as G

sys.path.append('../')

from audio.devices import dynConfig, Statue

if TYPE_CHECKING:
    from .link_state import LinkStateTracker
    from .display import StatusDisplay


def create_tone_generator(frequency: float, sample_rate: int) -> Callable[[int], np.ndarray]:
    """Create a tone generator closure for the given frequency.

    This function returns a closure that maintains phase continuity
    across buffer boundaries, ensuring a smooth continuous sine wave
    without clicks or discontinuities.

    The generated tone has amplitude 0.5 to leave headroom and avoid
    clipping when mixed with other audio.

    Args:
        frequency (float): Frequency in Hz of the tone to generate
        sample_rate (int): Sample rate in Hz for audio generation

    Returns:
        function: A generator function that takes frame count and returns
                 a numpy array of sine wave samples

    Example:
        >>> gen = create_tone_generator(1000, 44100)
        >>> samples = gen(1024)  # Generate 1024 samples
        >>> samples.shape
        (1024,)
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


def detect_tone(statue: Statue, other_statues: List[Statue], link_tracker: 'LinkStateTracker',
                status_display: Optional['StatusDisplay'] = None,
                shutdown_event: Optional[threading.Event] = None) -> None:
    """Detect tones from other statues using the Goertzel algorithm.

    This function runs in a separate thread for each statue, continuously
    monitoring the audio input for tones from other statues. When a tone
    is detected above the threshold, it updates the link state.

    The detection process:
    1. Read audio samples from the input device
    2. Apply Goertzel algorithm to detect each target frequency
    3. Calculate signal-to-noise ratio (SNR) for reliability
    4. Update link state if detection threshold is crossed
    5. Update display metrics for visualization

    Args:
        statue (Statue): The statue doing the detection (detector)
        other_statues (list[Statue]): List of other statues to detect
        link_tracker (LinkStateTracker): Tracks connection states
        status_display (StatusDisplay, optional): Updates UI metrics
        shutdown_event (threading.Event, optional): Signals thread shutdown

    Note:
        This function runs indefinitely until shutdown_event is set or
        an error occurs. It should be run in a daemon thread.
    """
    config = dynConfig[statue.value]["detect"]  # Use detect config, not tone

    if config["device_index"] == -1:
        print(f"WARNING: No input device configured for {statue.value}")
        return

    freqs = [dynConfig[s.value]["tone_freq"] for s in other_statues]
    if not link_tracker.quiet:
        print(f"{statue.value} listening for tones {freqs}Hz on device {config['device_index']}")

    stream = sd.InputStream(
        device=config["device_index"],
        channels=1,  # Mono input
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
    )

    stream.start()
    if not link_tracker.quiet:
        print(f"✓ Detection started for {statue.value}")

    # Track current detection state for each statue
    detection_state = {s: False for s in other_statues}

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

                # Update status display if available
                if status_display:
                    status_display.update_metrics(statue, s, level, snr_db)

                # Determine if currently detected
                currently_detected = level > dynConfig["touch_threshold"]

                # Check if state changed
                if currently_detected != detection_state[s]:
                    detection_state[s] = currently_detected
                    # Update link tracker (handles printing)
                    link_tracker.update_link(statue, s, currently_detected)

        except KeyboardInterrupt:
            break
        except Exception as e:
            if shutdown_event and shutdown_event.is_set():
                # Expected during shutdown
                break
            print(f"Error in detection: {e}")
            break

    try:
        stream.stop()
        stream.close()
    except:
        # Ignore errors during cleanup
        pass

    if not link_tracker.quiet:
        print(f"Detection stopped for {statue.value}")