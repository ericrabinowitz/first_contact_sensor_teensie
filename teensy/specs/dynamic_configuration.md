# Teensy Dynamic Configuration Specification

## Overview
This document specifies the dynamic configuration system for the Teensy FirstContact controller, enabling real-time threshold updates via MQTT without requiring firmware recompilation or device restart. The system matches the Raspberry Pi controller's actual `teensy_config` structure.

## Configuration Protocol

### MQTT Topics
- **Request Topic**: `missing_link/config/request`
  - Teensy publishes "true" to request configuration
- **Response Topic**: `missing_link/config/response`
  - Raspberry Pi publishes complete configuration JSON

### Configuration JSON Structure
The Raspberry Pi sends the entire `teensy_config` dictionary:
```json
{
  "eros": {
    "emit": 10077,
    "detect": ["elektra", "sophia", "ultimo", "ariel"],
    "threshold": 0.01,
  },
  "elektra": {
    "emit": 12274,
    "detect": ["eros", "sophia", "ultimo", "ariel"],
    "threshold": 0.01,
  },
  // Additional statue configurations...
}
```

## Teensy Identification
The Teensy identifies its configuration by matching its current hostname with the name field in each statue's configuration. This eliminates the need for hardcoded statue identification beyond what's already in StatueConfig.h.

## Configurable Parameters

### Primary Configuration
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `threshold` | float | 0.01 | 0.001-1.0 | Tone detection sensitivity threshold |

### Informational Fields (Read-Only)
| Parameter | Type | Description |
|-----------|------|-------------|
| `emit` | int | Transmit frequency in Hz (for verification) |
| `detect` | array | List of detectable statue names |

## Implementation Details

### Configuration Structure
```cpp
struct TeensyConfig {
  // The main configurable parameter
  float threshold;

  // Informational fields from Pi config
  int emitFreq;           // Transmit frequency (read-only)
  String detectStatues[4]; // List of detectable statues
};
```

### Configuration Flow

1. **Startup Configuration**
   - Teensy connects to MQTT broker
   - Publishes "true" to `missing_link/config/request`
   - Waits for configuration on `missing_link/config/response`

2. **Configuration Matching**
   - Teensy gets its hostname via reverse DNS lookup
   - Iterates through all statue configs in received JSON
   - Matches `hostname` field to find its configuration
   - Extracts threshold and informational fields

3. **Runtime Updates**
   - Threshold updates applied immediately without restart
   - Configuration requested every 60 seconds for resilience
   - Handles network disconnections gracefully

### Error Handling

1. **No Matching Hostname**
   - Uses default threshold (0.01) if no config matches hostname
   - Logs warning message
   - System remains operational

2. **Invalid Values**
   - Threshold clamped to range 0.001-1.0
   - Invalid JSON ignored, current config retained
   - Errors logged to serial console

3. **Network Issues**
   - Hardcoded defaults used if no config received
   - 5-second timeout on initial request
   - Periodic retry every 60 seconds

## Fixed Parameters
These parameters remain as compile-time constants in the firmware:

### Audio Parameters (MusicPlayer.ino)
- `PLAYING_MUSIC_VOLUME`: 1.0
- `FADE_MUSIC_INIT_VOLUME`: 0.15
- `SIGNAL_AUDIO_VOLUME`: 0.75 (AudioSense.ino)

### Timing Parameters (MusicPlayer.ino)
- `PAUSE_TIMEOUT_MS`: 2000
- `IDLE_OUT_TIMEOUT_MS`: 10000
- `main_period_ms`: 150 (AudioSense.ino)

### Frequencies (StatueConfig.h)
- Transmit and receive frequencies remain hardcoded
- Statue identification remains compile-time based

## Backward Compatibility

- System operates with hardcoded defaults if configuration unavailable
- Existing frequency configuration (StatueConfig.h) unchanged
- Manual tone control via `statue/{name}/tone` topic still supported
- All existing MQTT topics and messages maintained

## Testing Requirements

1. **Hostname Matching**
   - Verify correct config selected based on hostname
   - Test with multiple Teensys on same network
   - Verify fallback when hostname not found

2. **Threshold Updates**
   - Confirm threshold applied correctly
   - Test range limiting (0.001-1.0)
   - Verify immediate effect on detection

3. **Network Resilience**
   - Test operation without config server
   - Verify periodic config refresh
   - Test reconnection after network loss

## Example Serial Output
```
My hostname: eros
Found configuration for eros (matched by hostname)
  Threshold: 0.0100
  Emit frequency: 10077 Hz
  Detects: elektra, sophia, ultimo, ariel
Applying configuration...
Detection threshold updated to: 0.0100
Configuration applied successfully
```

## Future Enhancements

1. **Additional Parameters**
   - If more parameters need to be configurable, add them to Pi's `teensy_config` first
   - Update this spec and Teensy code accordingly

2. **Configuration Acknowledgment**
   - Add MQTT topic for Teensy to confirm config receipt
   - Include current threshold in status messages

3. **Dynamic Frequency Configuration**
   - Could make frequencies configurable if needed
   - Would require updating tone detectors dynamically