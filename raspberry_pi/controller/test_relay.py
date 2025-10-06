#!/usr/bin/env python3
"""
Test script for relay control functionality.
This script tests the GPIO relay control for the mister independently
of the main controller script.

Usage:
    python3 test_relay.py           # Run a basic 3-second test
    python3 test_relay.py --manual   # Manual control mode
    python3 test_relay.py --cycle    # Cycle relay on/off repeatedly
"""

import sys
import time
import argparse

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO module not found.")
    print("Install with: sudo apt install python3-rpi.gpio")
    sys.exit(1)

# Configuration - matches controller.py
MISTER_RELAY_PIN = 4  # GPIO 4 (Physical Pin 7)


def setup_gpio():
    """Initialize GPIO for relay control."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MISTER_RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)
    print(f"GPIO {MISTER_RELAY_PIN} initialized (Physical Pin 7)")
    print("Relay starts in OFF state (HIGH = OFF for low-level trigger)")


def relay_on():
    """Turn relay ON."""
    GPIO.output(MISTER_RELAY_PIN, GPIO.LOW)
    print("Relay ON (GPIO LOW)")


def relay_off():
    """Turn relay OFF."""
    GPIO.output(MISTER_RELAY_PIN, GPIO.HIGH)
    print("Relay OFF (GPIO HIGH)")


def basic_test():
    """Run a basic relay test - turn on for 3 seconds."""
    print("\n=== Basic Relay Test ===")
    print("Testing relay control - will turn ON for 3 seconds")
    
    relay_on()
    print("Relay should be ON now...")
    time.sleep(3)
    
    relay_off()
    print("Relay should be OFF now")
    print("Basic test complete!")


def manual_control():
    """Manual control mode - interactive relay control."""
    print("\n=== Manual Relay Control ===")
    print("Commands:")
    print("  on  - Turn relay ON")
    print("  off - Turn relay OFF")
    print("  quit - Exit program")
    print()
    
    while True:
        try:
            cmd = input("Enter command: ").strip().lower()
            
            if cmd == "on":
                relay_on()
            elif cmd == "off":
                relay_off()
            elif cmd in ["quit", "q", "exit"]:
                print("Exiting...")
                break
            else:
                print(f"Unknown command: {cmd}")
        except KeyboardInterrupt:
            print("\nInterrupted")
            break


def cycle_test():
    """Cycle relay on/off repeatedly."""
    print("\n=== Cycle Test ===")
    print("Will cycle relay ON/OFF every 2 seconds")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        cycle = 0
        while True:
            cycle += 1
            print(f"Cycle {cycle}: ON")
            relay_on()
            time.sleep(2)
            
            print(f"Cycle {cycle}: OFF")
            relay_off()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping cycle test")
        relay_off()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test relay control for mister")
    parser.add_argument("--manual", action="store_true", 
                       help="Enter manual control mode")
    parser.add_argument("--cycle", action="store_true",
                       help="Cycle relay on/off repeatedly")
    
    args = parser.parse_args()
    
    print("Relay Test Script")
    print("=================")
    print(f"Using GPIO {MISTER_RELAY_PIN} (Physical Pin 7)")
    print("Relay module: SunFounder 2 Channel 5V (low-level trigger)")
    print()
    
    try:
        setup_gpio()
        
        if args.manual:
            manual_control()
        elif args.cycle:
            cycle_test()
        else:
            basic_test()
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        print("\nCleaning up GPIO...")
        relay_off()  # Ensure relay is OFF
        GPIO.cleanup()
        print("GPIO cleanup complete")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())