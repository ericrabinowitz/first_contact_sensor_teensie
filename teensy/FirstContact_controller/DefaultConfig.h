/*
DefaultConfig.h - Default configuration for Teensy statues stored in program memory
This configuration is loaded on startup and can be overridden by runtime updates from the Pi
*/

#ifndef DEFAULT_CONFIG_H
#define DEFAULT_CONFIG_H

#include <Arduino.h>

// Default configuration JSON stored in program memory
// MAC and IP addresses from dnsmasq.conf static DHCP assignments
const char DEFAULT_CONFIG_JSON[] PROGMEM = R"({
  "eros": {
    "emit": 10077,
    "detect": ["elektra", "sophia", "ultimo", "ariel"],
    "threshold": 0.01,
    "mac_address": "04:e9:e5:19:06:4c",
    "ip_address": "192.168.4.26"
  },
  "elektra": {
    "emit": 12274,
    "detect": ["eros", "sophia", "ultimo", "ariel"],
    "threshold": 0.01,
    "mac_address": "04:e9:e5:19:06:2f",
    "ip_address": "192.168.4.23"
  },
  "ariel": {
    "emit": 14643,
    "detect": ["eros", "elektra", "sophia", "ultimo"],
    "threshold": 0.01,
    "mac_address": "04:e9:e5:17:c4:51",
    "ip_address": "192.168.4.24"
  },
  "sophia": {
    "emit": 17227,
    "detect": ["eros", "elektra", "ultimo", "ariel"],
    "threshold": 0.01,
    "mac_address": "04:e9:e5:12:93:6b",
    "ip_address": "192.168.4.25"
  },
  "ultimo": {
    "emit": 19467,
    "detect": ["eros", "elektra", "sophia", "ariel"],
    "threshold": 0.01,
    "mac_address": "04:e9:e5:12:93:68",
    "ip_address": "192.168.4.27"
  }
})";

#endif // DEFAULT_CONFIG_H