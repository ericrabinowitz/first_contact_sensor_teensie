#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["paho-mqtt", "Pillow", "pygame", "numpy", "requests"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./lighting.py

import time
import math
import random
import numpy as np
from PIL import Image
import json
import threading
import argparse
import os
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
GREEN_MIX = 50

SEGMENT_1_LENGTH = 100  # Number of LEDs in segment 1
SEGMENT_2_LENGTH = 100  # Number of LEDs in segment 2
SEGMENT_3_LENGTH = 100  # Number of LEDs in segment 3

TOTAL_LEDS = SEGMENT_1_LENGTH + SEGMENT_2_LENGTH + SEGMENT_3_LENGTH
UPDATE_INTERVAL = 0.05  # seconds
CONNECTION_TIMEOUT = 5  # seconds to wait before assuming connection is broken

# Communication settings
USE_MQTT = not args.no_mqtt and mqtt_available
USE_IP = not args.no_ip and requests_available

# Visualization settings
VIZ_ENABLED = args.viz and pygame_available
if args.viz and not pygame_available:
    print("Warning: Pygame not available. Visualization disabled.")

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
    for i in range(SEGMENT_1_LENGTH):
        x = (
            arch_center_X
            + math.cos(math.radians(120 + i * 60 / SEGMENT_1_LENGTH)) * arch_radius
        )
        y = (
            arch_center_Y
            - math.sin(math.radians(120 + i * 60 / SEGMENT_1_LENGTH)) * arch_radius
        )
        arch_points.append((int(x), int(y)))

    # Point A over arch to point B (segment 2)
    for i in range(SEGMENT_2_LENGTH):
        x = (
            arch_center_X
            + math.cos(math.radians(120 - i * 60 / SEGMENT_2_LENGTH)) * arch_radius
        )
        y = (
            arch_center_Y
            - math.sin(math.radians(120 - i * 60 / SEGMENT_2_LENGTH)) * arch_radius
        )
        arch_points.append((int(x), int(y)))

    # Point B to right ground (segment 3)
    for i in range(SEGMENT_3_LENGTH):
        x = (
            arch_center_X
            + math.cos(math.radians(60 - i * 60 / SEGMENT_1_LENGTH)) * arch_radius
        )
        y = (
            arch_center_Y
            - math.sin(math.radians(60 - i * 60 / SEGMENT_1_LENGTH)) * arch_radius
        )
        arch_points.append((int(x), int(y)))

# Open the Perlin noise image or generate random noise
try:
    img = Image.open("Perlin128.png").convert("L")  # Convert to grayscale
    width, height = img.size

    # Load noise values into array
    noise = []
    for y in range(height):
        for x in range(width):
            noise.append(img.getpixel((x, y)) / 255.0)  # Normalize to 0-1
    noise = np.array(noise, dtype=np.float32)
except FileNotFoundError:
    print("Perlin noise image not found, generating random noise instead")
    width, height = 128, 128
    noise = np.random.rand(width * height)
    print(f"Generated {len(noise)} random noise values")

# State variables
active_mode = False
transition_progress = 0.0
last_update_time = time.time()
last_mqtt_publish_time = time.time()
last_http_publish_time = time.time()
start_time = time.time()
mqtt_connected = False
mqtt_client = None
ip_connection_status = {"esp32_1": False, "esp32_2": False}
connection_healthy = True
simulation_auto_trigger = False

# Simulation variables
last_trigger_time = time.time()
auto_trigger_interval = args.test_interval  # Seconds between simulated triggers
simulation_duration = args.duration


# Sigmoid function for exaggerating values closer to 0 or 1
def sigmoid(x, sharpness=10):
    return 1 / (1 + math.exp(-sharpness * (x - 0.5)))


# Apply exaggerated sigmoid to create more distinct twinkles
def twinkle_function(value, intensity=1.0):
    exaggerated = sigmoid(value, 8)  # Sharpen contrast
    # Add some random variation for twinkling effect
    variation = random.uniform(0.85, 1.15) * intensity
    return min(1.0, exaggerated * variation)


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


# Function to initialize Pygame for visualization
def init_visualization():
    if not VIZ_ENABLED or not pygame_available:
        return None, None

    pygame.init()
    screen = pygame.display.set_mode((VIZ_WIDTH, VIZ_HEIGHT))
    pygame.display.set_caption("Arch Light Show Visualization")
    clock = pygame.time.Clock()

    # Load fonts
    pygame.font.init()

    return screen, clock


