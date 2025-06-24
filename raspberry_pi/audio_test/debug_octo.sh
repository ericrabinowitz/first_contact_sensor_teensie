#!/bin/bash

echo "=== Detailed OCTO Debug ==="
echo "=========================="
echo

echo "1. Check if codec driver is loaded:"
lsmod | grep cs42

echo
echo "2. Check for missing dependencies:"
sudo modprobe cs42xx8_i2c
sudo modprobe cs42xx8
sudo modprobe snd-soc-audioinjector-octo-soundcard

echo
echo "3. Check dmesg again after manual module load:"
dmesg | grep -E "cs42|octo|audioinjector" | tail -20

echo
echo "4. Try to manually configure ALSA:"
echo "Current ALSA configuration:"
cat /etc/asound.conf

echo
echo "5. Check if we need to remove conflicting USB audio:"
echo "Current module load order:"
cat /etc/modprobe.d/*.conf 2>/dev/null | grep -E "snd|audio"

echo
echo "6. Force card reordering (make OCTO card 0):"
echo "Creating modprobe config..."
sudo tee /etc/modprobe.d/audioinjector.conf << EOF
# Make Audio Injector OCTO the default card
options snd_usb_audio index=2,3
options snd-soc-audioinjector-octo-soundcard index=0
EOF

echo
echo "7. Reload ALSA:"
sudo alsa force-reload

echo
echo "8. Check devices again:"
aplay -l

echo
echo "If OCTO still doesn't appear, try rebooting one more time." 