/*
StatueConfig.cpp - Runtime configuration variables for multi-statue system
*/

#include "StatueConfig.h"
#include <string.h>

// Runtime configuration variables (initialized from compile-time defaults)
int statueFrequencies[MAX_STATUES];
char statueNames[MAX_STATUES][10];
int myStatueIndex = MY_STATUE_INDEX;
int numStatues = NUM_STATUES;
bool configReceived = false;

// Initialize runtime configuration from compile-time defaults
void initDefaultConfig() {
  // Copy default frequencies and names to runtime arrays
  for (int i = 0; i < MAX_STATUES; i++) {
    statueFrequencies[i] = STATUE_FREQUENCIES[i];
    strcpy(statueNames[i], STATUE_NAMES[i]);
  }
  
  // Set initial values from defines
  myStatueIndex = MY_STATUE_INDEX;
  numStatues = NUM_STATUES;
  configReceived = false;
  
  Serial.println("Initialized with default configuration:");
  Serial.print("  My statue: ");
  Serial.print(statueNames[myStatueIndex]);
  Serial.print(" (");
  Serial.print(statueFrequencies[myStatueIndex]);
  Serial.println(" Hz)");
  Serial.print("  Active statues: ");
  Serial.println(numStatues);
}