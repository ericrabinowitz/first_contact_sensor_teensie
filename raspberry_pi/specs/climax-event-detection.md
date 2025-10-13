# Climax Event Detection Specification

## Overview
The "climax" event is a special state that occurs when all neighboring statue pairs in the Missing Link installation are connected simultaneously. This creates a complete circuit of human connection around all five statues.

## Statue Neighbor Relationships
Based on the Statue enum order with wraparound, the neighbor pairs are:
1. EROS ↔ ELEKTRA
2. ELEKTRA ↔ ARIEL
3. ARIEL ↔ SOPHIA
4. SOPHIA ↔ ULTIMO
5. ULTIMO ↔ EROS (wraparound)

## Detection Algorithm

### Bidirectional Link Detection
A link between two statues is considered active if either:
- Statue A detects Statue B, OR
- Statue B detects Statue A

This bidirectional approach ensures reliability even if detection is not perfectly symmetric due to cable length, interference, or other factors.

### Climax Condition
A climax occurs when ALL five neighbor pairs have active links simultaneously.

## Implementation

### Global State Variables
```python
# Track whether climax is currently active
climax_is_active: bool = False

# Track which neighbor pairs are currently linked
active_links: Set[Tuple[Statue, Statue]] = set()
```

### Core Function: `update_active_links()`

#### Purpose
Analyzes the current statue connections to determine if a climax event is occurring.

#### Returns
```python
Tuple[bool, bool, Set[Tuple[Statue, Statue]]]
```
- `climax_started`: True if climax just began
- `climax_stopped`: True if climax just ended
- `active_links`: Set of currently connected neighbor pairs (normalized tuples)

#### Algorithm
1. Get list of all statues in enum order
2. For each statue, determine its neighbors (using modulo for wraparound)
3. Check bidirectional links between neighbors
4. Normalize link tuples (smaller statue first) to avoid duplicates
5. Compare with previous state to detect transitions
6. Update global state variables
7. Return transition flags and active links

### Integration Point: `handle_contact_event()`
After calling `update_active_statues()`:
1. Call `update_active_links()`
2. Store returned active_links globally
3. If climax_started: print "Climax happening!"
4. If climax_stopped: print "Climax has stopped."

## Current Implementation
- Console logging only (print statements)
- State tracking for future use

## Future Extensions

### MQTT Events
```python
# Publish climax state changes
publish_mqtt("missing_link/climax", {
    "state": "active" | "inactive",
    "active_links": [...],
    "timestamp": ...
})
```

### Audio Effects
- Play special climax audio track
- Mix additional audio layer
- Adjust volume or effects

### Hardware Control
- Activate relay on GPIO pins
- Trigger special lighting effects
- Control external devices

### Debug Endpoint
Add to `/config/dynamic`:
```json
{
    "climax_is_active": true/false,
    "active_links": [
        ["eros", "elektra"],
        ["elektra", "ariel"],
        ...
    ]
}
```

## Testing Scenarios

### Full Climax
All five pairs connected:
- EROS sees ELEKTRA
- ELEKTRA sees ARIEL
- ARIEL sees SOPHIA
- SOPHIA sees ULTIMO
- ULTIMO sees EROS

### Partial Connections
Test with 4 out of 5 pairs connected to ensure climax doesn't trigger.

### Asymmetric Detection
Test when only one direction of detection works (e.g., EROS sees ELEKTRA but not vice versa) to verify bidirectional logic.

### Rapid State Changes
Test quick connect/disconnect cycles to ensure state transitions are properly detected.