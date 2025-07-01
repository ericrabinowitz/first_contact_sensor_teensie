"""Tone detection functions for contact sensing.

This module provides the core tone detection functionality using
the Goertzel algorithm for efficient single-frequency detection.
"""

import sys
import numpy as np
import sounddevice as sd
import fastgoertzel as G

sys.path.append('../')

from audio.devices import dynConfig


def detect_tone(statue, other_statues, link_tracker, status_display=None):
    """Detect tones from other statues using the Goertzel algorithm.
    
    Args:
        statue: The statue doing the detection (detector)
        other_statues: List of other statues to detect (targets)
        link_tracker: LinkStateTracker instance for updating connections
        status_display: Optional StatusDisplay instance for metrics updates
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
            print(f"Error in detection: {e}")
            break

    stream.stop()
    stream.close()
    if not link_tracker.quiet:
        print(f"Detection stopped for {statue.value}")