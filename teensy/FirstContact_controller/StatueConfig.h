/*
StatueConfig.h - Dynamic configuration for multi-statue tone detection
This file provides dynamic statue identification based on IP address matching
and loads configuration from embedded JSON in program memory.

The system self-identifies by matching its DHCP-assigned IP address with the
configuration, eliminating the need for compile-time statue identification.
*/

#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

#include <Arduino.h>

// Total number of statues (don't change this)
#define MAX_STATUES 5
#define NUM_STATUES 5

// These are now dynamic variables, not compile-time constants
// They are set at runtime based on IP address matching
extern char THIS_STATUE_ID;        // 'A' through 'E' based on statue index
extern int MY_STATUE_INDEX;        // 0-4 based on which statue we are
extern int MY_TX_FREQ;             // This statue's transmit frequency
extern const char *MY_STATUE_NAME; // This statue's name

// Arrays populated from configuration
extern int STATUE_FREQUENCIES[MAX_STATUES];  // All statue frequencies
extern char STATUE_NAMES[MAX_STATUES][10];   // All statue names
extern float STATUE_THRESHOLDS[MAX_STATUES]; // All statue thresholds

// Initialize the statue configuration based on IP address
// Must be called after Ethernet initialization but before audioSenseSetup()
// Returns true if successful, false if no matching IP found
bool initStatueConfig();

// Update detector thresholds based on current STATUE_THRESHOLDS array
// Called after config changes to recalculate per-detector thresholds
void updateDetectorThresholds();

// Default configuration JSON stored in program memory
// MAC and IP addresses from dnsmasq.conf static DHCP assignments
const char DEFAULT_CONFIG_JSON[] PROGMEM = R"({
  "eros": {
    "emit": 10077,
    "detect": ["elektra", "sophia", "ultimo", "ariel"],
    "threshold": 0.01
  },
  "elektra": {
    "emit": 12274,
    "detect": ["eros", "sophia", "ultimo", "ariel"],
    "threshold": 0.01
  },
  "ariel": {
    "emit": 14643,
    "detect": ["eros", "elektra", "sophia", "ultimo"],
    "threshold": 0.01
  },
  "sophia": {
    "emit": 17227,
    "detect": ["eros", "elektra", "ultimo", "ariel"],
    "threshold": 0.01
  },
  "ultimo": {
    "emit": 19467,
    "detect": ["eros", "elektra", "sophia", "ariel"],
    "threshold": 0.01
  }
})";

#endif // STATUE_CONFIG_H
