/*
Networking: The ethernet, DNS, and MQTT WLED messaging logic.
*/

#ifndef NETWORKING_H
#define NETWORKING_H

#include <Arduino.h>
#include <QNEthernet.h>
#include <cstring>
#include <string>

using namespace qindesign::network;

// Network-related helper functions
void initEthernet();
String reverseDnsLookup(IPAddress ip);
char *stringToCharArray(String str);
int buildDnsPtrQuery(byte *buffer, int buflen, const String &reverseName);
String parsePtrResponse(byte *buffer, int buflen, int queryLength);

// Replace printLocalIp declaration with getLocalIp
String getLocalIp();

// Networking accessors for Messaging.ino
IPAddress getServer();
char* getHostname();
EthernetClient& getEthClient();

#endif // NETWORKING_H
