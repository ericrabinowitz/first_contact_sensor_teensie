# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Missing Link art project involves life-sized statues that light up and play music when humans form a chain between statue pairs. The system uses a distributed architecture with multiple platforms:

- **Teensy 4.1**: Contact sensing, audio playback, and MQTT communication
- **Raspberry Pi**: Central orchestration with DHCP, DNS, MQTT broker, and controller script
- **QuinLED boards**: LED light effects via WLED software

## Development Commands

### Raspberry Pi Setup
```bash
# Initial setup (run on fresh Pi image with username=pi, hostname=rpi)
ssh pi@rpi.local
sudo apt install -y git
cd ~
git clone https://github.com/ericrabinowitz/first_contact_sensor_teensie.git
cd ~/first_contact_sensor_teensie/raspberry_pi/setup
./setup.sh

# Update existing installation
cd ~/first_contact_sensor_teensie/raspberry_pi/setup
git pull
./setup.sh
```

### Controller Script (Python)
```bash
# Run controller script directly
cd ~/first_contact_sensor_teensie/raspberry_pi/controller
./controller.py

# Service management (custom aliases)
controller.status
controller.logs
controller.restart
```

### Service Management
```bash
# Check service status
NetworkManager.status
mosquitto.status
dnsmasq.status

# View logs
NetworkManager.logs
mosquitto.logs
dnsmasq.logs
```

### Testing & Debugging
```bash
# Controller API endpoints
curl http://192.168.4.1:8080/info
curl http://192.168.4.1:8080/config
curl -H "Content-Type: application/json" -X POST http://192.168.4.1:8080/touch -d '{"action":"link", "statues":["eros","elektra"]}'

# MQTT testing
mosquitto_sub -t "missing_link/touch"
mosquito_pub -t "missing_link/haptic" -m '{"statue":"eros"}'

# Audio testing
aplay ~/first_contact_sensor_teensie/audio_files/"Missing Link unSCruz active 1 Remi Wolf Polo Pan Hello.wav"
```

## Architecture

### Teensy 4.1 (Arduino)
- **Main file**: `teensy/FirstContact_controller/FirstContact_controller.ino`
- **Modules**: AudioSense, Display, MusicPlayer, Networking, Haptics, Lights
- **Libraries**: QNEthernet, PubSubClient, Adafruit GFX/SSD1306, Audio Shield
- **Hardware**: Audio Shield, SSD1306 OLED, Ethernet, haptic motors

### Raspberry Pi Controller
- **Main file**: `raspberry_pi/controller/controller.py`
- **Dependencies**: Uses `uv` with inline script dependencies (deepmerge, just-playback, paho-mqtt)
- **Services**: MQTT broker (mosquitto), DHCP/DNS (dnsmasq), controller script
- **Network**: Acts as 192.168.4.1 gateway with DHCP range 192.168.4.100-200

### Communication Flow
1. Teensy detects contact via sine wave tone detection
2. Publishes to MQTT topic `missing_link/touch` with link/unlink action
3. Pi controller receives MQTT message and orchestrates:
   - Audio playback (active/dormant songs)
   - LED effects via WLED API (`wled/{statue}/api`)
   - Haptic feedback via MQTT (`missing_link/haptic`)

### File Organization
- `/teensy/`: Arduino IDE projects and libraries for Teensy development
- `/raspberry_pi/`: Python controller, setup scripts, and configuration files
- `/quinled/`: WLED configuration documentation
- `/audio_files/`: WAV files for active/dormant statue states
- `/WLED/`: WLED firmware and effects documentation

## Important Notes

- The project uses DHCP with static IP assignments
- All network communication uses the 192.168.4.x subnet
- The Raspberry Pi acts as the central hub for all networking services
- Teensy boards require Arduino IDE with Teensy add-on and specific libraries
- WLED boards are configured via web interface at their assigned IPs
- Audio files are categorized by "active" and "dormant" keywords in filenames

## Code Style Guidelines

