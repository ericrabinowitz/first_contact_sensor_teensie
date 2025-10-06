/*
  Mister Control Implementation
  Handles relay control for mister activation with timer-based auto-off.
*/

#include "Mister.h"
#include "StatueConfig.h"
#include <Arduino.h>

// Timer variables for mister auto-off
static unsigned long misterTimerStart = 0;
static unsigned long misterDuration = 0;
static bool misterActive = false;

void initMister() {
  #if MISTER_ENABLED
    pinMode(MISTER_RELAY_PIN, OUTPUT);
    digitalWrite(MISTER_RELAY_PIN, HIGH);  // Start with relay OFF (HIGH = off for low-level trigger)
    
    Serial.println("Mister control initialized on pin " + String(MISTER_RELAY_PIN));
    Serial.println("Mister relay control ENABLED for this Teensy");
  #else
    Serial.println("Mister relay control DISABLED for this Teensy");
  #endif
}

void activateMister(unsigned long duration_ms) {
  #if MISTER_ENABLED
    // Limit duration for safety
    if (duration_ms > MISTER_MAX_DURATION_MS) {
      duration_ms = MISTER_MAX_DURATION_MS;
      Serial.println("Mister duration limited to " + String(MISTER_MAX_DURATION_MS) + "ms for safety");
    }
    
    // Set timer variables
    misterDuration = duration_ms;
    misterTimerStart = millis();
    misterActive = true;
    
    // Turn relay ON (LOW for low-level trigger relay)
    digitalWrite(MISTER_RELAY_PIN, LOW);
    
    Serial.println("Mister activated for " + String(duration_ms) + "ms");
  #endif
}

void deactivateMister() {
  #if MISTER_ENABLED
    // Turn relay OFF (HIGH for low-level trigger relay)
    digitalWrite(MISTER_RELAY_PIN, HIGH);
    misterActive = false;
    misterDuration = 0;
    
    Serial.println("Mister deactivated");
  #endif
}

// Check if the timer has expired and turn off mister if needed
void handleMisterTimer() {
  #if MISTER_ENABLED
    if (misterActive && misterDuration > 0) {
      unsigned long elapsed = millis() - misterTimerStart;
      if (elapsed >= misterDuration) {
        deactivateMister();
      }
    }
  #endif
}

bool isMisterActive() {
  #if MISTER_ENABLED
    return misterActive;
  #else
    return false;
  #endif
}

unsigned long getMisterRemainingMs() {
  #if MISTER_ENABLED
    if (!misterActive || misterDuration == 0) {
      return 0;
    }
    
    unsigned long elapsed = millis() - misterTimerStart;
    if (elapsed >= misterDuration) {
      return 0;
    }
    
    return misterDuration - elapsed;
  #else
    return 0;
  #endif
}

void processMisterCommand(const char* action, unsigned long duration_ms) {
  #if MISTER_ENABLED
    if (strcmp(action, "activate") == 0) {
      // Use provided duration or default
      unsigned long duration = (duration_ms > 0) ? duration_ms : MISTER_DEFAULT_DURATION_MS;
      activateMister(duration);
      
    } else if (strcmp(action, "deactivate") == 0) {
      deactivateMister();
      
    } else if (strcmp(action, "status") == 0) {
      // Status could be published back via MQTT if needed
      Serial.print("Mister status: ");
      if (misterActive) {
        Serial.println("ACTIVE, " + String(getMisterRemainingMs() / 1000) + " seconds remaining");
      } else {
        Serial.println("INACTIVE");
      }
      
    } else {
      Serial.println("Unknown mister command: " + String(action));
    }
  #else
    Serial.println("Mister control disabled on this Teensy");
  #endif
}