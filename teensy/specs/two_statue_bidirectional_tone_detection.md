# Two-Statue Bidirectional Tone Detection Specification for Teensy

## Overview
This specification describes modifications to the Teensy FirstContact_controller code to support a two-statue test where each statue transmits a unique frequency and listens for the other statue's frequency, enabling bidirectional contact detection.

### Frequency Assignment
- **Statue A**: Transmits 10kHz, Listens for 17kHz
- **Statue B**: Transmits 17kHz, Listens for 10kHz

### Detection Logic
- When human contact bridges Statue A to Statue B:
  - Statue A's 10kHz signal reaches Statue B
  - Statue B detects 10kHz and registers contact
- When human contact bridges Statue B to Statue A:
  - Statue B's 17kHz signal reaches Statue A
  - Statue A detects 17kHz and registers contact
- Bidirectional contact: Both statues detect each other

## Implementation Details

### 1. Add Statue Identity Configuration
Create a new header file `StatueConfig.h` in the FirstContact_controller directory:

```cpp
#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

// Define which statue this code is running on
// Change this to 'B' when compiling for the second statue
#define THIS_STATUE_ID 'A'  

// Frequency assignments
#define FREQ_STATUE_A 10000  // 10kHz
#define FREQ_STATUE_B 17000  // 17kHz

// Get frequencies based on statue ID
#if THIS_STATUE_ID == 'A'
  #define MY_TX_FREQ FREQ_STATUE_A
  #define OTHER_RX_FREQ FREQ_STATUE_B
  #define MY_STATUE_NAME "EROS"
#else
  #define MY_TX_FREQ FREQ_STATUE_B
  #define OTHER_RX_FREQ FREQ_STATUE_A
  #define MY_STATUE_NAME "ELEKTRA"
#endif

#endif // STATUE_CONFIG_H
```

### 2. Modify AudioSense.ino

#### Include the configuration header
Add at the top of the file:
```cpp
#include "StatueConfig.h"
```

#### Update frequency definitions
Replace the existing frequency constants:
```cpp
// Remove these lines:
// const int f_1 = 10000;
// const int f_2 = 20;
// const int f_3 = 20;
// const int f_4 = 20;

// Add these lines:
const int tx_freq = MY_TX_FREQ;
const int rx_freq = OTHER_RX_FREQ;
```

#### Update audioSenseSetup()
Modify the tone detector and sine generator configuration:
```cpp
void audioSenseSetup() {
  // ... existing code ...
  
  // Add debug output for statue identity
  Serial.printf("Configuring Statue %c (%s)\n", THIS_STATUE_ID, MY_STATUE_NAME);
  Serial.printf("  TX Frequency: %d Hz\n", tx_freq);
  Serial.printf("  RX Frequency: %d Hz\n", rx_freq);
  
  const int sample_time_ms = main_period_ms / 2;

  // Configure the left/right tone analyzers to detect the OTHER statue's frequency
  left_f_1.frequency(rx_freq, sample_time_ms * rx_freq / 1000);
  right_f_1.frequency(rx_freq, sample_time_ms * rx_freq / 1000);

  // ... existing LED setup code ...

  // Configure sine generator to transmit THIS statue's frequency
  AudioNoInterrupts();
  sine1.frequency(tx_freq);
  sine1.amplitude(1.0);
  AudioInterrupts();
}
```

#### Update debug output
Modify the debugPrintAudioSense() function to show which frequency is being detected:
```cpp
void debugPrintAudioSense(float l1, float r1) {
#ifdef DEBUG_PRINT
  Serial.print("Detecting ");
  Serial.print(rx_freq);
  Serial.print("Hz: L=");
  Serial.print(l1);
  Serial.print(", R=");
  Serial.print(r1);
  Serial.print("\n");
#endif
}
```

### 3. Update Display Output (Display.ino)

Add statue identity information to the OLED display:

```cpp
// In displaySetup() or displayState()
void displayStatueInfo() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Show statue identity
  display.setCursor(0, 0);
  display.print("Statue ");
  display.print(THIS_STATUE_ID);
  display.print(": ");
  display.println(MY_STATUE_NAME);
  
  // Show frequency configuration
  display.print("TX: ");
  display.print(tx_freq);
  display.println(" Hz");
  
  display.print("RX: ");
  display.print(rx_freq);
  display.println(" Hz");
  
  display.display();
}
```

### 4. Optional: Update MQTT Topics (Networking.ino)

Include statue identity in MQTT topics for better debugging:

