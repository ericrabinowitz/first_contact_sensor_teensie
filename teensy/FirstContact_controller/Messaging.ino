#include "AudioSense.h"
#include "Messaging.h"
#include "Networking.h"
#include "StatueConfig.h"
#include "defines.h"

// Use accessor to get the EthernetClient instance
PubSubClient client(getEthClient());

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
      // LED control now handled by Pi controller
      // client.subscribe("wled/all/api"); // No longer needed

      // Subscribe to statue-specific tone control topic
      char toneTopic[32];
      String statueName = String(MY_STATUE_NAME);
      statueName.toLowerCase();
      snprintf(toneTopic, sizeof(toneTopic), "statue/%s/tone",
               statueName.c_str());
      client.subscribe(toneTopic);
      Serial.print("Subscribed to: ");
      Serial.println(toneTopic);
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
