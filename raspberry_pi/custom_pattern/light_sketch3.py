#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["paho-mqtt", "Pillow", "pygame", "numpy", "requests"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./light_sketch3.py

import time
import math

import numpy as np
from PIL import Image
import json
import argparse
from collections import deque


# Optional imports based on mode
mqtt_available = False
requests_available = False
pygame_available = False

try:
    import pygame

    pygame_available = True
except ImportError:
    pass

try:
    import paho.mqtt.client as mqtt

    mqtt_available = True
except ImportError:
    pass

try:
    import requests

    requests_available = True
except ImportError:
    pass

# Parse command line arguments
parser = argparse.ArgumentParser(description="LED Arch Light Show with Perlin Noise")
parser.add_argument(
    "--mode",
    choices=["production", "simulation", "test"],
    default="production",
    help="Operating mode: production (default), simulation (visualization with simulated triggers), test (no external dependencies)",
)
parser.add_argument("--viz", action="store_true", help="Enable visualization")
parser.add_argument("--no-mqtt", action="store_true", help="Disable MQTT communication")
parser.add_argument(
    "--no-ip", action="store_true", help="Disable direct IP communication"
)
parser.add_argument(
    "--mqtt-broker", type=str, default="mqtt.broker.address", help="MQTT broker address"
)
parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
parser.add_argument(
    "--esp32-1-ip", type=str, default="192.168.1.100", help="ESP32 #1 IP address"
)
parser.add_argument(
    "--esp32-2-ip", type=str, default="192.168.1.101", help="ESP32 #2 IP address"
)
parser.add_argument(
    "--test-interval",
    type=float,
    default=10.0,
    help="Interval between simulated triggers in seconds",
)
parser.add_argument(
    "--duration",
    type=float,
    default=60.0,
    help="Duration of simulation in seconds (0 = infinite)",
)
args = parser.parse_args()

# Set mode-specific defaults
if args.mode == "simulation":
    if not args.viz:
        args.viz = True  # Enable visualization by default in simulation mode
    args.no_mqtt = True  # Disable real MQTT in simulation mode
    args.no_ip = True  # Disable real IP in simulation mode
elif args.mode == "test":
    args.no_mqtt = True  # Disable MQTT in test mode
    args.no_ip = True  # Disable IP in test mode

# Constants
MQTT_BROKER = args.mqtt_broker
MQTT_PORT = args.mqtt_port
MQTT_TOPIC_TRIGGER = "lightshow/trigger"
MQTT_TOPIC_SEGMENT1 = "lightshow/esp32_1/segment1"
MQTT_TOPIC_SEGMENT2 = "lightshow/esp32_1/segment2"
MQTT_TOPIC_SEGMENT3 = "lightshow/esp32_2/segment3"

# ESP32 IP addresses for direct HTTP communication
ESP32_1_IP = args.esp32_1_ip  # Controls segments 1 and 2
ESP32_2_IP = args.esp32_2_ip  # Controls segment 3

TRANSITION_TIME = 1500  # ms
TRAVEL_SPEED = 100  # LED/sec
GREEN_MIX = 0
SEGMENT_1_LENGTH = 100
SEGMENT_2_LENGTH = 100
SEGMENT_3_LENGTH = 100

TOTAL_LEDS = SEGMENT_1_LENGTH + SEGMENT_2_LENGTH + SEGMENT_3_LENGTH
UPDATE_INTERVAL = 0.05  # seconds
CONNECTION_TIMEOUT = 5  # seconds to wait before assuming connection is broken


# Communication settings
USE_MQTT = not args.no_mqtt and mqtt_available
USE_IP = not args.no_ip and requests_available


# MQTT setup and callbacks
if USE_MQTT:

    def on_connect(client, userdata, flags, rc):
        global mqtt_connected
        print(f"Connected to MQTT broker with result code {rc}")
        mqtt_connected = rc == 0
        if mqtt_connected:
            client.subscribe(MQTT_TOPIC_TRIGGER)
            print(f"Subscribed to {MQTT_TOPIC_TRIGGER}")

    def on_disconnect(client, userdata, rc):
        global mqtt_connected
        print(f"Disconnected from MQTT broker with result code {rc}")
        mqtt_connected = False

    def on_message(client, userdata, msg):
        global active_mode, transition_progress
        try:
            payload = msg.payload.decode()
            topic = msg.topic
            print(f"Received message on {topic}: {payload}")

            if topic == MQTT_TOPIC_TRIGGER:
                if payload == "ON":
                    print("Activating light show mode via MQTT")
                    active_mode = True
                    transition_progress = 0.0
                elif payload == "OFF":
                    print("Deactivating light show mode via MQTT")
                    active_mode = False
                    transition_progress = 1.0
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    # Set up MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    # Set up last will message to handle unexpected disconnects
    mqtt_client.will_set(MQTT_TOPIC_TRIGGER, "OFF", qos=1, retain=True)

    # Try to connect to MQTT broker
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()  # Start the MQTT client loop in a separate thread
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        mqtt_connected = False


# Function to check IP connection
def check_ip_connection(ip_address):
    if requests_available:
        try:
            response = requests.get(f"http://{ip_address}/json/info", timeout=1)
            return response.status_code == 200
        except:
            return False
    return False