```cpp
// In publishState() or similar
void publishStateWithIdentity(const ContactState &state) {
  char topic[64];
  sprintf(topic, "missing_link/statue_%c/contact", THIS_STATUE_ID);
  
  char payload[128];
  if (state.isLinked) {
    sprintf(payload, "{\"statue\":\"%c\",\"name\":\"%s\",\"state\":\"linked\"}", 
            THIS_STATUE_ID, MY_STATUE_NAME);
  } else {
    sprintf(payload, "{\"statue\":\"%c\",\"name\":\"%s\",\"state\":\"unlinked\"}", 
            THIS_STATUE_ID, MY_STATUE_NAME);
  }
  
  mqttClient.publish(topic, payload);
}
```

## Build and Deploy Process

### For Statue A (EROS):
1. Open `StatueConfig.h`
2. Ensure `THIS_STATUE_ID` is set to `'A'`
3. Compile the sketch in Arduino IDE
4. Upload to the first Teensy 4.1

### For Statue B (ELEKTRA):
1. Open `StatueConfig.h`
2. Change `THIS_STATUE_ID` to `'B'`
3. Compile the sketch in Arduino IDE
4. Upload to the second Teensy 4.1

## Hardware Setup

### Audio Connections
```
Statue A (10kHz TX)          Statue B (17kHz TX)
┌─────────────────┐          ┌─────────────────┐
│ Teensy + Audio  │          │ Teensy + Audio  │
│    Shield       │          │    Shield       │
│                 │          │                 │
│ Line Out L ─────┼──────────┼─── Line In L    │
│ Line Out R ─────┼──────────┼─── Line In R    │
│                 │          │                 │
│ Line In L ──────┼──────────┼─── Line Out L   │
│ Line In R ──────┼──────────┼─── Line Out R   │
└─────────────────┘          └─────────────────┘
```

### Contact Points
- Connect contact points (hands) to the appropriate pins on each Teensy
- Ensure proper grounding between boards

## Testing Procedure

### Initial Setup
1. Power both Teensy boards
2. Connect to serial monitors for both boards
3. Verify frequency configuration messages in serial output

### Contact Testing
1. **Test A→B Contact**:
   - Touch Statue A's contact point
   - Touch Statue B's contact point while maintaining contact with A
   - Statue B should show "CONTACT" (detecting 10kHz)
   - Statue A should show "--OFF---" (no 17kHz detected)

2. **Test B→A Contact**:
   - Touch Statue B's contact point
   - Touch Statue A's contact point while maintaining contact with B
   - Statue A should show "CONTACT" (detecting 17kHz)
   - Statue B should show "--OFF---" (no 10kHz detected)

3. **Test Bidirectional Contact**:
   - Create a chain: Touch A → Human 1 → Human 2 → Touch B
   - Both statues should show "CONTACT"

### Debug Output
Monitor serial output for:
- Frequency detection levels
- State transitions
- CPU usage statistics

## Benefits of This Approach

1. **Minimal Code Changes**: Only requires adding one configuration file and updating frequency assignments
2. **Compile-Time Configuration**: No runtime overhead for statue identification
3. **Maintains Compatibility**: All existing features (MQTT, display, music) continue to work
4. **Easy Testing**: Can test with just two Teensy boards
5. **Scalable**: Can extend to more statue pairs by adding more frequency pairs

## Future Enhancements

### Dynamic Configuration
- Add DIP switches or jumpers for hardware-based statue ID selection
- Implement MQTT-based configuration for runtime frequency changes

### Multiple Statue Support
- Extend to support 5 statues with unique frequency pairs:
  - EROS: TX 3000Hz, RX others
  - ELEKTRA: TX 17000Hz, RX others
  - SOPHIA: TX 9500Hz, RX others
  - ULTIMO: TX 13500Hz, RX others
  - ARIEL: TX 19500Hz, RX others

### Advanced Features
- Signal strength reporting for debugging cable losses
- Automatic gain control for varying contact resistance
- Frequency hopping to avoid interference
- Built-in frequency sweep test mode

## Troubleshooting

### No Detection
- Verify audio connections between boards
- Check serial output for correct frequency configuration
- Ensure adequate volume level (SIGNAL_AUDIO_VOLUME)
- Test with oscilloscope to verify signal generation

### False Positives
- Increase detection threshold in AudioSense.ino
- Add shielding to audio cables
- Ensure proper grounding between boards

### Intermittent Detection
- Check contact point connections
- Verify power supply stability
- Add capacitive filtering to contact points
- Adjust TRANSITION_BUFFER_MS for more stable readings