# Relay-Controlled Mister Setup

This document describes the setup and wiring for the relay-controlled mister feature that activates when all 5 statues are connected.

## Hardware Components

- **Relay Module**: SunFounder 2 Channel DC 5V Relay Module with Optocoupler (low-level trigger)
- **Raspberry Pi**: Main controller (with HiFiBerry DAC8x installed)
- **Mister**: 12V/24V misting system
- **Power Supply**: Appropriate voltage for your mister

## GPIO Pin Selection

**GPIO 4 (Physical Pin 7)** is used for relay control.

### Why GPIO 4?
- Compatible with HiFiBerry DAC8x (which uses GPIO 2-3, 18-27)
- Easily accessible on the Pi header
- No conflicts with I2C, SPI, or UART functions
- General purpose GPIO with no special boot behavior

### HiFiBerry DAC8x GPIO Usage
The HiFiBerry DAC8x reserves these pins (DO NOT USE):
- GPIO 2-3 (Pins 3, 5): I2C configuration
- GPIO 18-27 (Pins 12, 13, 15, 16, 18, 22, 35, 37, 38, 40): Sound interface

## Wiring Connections

### Raspberry Pi to Relay Module

```
Raspberry Pi          →    SunFounder Relay Module
------------------------------------------------
Pin 2 (5V Power)     →    VCC
Pin 6 (Ground)       →    GND
Pin 7 (GPIO 4)       →    IN1 (Channel 1 control)
                          IN2 (unused - Channel 2)
```

### Relay to Mister

```
Relay Channel 1 Terminals    →    Mister Circuit
------------------------------------------------
COM (Common)                →    Mister positive wire
NO (Normally Open)          →    Power supply positive
NC (Normally Closed)        →    Not connected

Power Supply Ground         →    Mister ground wire
```

## Physical Pin Layout

```
Raspberry Pi 40-pin Header (Top View, USB ports facing down)
    3.3V [01] [02] 5V     ← Connect to Relay VCC
   GPIO2 [03] [04] 5V
   GPIO3 [05] [06] GND    ← Connect to Relay GND
>> GPIO4 [07] [08] GPIO14 << Use Pin 7 for Relay IN1
     GND [09] [10] GPIO15
  GPIO17 [11] [12] GPIO18
  GPIO27 [13] [14] GND
  GPIO22 [15] [16] GPIO23
    3.3V [17] [18] GPIO24
  GPIO10 [19] [20] GND
   GPIO9 [21] [22] GPIO25
  GPIO11 [23] [24] GPIO8
     GND [25] [26] GPIO7
   GPIO0 [27] [28] GPIO1
   GPIO5 [29] [30] GND
   GPIO6 [31] [32] GPIO12
  GPIO13 [33] [34] GND
  GPIO19 [35] [36] GPIO16
  GPIO26 [37] [38] GPIO20
     GND [39] [40] GPIO21
```

## Software Configuration

### Automatic Setup
The controller.py script automatically:
1. Initializes GPIO 4 as output (HIGH = relay OFF)
2. Monitors when all 5 statues connect
3. Activates relay (LOW) for 10 seconds
4. Deactivates relay (HIGH) after timeout
5. Cleans up GPIO on exit

### Manual Testing

1. **Test the relay independently**:
```bash
cd ~/first_contact_sensor_teensie/raspberry_pi/controller
python3 test_relay.py              # Basic 3-second test
python3 test_relay.py --manual     # Interactive control
python3 test_relay.py --cycle      # Continuous on/off cycling
```

2. **Monitor controller logs**:
```bash
# Watch for "ALL 5 STATUES ARE NOW CONNECTED!" message
controller.logs

# Run controller in debug mode
DEBUG=1 ./controller.py
```

## Installation Steps

### 1. Install GPIO Library
```bash
# Should already be installed, but if needed:
sudo apt update
sudo apt install python3-rpi.gpio
```

### 2. Connect Hardware
1. Power off Raspberry Pi
2. Connect relay module as per wiring diagram
3. Connect mister to relay NO and COM terminals
4. Double-check all connections
5. Power on Raspberry Pi

### 3. Test Relay
```bash
cd ~/first_contact_sensor_teensie/raspberry_pi/controller
python3 test_relay.py
# You should hear relay click and see LED indicator change
```

### 4. Test with Controller
```bash
# Run controller in debug mode
DEBUG=1 ./controller.py

# In another terminal, simulate all statues connecting:
mosquitto_pub -t "missing_link/touch" -m '{"detector":"eros","emitters":["elektra","sophia","ultimo","ariel"]}'

# You should see:
# "ALL 5 STATUES ARE NOW CONNECTED!"
# "Activating mister for 10 seconds"
# (after 10 seconds)
# "Deactivating mister"
```

## Troubleshooting

### Relay Not Clicking
1. Check 5V power to relay module
2. Verify GPIO 4 connection to IN1
3. Test with test_relay.py script
4. Check relay module LED indicators

### Mister Not Activating
1. Verify relay is clicking (mechanical sound)
2. Check mister power supply
3. Test mister directly without relay
4. Check NO/COM terminal connections

### GPIO Errors
1. Ensure RPi.GPIO is installed
2. Check no other process is using GPIO 4
3. Verify script is run with appropriate permissions
4. Check HiFiBerry DAC8x is not using GPIO 4

### Controller Not Detecting All Statues
1. Check MQTT messages with `mosquitto_sub -t "missing_link/touch"`
2. Verify all 5 statue names are correct
3. Check debug output shows all statues in active_statues set
4. Ensure statue detection logic is working

## Safety Notes

- The relay provides optical isolation between Pi and mister circuit
- Always use appropriate power supply for your mister
- Ensure mister circuit doesn't exceed relay ratings (10A/250VAC)
- Mount relay module in a dry, ventilated enclosure
- Use proper gauge wire for mister current requirements

## Feature Behavior

When all 5 statues (EROS, ELEKTRA, SOPHIA, ULTIMO, ARIEL) form a complete connection:
1. Controller detects all_connected state
2. Relay activates (GPIO 4 goes LOW)
3. Mister turns ON
4. Timer starts for 10 seconds
5. After 10 seconds, relay deactivates (GPIO 4 goes HIGH)
6. Mister turns OFF

The mister will NOT activate:
- When fewer than 5 statues are connected
- When statues disconnect and reconnect (unless they all disconnect first)
- If already active (timer resets instead)

## Code Locations

- **Main Implementation**: `raspberry_pi/controller/controller.py`
  - Lines 60-61: Configuration constants
  - Lines 391-446: GPIO initialization and relay control functions
  - Lines 500-508: All-connected detection logic
  - Lines 791-792: Mister activation trigger
  - Lines 1011-1018: GPIO cleanup

- **Test Script**: `raspberry_pi/controller/test_relay.py`
  - Standalone relay testing utility

## Future Enhancements

- [ ] Make mister duration configurable via environment variable
- [ ] Add MQTT command to manually trigger mister
- [ ] Log mister activations to file
- [ ] Add web UI control for mister
- [ ] Support multiple relay channels for different effects