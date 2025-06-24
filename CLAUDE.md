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