/*
Networking: The ethernet, DNS, and MQTT WLED messaging logic.
*/

#ifndef NETWORKING_H
#define NETWORKING_H

#include <Arduino.h>
#include <PubSubClient.h>
#include <QNEthernet.h>
#include <cstring>
#include <string>

// Network-related helper functions
void initEthernet();
String reverseDnsLookup(IPAddress ip);
char *stringToCharArray(String str);
int buildDnsPtrQuery(byte *buffer, int buflen, const String &reverseName);
String parsePtrResponse(byte *buffer, int buflen, int queryLength);

// Replace printLocalIp declaration with getLocalIp
String getLocalIp();

// MQTT callbacks and helper functions
void mqttSubCallback(char *topic, byte *payload, unsigned int length);
void reconnect();
void mqttLoop();
void initMqtt();
void publishState(ContactState state);

extern PubSubClient client; // Externally defined MQTT client instance

#endif // NETWORKING_H
