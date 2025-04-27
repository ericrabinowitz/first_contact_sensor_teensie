/*
Lights: MQTT, state publishing, and LED state logic.
*/

#ifndef LIGHTS_H
#define LIGHTS_H

#include <Arduino.h>
#include <PubSubClient.h>
#include "AudioSense.h"

// MQTT callbacks and helper functions
void mqttSubCallback(char *topic, byte *payload, unsigned int length);
void reconnect();
void mqttLoop();
void initMqtt();
void publishState(ContactState state);
bool setInactiveLedState();
bool setActiveLedState();

extern PubSubClient client;

#endif // LIGHTS_H
