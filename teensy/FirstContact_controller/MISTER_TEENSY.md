# Teensy Mister Control - Third Contingency

This document describes the Teensy-based mister relay control implementation, providing a third fallback option for the Missing Link art project.

## Overview

The Teensy 4.1 can control the mister relay via MQTT commands, serving as a backup if both the main Pi's GPIO and the Pi Zero are unavailable.

## Architecture Hierarchy

1. **Primary Method**: Main Pi → MQTT → Pi Zero 2 → GPIO → Relay
2. **Secondary Method**: Main Pi → Local GPIO → Relay (MISTER_MODE=local)
3. **Tertiary Method**: Main Pi → MQTT → Teensy → GPIO → Relay (this implementation)

All three methods listen to the same MQTT topic: `missing_link/mister`

## Hardware Configuration

### Pin Assignment
- **GPIO 30**: Mister relay control (unused pin, away from audio/display)
- Compatible with 3.3V logic level of Teensy 4.1
- Same SunFounder 2-channel relay module works with Teensy

### Wiring
```
Teensy 4.1         →  SunFounder Relay Module
Pin 30 (GPIO 30)   →  IN1 (Channel 1 control)
3.3V               →  VCC (via level shifter if needed)
GND                →  GND
```

**Note**: The SunFounder relay expects 5V control signals. While it often works with 3.3V directly, for reliable operation consider using a level shifter or a 3.3V-compatible relay module.

## Software Configuration

### Enabling Mister Control

Only ONE Teensy should have mister control enabled to avoid conflicts.

In `StatueConfig.h`, the ULTIMO statue (ID 'E') is designated:

```cpp
// Mister relay control configuration
#if THIS_STATUE_ID == 'E'  // ULTIMO is designated for mister control
#define MISTER_ENABLED 1
#else
#define MISTER_ENABLED 0
#endif
```

To change which statue controls the mister, modify the condition in `StatueConfig.h`.

### Compilation

1. Set `THIS_STATUE_ID` to 'E' in `StatueConfig.h` for the ULTIMO Teensy
2. Upload the code to the designated Teensy
3. Other Teensys will have `MISTER_ENABLED` set to 0 automatically

## MQTT Protocol

The Teensy subscribes to `missing_link/mister` and processes JSON commands:

### Activate Mister
```json
{
  "action": "activate",
  "duration": 10
}
```
- `duration`: Time in seconds (converted to milliseconds internally)
- Default: 10 seconds
- Maximum: 60 seconds (safety limit)

### Deactivate Mister
```json
{
  "action": "deactivate"
}
```

### Status Request
```json
{
  "action": "status"
}
```
- Status is printed to Serial console
- Could be extended to publish back to MQTT

## Implementation Details

### Files Modified/Created

1. **Mister.h**: Interface definitions
   - Pin configuration
   - Function declarations
   - Duration constants

2. **Mister.ino**: Implementation
   - Timer-based auto-off
   - Relay control logic
   - Safety limits

3. **Messaging.ino**: MQTT integration
   - Subscribes to `missing_link/mister`
   - Simple JSON parsing
   - Command dispatch

4. **FirstContact_controller.ino**: Main integration
   - Calls `initMister()` in setup
   - Calls `handleMisterTimer()` in loop

5. **StatueConfig.h**: Configuration
   - `MISTER_ENABLED` flag
   - Statue-specific enable

### Timer Management

- Non-blocking timer using `millis()`
- Auto-off after specified duration
- Maximum duration enforced (60 seconds)
- Timer checked each loop iteration

### JSON Parsing

Simple, lightweight JSON parsing without external libraries:
- Searches for "action" and "duration" fields
- Extracts values using string manipulation
- Robust against malformed JSON

## Testing

### 1. Hardware Test
```cpp
// In setup(), temporarily add:
digitalWrite(MISTER_RELAY_PIN, LOW);   // Relay ON
delay(1000);
digitalWrite(MISTER_RELAY_PIN, HIGH);  // Relay OFF
```

### 2. Serial Console Test
Monitor Serial output to see:
- "Mister relay control ENABLED for this Teensy"
- "Subscribed to: missing_link/mister"
- Command reception and processing

### 3. MQTT Test
From main Pi:
```bash
cd ~/first_contact_sensor_teensie/raspberry_pi/mister
python3 test_mister_mqtt.py --interactive

# Commands:
# on 5     - Activate for 5 seconds
# off      - Deactivate immediately
# status   - Check current state
```

### 4. Priority Testing
With both Pi Zero and Teensy online:
1. Send MQTT command
2. Verify Pi Zero responds (primary handler)
3. Teensy receives but Pi Zero takes precedence

With Pi Zero offline:
1. Send MQTT command
2. Verify Teensy responds as backup

## Troubleshooting

### Relay Not Clicking
- Check 3.3V/5V compatibility
- Verify wiring to pin 30
- Test with direct digitalWrite in setup()
- Check relay module power

### Not Receiving MQTT
- Verify `THIS_STATUE_ID` is 'E'
- Check MQTT broker connectivity
- Monitor Serial for subscription confirmation
- Ensure only one Teensy has `MISTER_ENABLED`

### Commands Not Working
- Check JSON format in MQTT messages
- Monitor Serial for parsing errors
- Verify action strings match exactly
- Check duration is in seconds (not ms)

## Safety Features

1. **Maximum Duration**: Limited to 60 seconds
2. **Single Control**: Only one Teensy enabled
3. **Auto-off Timer**: Always enforced
4. **High Default**: Relay starts OFF (HIGH)
5. **Graceful Degrade**: Works without MQTT

## Integration with Existing System

### Coexistence
- All three control methods use same MQTT topic
- Pi Zero (if online) takes precedence
- Teensy acts as passive backup
- No interference between controllers

### Message Flow
1. Controller.py detects all 5 statues connected
2. Publishes to `missing_link/mister`
3. All subscribers receive:
   - Pi Zero (if online) - PRIMARY
   - Teensy ULTIMO - BACKUP
   - Main Pi (if local mode) - FALLBACK

### Priority Order
1. Pi Zero responds fastest (dedicated service)
2. Teensy responds if Pi Zero unavailable
3. Main Pi local GPIO as last resort

## Future Enhancements

1. **Status Publishing**: Teensy could publish status back to MQTT
2. **LED Indicator**: Add LED to show relay state
3. **Multiple Relays**: Extend to control multiple devices
4. **Watchdog**: Add connection monitoring
5. **Config Topic**: Dynamic duration configuration via MQTT

## Summary

This implementation provides robust triple-redundancy for mister control:
- Minimal code changes
- Leverages existing MQTT infrastructure
- Designated single Teensy (ULTIMO) as controller
- Same protocol across all implementations
- Automatic failover without configuration changes

The system ensures the "climax moment" when all 5 statues connect will reliably trigger the mister, regardless of which control system is operational.