#!/usr/bin/env python3
"""Monitor MQTT messages for WLED debugging."""

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime

# MQTT settings
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883

# Topics to monitor
TOPICS = [
    "missing_link/contact",      # Contact events from statues
    "wled/+/api",                # WLED commands (+ is wildcard for board name)
    "missing_link/haptic",       # Haptic feedback
]


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker."""
    print(f"Connected to MQTT broker with result code {reason_code}")
    for topic in TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to: {topic}")


def on_message(client, userdata, msg):
    """Callback when message received."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    topic = msg.topic
    
    print(f"\n[{timestamp}] Topic: {topic}")
    
    try:
        payload = json.loads(msg.payload)
        
        # Parse based on topic
        if "contact" in topic:
            detector = payload.get("detector", "?")
            emitters = payload.get("emitters", [])
            print(f"  Contact Event:")
            print(f"    Detector: {detector}")
            print(f"    Emitters: {emitters}")
            if len(emitters) == 0:
                print("    >>> STATUE UNLINKED - Should trigger DORMANT state")
            else:
                print("    >>> STATUE LINKED - Should trigger ACTIVE state")
                
        elif "wled" in topic:
            board = topic.split("/")[1]
            print(f"  WLED Command to board: {board}")
            
            # Check if turning on/off
            if "on" in payload:
                print(f"    Power: {'ON' if payload['on'] else 'OFF'}")
            
            # Check brightness
            if "bri" in payload:
                print(f"    Global Brightness: {payload['bri']}")
            
            # Check segments
            if "seg" in payload:
                for seg in payload["seg"]:
                    seg_id = seg.get("id", "?")
                    fx = seg.get("fx", None)
                    bri = seg.get("bri", None)
                    col = seg.get("col", None)
                    
                    print(f"    Segment {seg_id}:")
                    if fx is not None:
                        effect_names = {
                            0: "SOLID",
                            42: "FIREWORKS (ACTIVE)",
                            71: "NOISE_2 (DORMANT)",
                            41: "LIGHTHOUSE",
                        }
                        effect_name = effect_names.get(fx, f"Effect_{fx}")
                        print(f"      Effect: {effect_name} (ID: {fx})")
                    if bri is not None:
                        print(f"      Brightness: {bri}")
                    if col:
                        print(f"      Colors: {col}")
                        
        elif "haptic" in topic:
            print(f"  Haptic Event: {payload}")
            
    except json.JSONDecodeError:
        print(f"  Raw payload: {msg.payload}")
    except Exception as e:
        print(f"  Error parsing: {e}")
        print(f"  Raw payload: {msg.payload}")


def main():
    """Main monitoring loop."""
    print("="*60)
    print("WLED MQTT Monitor - Watching for dormant state issues")
    print("="*60)
    print("\nMonitoring topics:")
    for topic in TOPICS:
        print(f"  - {topic}")
    print("\nLooking for:")
    print("  1. Contact events with empty emitters (should trigger dormant)")
    print("  2. WLED commands with NOISE_2 effect (ID: 71)")
    print("  3. Brightness levels in dormant state")
    print("\nPress Ctrl+C to exit\n")
    
    # Create MQTT client
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTProtocolVersion.MQTTv311,
        client_id="wled_monitor",
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect and start loop
    client.connect(MQTT_BROKER, MQTT_PORT)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        client.disconnect()


if __name__ == "__main__":
    main()