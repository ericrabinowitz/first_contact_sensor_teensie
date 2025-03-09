# pip install paho-mqtt
import paho.mqtt.client as mqtt
import json

# Define the MQTT server settings
MQTT_BROKER = 'rpi'  # IP address of your MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_TOPIC = 'wled/all/api'  # Topic that ESP32 will subscribe to for control
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None

# Define your message (for example, to turn on WLED, set color, or change effects)
# Example: A simple JSON message for WLED to change color or effect
message = {
    "on": False,  # Turn on WLED
    "bri": 255,  # Maximum brightness
    "seg": [{
        "col": [255, 0, 0],  # RGB color - Red
#        "fx": 40  # Set to some effect (this is just an example)
    },
    {
        "col": [0, 255, 0],  # RGB color - Red
#        "fx": 80  # Set to some effect (this is just an example)
    },
    {
        "col": [0, 0, 255],  # RGB color - Red
#        "fx": 70  # Set to some effect (this is just an example)
    }]
}

# Convert message to JSON format
message_json = json.dumps(message)
print(message_json)

def send_mqtt_message():
    # Create a new MQTT client instance
    client = mqtt.Client()

    # Set username and password if required
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    # Connect to the MQTT broker
    client.connect(MQTT_BROKER, MQTT_PORT)

    # Publish the message to the ESP32 WLED topic
    client.publish(MQTT_TOPIC, message_json)

    print(f"Message sent: {message_json}")
   
    # Disconnect from the MQTT broker
    client.disconnect()

# Call the function to send the message
send_mqtt_message()