# Function to draw the LED arch visualization
def draw_visualization(screen, segment1, segment2, segment3):
    if not VIZ_ENABLED or screen is None or not pygame_available:
        return

    # Clear screen
    screen.fill((0, 0, 0))

    # Draw arch structure (gray line)
    pygame.draw.lines(screen, (50, 50, 50), False, arch_points, 2)

    # Draw LEDs
    for i, point in enumerate(arch_points):
        if i < SEGMENT_1_LENGTH:
            color = segment1[i]
        elif i < SEGMENT_1_LENGTH + SEGMENT_2_LENGTH:
            color = segment2[i - SEGMENT_1_LENGTH]
        else:
            color = segment3[i - SEGMENT_1_LENGTH - SEGMENT_2_LENGTH]

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

    # Draw status info
    status_text = f"Mode: {'Active' if active_mode else 'Neutral'} | Progress: {transition_progress:.2f}"
    status_label = font.render(status_text, True, (255, 255, 255))
    screen.blit(status_label, (10, 10))

    # Draw mode indicator
    mode_text = f"Running in {args.mode.upper()} mode"
    if args.mode == "simulation":
        mode_text += f" | Auto-trigger: {'ON' if simulation_auto_trigger else 'OFF'}"
        if simulation_auto_trigger:
            next_trigger = max(
                0, auto_trigger_interval - (time.time() - last_trigger_time)
            )
            mode_text += f" | Next trigger in: {next_trigger:.1f}s"
    mode_label = font.render(mode_text, True, (255, 200, 0))
    screen.blit(mode_label, (10, 30))

    # Draw connection status
    if args.mode == "production":
        mqtt_status = f"MQTT: {'Connected' if mqtt_connected else 'Disconnected'}"
        mqtt_label = font.render(
            mqtt_status, True, (255, 255, 255) if mqtt_connected else (255, 100, 100)
        )
        screen.blit(mqtt_label, (10, 50))

        ip1_status = f"ESP32 #1 (IP): {'Connected' if ip_connection_status['esp32_1'] else 'Disconnected'}"
        ip1_label = font.render(
            ip1_status,
            True,
            (255, 255, 255) if ip_connection_status["esp32_1"] else (255, 100, 100),
        )
        screen.blit(ip1_label, (10, 70))

        ip2_status = f"ESP32 #2 (IP): {'Connected' if ip_connection_status['esp32_2'] else 'Disconnected'}"
        ip2_label = font.render(
            ip2_status,
            True,
            (255, 255, 255) if ip_connection_status["esp32_2"] else (255, 100, 100),
        )
        screen.blit(ip2_label, (10, 90))

    # Draw controls help
    controls = [
        "SPACE - Toggle active mode",
        "T - Toggle auto-trigger (simulation mode)",
        "+/- - Adjust auto-trigger interval",
        "ESC - Exit",
    ]

    y_pos = VIZ_HEIGHT - (len(controls) * 20) - 10
    for control in controls:
        control_label = font.render(control, True, (200, 200, 200))
        screen.blit(control_label, (10, y_pos))
        y_pos += 20

    pygame.display.flip()


# Health check function
def connection_health_check():
    global connection_healthy, active_mode, ip_connection_status
    while True:
        # In simulation or test mode, connections are "healthy" by default
        if args.mode in ["simulation", "test"]:
            connection_healthy = True
        else:
            # Check direct IP connections periodically if enabled
            if USE_IP:
                ip_connection_status["esp32_1"] = check_ip_connection(ESP32_1_IP)
                ip_connection_status["esp32_2"] = check_ip_connection(ESP32_2_IP)

            # Determine overall connection health
            if USE_MQTT and USE_IP:
                # If both methods are enabled, we're healthy if either is working
                connection_healthy = (
                    mqtt_connected
                    or ip_connection_status["esp32_1"]
                    or ip_connection_status["esp32_2"]
                )
            elif USE_MQTT:
                connection_healthy = mqtt_connected
            elif USE_IP:
                connection_healthy = (
                    ip_connection_status["esp32_1"] or ip_connection_status["esp32_2"]
                )
            else:
                # If no communication methods enabled, just run in visualization mode
                connection_healthy = True

            # If connections are down and we're in active mode, fade back to neutral
            if not connection_healthy and active_mode:
                print("All connections lost, fading back to neutral state")
                active_mode = False

        time.sleep(2)  # Check every 2 seconds


# Simulation trigger function
def simulation_trigger_loop():
    global active_mode, transition_progress, last_trigger_time

    while True:
        if args.mode == "simulation" and simulation_auto_trigger:
            current_time = time.time()

            # Check if it's time for another trigger
            if current_time - last_trigger_time >= auto_trigger_interval:
                # Toggle active mode
                active_mode = not active_mode
                transition_progress = 0.0 if active_mode else 1.0
                last_trigger_time = current_time
                print(
                    f"Simulation auto-trigger: Active mode {'ON' if active_mode else 'OFF'}"
                )

            # Check if simulation duration has been reached
            if (
                simulation_duration > 0
                and (current_time - start_time) >= simulation_duration
            ):
                print(
                    f"Simulation duration of {simulation_duration}s reached. Exiting."
                )
                os._exit(0)  # Force exit

        time.sleep(0.1)  # Check 10 times per second


# Initialize visualization if enabled
screen, clock = init_visualization()

# Start health check thread
health_thread = threading.Thread(target=connection_health_check, daemon=True)
health_thread.start()

