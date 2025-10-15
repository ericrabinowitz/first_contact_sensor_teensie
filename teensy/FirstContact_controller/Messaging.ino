#include "AudioSense.h"
#include "Messaging.h"
#include "Networking.h"
#include "StatueConfig.h"
#include "defines.h"
#include <ArduinoJson.h>
#include <math.h>

// External function from StatueConfig.cpp
extern int getStatueIndex(const char *name);

// Use accessor to get the EthernetClient instance
PubSubClient client(getEthClient());

// Global configuration instance
TeensyConfig teensyConfig;

// Track last config request time
unsigned long lastConfigRequestMs = 0;
const unsigned long CONFIG_REQUEST_INTERVAL_MS =
    60000; // Request config every 60 seconds

void mqttSubCallback(char *topic, byte *payload, unsigned int length) {
  Serial.print("\nmqttSubCallback() Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  // Convert payload to string for easier processing
  char payloadStr[length + 1];
  for (unsigned int i = 0; i < length; i++) {
    payloadStr[i] = (char)payload[i];
    Serial.print((char)payload[i]);
  }
  payloadStr[length] = '\0';
  Serial.println();

  // Check if this is a configuration response
  if (strcmp(topic, "missing_link/config/response") == 0) {
    Serial.println("Received configuration from controller");
    parseConfig(payloadStr, length);
    return;
  }

  // Build expected tone control topic for this statue
  char toneTopic[32];
  String statueName = String(MY_STATUE_NAME);
  statueName.toLowerCase();
  snprintf(toneTopic, sizeof(toneTopic), "statue/%s/tone", statueName.c_str());

  // Check if this is a tone control message for this statue
  if (strcmp(topic, toneTopic) == 0) {
    if (strcmp(payloadStr, "ON") == 0) {
      setToneEnabled(true);
    } else if (strcmp(payloadStr, "OFF") == 0) {
      setToneEnabled(false);
    } else {
      Serial.print("Unknown tone command: ");
      Serial.println(payloadStr);
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(getHostname())) {
      Serial.println("connected");

      // Subscribe to configuration response topic
      client.subscribe("missing_link/config/response");
      Serial.println("Subscribed to: missing_link/config/response");

      // Subscribe to statue-specific tone control topic
      char toneTopic[32];
      String statueName = String(MY_STATUE_NAME);
      statueName.toLowerCase();
      snprintf(toneTopic, sizeof(toneTopic), "statue/%s/tone",
               statueName.c_str());
      client.subscribe(toneTopic);
      Serial.print("Subscribed to: ");
      Serial.println(toneTopic);

      // Request configuration after connecting
      requestConfig();
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void mqttLoop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Periodically request configuration
  unsigned long currentMs = millis();
  if (currentMs - lastConfigRequestMs > CONFIG_REQUEST_INTERVAL_MS) {
    requestConfig();
    lastConfigRequestMs = currentMs;
  }
}

void initMqtt() {
  // Load default configuration from program memory first
  loadDefaultConfig();

  client.setServer(getServer(), 1883);
  client.setCallback(mqttSubCallback);
}

/*
  publishState() - Publish current detection state to MQTT
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void publishState(ContactState state) {
  if (state.isUnchanged()) {
    // No change in state to report.
    return;
  }

  // Build JSON message with current detection state
  char jsonMsg[256];
  char emittersList[128] = "[";
  bool first = true;

  // Build list of currently detected statues
  for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
    if (statue_idx == MY_STATUE_INDEX)
      continue;

    if (state.isLinkedTo(statue_idx)) {
      if (!first) {
        strcat(emittersList, ",");
      }
      strcat(emittersList, "\"");

      // Convert statue name to lowercase
      String emitterName = String(STATUE_NAMES[statue_idx]);
      emitterName.toLowerCase();
      strcat(emittersList, emitterName.c_str());

      strcat(emittersList, "\"");
      first = false;
    }
  }
  strcat(emittersList, "]");

  // Get detector name (this statue)
  String detectorName = String(MY_STATUE_NAME);
  detectorName.toLowerCase();

  // Format complete JSON message
  snprintf(jsonMsg, sizeof(jsonMsg), "{\"detector\":\"%s\",\"emitters\":%s}",
           detectorName.c_str(), emittersList);

  // Publish to missing_link/contact topic
  if (client.publish("missing_link/contact", jsonMsg)) {
    Serial.print("Published: ");
    Serial.println(jsonMsg);
  } else {
    Serial.println("Failed to publish detection state");
  }
}

void publishSignals() {
  // External reference to signal levels from AudioSense.ino
  extern float detectorSignals[MAX_STATUES - 1];

  // Build JSON message with current signal levels for all detectors
  char jsonMsg[256];
  char signalsJson[128];

  // Start building the signals object
  strcpy(signalsJson, "{");
  bool first = true;

  int detectorIndex = 0;
  for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
    if (statue_idx == MY_STATUE_INDEX)
      continue;

    if (!first) {
      strcat(signalsJson, ",");
    }

    // Convert statue name to lowercase
    String statueName = String(STATUE_NAMES[statue_idx]);
    statueName.toLowerCase();

    // Get signal level and sanitize NaN values
    float signalLevel = detectorSignals[detectorIndex];
    if (isnan(signalLevel)) {
      signalLevel = 0.0;
    }

    // Add "statuename": level entry
    char entry[32];
    snprintf(entry, sizeof(entry), "\"%s\":%.3f", statueName.c_str(),
             signalLevel);
    strcat(signalsJson, entry);

    first = false;
    detectorIndex++;
  }
  strcat(signalsJson, "}");

  // Get detector name (this statue)
  String detectorName = String(MY_STATUE_NAME);
  detectorName.toLowerCase();

  // Format complete JSON message
  snprintf(jsonMsg, sizeof(jsonMsg), "{\"detector\":\"%s\",\"signals\":%s}",
           detectorName.c_str(), signalsJson);

  // Publish to missing_link/signals topic (no debug output - too verbose at
  // 2Hz)
  client.publish("missing_link/signals", jsonMsg);
}

// Load default configuration from program memory
void loadDefaultConfig() {
  // First initialize the statue configuration based on hostname
  // This sets MY_STATUE_INDEX, MY_TX_FREQ, etc. based on hostname matching
  bool statueConfigured = initStatueConfig();

  if (!statueConfigured) {
    Serial.println(
        "WARNING: Failed to identify statue by hostname, using defaults");
  }

  // Now load the threshold configuration using the same JSON
  // Get the length of the PROGMEM string
  size_t len = strlen_P(DEFAULT_CONFIG_JSON);

  // Allocate buffer in RAM and copy from PROGMEM
  char *jsonBuffer = new char[len + 1];
  strcpy_P(jsonBuffer, DEFAULT_CONFIG_JSON);

  Serial.println("Loading threshold configuration from program memory...");
  parseConfig(jsonBuffer, len);

  // Clean up allocated memory
  delete[] jsonBuffer;
}

// Request configuration from controller
void requestConfig() {
  if (client.connected()) {
    Serial.println("Requesting configuration from controller...");
    client.publish("missing_link/config/request", "true");
  }
}

// Parse configuration JSON and update TeensyConfig
void parseConfig(const char *json, unsigned int length) {
  // Use static allocation for better memory management
  StaticJsonDocument<2048> doc;

  DeserializationError error = deserializeJson(doc, json, length);
  if (error) {
    Serial.print("Failed to parse config JSON: ");
    Serial.println(error.c_str());
    return;
  }

  // Get this Teensy's hostname from reverse DNS
  String myHostname = String(getHostname());
  Serial.print("My hostname: ");
  Serial.println(myHostname);

  // First, update all statue thresholds from the full configuration
  // This allows each detector to use the appropriate target statue's threshold
  bool thresholdsChanged = false;
  for (JsonPair kv : doc.as<JsonObject>()) {
    String statueName = kv.key().c_str();
    JsonObject statueConfig = kv.value();

    int idx = getStatueIndex(statueName.c_str());
    if (idx >= 0 && idx < MAX_STATUES &&
        statueConfig.containsKey("threshold")) {
      float newThreshold =
          constrain(statueConfig["threshold"].as<float>(), 0.001, 1.0);
      if (STATUE_THRESHOLDS[idx] != newThreshold) {
        Serial.print("  ");
        Serial.print(STATUE_NAMES[idx]);
        Serial.print(" threshold: ");
        Serial.print(STATUE_THRESHOLDS[idx], 4);
        Serial.print(" -> ");
        Serial.println(newThreshold, 4);
        STATUE_THRESHOLDS[idx] = newThreshold;
        thresholdsChanged = true;
      }
    }
  }

  // Now find our specific configuration by hostname
  bool configFound = false;
  for (JsonPair kv : doc.as<JsonObject>()) {
    String statueName = kv.key().c_str();
    JsonObject statueConfig = kv.value();

    // Match statue name (JSON key) against hostname (case-insensitive)
    if (statueName.equalsIgnoreCase(myHostname)) {
      Serial.print("Found configuration for ");
      Serial.print(statueName);
      Serial.println(" (matched by hostname)");

      configFound = true;

      // Extract our threshold (kept as informational)
      if (statueConfig.containsKey("threshold")) {
        float newThreshold = statueConfig["threshold"];
        teensyConfig.threshold = constrain(newThreshold, 0.001, 1.0);
        Serial.print("  My threshold: ");
        Serial.println(teensyConfig.threshold, 4);
      }

      // Store informational fields
      if (statueConfig.containsKey("emit")) {
        teensyConfig.emitFreq = statueConfig["emit"];
        Serial.print("  Emit frequency: ");
        Serial.print(teensyConfig.emitFreq);
        Serial.println(" Hz");
      }

      // Store detect array (informational)
      if (statueConfig.containsKey("detect")) {
        JsonArray detectArray = statueConfig["detect"];
        int idx = 0;
        Serial.print("  Detects: ");
        for (JsonVariant v : detectArray) {
          if (idx < 4) {
            teensyConfig.detectStatues[idx] = v.as<String>();
            if (idx > 0)
              Serial.print(", ");
            Serial.print(teensyConfig.detectStatues[idx]);
            idx++;
          }
        }
        Serial.println();
      }

      // Apply the configuration
      applyConfig();
      break;
    }
  }

  if (!configFound) {
    Serial.println("No configuration found matching this Teensy's hostname");
    Serial.println("Using default threshold values");
  }

  // Update detector thresholds based on all parsed statue thresholds
  // Each detector will use the threshold of its target statue
  updateDetectorThresholds();
}

// Apply configuration changes to the system
void applyConfig() {
  Serial.println("Applying configuration...");

  // There are currently no configurable parameters, so this is a no-op.

  Serial.println("Configuration applied successfully");
}

// LED state functions removed - now handled by Raspberry Pi controller
// based on messages published to missing_link/contact topic

/*
// Legacy LED control functions - kept for reference
bool setActiveLedState() {
  bool result = client.publish("wled/elektra/api", "{\"tt\": 0, \"seg\": [{ \
    \"id\": 0, \
    \"on\": true, \
    \"bri\": 255, \
    \"col\": [[0, 25, 255], [0, 200, 255], [0, 25, 255]], \
    \"fx\": 72, \
    \"pal\": 3 \
  }]}");

  return result && client.publish("wled/eros/api", "{\"tt\": 0, \"seg\": [{ \
    \"id\": 0, \
    \"on\": true, \
    \"bri\": 255, \
    \"col\": [[255, 0, 100], [225, 0, 255], [255, 0, 100]], \
    \"fx\": 72, \
    \"pal\": 3 \
  }]}");
}

bool setInactiveLedState() {
  bool result = client.publish("wled/all/api", "{\"tt\": 0, \"seg\": [{ \
    \"id\": 0, \
    \"fx\": 0, \
    \"bri\": 255, \
    \"col\": [[0,0,0], [0,0,0], [0,0,0]] \
   }]}");
  return result && client.publish("wled/all/api", "{\"tt\": 0, \"seg\": [{ \
    \"id\": 0, \
    \"on\": true, \
    \"bri\": 255, \
    \"col\": [[255, 255, 255], [0, 0, 0], [0, 0, 0]], \
    \"fx\": 42, \
    \"pal\": 3 \
  }]}");
}
*/
