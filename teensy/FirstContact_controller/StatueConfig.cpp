/*
StatueConfig.cpp - Implementation of dynamic statue configuration
*/

#include "StatueConfig.h"
#include "Networking.h"
#include <ArduinoJson.h>

// Variable definitions - these replace the former #define constants
char THIS_STATUE_ID = 'A'; // Default to 'A', will be set dynamically
int MY_STATUE_INDEX = 0;   // Default to 0, will be set dynamically
int MY_TX_FREQ = 10077;    // Default frequency, will be set dynamically
const char *MY_STATUE_NAME = "EROS"; // Default name, will be set dynamically

// Arrays to hold all statue configurations
int STATUE_FREQUENCIES[MAX_STATUES] = {10077, 12274, 14643, 17227,
                                       19467}; // Defaults
char STATUE_NAMES[MAX_STATUES][10] = {"EROS", "ELEKTRA", "ARIEL", "SOPHIA",
                                      "ULTIMO"}; // Defaults
float STATUE_THRESHOLDS[MAX_STATUES] = {0.01, 0.01, 0.01, 0.01,
                                        0.01}; // Defaults

// External reference to detector thresholds array in AudioSense.ino
extern float detectorThresholds[MAX_STATUES - 1];

// Helper function to map statue name to index
int getStatueIndex(const char *name) {
  String nameUpper = String(name);
  nameUpper.toUpperCase();

  if (nameUpper == "EROS")
    return 0;
  else if (nameUpper == "ELEKTRA")
    return 1;
  else if (nameUpper == "ARIEL")
    return 2;
  else if (nameUpper == "SOPHIA")
    return 3;
  else if (nameUpper == "ULTIMO")
    return 4;
  else
    return -1; // Unknown statue
}

// Initialize the statue configuration based on IP address
bool initStatueConfig() {
  // Get the current IP address
  String myIpAddress = getLocalIp();
  Serial.println("=== Initializing Statue Configuration ===");
  Serial.print("My IP address: ");
  Serial.println(myIpAddress);

  // Copy JSON from PROGMEM to RAM for parsing
  size_t len = strlen_P(DEFAULT_CONFIG_JSON);
  char *jsonBuffer = new char[len + 1];
  strcpy_P(jsonBuffer, DEFAULT_CONFIG_JSON);

  // Parse the JSON
  StaticJsonDocument<2048> doc;
  DeserializationError error = deserializeJson(doc, jsonBuffer, len);

  // Clean up buffer
  delete[] jsonBuffer;

  if (error) {
    Serial.print("Failed to parse statue config JSON: ");
    Serial.println(error.c_str());
    return false;
  }

  // Variables to track if we found our configuration
  bool configFound = false;
  String matchedStatueName = "";

  // First pass: Find which statue we are based on IP address
  for (JsonPair kv : doc.as<JsonObject>()) {
    String statueName = kv.key().c_str();
    JsonObject statueConfig = kv.value();

    if (statueConfig.containsKey("ip_address")) {
      String configIp = statueConfig["ip_address"].as<String>();
      if (configIp == myIpAddress) {
        matchedStatueName = statueName;
        configFound = true;

        // Set our identity
        MY_STATUE_INDEX = getStatueIndex(statueName.c_str());
        THIS_STATUE_ID = 'A' + MY_STATUE_INDEX; // A=0, B=1, C=2, D=3, E=4

        if (statueConfig.containsKey("emit")) {
          MY_TX_FREQ = statueConfig["emit"].as<int>();
        }

        // Store the name in uppercase
        matchedStatueName.toUpperCase();
        MY_STATUE_NAME =
            STATUE_NAMES[MY_STATUE_INDEX]; // Will be set properly below

        Serial.print("Identified as: ");
        Serial.print(matchedStatueName);
        Serial.print(" (Statue ");
        Serial.print(THIS_STATUE_ID);
        Serial.print(", Index ");
        Serial.print(MY_STATUE_INDEX);
        Serial.println(")");
        Serial.print("Transmit frequency: ");
        Serial.print(MY_TX_FREQ);
        Serial.println(" Hz");

        break;
      }
    }
  }

  // Second pass: Populate all statue frequencies, names, and thresholds arrays
  for (JsonPair kv : doc.as<JsonObject>()) {
    String statueName = kv.key().c_str();
    JsonObject statueConfig = kv.value();

    int idx = getStatueIndex(statueName.c_str());
    if (idx >= 0 && idx < MAX_STATUES) {
      // Get the emit frequency
      if (statueConfig.containsKey("emit")) {
        STATUE_FREQUENCIES[idx] = statueConfig["emit"].as<int>();
      }

      // Get the threshold for this statue
      if (statueConfig.containsKey("threshold")) {
        STATUE_THRESHOLDS[idx] = statueConfig["threshold"].as<float>();
      }

      // Store the name in uppercase
      statueName.toUpperCase();
      strncpy(STATUE_NAMES[idx], statueName.c_str(), 9);
      STATUE_NAMES[idx][9] = '\0'; // Ensure null termination
    }
  }

  // Update MY_STATUE_NAME to point to the correct entry in the array
  if (configFound) {
    MY_STATUE_NAME = STATUE_NAMES[MY_STATUE_INDEX];
  }

  // Update detector thresholds based on parsed statue thresholds
  updateDetectorThresholds();

  // Print the complete configuration
  Serial.println("\nComplete statue configuration:");
  for (int i = 0; i < NUM_STATUES; i++) {
    Serial.print("  ");
    Serial.print(STATUE_NAMES[i]);
    Serial.print(" (");
    Serial.print(char('A' + i));
    Serial.print("): ");
    Serial.print(STATUE_FREQUENCIES[i]);
    Serial.print(" Hz, threshold ");
    Serial.print(STATUE_THRESHOLDS[i], 4);
    if (i == MY_STATUE_INDEX) {
      Serial.print(" <- THIS STATUE");
    }
    Serial.println();
  }

  if (!configFound) {
    Serial.println(
        "\nWARNING: No configuration found matching this Teensy's IP address!");
    Serial.println("Using default configuration (EROS, Statue A)");
    return false;
  }

  return true;
}

// Update detector thresholds based on current STATUE_THRESHOLDS array
// TODO: consolidate detector thresholds <-> statue thresholds
void updateDetectorThresholds() {
  int detectorIndex = 0;
  bool anyChanged = false;

  for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
    if (statue_idx != MY_STATUE_INDEX) {
      float oldThreshold = detectorThresholds[detectorIndex];
      float newThreshold = STATUE_THRESHOLDS[statue_idx];

      // Use the TARGET statue's threshold for detecting it
      if (oldThreshold != newThreshold) {
        if (!anyChanged) {
          Serial.println("\nUpdating detector thresholds:");
          anyChanged = true;
        }

        detectorThresholds[detectorIndex] = newThreshold;

        Serial.print("  Detector ");
        Serial.print(detectorIndex);
        Serial.print(" (");
        Serial.print(STATUE_NAMES[statue_idx]);
        Serial.print("): ");
        Serial.print(oldThreshold, 4);
        Serial.print(" -> ");
        Serial.println(newThreshold, 4);
      }

      detectorIndex++;
    }
  }

  if (!anyChanged) {
    Serial.println("Detector thresholds unchanged");
  }
}
