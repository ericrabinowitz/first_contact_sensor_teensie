#!/bin/bash

echo "=== Fixing OCTO Clock Configuration ==="
echo

# Check current config
echo "Current /boot/config.txt audio settings:"
grep -E "audio|i2s|i2c|gpio" /boot/config.txt | grep -v "^#"

echo
echo "Adding GPIO clock configuration for OCTO..."

# The OCTO needs GPIO4 for master clock
sudo tee -a /boot/config.txt << EOF

# Audio Injector OCTO clock configuration
# Enable GPIO4 as clock output for CS42448
dtoverlay=i2s-gpio28-31
gpio=4=op,dh
EOF

echo
echo "Trying alternative overlay..."
# Remove current overlay
sudo sed -i '/dtoverlay=audioinjector-addons/d' /boot/config.txt

# Try the specific wm8731 overlay (some OCTOs use this)
sudo tee -a /boot/config.txt << EOF
# Try WM8731 overlay for Audio Injector
dtoverlay=audioinjector-wm8731-audio
EOF

echo
echo "Final configuration:"
grep -E "audio|overlay" /boot/config.txt | grep -v "^#"

echo
echo "IMPORTANT: The Audio Injector OCTO requires:"
echo "1. Physical connection to all 40 GPIO pins"
echo "2. Sufficient power supply (2.5A minimum recommended)"
echo "3. No other HATs or GPIO conflicts"
echo
echo "Please check:"
echo "- Is the OCTO firmly seated on all 40 pins?"
echo "- Are you using a good power supply?"
echo "- Remove any other HATs or GPIO connections"
echo
read -p "Reboot now to test? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi 