#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "backports.strenum", "paho-mqtt", "ultraimport", "sounddevice"
# ]
# ///
"""
MQTT Status Monitor for Missing Link installation.

Displays real-time connection status between statues by listening to the same
MQTT messages as the controller. Shows which statue is connected to which,
with placeholders for future level/SNR data.

This script runs independently from the controller and is useful for:
- Monitoring system status during development
- Debugging connection issues
- Remote monitoring from a development machine

Execute: ./status_monitor.py
"""

import json
import re
import signal
import sys
import threading
from typing import Any

import paho.mqtt.client as mqtt
import ultraimport as ui

Statue = ui.ultraimport("__dir__/../config/constants.py", "Statue")
LinkStateTracker = ui.ultraimport("__dir__/../contact/link_state.py", "LinkStateTracker")
StatusDisplay = ui.ultraimport("__dir__/../contact/display.py", "StatusDisplay")

# ### MQTT Configuration

# Topic for link/contact messages
LINK_MQTT_TOPIC = "missing_link/contact"
# {
#     "detector": "eros",      # Statue that detected the contact
#     "emitters": ["elektra"], # Statues currently linked to the detector
# }

# Topic for signal level reports
SIGNALS_MQTT_TOPIC = "missing_link/signals"
# {
#     "detector": "eros",
#     "signals": {
#         "elektra": 0.123,
#         "sophia": 0.045,
#         "ultimo": 0.001,
#         "ariel": 0.000
#     },
#     "threshold": 0.010
# }

# Topic for climax event status
CLIMAX_MQTT_TOPIC = "missing_link/climax"
# {
#     "state": "active" | "inactive",
#     "connected_pairs": [["eros", "elektra"], ...],
#     "missing_pairs": [["sophia", "ultimo"], ...]
# }

# MQTT broker settings - matches controller.py
MQTT_BROKER = "127.0.0.1"  # Default: localhost
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # Set if using authentication
MQTT_PASSWORD = None  # Set if using authentication
MQTT_QOS = 0  # Quality of Service (0 = at most once)

# Global variables
mqttc: Any = None
link_tracker: Any = None
status_display: Any = None
display_thread: Any = None

# Climax state tracking
climax_state: str = "inactive"
climax_connected_pairs: list = []
climax_missing_pairs: list = []


def create_mock_devices():
    """Create mock device list for display purposes.

    Since we're only monitoring MQTT, we don't have actual audio devices.
    Create a simple device list with all statues.
    """
    devices = []
    for idx, statue in enumerate(Statue):
        devices.append({
            "statue": statue,
            "channel_index": idx,
            "device_index": idx,
        })
    return devices


def on_connect(client, userdata, flags, reason_code, properties):
    """MQTT connection callback."""
    print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Connection result: {reason_code}")

    # Subscribe to contact topic
    client.subscribe(LINK_MQTT_TOPIC, qos=MQTT_QOS)
    print(f"Subscribed to topic: {LINK_MQTT_TOPIC}")

    # Subscribe to signals topic (includes threshold data)
    client.subscribe(SIGNALS_MQTT_TOPIC, qos=MQTT_QOS)
    print(f"Subscribed to topic: {SIGNALS_MQTT_TOPIC}")

    # Subscribe to climax topic
    client.subscribe(CLIMAX_MQTT_TOPIC, qos=MQTT_QOS)
    print(f"Subscribed to topic: {CLIMAX_MQTT_TOPIC}")

    print("\nWaiting for MQTT messages...\n")


