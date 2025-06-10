# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

The Missing Link is an interactive art installation with a distributed three-tier architecture:

1. **Teensy 4.1 Controllers** (edge devices) - Contact sensing, local audio, haptic feedback
2. **Raspberry Pi** (central hub) - Network services, MQTT broker, orchestration  
3. **QuinLED boards** - LED lighting control via WLED firmware

Communication flows through MQTT messaging on a local network (192.168.4.x) managed by the Raspberry Pi.

## Development Commands

### Raspberry Pi (Primary Development Platform)

```bash
# Initial setup/deployment
cd ~/first_contact_sensor_teensie/raspberry_pi/setup
./setup.sh

# Service management (custom aliases available)
controller.status    # Main controller service status
controller.logs      # View controller logs
mosquitto.status     # MQTT broker status
dnsmasq.status      # DHCP/DNS server status

# Development/debugging
curl http://192.168.4.1:8080/info                    # System info
curl http://192.168.4.1:8080/config                  # Runtime config
curl -H "Content-Type: application/json" -X POST \   # Simulate statue link
  http://192.168.4.1:8080/touch \
  -d '{"action":"link", "statues":["eros","elektra"]}'

# Audio testing
cd raspberry_pi/audio_test
./multi_channel_test_rpi_fixed.py    # Test USB audio devices

# MQTT debugging
mosquitto_sub -t "missing_link/touch"               # Listen for touch events
mosquitto_pub -t "missing_link/haptic" -m '{"statue":"eros"}'  # Send haptic cmd
```

### Teensy Development

**Platform**: Arduino IDE 2.3.4+ with Teensy support
**Target**: Teensy 4.1 board
**Main sketch**: `teensy/FirstContact_controller/FirstContact_controller.ino`

Required libraries:
- QNEthernet v0.31.0 (networking)
- PubSubClient v2.8 (MQTT)
- Adafruit SSD1306/GFX/BusIO (display)

Configuration is managed in `teensy/FirstContact_controller/defines.h`

### QuinLED Configuration

**Setup**: Flash WLED firmware via https://install.quinled.info/dig-octa/
**Config**: Web interface or JSON files in `quinled/` directory
**Integration**: MQTT commands sent from Raspberry Pi controller

## Key Files & Architecture

**Network Infrastructure**:
- `raspberry_pi/setup/dnsmasq.conf` - DHCP/DNS server configuration
- `raspberry_pi/setup/wired_connection_1.nmconnection` - Static IP setup
- Raspberry Pi serves as gateway at 192.168.4.1

**Controller Logic**:
- `raspberry_pi/controller/controller.py` - Main orchestration script (UV-managed Python)
- `teensy/FirstContact_controller/` - Modular Teensy code split by function
- Communication via MQTT topics: `missing_link/touch`, `missing_link/haptic`

**Audio System**:
- Source files in `audio_files/` (WAV format)
- Teensy: Local SD card playback
- Raspberry Pi: Multi-channel USB audio via ALSA
- Files copied to ramdisk `/run/audio_files` for performance

**Contact Detection**:
- Sine wave transmission through sculpture hands
- Tone detection using PJRC Audio Library
- Human chain detection triggers coordinated lighting/audio response

## Testing Framework

**Primary Test Suite**: `raspberry_pi/audio_test/multi_channel_test_rpi_fixed.py`
- USB audio device enumeration and compatibility
- Multi-channel synchronized playback testing
- ALSA integration validation

**Component Tests**:
- `raspberry_pi/mqtt_test/` - MQTT broker communication
- `raspberry_pi/tone_detect_test/` - Audio signal processing
- `raspberry_pi/audio_test/test_usb_devices.py` - Hardware detection

## Development Notes

**Python Environment**: Uses UV package manager with inline script dependencies (modern Python packaging)

**Service Architecture**: systemd-managed services with custom bash aliases for operations

**Network Topology**: Closed-loop network with Raspberry Pi as DHCP server and internet gateway

**Audio Coordination**: Central controller manages multi-statue audio synchronization and statue-specific dormant/active audio states