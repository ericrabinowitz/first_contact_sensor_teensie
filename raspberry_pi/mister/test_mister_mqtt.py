#!/usr/bin/env python3
"""
Test script for MQTT-based mister control.
This script tests the MQTT communication between the main Pi and Pi Zero.
Run this on the main Pi to test sending commands to the Pi Zero mister controller.
"""

import json
import sys
import time
import argparse

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt module not found.")
    print("Install with: sudo apt install python3-paho-mqtt")
    sys.exit(1)


# Configuration
MQTT_BROKER = "192.168.4.1"  # Main Pi (local)
MQTT_PORT = 1883
MISTER_TOPIC = "missing_link/mister"
STATUS_TOPIC = "missing_link/mister/status"

# Global variables
client = None
last_status = None


def on_connect(mqttc, userdata, flags, rc):
    """Callback for when the client connects to the MQTT broker."""
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        # Subscribe to status topic to see responses
        mqttc.subscribe(STATUS_TOPIC)
        print(f"Subscribed to status topic: {STATUS_TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(mqttc, userdata, msg):
    """Callback for status messages from Pi Zero."""
    global last_status
    try:
        payload = json.loads(msg.payload.decode())
        last_status = payload
        
        status = payload.get("status", "unknown")
        remaining = payload.get("remaining_seconds", 0)
        
        if status == "active":
            print(f"Mister Status: ACTIVE ({remaining} seconds remaining)")
        else:
            print(f"Mister Status: {status.upper()}")
            
    except json.JSONDecodeError as e:
        print(f"Error parsing status message: {e}")


def send_command(action, duration=None):
    """Send a command to the mister controller."""
    payload = {"action": action}
    
    if duration is not None:
        payload["duration"] = duration
    
    print(f"Sending command: {payload}")
    client.publish(MISTER_TOPIC, json.dumps(payload), qos=1)


def test_basic():
    """Run basic activation test."""
    print("\n=== Basic Mister Test ===")
    print("Activating mister for 5 seconds...")
    
    send_command("activate", duration=5)
    time.sleep(1)
    
    # Request status
    send_command("status")
    time.sleep(1)
    
    print("Waiting for mister to complete...")
    time.sleep(5)
    
    # Final status check
    send_command("status")
    time.sleep(1)
    
    print("Basic test complete!")


def test_interrupt():
    """Test interrupting an active mister."""
    print("\n=== Interrupt Test ===")
    print("Activating mister for 10 seconds...")
    
    send_command("activate", duration=10)
    time.sleep(2)
    
    print("Interrupting after 2 seconds...")
    send_command("deactivate")
    time.sleep(1)
    
    send_command("status")
    time.sleep(1)
    
    print("Interrupt test complete!")


def test_multiple():
    """Test multiple activations."""
    print("\n=== Multiple Activation Test ===")
    
    for i in range(3):
        print(f"\nCycle {i+1}/3:")
        send_command("activate", duration=3)
        time.sleep(4)
    
    print("Multiple activation test complete!")


def simulate_all_statues():
    """Simulate all 5 statues connecting (triggers mister)."""
    print("\n=== Simulating All Statues Connected ===")
    print("Publishing contact event with all 5 statues...")
    
    # This simulates what the controller would receive
    contact_payload = {
        "detector": "ultimo",
        "emitters": ["eros", "elektra", "sophia", "ariel"]
    }
    
    print(f"Publishing to missing_link/contact: {contact_payload}")
    client.publish("missing_link/contact", json.dumps(contact_payload), qos=1)
    
    print("Waiting for mister activation (10 seconds)...")
    time.sleep(12)
    
    print("Simulation complete!")


def interactive_mode():
    """Interactive control mode."""
    print("\n=== Interactive Mister Control ===")
    print("Commands:")
    print("  on [duration] - Activate mister (default 10s)")
    print("  off          - Deactivate mister")
    print("  status       - Request current status")
    print("  simulate     - Simulate all statues connected")
    print("  quit         - Exit")
    print()
    
    while True:
        try:
            cmd = input("Command: ").strip().lower().split()
            
            if not cmd:
                continue
                
            if cmd[0] in ["on", "activate"]:
                duration = int(cmd[1]) if len(cmd) > 1 else 10
                send_command("activate", duration=duration)
                
            elif cmd[0] in ["off", "deactivate"]:
                send_command("deactivate")
                
            elif cmd[0] == "status":
                send_command("status")
                time.sleep(0.5)  # Give time for response
                
            elif cmd[0] == "simulate":
                simulate_all_statues()
                
            elif cmd[0] in ["quit", "q", "exit"]:
                print("Exiting...")
                break
                
            else:
                print(f"Unknown command: {cmd[0]}")
                
        except KeyboardInterrupt:
            print("\nInterrupted")
            break
        except ValueError as e:
            print(f"Error: {e}")


def main():
    """Main entry point."""
    global client
    
    parser = argparse.ArgumentParser(description="Test MQTT mister control")
    parser.add_argument("--broker", default=MQTT_BROKER,
                       help="MQTT broker address")
    parser.add_argument("--port", type=int, default=MQTT_PORT,
                       help="MQTT broker port")
    parser.add_argument("--basic", action="store_true",
                       help="Run basic test")
    parser.add_argument("--interrupt", action="store_true",
                       help="Run interrupt test")
    parser.add_argument("--multiple", action="store_true",
                       help="Run multiple activation test")
    parser.add_argument("--simulate", action="store_true",
                       help="Simulate all statues connected")
    parser.add_argument("--interactive", action="store_true",
                       help="Interactive control mode")
    
    args = parser.parse_args()
    
    # Update configuration
    MQTT_BROKER = args.broker
    MQTT_PORT = args.port
    
    print("MQTT Mister Control Test")
    print("========================")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Command Topic: {MISTER_TOPIC}")
    print(f"Status Topic: {STATUS_TOPIC}")
    print()
    
    # Setup MQTT client
    client = mqtt.Client(client_id="mister_test_client")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("Connecting to MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Give time to connect
        time.sleep(1)
        
        # Run requested tests
        if args.basic:
            test_basic()
        elif args.interrupt:
            test_interrupt()
        elif args.multiple:
            test_multiple()
        elif args.simulate:
            simulate_all_statues()
        elif args.interactive:
            interactive_mode()
        else:
            # Default to interactive mode
            print("No test specified, entering interactive mode...")
            interactive_mode()
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        print("\nDisconnecting from MQTT broker...")
        client.loop_stop()
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())