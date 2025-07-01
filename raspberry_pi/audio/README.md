# Audio Module

The audio module provides multi-channel audio playback and device management for the Missing Link installation.

## Overview

This module handles:
- USB audio device enumeration and configuration
- Multi-channel synchronized audio playback
- Channel routing for audio and tone separation
- Real-time channel toggling based on statue connections

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   USB Device 1  │     │   USB Device 2  │     │   USB Device 3  │
│  (EROS)        │     │  (ELEKTRA)      │     │  (SOPHIA)       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ L: Audio Ch 0  │     │ L: Audio Ch 1   │     │ L: Audio Ch 2   │
│ R: Tone 3000Hz │     │ R: Tone 7000Hz  │     │ R: Tone 9500Hz  │
│ In: Detection  │     │ In: Detection   │     │ In: Detection   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Components

### devices.py
- `Statue`: Enum of the 5 statue names
- `configure_devices()`: Main device configuration function
- `get_audio_devices()`: Returns configured audio devices
- `dynConfig`: Global configuration dictionary

### music.py
- `play_audio()`: Simple single-channel playback
- `MultiChannelPlayback`: Base synchronized playback class
- `ToggleableMultiChannelPlayback`: Adds channel enable/disable

### multichannel_audio_demo.py
Interactive demo showing:
- Channel mapping visualization
- Real-time channel toggling
- Progress and status display

## Usage

### Basic Configuration
```python
from audio.devices import configure_devices, Statue

# Configure all connected USB devices
devices = configure_devices()

# Access configuration
for device in devices:
    print(f"{device['statue'].value}: device {device['device_index']}")
```

### Multi-Channel Playback
```python
from audio.music import ToggleableMultiChannelPlayback
import soundfile as sf

# Load multi-channel audio
data, sr = sf.read("6-channel-audio.wav")

# Create playback with devices
playback = ToggleableMultiChannelPlayback(data, sr, devices)
playback.start()

# Toggle channels based on connections
playback.toggle_channel(0)  # Enable EROS
playback.toggle_channel(1)  # Enable ELEKTRA
```

### With Tone Generation
```python
# Create tone generators for each statue
tone_generators = {}
for device in devices:
    statue = device['statue']
    freq = TONE_FREQUENCIES[statue]
    tone_generators[statue] = create_tone_generator(freq, sr)

# Pass to playback for right channel output
playback = ToggleableMultiChannelPlayback(
    data, sr, devices,
    right_channel_callbacks=tone_generators
)
```

## Channel Mapping

The TRS (Tip-Ring-Sleeve) jack mapping:
- **Tip (Left)**: Audio playback channel
- **Ring (Right)**: Tone generation channel
- **Sleeve**: Ground

This allows a single stereo cable to carry both the music audio and the detection tone.

## Dependencies

- `sounddevice`: Audio I/O
- `soundfile`: WAV file reading
- `numpy`: Audio data manipulation

## Testing

Run the interactive demo:
```make audio-demo```

Press number keys 1-5 to toggle channels on/off.