# Function to send data via HTTP
def send_to_wled_http(device, segment_data):
    if not requests_available:
        return False

    if device == "esp32_1":
        ip = ESP32_1_IP
    else:
        ip = ESP32_2_IP

    url = f"http://{ip}/json"
    try:
        response = requests.post(url, json=segment_data, timeout=1)
        if response.status_code == 200:
            ip_connection_status[device] = True
            return True
        else:
            print(f"Error sending data to {ip}: {response.status_code}")
            ip_connection_status[device] = False
            return False
    except Exception as e:
        print(f"Failed to send data to {ip}: {e}")
        ip_connection_status[device] = False
        return False


# Function to publish data via MQTT
def publish_to_mqtt(topic, data):
    if mqtt_connected and mqtt_client:
        try:
            result = mqtt_client.publish(topic, data, qos=0)
            return result.rc == 0
        except Exception as e:
            print(f"Error publishing to MQTT topic {topic}: {e}")
            return False
    return False


# Visualization settings
VIZ_ENABLED = args.viz and pygame_available
if args.viz and not pygame_available:
    print("Warning: Pygame not available. Visualization disabled.")


# setup noise
img = Image.open("Perlin128.png")
width, height = img.size
noise = []
for y in range(height):
    for x in range(width):
        noise.append(img.getpixel((x, y)))


last_update_time = time.time()
fade = 0  # ∈{0..1}
segment1 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Elektra, Segment5, Hoop1
segment2 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Elektra, Segment6, Hoop2
segment3 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Eros, Segment5, Hoop3
blue_noise = deque([0] * 300, maxlen=300)  # blue noise left to right
red_noise = deque([0] * 300, maxlen=300)  # red noise right to left

# Setup visualization
VIZ_ENABLED = True
if VIZ_ENABLED:
    VIZ_WIDTH = 800
    VIZ_HEIGHT = 600
    VIZ_LED_SIZE = 5

    # Calculate arch points
    arch_points = []
    arch_center_X = VIZ_WIDTH / 2.0
    arch_center_Y = VIZ_HEIGHT * 0.75
    arch_radius = VIZ_WIDTH * 0.45

    # Left ground to point A (segment 1)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(180 - i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(180 - i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))

    # Point A over arch to point B (segment 2)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(120 - i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(120 - i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))

    # Point B to right ground (segment 3)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(60 - i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(60 - i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))


def init_visualization():
    pygame.init()
    screen = pygame.display.set_mode((VIZ_WIDTH, VIZ_HEIGHT))
    pygame.display.set_caption("Arch Light Show Visualization")
    clock = pygame.time.Clock()

    # Load fonts
    pygame.font.init()

    return screen, clock


def draw_visualization(screen, segment1, segment2, segment3):
    if not VIZ_ENABLED or screen is None or not pygame_available:
        return

    # Clear screen
    screen.fill((0, 0, 0))

    # Draw arch structure (gray line)
    pygame.draw.lines(screen, (50, 50, 50), False, arch_points, 2)

    # Draw LEDs
    for i, point in enumerate(arch_points):

        if i < 100:
            color = segment1[i]
        elif i < 200:
            color = segment2[i - 100]
        else:
            color = segment3[i - 200]

        pygame.draw.circle(screen, color, point, VIZ_LED_SIZE)

    # Draw labels
    font = pygame.font.SysFont("Arial", 16)

    # Draw point labels
    pygame.draw.circle(screen, (255, 255, 255), arch_points[SEGMENT_1_LENGTH - 1], 8)
    point_a_label = font.render("Point A", True, (255, 255, 255))
    screen.blit(
        point_a_label,
        (
            arch_points[SEGMENT_1_LENGTH - 1][0] - 30,
            arch_points[SEGMENT_1_LENGTH - 1][1] - 25,
        ),
    )

    pygame.draw.circle(
        screen, (255, 255, 255), arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1], 8
    )
    point_b_label = font.render("Point B", True, (255, 255, 255))
    screen.blit(
        point_b_label,
        (
            arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1][0] - 30,
            arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1][1] - 25,
        ),
    )

    pygame.display.flip()


noise_offset1 = 0
noise_offset2 = 0

running = True
# screen, clock = init_visualization()
counter = 0
active_mode = True

while running:
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

    counter += 1
    if counter > 200:
        active_mode = False

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

    if args.mode == "production":
        # Prepare data in WLED-compatible format
        esp32_1_data = {
            "seg": [{"i": segment1}, {"i": segment2}]  # Segment 1  # Segment 2
        }

        esp32_2_data = {"seg": [{"i": segment3}]}  # Segment 3

        # Communication: Try to send data using available methods

        # 1. MQTT Communication
        if (
            USE_MQTT
            and mqtt_connected
            and (current_time - last_mqtt_publish_time) > 0.1
        ):
            last_mqtt_publish_time = current_time

            segment1_data = json.dumps({"seg": [{"i": segment1}]})
            segment2_data = json.dumps({"seg": [{"i": segment2}]})
            segment3_data = json.dumps({"seg": [{"i": segment3}]})

            publish_to_mqtt(MQTT_TOPIC_SEGMENT1, segment1_data)
            publish_to_mqtt(MQTT_TOPIC_SEGMENT2, segment2_data)
            publish_to_mqtt(MQTT_TOPIC_SEGMENT3, segment3_data)

        # 2. Direct IP Communication
        if USE_IP and (current_time - last_http_publish_time) > 0.1:
            last_http_publish_time = current_time
            send_to_wled_http("esp32_1", esp32_1_data)
            send_to_wled_http("esp32_2", esp32_2_data)
    # np.flip(segment1, 0)
    # Update visualization
    # if VIZ_ENABLED and screen and pygame_available:
    #     draw_visualization(screen, segment1, segment2, segment3)