# Start simulation trigger thread if in simulation mode
if args.mode == "simulation":
    simulation_thread = threading.Thread(target=simulation_trigger_loop, daemon=True)
    simulation_thread.start()
    simulation_auto_trigger = True  # Auto-trigger by default in simulation mode

print("\n===== LED ARCH LIGHT SHOW =====")
print(f"Mode: {args.mode}")
print(f"Visualization: {'Enabled' if VIZ_ENABLED else 'Disabled'}")
if args.mode == "production":
    print(f"MQTT Communication: {'Enabled' if USE_MQTT else 'Disabled'}")
    print(f"IP Communication: {'Enabled' if USE_IP else 'Disabled'}")
if args.mode == "simulation":
    print(f"Auto-trigger interval: {auto_trigger_interval}s")
    print(f"Simulation duration: {simulation_duration}s (0 = infinite)")


print("\nControls:")
print("  SPACE - Toggle active mode")
if args.mode == "simulation":
    print("  T - Toggle auto-trigger")
    print("  +/- - Adjust auto-trigger interval")

print("  ESC - Exit")
print("===============================\n")

# Main loop declarations
fade = 0  # ∈{0..1}
mask = deque([0] * 300, maxlen=300)  # static length, no need for POP
segment1 = deque([0] * 300, maxlen=300)  # 100 RGB LEDs, Elektra, Segment5, Hoop1
segment2 = deque([0] * 300, maxlen=300)  # 100 RGB LEDs, Elektra, Segment6, Hoop2
segment3 = deque([0] * 300, maxlen=300)  # 100 RGB LEDs, Eros, Segment5, Hoop3
blue_noise = deque([0] * 300, maxlen=300)  # blue noise left to right
red_noise = deque([0] * 300, maxlen=300)  # red noise right to left
noise_offset1 = 0
noise_offset2 = 0


# Main loop
try:
    # twinkle_offset = 0
    running = True

    while running:
        current_time = time.time()
        elapsed = current_time - last_update_time
        last_update_time = current_time

        # Handle visualization events
        if VIZ_ENABLED and pygame_available:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Toggle active mode for testing
                        active_mode = not active_mode
                        transition_progress = 0.0 if active_mode else 1.0
                        last_trigger_time = current_time
                        print(f"Manually toggled active mode: {active_mode}")
                    elif event.key == pygame.K_t and args.mode == "simulation":
                        # Toggle auto-trigger in simulation mode
                        simulation_auto_trigger = not simulation_auto_trigger
                        print(
                            f"Auto-trigger: {'enabled' if simulation_auto_trigger else 'disabled'}"
                        )
                    elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                        # Increase auto-trigger interval
                        auto_trigger_interval = min(60, auto_trigger_interval + 1)
                        print(f"Auto-trigger interval: {auto_trigger_interval}s")
                    elif event.key == pygame.K_MINUS:
                        # Decrease auto-trigger interval
                        auto_trigger_interval = max(1, auto_trigger_interval - 1)
                        print(f"Auto-trigger interval: {auto_trigger_interval}s")
                    elif event.key == pygame.K_ESCAPE:
                        running = False

        if elapsed < UPDATE_INTERVAL:
            if VIZ_ENABLED and clock and pygame_available:
                clock.tick(30)  # Cap visualization at 60 FPS
            else:
                time.sleep(0.001)  # Small sleep to prevent CPU hogging
            continue

        # Check connection health
        if not connection_healthy and active_mode:
            active_mode = False

        # Update transition mask
        if active_mode == True:
            fade += elapsed / TRANSITION_TIME
            if fade >= 1:
                fade = 1
        else:
            fade -= elapsed / TRANSITION_TIME
            if fade <= 0:
                fade = 0
        mask.appendleft(fade)

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
            index = i * 3
            if index < 300:
                segment1[index] = red_noise[i]  # Red value
                segment2[index] = red_noise[i + 100]  # Red value
                segment3[index] = red_noise[i + 200]  # Red value
            if index + 1 < 300:
                segment1[index + 1] = GREEN_MIX  # Green value
                segment2[index + 1] = GREEN_MIX  # Green value
                segment3[index + 1] = GREEN_MIX  # Green value
            if index + 2 < 300:
                segment1[index + 2] = blue_noise[i]  # Blue value
                segment2[index + 2] = blue_noise[i + 100]  # Blue value
                segment3[index + 2] = blue_noise[i + 200]  # Blue value

        print("Segments created")

        # Production mode: communicate with actual hardware
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

        # Update visualization
        if VIZ_ENABLED and screen and pygame_available:
            draw_visualization(screen, segment1, segment2, segment3)

except KeyboardInterrupt:
    print("\nExiting light show")
except Exception as e:
    print(f"Error in main loop: {e}")
finally:
    if args.mode == "production" and USE_MQTT and mqtt_connected and mqtt_client:
        mqtt_client.publish(MQTT_TOPIC_TRIGGER, "OFF", qos=1, retain=True)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if VIZ_ENABLED and pygame_available:
        pygame.quit()
    print("Light show terminated")
