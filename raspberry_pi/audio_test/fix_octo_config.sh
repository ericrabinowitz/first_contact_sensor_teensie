#!/bin/bash

echo "=== OCTO Configuration Fix ==="
echo "=============================="
echo

# Check current config
echo "1. Current /boot/config.txt audio settings:"
grep -E "(audio|audioinjector)" /boot/config.txt

echo
echo "2. Checking if non_stop_clocks is already set..."
if grep -q "dtoverlay=audioinjector-addons,non_stop_clocks" /boot/config.txt; then
    echo "✓ non_stop_clocks is already enabled"
else
    echo "✗ non_stop_clocks is NOT enabled"
    echo
    echo "3. Fixing configuration..."
    
    # Backup current config
    sudo cp /boot/config.txt /boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)
    
    # Replace the dtoverlay line
    sudo sed -i 's/^dtoverlay=audioinjector-addons$/dtoverlay=audioinjector-addons,non_stop_clocks/' /boot/config.txt
    
    echo "Updated /boot/config.txt"
    echo
    echo "New audio settings:"
    grep -E "(audio|audioinjector)" /boot/config.txt
fi

echo
echo "4. Testing current behavior with speaker-test..."
echo "This will play a 1kHz tone on channel 1 only"
echo "Listen if it rotates between speakers or stays on one"
echo
read -p "Press Enter to test..."

speaker-test -D hw:2,0 -c 8 -s 1 -f 1000 -t sine -l 1

echo
echo "5. Additional fixes from GitHub issues:"
echo "- Remove pulseaudio if installed"
if dpkg -l | grep -q pulseaudio; then
    echo "  Pulseaudio is installed. Consider removing with:"
    echo "  sudo apt remove pulseaudio"
fi

echo
echo "- Check I2C speed (should be 100kHz for stability)"
grep "i2c_baudrate" /boot/config.txt || echo "  No I2C speed set"

echo
echo "IMPORTANT: If you made any changes, you need to reboot!"
echo "After reboot, the 'purring' and rotation should stop."
echo
echo "If problems persist after reboot, try:"
echo "1. Check for shorts or loose connections"
echo "2. Ensure adequate power supply"
echo "3. Keep Pi temperature below 70°C"
echo "4. Try the channel unscrambling workaround" 