#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["paho-mqtt", "Pillow", "requests", "numpy"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./edited.py

import time
import math

from PIL import Image
import paho.mqtt.client as mqtt
import requests
import numpy as np

# Constants
WLED_IP_1 = "192.168.1.100"  # ESP32 controlling segments 1 and 2
WLED_IP_2 = "192.168.1.101"  # ESP32 controlling segment 3
MQTT_BROKER = "mqtt.broker.address"
MQTT_PORT = 1883
MQTT_TOPIC = "lightshow/trigger"
SEGMENT_1_LENGTH = 100  # Number of LEDs in segment 1
SEGMENT_2_LENGTH = 100  # Number of LEDs in segment 2
SEGMENT_3_LENGTH = 100  # Number of LEDs in segment 3
TOTAL_LEDS = SEGMENT_1_LENGTH + SEGMENT_2_LENGTH + SEGMENT_3_LENGTH
UPDATE_INTERVAL = 0.05  # seconds

# Open the Perlin noise image
img = Image.open("Perlin128.png").convert("L")  # Convert to grayscale
width, height = img.size

# Load noise values into array
noise = []
for y in range(height):
    for x in range(width):
        noise.append(img.getpixel((x, y)))

# Convert to numpy array for easier manipulation
noise = np.array(noise, dtype=np.uint8)

# Active state flag
active_mode = False
fade = 0
last_update_time = time.time()


# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    global active_mode, transition_progress
    if msg.payload.decode() == "ON":
        print("Activating light show mode")
        active_mode = True
        fade = 0.0
    elif msg.payload.decode() == "OFF":
        print("Deactivating light show mode")
        active_mode = False
        fade = 255


# Set up MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()  # Start the MQTT client loop in a separate thread


# Function to send data to WLED
def send_to_wled(ip, segment_data):
    url = f"http://{ip}/json"
    payload = {"seg": segment_data}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Error sending data to {ip}: {response.status_code}")
    except Exception as e:
        print(f"Failed to send data to {ip}: {e}")


# Main loop
try:
    noise_offset1 = 0
    noise_offset2 = 0
    while True:
        current_time = time.time()
        elapsed = current_time - last_update_time

        if elapsed < UPDATE_INTERVAL:
            time.sleep(0.001)  # Small sleep to prevent CPU hogging
            continue

        current_time = time.time()
        elapsed = current_time - last_update_time
        last_update_time = current_time

        # Update transition mask
        delta = math.ceil((elapsed / TRANSITION_TIME) * 512)
        if active_mode == True:
            fade += delta
            if fade >= 255:
                fade = 255
        else:
            fade -= delta
            if fade <= 0:
                fade = 0

        # Calculate noise offset for animation
        noise_offset1 = (noise_offset1 + 3) % 8192
        noise_offset2 = noise_offset1 + 8192
        if noise_offset1 >= 8192:
            noise_offset1 = 0

        # Prepare LED arrays for each segment
        blue_noise.appendleft(min(fade, noise[noise_offset1]))
        red_noise.append(min(fade, noise[noise_offset2]))
        for i in range(100):
            index = i + 200
            blue_noise[index] = min(blue_noise[index], 255 - i * 2)
            red_noise[100 - i] = min(red_noise[100 - i], 255 - i * 2)

        # populate RGB values from noise streams
        for i in range(100):
            segment1[i] = [red_noise[i], GREEN_MIX, blue_noise[i]]
            segment2[i] = [red_noise[i + 100], GREEN_MIX, blue_noise[i + 100]]
            segment3[i] = [red_noise[i + 200], GREEN_MIX, blue_noise[i + 200]]

        # Prepare data for WLED API
        wled1_data = [{"i": segment1}, {"i": segment2}]  # Segment 1  # Segment 2

        wled2_data = [{"i": segment3}]  # Segment 3

        # Send data to both ESP32s
        send_to_wled(WLED_IP_1, wled1_data)
        send_to_wled(WLED_IP_2, wled2_data)

except KeyboardInterrupt:
    print("Exiting light show")
    client.loop_stop()
    client.disconnect()
