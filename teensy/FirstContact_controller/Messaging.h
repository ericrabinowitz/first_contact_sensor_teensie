/*
Messaging: MQTT, state publishing, and LED state logic.
*/

#ifndef MESSAGING_H
#define MESSAGING_H

#include "AudioSense.h"
#include <Arduino.h>
#include <PubSubClient.h>

// Configuration structure matching Pi's teensy_config
struct TeensyConfig {
  // The main configurable parameter
  float threshold;

  // Informational fields from Pi config
  int emitFreq;            // Transmit frequency (read-only, for verification)
  String detectStatues[4]; // List of detectable statues (informational)
  String ipAddress;        // This Teensy's IP address
  String macAddress;       // This Teensy's MAC address

  // Constructor with defaults
  TeensyConfig() : threshold(0.01), emitFreq(0), ipAddress(""), macAddress("") {
    // Initialize detect array as empty
    for (int i = 0; i < 4; i++) {
      detectStatues[i] = "";
    }
  }
};

// Global configuration instance
extern TeensyConfig teensyConfig;

// Configuration functions
void loadDefaultConfig();
void requestConfig();
void applyConfig();
void parseConfig(const char *json, unsigned int length);

// MQTT callbacks and helper functions
void mqttSubCallback(char *topic, byte *payload, unsigned int length);
void reconnect();
void mqttLoop();
void initMqtt();
void publishState(ContactState state);
// LED functions removed - now handled by Pi controller
// bool setInactiveLedState();
// bool setActiveLedState();

extern PubSubClient client;

#endif // MESSAGING_H
