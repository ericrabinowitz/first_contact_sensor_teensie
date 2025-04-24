#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["paho-mqtt", "Pillow", "numpy", "requests"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./original.py

import time
import math
import random
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
SEGMENT_1_LENGTH = 60  # Number of LEDs in segment 1
SEGMENT_2_LENGTH = 120  # Number of LEDs in segment 2
SEGMENT_3_LENGTH = 60  # Number of LEDs in segment 3
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
noise = np.array(noise, dtype=np.float32) / 255.0  # Normalize to 0-1

# Active state flag
active_mode = False
transition_progress = 0.0
last_update_time = time.time()


# Sigmoid function for exaggerating values closer to 0 or 1
def sigmoid(x, sharpness=10):
    return 1 / (1 + math.exp(-sharpness * (x - 0.5)))


# Apply exaggerated sigmoid to create more distinct twinkles
def twinkle_function(value, intensity=1.0):
    exaggerated = sigmoid(value, 8)  # Sharpen contrast
    # Add some random variation for twinkling effect
    variation = random.uniform(0.85, 1.15) * intensity
    return min(1.0, exaggerated * variation)


# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    global active_mode, transition_progress
    if msg.payload.decode() == "ON":
        print("Activating light show mode")
        active_mode = True
        transition_progress = 0.0
    elif msg.payload.decode() == "OFF":
        print("Deactivating light show mode")
        active_mode = False
        transition_progress = 1.0


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
    noise_offset = 0
    while True:
        current_time = time.time()
        elapsed = current_time - last_update_time

        if elapsed < UPDATE_INTERVAL:
            time.sleep(0.001)  # Small sleep to prevent CPU hogging
            continue

        last_update_time = current_time

        # Update transition progress
        if active_mode and transition_progress < 1.0:
            transition_progress = min(
                1.0, transition_progress + elapsed * 0.5
            )  # Transition over 2 seconds
        elif not active_mode and transition_progress > 0.0:
            transition_progress = max(
                0.0, transition_progress - elapsed * 0.5
            )  # Transition over 2 seconds

        # Calculate noise offset for animation
        noise_offset = (noise_offset + 1) % (width * height)

        # Prepare LED arrays for each segment
        segment1 = []
        segment2 = []
        segment3 = []

        # Neutral state: twinkling effect
        for i in range(SEGMENT_1_LENGTH):
            pos = (noise_offset + i) % len(noise)
            twinkle_val = int(twinkle_function(noise[pos], 0.3) * 32)  # Dim twinkle
            segment1.append([twinkle_val, twinkle_val, twinkle_val])  # White twinkle

        for i in range(SEGMENT_2_LENGTH):
            pos = (noise_offset + SEGMENT_1_LENGTH + i) % len(noise)
            twinkle_val = int(twinkle_function(noise[pos], 0.3) * 32)  # Dim twinkle
            segment2.append([twinkle_val, twinkle_val, twinkle_val])  # White twinkle

        for i in range(SEGMENT_3_LENGTH):
            pos = (noise_offset + SEGMENT_1_LENGTH + SEGMENT_2_LENGTH + i) % len(noise)
            twinkle_val = int(twinkle_function(noise[pos], 0.3) * 32)  # Dim twinkle
            segment3.append([twinkle_val, twinkle_val, twinkle_val])  # White twinkle

        # Apply active mode if enabled
        if transition_progress > 0:
            # Blue wave from left to right (segment 1 to 3)
            for i in range(SEGMENT_1_LENGTH):
                # Intensity increases as we approach point A
                blue_intensity = i / SEGMENT_1_LENGTH
                blue_val = int(
                    255
                    * blue_intensity
                    * transition_progress
                    * twinkle_function(noise[(noise_offset + i * 3) % len(noise)])
                )
                segment1[i][2] = max(segment1[i][2], blue_val)  # Blue channel

            for i in range(SEGMENT_2_LENGTH):
                # Intensity decreases as we move from point A to point B
                blue_intensity = 1.0 - (i / SEGMENT_2_LENGTH)
                blue_val = int(
                    255
                    * blue_intensity
                    * transition_progress
                    * twinkle_function(
                        noise[(noise_offset + (SEGMENT_1_LENGTH + i) * 3) % len(noise)]
                    )
                )
                segment2[i][2] = max(segment2[i][2], blue_val)  # Blue channel

            # Red wave from right to left (segment 3 to 1)
            for i in range(SEGMENT_3_LENGTH):
                # Intensity increases as we approach point B
                red_intensity = i / SEGMENT_3_LENGTH
                red_val = int(
                    255
                    * red_intensity
                    * transition_progress
                    * twinkle_function(
                        noise[(noise_offset + (TOTAL_LEDS - i) * 5) % len(noise)]
                    )
                )
                segment3[SEGMENT_3_LENGTH - 1 - i][0] = max(
                    segment3[SEGMENT_3_LENGTH - 1 - i][0], red_val
                )  # Red channel

            for i in range(SEGMENT_2_LENGTH):
                # Intensity decreases as we move from point B to point A
                red_intensity = 1.0 - (i / SEGMENT_2_LENGTH)
                red_val = int(
                    255
                    * red_intensity
                    * transition_progress
                    * twinkle_function(
                        noise[
                            (noise_offset + (TOTAL_LEDS - SEGMENT_3_LENGTH - i) * 5)
                            % len(noise)
                        ]
                    )
                )
                segment2[SEGMENT_2_LENGTH - 1 - i][0] = max(
                    segment2[SEGMENT_2_LENGTH - 1 - i][0], red_val
                )  # Red channel

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
