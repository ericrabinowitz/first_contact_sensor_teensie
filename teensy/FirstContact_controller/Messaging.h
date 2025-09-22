/*
Messaging: MQTT, state publishing, and LED state logic.
*/

#ifndef MESSAGING_H
#define MESSAGING_H

#include <Arduino.h>
#include <PubSubClient.h>
#include "AudioSense.h"

// Configuration structure for dynamic parameters
struct TeensyConfig {
  // Detection parameters
  float threshold;
  uint16_t mainPeriodMs;

  // Audio parameters
  float signalVolume;
  float musicVolume;
  float fadeInitVolume;

  // Timing parameters
  uint16_t pauseTimeoutMs;
  uint16_t idleTimeoutMs;

  // Control parameters
  bool toneEnabled;
  bool debugMode;

  // Constructor with defaults
  TeensyConfig() :
    threshold(0.01),
    mainPeriodMs(150),
    signalVolume(0.75),
    musicVolume(1.0),
    fadeInitVolume(0.15),
    pauseTimeoutMs(2000),
    idleTimeoutMs(10000),
    toneEnabled(true),
    debugMode(false) {}
};

// Global configuration instance
extern TeensyConfig teensyConfig;

// Configuration functions
void requestConfig();
void applyConfig();
void parseConfig(const char* json, unsigned int length);

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
