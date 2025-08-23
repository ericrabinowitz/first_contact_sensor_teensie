#!/usr/bin/env python3
"""
Mister Controller for Pi Zero 2
Runs on Pi Zero 2 (rpi-ntp) and listens for MQTT commands to control the mister relay.
This allows the main Pi to delegate GPIO control to the Pi Zero.
"""

import json
import sys
import time
import threading
import signal
from datetime import datetime

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO module not found.")
    print("Install with: sudo apt install python3-rpi.gpio")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt module not found.")
    print("Install with: sudo apt install python3-paho-mqtt")
    sys.exit(1)


# Configuration
MQTT_BROKER = "192.168.4.1"  # Main Pi IP address
MQTT_PORT = 1883
MQTT_TOPIC = "missing_link/mister"
MQTT_STATUS_TOPIC = "missing_link/mister/status"
MQTT_CLIENT_ID = "mister_controller_pi_zero"

# GPIO Configuration
MISTER_RELAY_PIN = 4  # GPIO 4 (Physical Pin 7)
DEFAULT_DURATION = 10  # Default duration in seconds

# Global state
mister_timer = None
mister_active = False
activation_time = None
duration_seconds = 0
debug = False
mqtt_client = None
running = True


def setup_gpio():
    """Initialize GPIO for relay control."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MISTER_RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)
    print(f"GPIO {MISTER_RELAY_PIN} initialized for relay control")


def activate_mister(duration=DEFAULT_DURATION):
    """Activate the mister for specified duration."""
    global mister_timer, mister_active, activation_time, duration_seconds
    
    # Cancel any existing timer
    if mister_timer is not None:
        mister_timer.cancel()
    
    duration_seconds = duration
    activation_time = datetime.now()
    
    if mister_active:
        if debug:
            print(f"Mister already active, resetting timer to {duration} seconds")
    else:
        print(f"Activating mister for {duration} seconds")
    
    # Turn relay ON (LOW for low-level trigger)
    GPIO.output(MISTER_RELAY_PIN, GPIO.LOW)
    mister_active = True
    
    # Publish status
    publish_status()
    
    # Create timer to turn off after duration
    mister_timer = threading.Timer(duration, deactivate_mister)
    mister_timer.start()


def deactivate_mister():
    """Deactivate the mister."""
    global mister_active, activation_time, duration_seconds
    
    print("Deactivating mister")
    
    # Turn relay OFF (HIGH for low-level trigger)
    GPIO.output(MISTER_RELAY_PIN, GPIO.HIGH)
    mister_active = False
    activation_time = None
    duration_seconds = 0
    
    # Publish status
    publish_status()


def get_remaining_seconds():
    """Calculate remaining seconds for active mister."""
    if not mister_active or activation_time is None:
        return 0
    
    elapsed = (datetime.now() - activation_time).total_seconds()
    remaining = max(0, duration_seconds - elapsed)
    return int(remaining)


def publish_status():
    """Publish current mister status to MQTT."""
    if mqtt_client is None:
        return
    
    status = {
        "status": "active" if mister_active else "inactive",
        "remaining_seconds": get_remaining_seconds(),
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(status), qos=1)
        if debug:
            print(f"Published status: {status}")
    except Exception as e:
        print(f"Error publishing status: {e}")


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the MQTT broker."""
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
        
        # Publish initial status
        publish_status()
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")


def on_message(client, userdata, msg):
    """Callback for when a message is received from the MQTT broker."""
    try:
        payload = json.loads(msg.payload.decode())
        action = payload.get("action", "")
        
        if debug:
            print(f"Received MQTT message: {payload}")
        
        if action == "activate":
            duration = payload.get("duration", DEFAULT_DURATION)
            activate_mister(duration)
            
        elif action == "deactivate":
            if mister_timer is not None:
                mister_timer.cancel()
            deactivate_mister()
            
        elif action == "status":
            publish_status()
            
        else:
            print(f"Unknown action: {action}")
            
    except json.JSONDecodeError as e:
        print(f"Error parsing MQTT message: {e}")
    except Exception as e:
        print(f"Error handling MQTT message: {e}")


def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the MQTT broker."""
    if rc != 0:
        print(f"Unexpected disconnection from MQTT broker (rc={rc})")
        # Will automatically reconnect due to loop_forever()


def setup_mqtt():
    """Initialize MQTT client and connect to broker."""
    global mqtt_client
    
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    
    # Enable automatic reconnection
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        return True
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        return False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\nShutdown signal received...")
    running = False
    
    # Clean shutdown
    if mister_timer is not None:
        mister_timer.cancel()
    
    # Ensure mister is OFF
    GPIO.output(MISTER_RELAY_PIN, GPIO.HIGH)
    
    if mqtt_client is not None:
        # Publish final status
        deactivate_mister()
        mqtt_client.disconnect()
    
    GPIO.cleanup()
    print("Cleanup complete")
    sys.exit(0)


def main():
    """Main entry point."""
    global debug
    
    # Check for debug mode
    debug = "--debug" in sys.argv or "-d" in sys.argv
    
    print("=================================")
    print("Mister Controller for Pi Zero 2")
    print("=================================")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"MQTT Topic: {MQTT_TOPIC}")
    print(f"GPIO Pin: {MISTER_RELAY_PIN}")
    print(f"Default Duration: {DEFAULT_DURATION} seconds")
    if debug:
        print("Debug mode enabled")
    print()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize GPIO
    setup_gpio()
    
    # Connect to MQTT broker
    print("Connecting to MQTT broker...")
    if not setup_mqtt():
        print("Failed to connect to MQTT broker")
        GPIO.cleanup()
        return 1
    
    # Start MQTT loop
    print("Starting MQTT client loop...")
    print("Press Ctrl+C to exit")
    
    try:
        # This will handle reconnections automatically
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"Error in main loop: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())