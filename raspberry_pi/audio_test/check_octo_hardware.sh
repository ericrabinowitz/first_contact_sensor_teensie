#!/bin/bash

echo "=== Audio Injector OCTO Hardware Check ==="
echo "========================================="
echo

echo "CRITICAL: Before proceeding, please verify:"
echo
echo "1. Is the OCTO HAT firmly connected to ALL 40 GPIO pins?"
echo "   - The board should be seated flat against the GPIO header"
echo "   - No visible gap between the HAT and the Pi"
echo
echo "2. Power supply check:"
echo "   - Are you using at least a 2.5A power supply?"
echo "   - Is the red PWR LED on the Pi steady (not blinking)?"
echo
echo "3. Visual inspection of the OCTO board:"
echo "   - Do you see any LEDs on the OCTO board?"
echo "   - Are there any bent pins on the GPIO connector?"
echo
echo "Press ENTER after verifying the above..."
read

echo
echo "Checking GPIO pins used by OCTO..."
gpio readall 2>/dev/null | grep -E "BCM (18|19|20|21|4)" || echo "GPIO tool not installed"

echo
echo "Checking if codec responds to different I2C speeds..."
echo "Trying 100kHz (standard speed):"
sudo modprobe -r i2c_bcm2835
sudo modprobe i2c_bcm2835 baudrate=100000
sleep 1
sudo i2cdetect -y 1

echo
echo "Checking power warnings:"
dmesg | grep -i "voltage" | tail -5

echo
echo "If you see:"
echo "- No device at 0x48: Hardware connection issue"
echo "- Device at 0x48 but codec fails: Clock/power issue"
echo "- Under-voltage warnings: Power supply issue" 