#include "AudioSense.h"
#include "Messaging.h"
#include "Networking.h"
#include "StatueConfig.h"
#include "defines.h"
#include <ArduinoJson.h>

// Use accessor to get the EthernetClient instance
PubSubClient client(getEthClient());

// Global configuration instance
TeensyConfig teensyConfig;

// Track last config request time
unsigned long lastConfigRequestMs = 0;
const unsigned long CONFIG_REQUEST_INTERVAL_MS = 60000; // Request config every 60 seconds

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
      teensyConfig.toneEnabled = true;
      setToneEnabled(true);
    } else if (strcmp(payloadStr, "OFF") == 0) {
      teensyConfig.toneEnabled = false;
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

// Request configuration from controller
void requestConfig() {
  if (client.connected()) {
    Serial.println("Requesting configuration from controller...");
    client.publish("missing_link/config/request", "true");
  }
}

// Parse configuration JSON and update TeensyConfig
void parseConfig(const char* json, unsigned int length) {
  // Use static allocation for better memory management
  StaticJsonDocument<2048> doc;

  DeserializationError error = deserializeJson(doc, json, length);
  if (error) {
    Serial.print("Failed to parse config JSON: ");
    Serial.println(error.c_str());
    return;
  }

  // Get this statue's configuration
  String statueName = String(MY_STATUE_NAME);
  statueName.toLowerCase();

  if (!doc.containsKey(statueName)) {
    Serial.print("No configuration found for statue: ");
    Serial.println(statueName);
    return;
  }

  JsonObject statueConfig = doc[statueName];

  // Update configuration with received values (use defaults if not present)
  if (statueConfig.containsKey("threshold")) {
    float newThreshold = statueConfig["threshold"];
    // Clamp to valid range
    teensyConfig.threshold = constrain(newThreshold, 0.001, 1.0);
    Serial.print("Updated threshold: ");
    Serial.println(teensyConfig.threshold, 4);
  }

  if (statueConfig.containsKey("signal_volume")) {
    teensyConfig.signalVolume = constrain((float)statueConfig["signal_volume"], 0.0, 1.0);
    Serial.print("Updated signal volume: ");
    Serial.println(teensyConfig.signalVolume);
  }

  if (statueConfig.containsKey("music_volume")) {
    teensyConfig.musicVolume = constrain((float)statueConfig["music_volume"], 0.0, 1.0);
    Serial.print("Updated music volume: ");
    Serial.println(teensyConfig.musicVolume);
  }

  if (statueConfig.containsKey("fade_init_volume")) {
    teensyConfig.fadeInitVolume = constrain((float)statueConfig["fade_init_volume"], 0.0, 1.0);
    Serial.print("Updated fade init volume: ");
    Serial.println(teensyConfig.fadeInitVolume);
  }

  if (statueConfig.containsKey("pause_timeout_ms")) {
    teensyConfig.pauseTimeoutMs = constrain((uint16_t)statueConfig["pause_timeout_ms"], 100, 10000);
    Serial.print("Updated pause timeout: ");
    Serial.println(teensyConfig.pauseTimeoutMs);
  }

  if (statueConfig.containsKey("idle_timeout_ms")) {
    teensyConfig.idleTimeoutMs = constrain((uint16_t)statueConfig["idle_timeout_ms"], 1000, 60000);
    Serial.print("Updated idle timeout: ");
    Serial.println(teensyConfig.idleTimeoutMs);
  }

  if (statueConfig.containsKey("main_period_ms")) {
    teensyConfig.mainPeriodMs = constrain((uint16_t)statueConfig["main_period_ms"], 50, 1000);
    Serial.print("Updated main period: ");
    Serial.println(teensyConfig.mainPeriodMs);
  }

  if (statueConfig.containsKey("tone_enabled")) {
    teensyConfig.toneEnabled = statueConfig["tone_enabled"];
    Serial.print("Updated tone enabled: ");
    Serial.println(teensyConfig.toneEnabled ? "true" : "false");
  }

  if (statueConfig.containsKey("debug_mode")) {
    teensyConfig.debugMode = statueConfig["debug_mode"];
    Serial.print("Updated debug mode: ");
    Serial.println(teensyConfig.debugMode ? "true" : "false");
  }

  // Apply the configuration to the system
  applyConfig();
}

// Apply configuration changes to the system
void applyConfig() {
  Serial.println("Applying configuration...");

  // Update tone generation state
  setToneEnabled(teensyConfig.toneEnabled);

  // Update detection threshold
  updateDetectionThreshold(teensyConfig.threshold);

  // Update audio volumes
  updateAudioVolumes(teensyConfig.signalVolume, teensyConfig.musicVolume);

  // Update main loop period
  updateMainPeriod(teensyConfig.mainPeriodMs);

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
