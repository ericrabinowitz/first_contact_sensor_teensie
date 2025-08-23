# MQTT-Based Mister Control System

This directory contains the implementation for controlling a mister relay via MQTT, allowing the main Raspberry Pi to delegate GPIO control to a Pi Zero 2.

## Architecture

The system uses MQTT messaging to separate concerns:
- **Main Pi (192.168.4.1)**: Runs controller.py, detects when all 5 statues connect, publishes MQTT commands
- **Pi Zero 2 (192.168.4.2)**: Runs mister_controller.py, subscribes to MQTT, controls relay via GPIO

## Components

### 1. `mister_controller.py`
- Runs on Pi Zero 2 (rpi-ntp)
- Subscribes to `missing_link/mister` topic
- Controls GPIO 4 for relay activation
- Publishes status to `missing_link/mister/status`
- Handles 10-second timer automatically

### 2. `mister.service`
- Systemd service file for auto-start on boot
- Ensures mister controller runs continuously
- Restarts automatically on failure

### 3. `test_mister_mqtt.py`
- Test script for MQTT communication
- Run from main Pi to test mister control
- Includes interactive mode and automated tests

## Setup Instructions

### On Pi Zero 2 (rpi-ntp)

1. **Connect Hardware**:
   ```
   Pi Zero 2         →  SunFounder Relay Module
   Pin 2 (5V)       →  VCC
   Pin 6 (GND)      →  GND
   Pin 7 (GPIO 4)   →  IN1
   ```

2. **Run Setup Script**:
   ```bash
   ssh pi@192.168.4.2
   cd ~/first_contact_sensor_teensie/raspberry_pi/setup
   bash pi_zero_mister_setup.sh
   ```

3. **Verify Service**:
   ```bash
   sudo systemctl status mister
   sudo journalctl -u mister -f  # Watch logs
   ```

### On Main Pi

1. **Configure Mode** (already set to mqtt by default):
   ```bash
   # In controller.py, MISTER_MODE defaults to "mqtt"
   # Or set explicitly:
   export MISTER_MODE=mqtt
   ./controller.py
   ```

2. **Test Communication**:
   ```bash
   cd ~/first_contact_sensor_teensie/raspberry_pi/mister
   python3 test_mister_mqtt.py --interactive
   ```

## MQTT Protocol

### Command Topic: `missing_link/mister`

**Activate Mister**:
```json
{
  "action": "activate",
  "duration": 10
}
```

**Deactivate Mister**:
```json
{
  "action": "deactivate"
}
```

**Request Status**:
```json
{
  "action": "status"
}
```

### Status Topic: `missing_link/mister/status`

**Status Response**:
```json
{
  "status": "active",
  "remaining_seconds": 7,
  "timestamp": "2024-01-20T15:30:45.123456"
}
```

## Operating Modes

### MQTT Mode (Default)
- Main Pi publishes commands to MQTT
- Pi Zero 2 receives commands and controls relay
- Status updates published back via MQTT
- Best for production use

### Local Mode (Fallback)
- Main Pi controls relay directly via GPIO
- Set with: `export MISTER_MODE=local`
- Useful if Pi Zero is unavailable
- Requires GPIO 4 to be free on main Pi

## Testing

### Test Relay Hardware (on Pi Zero)
```bash
python3 ~/test_relay.py
```

### Test MQTT Communication (from Main Pi)
```bash
# Basic test - activate for 5 seconds
python3 test_mister_mqtt.py --basic

# Interrupt test - stop early
python3 test_mister_mqtt.py --interrupt

# Simulate all statues connected
python3 test_mister_mqtt.py --simulate

# Interactive control
python3 test_mister_mqtt.py --interactive
```

### Monitor MQTT Traffic
```bash
# On main Pi, subscribe to all mister topics
mosquitto_sub -h 192.168.4.1 -t "missing_link/mister/#" -v
```

## Troubleshooting

### Pi Zero Not Receiving Commands
1. Check network connectivity: `ping 192.168.4.1`
2. Verify MQTT broker running: `sudo systemctl status mosquitto`
3. Check service logs: `sudo journalctl -u mister -n 50`
4. Test MQTT manually: `mosquitto_pub -h 192.168.4.1 -t missing_link/mister -m '{"action":"status"}'`

### Relay Not Clicking
1. Check GPIO connections (Pin 7 to IN1)
2. Verify 5V power to relay module
3. Test relay directly: `python3 ~/test_relay.py`
4. Check for GPIO conflicts

### Service Not Starting
1. Check Python dependencies: `python3 -c "import RPi.GPIO; import paho.mqtt"`
2. Verify script permissions: `ls -la ~/first_contact_sensor_teensie/raspberry_pi/mister/`
3. Check service status: `sudo systemctl status mister`
4. Review service logs: `sudo journalctl -u mister --since "5 minutes ago"`

### Fallback to Local Mode
If Pi Zero is unavailable, on main Pi:
```bash
export MISTER_MODE=local
./controller.py
```

## System Flow

1. **All 5 statues connect** (detected in controller.py)
2. **Controller publishes** activate command to MQTT
3. **Pi Zero receives** command via mister_controller.py
4. **GPIO 4 activated** (relay turns ON)
5. **Timer starts** for 10 seconds
6. **Status published** to MQTT
7. **After 10 seconds**, relay turns OFF automatically
8. **Final status** published to MQTT

## Benefits

- **Isolation**: GPIO issues on main Pi don't affect mister
- **Reliability**: Dedicated Pi Zero for mister control
- **Flexibility**: Easy switch between MQTT/local modes
- **Monitoring**: Real-time status via MQTT
- **Resilience**: Auto-reconnect and service restart