def on_message(client, userdata, msg):
    """MQTT message callback - handles incoming contact and signals events."""
    try:
        # Handle contact events
        if msg.topic == LINK_MQTT_TOPIC:
            payload = json.loads(msg.payload)

            # Extract detector and emitters from payload
            detector_name = payload.get("detector", "")
            emitters_names = payload.get("emitters", [])

            # Convert to Statue enums
            try:
                detector = Statue(detector_name)
            except ValueError:
                print(f"Warning: Unknown detector statue: {detector_name}")
                return

            emitters = []
            for emitter_name in emitters_names:
                try:
                    emitter = Statue(emitter_name)
                    emitters.append(emitter)
                except ValueError:
                    print(f"Warning: Unknown emitter statue: {emitter_name}")

            # Update link tracker with new state
            link_tracker.update_detector_emitters(detector, emitters)

            # Update timestamp in display
            status_display.update_detector_timestamp(detector)

        # Handle signals events (includes threshold data)
        elif msg.topic == SIGNALS_MQTT_TOPIC:
            # Preprocess payload to handle NaN values from Teensy
            payload_str = msg.payload.decode('utf-8')
            # Replace nan/NaN with 0.0 (treat as no signal)
            #payload_str = re.sub(r'\bnan\b', '0.0', payload_str, flags=re.IGNORECASE)
            payload = json.loads(payload_str)

            # Extract detector, signals dict, and threshold
            detector_name = payload.get("detector", "")
            signals = payload.get("signals", {})
            threshold = payload.get("threshold", 0.0)

            try:
                detector = Statue(detector_name)
            except ValueError:
                print(f"Warning: Unknown detector statue: {detector_name}")
                return

            # Update threshold for this detector
            if threshold > 0:
                status_display.update_threshold(detector, threshold)

            # Update detection metrics for each emitter
            for emitter_name, level in signals.items():
                try:
                    emitter = Statue(emitter_name)
                    # Update display with signal level
                    status_display.update_metrics(detector, emitter, level)
                except ValueError:
                    print(f"Warning: Unknown emitter statue: {emitter_name}")
                except (TypeError, ValueError) as e:
                    print(f"Warning: Invalid signal level for {emitter_name}: {e}")

        # Handle climax events
        elif msg.topic == CLIMAX_MQTT_TOPIC:
            global climax_state, climax_connected_pairs, climax_missing_pairs

            payload = json.loads(msg.payload)

            # Extract climax state
            climax_state = payload.get("state", "inactive")
            climax_connected_pairs = payload.get("connected_pairs", [])
            climax_missing_pairs = payload.get("missing_pairs", [])

            # Update status display with climax data
            status_display.update_climax_state(climax_state, climax_connected_pairs, climax_missing_pairs)

    except json.JSONDecodeError:
        print(f"Warning: Failed to parse JSON message: {msg.payload}")
    except Exception as e:
        print(f"Error processing message: {e}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """MQTT disconnection callback."""
    print(f"\nDisconnected from MQTT broker: {reason_code}")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down...")

    # Stop display
    if status_display:
        status_display.stop()

    # Wait for display thread
    if display_thread and display_thread.is_alive():
        display_thread.join(timeout=1.0)

    # Disconnect MQTT
    if mqttc:
        mqttc.loop_stop()
        mqttc.disconnect()

    print("Goodbye!")
    sys.exit(0)


def main():
    """Main entry point for status monitor."""
    global mqttc, link_tracker, status_display, display_thread

    print("=== Missing Link MQTT Status Monitor ===\n")

    # Create link tracker (no audio playback, quiet mode)
    link_tracker = LinkStateTracker(playback=None, quiet=True)

    # Create mock devices for display
    devices = create_mock_devices()

    # Create status display in MQTT mode
    status_display = StatusDisplay(
        link_tracker=link_tracker,
        devices=devices,
        freq_controller=None,
        mqtt_mode=True
    )

    # Set up MQTT client
    mqttc = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        clean_session=True,
        client_id="status_monitor",
    )

    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Connect to MQTT broker
    try:
        mqttc.connect(MQTT_BROKER, MQTT_PORT)
    except Exception as e:
        print(f"Error: Failed to connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Details: {e}")
        print("\nMake sure the MQTT broker is running and accessible.")
        sys.exit(1)

    # Start MQTT loop in background
    mqttc.loop_start()

    # Start display thread
    display_thread = threading.Thread(target=status_display.run, daemon=True)
    display_thread.start()

    # Keep main thread alive
    try:
        while True:
            # Just wait - the display and MQTT threads handle everything
            display_thread.join(timeout=1.0)
            if not display_thread.is_alive():
                break
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
