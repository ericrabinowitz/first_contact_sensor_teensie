#!/bin/bash

echo "=== Verifying Audio Injector OCTO ==="
echo "====================================="
echo

echo "1. Audio devices:"
echo "-----------------"
aplay -l

echo
echo "2. ALSA cards:"
echo "--------------"
cat /proc/asound/cards

echo
echo "3. I2C devices (should show devices at addresses):"
echo "--------------------------------------------------"
sudo i2cdetect -y 1 2>/dev/null || echo "i2cdetect not installed, install with: sudo apt-get install i2c-tools"

echo
echo "4. Kernel messages about Audio Injector:"
echo "----------------------------------------"
dmesg | grep -i "audio.*inject\|inject.*audio" | tail -10

echo
echo "5. Test speaker output (8 channels):"
echo "------------------------------------"
echo "This will play a test tone on each of the 8 output channels."
echo "You should hear sound from different speakers in sequence."
echo
read -p "Run speaker test? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    speaker-test -c 8 -t wav -l 1
fi 