### Python
- Use type hints for all function parameters and return values
- Follow PEP 8 style guide (enforced by ruff linter)
- Follow Google Style Guide for Python (https://google.github.io/styleguide/pyguide.html)
- Prefer f-strings over .format() or % formatting
- Use descriptive variable names (e.g., `statue_name` not `sn`)
- Keep functions under 50 lines when possible
- Add comprehensive docstrings to all public functions and classes
- Use `from __future__ import annotations` for forward references when needed

### General
- No trailing whitespace
- Use consistent indentation (4 spaces for Python)
- Line length limit: 100 characters
- Import order: standard library, third-party, local (enforced by ruff)

## Testing

### Quick Tests
```bash
# Run tone detection demo with 2-second timeout
make tone-detect-test

# Test multi-channel audio playback
make audio-test

# Interactive audio demo with channel toggles
make audio-demo

# Frequency sweep test for optimal tone selection
make freq-sweep
```

### Code Quality
```bash
# Run linter
make lint

# Run type checker
make typecheck

# Install dependencies
make lint-install
make typecheck-install
```

### Integration Testing
- Always test with actual hardware before committing
- Test with multiple USB devices connected (up to 5 for full setup)
- Verify tone detection between all statue pairs
- Check audio playback on all channels

## Troubleshooting

### USB Audio Device Issues
- **"Device unavailable" error**: Run `make stop` then retry
- **Check device permissions**: `ls -la /dev/snd/`
- **Verify PortAudio installation**: `make audio-deps`
- **List all audio devices**: `make audio-list`
- **Check detailed audio status**: `make audio-status`

### ALSA Errors
- **"resource busy"**: Another process is using the device
  - Solution: `make kill-all` to stop all Python processes
- **"Invalid number of channels"**: Device doesn't support stereo
  - Check device capabilities with `aplay -l`

### Python Import Errors
- The Makefile sets `PYTHONPATH` automatically
- Never use `sys.path.append()` in code
- All imports should be absolute: `from audio.devices import ...`

## Design Patterns

### Statue Communication
- Each statue has unique tone frequency (defined in `contact/config.py`):
  - EROS: 3000 Hz
  - ELEKTRA: 17000 Hz
  - SOPHIA: 9500 Hz
  - ULTIMO: 13500 Hz
  - ARIEL: 19500 Hz
- Detection is bidirectional (A detects B means B detects A)
- Use `LinkStateTracker` for managing connection states
- Goertzel algorithm for efficient single-frequency detection

### Audio Architecture
- **Stereo channel allocation**:
  - Left channel: WAV file playback (music)
  - Right channel: Sine wave tone generation
- Channels toggle automatically based on link state
- `ToggleableMultiChannelPlayback` manages all audio streams
- Each statue gets its own USB audio device

### Threading Model
- Main thread: UI and coordination
- Detection threads: One per statue for tone detection
- Audio threads: Managed by sounddevice callbacks
- All threads use daemon mode for clean shutdown

## Performance Considerations

- **Goertzel algorithm** is more efficient than FFT for single frequencies
- **Block size**: Use 1024 samples for optimal latency/performance balance
- **Sample rate**: 48000 Hz for better high-frequency response
- **Cable effects**: ~0.5dB attenuation per kHz (important for long cables)
- **Detection threshold**: 0.1 (10% of max signal level)
- **Update rate**: Status display refreshes at 4Hz (every 250ms)

## Hardware Configuration

### USB Audio Devices
- Device 0: Reserved for Raspberry Pi audio jack (bcm2835)
- Devices 1-5: USB audio adapters for statues
- Physical mapping maintained in `audio/devices.py`:
  - Device 1: EROS
  - Device 2: ELEKTRA
  - Device 3: SOPHIA
  - Device 4: ULTIMO
  - Device 5: ARIEL

### Network Setup
- **Raspberry Pi**: Static IP 192.168.4.1
- **DHCP range**: 192.168.4.100-200
- **Services**: dnsmasq (DHCP/DNS), mosquitto (MQTT), controller.py
- **Teensy boards**: Get static DHCP assignments

## MQTT Protocol

### Topics

#### Published by Teensy
- `missing_link/touch`: Contact detection events
  ```json
  {
    "action": "link",    // or "unlink"
    "statues": ["eros", "elektra"]
  }
  ```

#### Subscribed by Teensy
- `missing_link/haptic`: Haptic feedback commands
  ```json
  {
    "statue": "eros"
  }
  ```

#### Published by Controller
- `wled/{statue}/api`: WLED light control commands

## Dependencies

### Python (3.9+)
- **fastgoertzel**: Efficient tone detection algorithm
- **numpy**: Signal processing and array operations
- **sounddevice**: Cross-platform audio I/O
- **soundfile**: Reading WAV files
- **paho-mqtt**: MQTT client library
- **deepmerge**: Configuration merging (controller only)
- **just-playback**: Simple audio playback (controller only)

### System Requirements
- **PortAudio**: Required for sounddevice (`make audio-deps`)
- **ALSA**: Linux audio subsystem
- **USB audio support**: Multiple USB audio devices

## Common Tasks

### Adding a New Statue
1. Add to `Statue` enum in `audio/devices.py`
2. Update `TONE_FREQUENCIES` in `contact/config.py`
3. Add USB device mapping in `configure_devices()`
4. Update display formatting if needed

### Changing Tone Frequencies
1. Run `make freq-sweep` to test new frequencies
2. Update `TONE_FREQUENCIES` in `contact/config.py`
3. Ensure frequencies are non-harmonic (avoid 2:1, 3:2 ratios)
4. Test with all statue pairs

### Debugging Connection Issues
1. Check USB devices: `make audio-list`
2. Run tone detection: `make tone-detect-demo`
3. Monitor detection matrix for signal levels
4. Verify cable connections and lengths

## Production Deployment

### Pre-deployment Checklist
- [ ] Run `make lint` and fix all issues
- [ ] Run `make typecheck` and verify no errors
- [ ] Test all 5 statues with `make tone-detect-demo`
- [ ] Verify WLED integration works
- [ ] Test with production audio files
- [ ] Check service auto-start: `controller.status`

### Production Settings
- Set `dynConfig["debug"] = False` in `audio/devices.py`
- Use production audio files in `/home/pi/audio_files/`
- Ensure all services start on boot
- Monitor logs: `controller.logs`, `mosquitto.logs`

## Future Enhancements

- [ ] Automatic gain control for varying cable lengths
- [ ] Noise gate for better detection in noisy environments
- [ ] Automated test suite for CI/CD
- [ ] Dynamic frequency allocation to avoid interference
- [ ] Recording capability for debugging audio issues

## Memories

- Don't do attribution to claude code