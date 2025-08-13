/*
Messaging: MQTT, state publishing, and LED state logic.
*/

#ifndef MESSAGING_H
#define MESSAGING_H

#include <Arduino.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "AudioSense.h"

// MQTT callbacks and helper functions
void mqttSubCallback(char *topic, byte *payload, unsigned int length);
void reconnect();
void mqttLoop();
void initMqtt();
void publishState(ContactState state);
void requestConfig();
void parseConfigResponse(char* payload, unsigned int length);
// LED functions removed - now handled by Pi controller
// bool setInactiveLedState();
// bool setActiveLedState();

extern PubSubClient client;

#endif // MESSAGING_H
