# Contact Detection Module

The contact detection module implements tone-based sensing to detect when humans form chains between statues.

## Overview

This module provides:
- Sine wave tone generation at specific frequencies
- Goertzel algorithm-based tone detection
- Link state tracking between statues
- Real-time terminal status display
- Integration with audio playback system

## How It Works

1. **Tone Generation**: Each statue continuously outputs a unique sine wave tone
2. **Signal Path**: When humans touch two statues, their bodies conduct the signal
3. **Tone Detection**: Statues listen for tones from other statues
4. **Link Tracking**: Detected tones indicate active connections
5. **Audio Response**: Connected statues play synchronized music

## Frequencies

Non-harmonic frequencies chosen to avoid interference:
- EROS: 3000 Hz
- ELEKTRA: 7000 Hz
- SOPHIA: 9500 Hz
- ULTIMO: 13500 Hz
- ARIEL: 19500 Hz

These frequencies were selected based on extensive testing for:
- High detection reliability (>99%)
- Good signal-to-noise ratio (>30dB)
- Minimal cable attenuation
- No harmonic interference

## Components

### tone_detect.py
Core detection and generation functions:
- `create_tone_generator()`: Returns a phase-continuous tone generator
- `detect_tone()`: Runs Goertzel detection in a thread

### link_state.py
Connection state management:
- `LinkStateTracker`: Maintains connection graph
- Automatic audio channel control
- Bidirectional link consistency

### display.py
Terminal UI components:
- `StatusDisplay`: Real-time status visualization
- 2D detection matrix showing all signal levels
- Connection status with visual indicators

### config.py
Configuration constants:
- `TONE_FREQUENCIES`: Frequency assignments
- `AUDIO_JACK`: Channel mapping (Tip/Ring)
- `DEFAULT_AUDIO_FILE`: Demo audio file

### tone_detect_demo.py
Main demonstration script showing full system integration

## Usage

### Running the Demo
```
# Run indefinitely until Ctrl+C
make tone-detect-demo

# With timeout for testing
make tone-detect-test
```

### Programmatic Usage
```python
from contact import (
    TONE_FREQUENCIES,
    LinkStateTracker,
    create_tone_generator,
    detect_tone
)

# Create link tracker
tracker = LinkStateTracker()

# Start detection for a statue
detect_tone(
    statue=Statue.EROS,
    other_statues=[Statue.ELEKTRA, Statue.SOPHIA],
    link_tracker=tracker
)
```

## Detection Algorithm

The Goertzel algorithm efficiently detects single frequencies:

```python
# For each target frequency
goertzel = G.Goertzel(sample_rate, target_freq, block_size)
magnitude = goertzel.filter(audio_data)
power = magnitude ** 2

# Calculate SNR
signal_power = power
noise_power = total_power - signal_power
snr_db = 10 * np.log10(signal_power / noise_power)

# Threshold detection
is_detected = magnitude > threshold
```

## Display Output

```
=== Missing Link Tone Detection ===

CONNECTION STATUS:
eros     [ON]  ━━━━━━━━━━━━  Linked to: elektra
elektra  [ON]  ━━━━━━━━━━━━  Linked to: eros
sophia   [OFF] ────────────  Not linked

TONE DETECTION MATRIX:
  DETECTOR     │   EROS    ELEKTRA  SOPHIA
  (Listening)  │   3000     7000     9500   Hz
  ─────────────────────────────────────────────
  EROS         │    ---     0.152    0.001
  ELEKTRA      │   0.148     ---     0.000
  SOPHIA       │   0.000    0.001     ---
```

## Testing

### Frequency Sweep Test
```bash
./frequency_sweep_test.py
```
Tests a range of frequencies to find optimal values.

### Tone Generation Test
```bash
./tone_test.py --statue eros --duration 5
```
Generates a test tone for verification.

## Troubleshooting

### No Detection
- Check USB device connections
- Verify input gain settings
- Test with tone_test.py
- Check for electrical continuity

### False Positives
- Increase detection threshold
- Check for electrical interference
- Verify frequency separation

### ALSA Errors on Shutdown
- Fixed in current version
- Uses coordinated shutdown with threading.Event

## Dependencies

- `fastgoertzel`: Efficient Goertzel implementation
- `numpy`: Signal processing
- `sounddevice`: Audio I/O
- `soundfile`: Audio file support