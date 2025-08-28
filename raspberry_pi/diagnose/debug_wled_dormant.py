#!/usr/bin/env python3
"""Debug script for testing WLED dormant state issues on playa."""

import json
import sys
import time
import requests
import paho.mqtt.client as mqtt

# MQTT settings (same as controller.py)
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
WLED_MQTT_TOPIC = "wled/{}/api"

# Test configurations
TEST_EFFECTS = {
    "SOLID": 0,
    "FIREWORKS": 42,
    "NOISE_1": 70,
    "NOISE_2": 71,  # Current dormant effect
    "NOISE_3": 72,
    "NOISE_4": 73,
    "SPARKLE": 20,
    "DARK_SPARKLE": 21,
    "TWINKLE": 17,
    "DISSOLVE": 18,
}

TEST_BRIGHTNESS = {
    "VERY_LOW": 32,
    "LOW": 64,
    "MEDIUM": 127,  # Current dormant brightness
    "HIGH": 192,
    "MAX": 255,
}

DORMANT_COLOR = [[255, 255, 255], [0, 0, 0], [0, 0, 0]]  # White to black
ACTIVE_COLOR = [[255, 0, 100], [225, 0, 255], [255, 0, 100]]  # Red/pink

# Board names
BOARDS = ["five_v_1", "five_v_2", "twelve_v_1"]


def send_mqtt_command(board, payload):
    """Send WLED command via MQTT."""
    mqttc = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        client_id="debug_wled",
    )
    mqttc.connect(MQTT_BROKER, MQTT_PORT)
    topic = WLED_MQTT_TOPIC.format(board)
    print(f"Publishing to {topic}: {json.dumps(payload, indent=2)}")
    mqttc.publish(topic, json.dumps(payload))
    mqttc.disconnect()
    time.sleep(0.5)  # Give time for command to process


def test_dormant_state(effect_name="NOISE_2", brightness_name="MEDIUM"):
    """Test dormant state with specified effect and brightness."""
    effect_id = TEST_EFFECTS[effect_name]
    brightness = TEST_BRIGHTNESS[brightness_name]

    print(f"\n=== Testing Dormant State ===")
    print(f"Effect: {effect_name} (ID: {effect_id})")
    print(f"Brightness: {brightness_name} ({brightness})")
    print(f"Color: {DORMANT_COLOR}")

    payload = {
        "tt": 0,
        "on": True,
        "bri": brightness,
        "seg": [
            {
                "id": 3,  # Test on first segment
                "bri": brightness,
                "col": DORMANT_COLOR,
                "fx": effect_id,
                "pal": 3,  # Palette ID
            }
        ],
    }

    for board in BOARDS:
        print(f"\nSending to board: {board}")
        send_mqtt_command(board, payload)


def test_active_state():
    """Test active state (FIREWORKS effect) for comparison."""
    print(f"\n=== Testing Active State (FIREWORKS) ===")
    print(f"Effect: FIREWORKS (ID: {TEST_EFFECTS['FIREWORKS']})")
    print(f"Brightness: MAX ({TEST_BRIGHTNESS['MAX']})")
    print(f"Color: {ACTIVE_COLOR}")

    payload = {
        "tt": 0,
        "on": True,
        "bri": TEST_BRIGHTNESS["MAX"],
        "seg": [
            {
                "id": 0,
                "bri": TEST_BRIGHTNESS["MAX"],
                "col": ACTIVE_COLOR,
                "fx": TEST_EFFECTS["FIREWORKS"],
                "pal": 3,
            }
        ],
    }

    for board in BOARDS:
        print(f"\nSending to board: {board}")
        send_mqtt_command(board, payload)


def test_all_effects():
    """Cycle through all test effects to find visible ones."""
    print("\n=== Testing All Effects ===")
    print("Each effect will run for 3 seconds...")

    for effect_name, effect_id in TEST_EFFECTS.items():
        print(f"\nTesting: {effect_name} (ID: {effect_id})")

        payload = {
            "tt": 0,
            "on": True,
            "bri": TEST_BRIGHTNESS["HIGH"],
            "seg": [
                {
                    "id": 0,
                    "bri": TEST_BRIGHTNESS["HIGH"],
                    "col": DORMANT_COLOR,
                    "fx": effect_id,
                    "pal": 3,
                }
            ],
        }

        for board in BOARDS:
            send_mqtt_command(board, payload)

        time.sleep(3)


def test_brightness_levels():
    """Test different brightness levels with NOISE_2 effect."""
    print("\n=== Testing Brightness Levels with NOISE_2 ===")
    print("Each brightness level will run for 3 seconds...")

    for brightness_name, brightness in TEST_BRIGHTNESS.items():
        print(f"\nTesting brightness: {brightness_name} ({brightness})")

        payload = {
            "tt": 0,
            "on": True,
            "bri": brightness,
            "seg": [
                {
                    "id": 0,
                    "bri": brightness,
                    "col": DORMANT_COLOR,
                    "fx": TEST_EFFECTS["NOISE_2"],
                    "pal": 3,
                }
            ],
        }

        for board in BOARDS:
            send_mqtt_command(board, payload)

        time.sleep(3)


def turn_off():
    """Turn off all LEDs."""
    print("\n=== Turning OFF all LEDs ===")
    payload = {
        "tt": 0,
        "on": False,
        "bri": 0,
    }

    for board in BOARDS:
        send_mqtt_command(board, payload)


def main():
    """Main menu for testing."""
    while True:
        print("\n" + "="*50)
        print("WLED Dormant State Debugging")
        print("="*50)
        print("1. Test current dormant state (NOISE_2, brightness=127)")
        print("2. Test active state (FIREWORKS for comparison)")
        print("3. Test all effects (cycle through)")
        print("4. Test brightness levels (with NOISE_2)")
        print("5. Test custom effect")
        print("6. Turn OFF all LEDs")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            test_dormant_state()
        elif choice == "2":
            test_active_state()
        elif choice == "3":
            test_all_effects()
        elif choice == "4":
            test_brightness_levels()
        elif choice == "5":
            print("\nAvailable effects:")
            for name in TEST_EFFECTS.keys():
                print(f"  {name}")
            effect = input("Enter effect name: ").strip().upper()

            print("\nAvailable brightness levels:")
            for name in TEST_BRIGHTNESS.keys():
                print(f"  {name}")
            brightness = input("Enter brightness level: ").strip().upper()

            if effect in TEST_EFFECTS and brightness in TEST_BRIGHTNESS:
                test_dormant_state(effect, brightness)
            else:
                print("Invalid effect or brightness!")
        elif choice == "6":
            turn_off()
        elif choice == "0":
            break
        else:
            print("Invalid option!")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        turn_off()