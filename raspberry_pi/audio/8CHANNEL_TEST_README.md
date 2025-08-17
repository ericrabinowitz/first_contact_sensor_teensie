# 8-Channel Audio Test for HiFiBerry DAC8x

## Overview
Comprehensive testing suite for 8-channel audio output, designed for the HiFiBerry DAC8x but compatible with any 8+ channel audio device.

## Features
- **Real-time channel control**: Toggle individual channels with keys 1-8
- **Visual VU meters**: See audio levels and peaks for each channel
- **Test signal generation**: Create various test patterns
- **Interactive interface**: Terminal-based UI with live updates
- **Multiple test modes**: Tones, sweep, mixed waveforms

## Quick Start

### 1. List Available Devices
```bash
make 8ch-list
```
This shows all audio devices with 8+ output channels.

### 2. Generate Test Files
```bash
# Generate test tones (different frequency on each channel)
make 8ch-generate-tones

# Generate sweep test (2 seconds per channel sequentially)
make 8ch-generate-sweep

# Generate mixed waveforms (sine, square, sawtooth, noise)
make 8ch-generate-mixed
```

### 3. Run Interactive Test
```bash
make 8ch-test
```

## Interactive Controls
When running the interactive test:
- **1-8**: Toggle individual channels on/off
- **A**: Enable all channels
- **N**: Disable all channels
- **T**: Test sweep (cycle through channels)
- **S**: Save current output to WAV file
- **Q**: Quit

## Visual Interface
```
=== 8-Channel HiFiBerry DAC8x Test ===

Channel Status:                    Level              Peak
------------------------------------------------------------------
[1] EROS     [ON ]  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  65% | 72%
[2] ELEKTRA  [OFF]  ░░░░░░░░░░░░░░░░░░░░   0% |  0%
[3] SOPHIA   [ON ]  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░  92% | 95%
[4] ULTIMO   [ON ]  ▓▓▓▓▓▓░░░░░░░░░░░░░░  33% | 41%
[5] ARIEL    [OFF]  ░░░░░░░░░░░░░░░░░░░░   0% |  0%
[6] TEST_6   [ON ]  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░  58% | 63%
[7] TEST_7   [ON ]  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  83% | 88%
[8] TEST_8   [ON ]  ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  50% | 54%

Active: 6/8 | Progress: 24.3%
```

## Test Frequencies
Each channel plays a specific test tone:
- **Channel 1 (EROS)**: 440 Hz (A4)
- **Channel 2 (ELEKTRA)**: 523.25 Hz (C5)
- **Channel 3 (SOPHIA)**: 659.25 Hz (E5)
- **Channel 4 (ULTIMO)**: 783.99 Hz (G5)
- **Channel 5 (ARIEL)**: 220 Hz (A3)
- **Channel 6 (TEST_6)**: 330 Hz (E4)
- **Channel 7 (TEST_7)**: 392 Hz (G4)
- **Channel 8 (TEST_8)**: 493.88 Hz (B4)

## Command Line Options
```bash
# Play a specific WAV file
./eight_channel_test.py --input your_8ch_file.wav

# Generate with custom duration
./eight_channel_test.py --generate tones --duration 30 --output long_test.wav

# Use specific device
./eight_channel_test.py --device 3

# List devices
./eight_channel_test.py --list-devices
```

## Physical Output Mapping
When using the HiFiBerry DAC8x:
```
OUT1 (RCA White/Red) -> Channel 1 (EROS)
OUT2 (RCA White/Red) -> Channel 2 (ELEKTRA)
OUT3 (RCA White/Red) -> Channel 3 (SOPHIA)
OUT4 (RCA White/Red) -> Channel 4 (ULTIMO)
OUT5 (RCA White/Red) -> Channel 5 (ARIEL)
OUT6 (RCA White/Red) -> Channel 6 (Test/Spare)
OUT7 (RCA White/Red) -> Channel 7 (Test/Spare)
OUT8 (RCA White/Red) -> Channel 8 (Test/Spare)
```

## Troubleshooting

### Device Not Found
If the HiFiBerry isn't detected:
1. Check with `aplay -l` that it's visible to ALSA
2. Verify it's configured properly in `/boot/config.txt`
3. Try specifying device manually with `--device` flag

### Audio Dropouts
- Increase buffer size in the script (change `blocksize=512` to `1024`)
- Check CPU usage during playback
- Ensure no other audio processes are running

### No Sound on Specific Channels
1. Verify physical connections
2. Test with sweep mode (`T` key) to isolate each channel
3. Check amplifier/speaker connections
4. Use oscilloscope or multimeter to verify signal presence

## Integration with Main System
The 8-channel test helps verify:
- All 5 statue channels work correctly
- Spare channels available for future expansion
- No cross-talk between channels
- Proper gain staging for each output
- System can handle simultaneous 8-channel playback