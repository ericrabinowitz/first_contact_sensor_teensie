#!/bin/bash
# Pi Zero Mister Controller Setup Script
# Sets up a Raspberry Pi Zero 2 as a mister controller that responds to MQTT commands
# Run on Pi Zero 2 (rpi-ntp) with: bash pi_zero_mister_setup.sh

set -e  # Exit on error

echo "======================================"
echo "Pi Zero Mister Controller Setup"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   print_error "Please run without sudo"
   exit 1
fi

# Configuration
REPO_DIR="/home/pi/first_contact_sensor_teensie"
MISTER_DIR="${REPO_DIR}/raspberry_pi/mister"
SERVICE_FILE="mister.service"

# 1. Update system
print_status "Updating system packages..."
sudo apt update

# 2. Install required packages
print_status "Installing required packages..."
sudo apt install -y python3-rpi.gpio python3-paho-mqtt git

# 3. Clone or update repository
if [ -d "$REPO_DIR" ]; then
    print_status "Repository exists, updating..."
    cd "$REPO_DIR"
    git pull
else
    print_status "Cloning repository..."
    cd /home/pi
    git clone https://github.com/ericrabinowitz/first_contact_sensor_teensie.git
fi

# 4. Check if mister controller files exist
if [ ! -f "${MISTER_DIR}/mister_controller.py" ]; then
    print_error "Mister controller script not found at ${MISTER_DIR}/mister_controller.py"
    exit 1
fi

if [ ! -f "${MISTER_DIR}/${SERVICE_FILE}" ]; then
    print_error "Service file not found at ${MISTER_DIR}/${SERVICE_FILE}"
    exit 1
fi

print_status "Mister controller files found"

# 5. Make script executable
chmod +x "${MISTER_DIR}/mister_controller.py"
print_status "Made mister_controller.py executable"

# 6. Test GPIO access
print_status "Testing GPIO access..."
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()" 2>/dev/null || {
    print_warning "GPIO test failed - you may need to add user to gpio group"
    sudo usermod -a -G gpio $USER
    print_status "Added $USER to gpio group - reboot required"
}

# 7. Test MQTT connectivity
print_status "Testing MQTT broker connectivity..."
if ping -c 1 192.168.4.1 &> /dev/null; then
    print_status "Can reach main Pi at 192.168.4.1"
    
    # Try to connect to MQTT broker
    python3 -c "
import paho.mqtt.client as mqtt
import sys
try:
    client = mqtt.Client()
    client.connect('192.168.4.1', 1883, 2)
    client.disconnect()
    print('MQTT broker connection successful')
    sys.exit(0)
except:
    print('Cannot connect to MQTT broker - will retry when service starts')
    sys.exit(1)
" || print_warning "MQTT broker not accessible yet - ensure mosquitto is running on main Pi"
else
    print_warning "Cannot reach main Pi at 192.168.4.1 - check network configuration"
fi

# 8. Install systemd service
print_status "Installing systemd service..."
sudo cp "${MISTER_DIR}/${SERVICE_FILE}" /etc/systemd/system/
sudo systemctl daemon-reload
print_status "Service file installed"

# 9. Enable service to start on boot
print_status "Enabling mister service..."
sudo systemctl enable mister.service
print_status "Mister service enabled"

# 10. Start the service
print_status "Starting mister service..."
sudo systemctl start mister.service

# Wait a moment for service to start
sleep 2

# 11. Check service status
if sudo systemctl is-active --quiet mister.service; then
    print_status "Mister service is running"
else
    print_error "Mister service failed to start"
    echo "Check logs with: sudo journalctl -u mister.service -n 50"
fi

# 12. Create test script
print_status "Creating local test script..."
cat > /home/pi/test_relay.py << 'EOF'
#!/usr/bin/env python3
"""Quick test of relay on Pi Zero"""
import RPi.GPIO as GPIO
import time
import sys

RELAY_PIN = 4

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)
    
    print("Testing relay on GPIO 4...")
    print("Relay ON (you should hear a click)")
    GPIO.output(RELAY_PIN, GPIO.LOW)
    time.sleep(2)
    
    print("Relay OFF (you should hear another click)")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    
    GPIO.cleanup()
    print("Test complete!")
    
except Exception as e:
    print(f"Error: {e}")
    GPIO.cleanup()
    sys.exit(1)
EOF

chmod +x /home/pi/test_relay.py
print_status "Created test_relay.py in home directory"

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================"
echo ""
echo "Mister controller is now installed and running."
echo ""
echo "Service Management:"
echo "  Check status:  sudo systemctl status mister"
echo "  View logs:     sudo journalctl -u mister -f"
echo "  Restart:       sudo systemctl restart mister"
echo "  Stop:          sudo systemctl stop mister"
echo ""
echo "Testing:"
echo "  Test relay locally:  python3 ~/test_relay.py"
echo "  Test from main Pi:  python3 ~/first_contact_sensor_teensie/raspberry_pi/mister/test_mister_mqtt.py"
echo ""
echo "Hardware Connections:"
echo "  GPIO 4 (Pin 7) → Relay IN1"
echo "  5V (Pin 2)     → Relay VCC"
echo "  GND (Pin 6)    → Relay GND"
echo ""
echo "MQTT Topics:"
echo "  Commands: missing_link/mister"
echo "  Status:   missing_link/mister/status"
echo ""

# Check if reboot is needed
if [ -f /var/run/reboot-required ]; then
    print_warning "Reboot required to complete setup"
    echo "Reboot now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
fi