# MQTT Tone Control Implementation Summary

## Overview
Added MQTT subscription interface to control the sine wave generator via statue-specific topics.

## Topic Format
- **Topic**: `statue/{statue_name}/tone` (e.g., `statue/elektra/tone`)
- **Payload**: `ON` or `OFF`
- Statue name is automatically converted to lowercase

## Implementation Details

### Files Modified

1. **AudioSense.h**
   - Added: `void setToneEnabled(bool enabled)` function declaration

2. **AudioSense.ino**
   - Added: `setToneEnabled()` function implementation
   - Controls `sine1.amplitude()`: 1.0 for ON, 0.0 for OFF
   - Tracks state to avoid redundant updates
   - Logs state changes to Serial

3. **Messaging.ino**
   - Updated `reconnect()`: Subscribes to statue-specific tone topic
   - Updated `mqttSubCallback()`: Parses topic and payload, calls `setToneEnabled()`
   - Added includes for `StatueConfig.h` and `AudioSense.h`

## Testing

### To test the implementation:

1. **Enable tone** (from Raspberry Pi or MQTT client):
   ```bash
   mosquitto_pub -t "statue/elektra/tone" -m "ON"
   ```

2. **Disable tone**:
   ```bash
   mosquitto_pub -t "statue/elektra/tone" -m "OFF"
   ```

3. **Monitor Serial output** on Teensy:
   - Shows subscription confirmation: "Subscribed to: statue/elektra/tone"
   - Shows state changes: "Tone generator enabled" or "Tone generator disabled"

## Notes
- Each statue subscribes only to its own tone control topic
- The tone frequency remains set to the statue's TX frequency
- This control is independent of the normal detection logic
- Invalid payloads are logged but ignored