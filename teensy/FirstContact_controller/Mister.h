/*
  Mister Control Module
  Controls a relay for mister activation via MQTT commands.
  This provides a third contingency option if both the main Pi GPIO 
  and Pi Zero are unavailable.
*/

#pragma once

#include <Arduino.h>

// Mister relay configuration
#define MISTER_RELAY_PIN 30  // GPIO 30 - unused on Teensy 4.1, away from audio pins
#define MISTER_DEFAULT_DURATION_MS 10000  // Default 10 seconds
#define MISTER_MAX_DURATION_MS 60000      // Maximum 60 seconds for safety

// Function declarations
void initMister();
void activateMister(unsigned long duration_ms = MISTER_DEFAULT_DURATION_MS);
void deactivateMister();
void handleMisterTimer();
bool isMisterActive();
unsigned long getMisterRemainingMs();
void processMisterCommand(const char* action, unsigned long duration_ms = 0);