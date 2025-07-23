"""Configuration constants for contact detection system.

This module contains tone frequencies and other configuration
parameters used throughout the contact detection system.
"""

from audio.devices import Statue

# Frequencies from frequency_sweep_20250630_152512.log
# All achieved 100% detection with good SNR despite cable losses
TONE_FREQUENCIES = {
    Statue.EROS: 10000,      # 100% detection, 33.8dB SNR, 1.5dB cable loss
    Statue.ELEKTRA: 8500,   # Avoiding problematic 5639Hz, good spacing from neighbors
    Statue.SOPHIA: 9500,    # 100% detection, 33.3dB SNR, 4.8dB cable loss
    Statue.ULTIMO: 13500,   # 100% detection, 36.2dB SNR, 6.8dB cable loss
    Statue.ARIEL: 19500,    # 100% detection, 36.4dB SNR, 9.8dB cable loss
}

# Audio output device
AUDIO_JACK = "bcm2835 headphones"

# Default audio file for multi-channel playback
DEFAULT_AUDIO_FILE = "../../audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"
