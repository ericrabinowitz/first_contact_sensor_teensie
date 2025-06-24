#!/bin/bash

echo "=== OCTO Raw Mode Configuration ==="
echo "==================================="
echo

# Check if amixer can control the OCTO
echo "1. Checking OCTO mixer controls..."
amixer -c 2 contents

echo
echo "2. Checking for any ALSA controls..."
alsactl -f /tmp/octo_state.txt store 2
cat /tmp/octo_state.txt | grep -A5 -B5 "name\|value"

echo
echo "3. Testing raw 8-channel output with sox"
echo "Installing sox if needed..."
which sox || sudo apt-get install -y sox

echo
echo "4. Generating 8 separate test files..."
for i in {0..7}; do
    freq=$((200 + i * 100))
    echo "Creating channel $((i+1)) test file: ${freq}Hz"
    sox -n -r 48000 -c 1 /tmp/ch${i}.wav synth 2 sine $freq gain -20
done

echo
echo "5. Combining into 8-channel file..."
sox -M /tmp/ch0.wav /tmp/ch1.wav /tmp/ch2.wav /tmp/ch3.wav \
       /tmp/ch4.wav /tmp/ch5.wav /tmp/ch6.wav /tmp/ch7.wav \
       /tmp/test_8ch_raw.wav

echo
echo "6. Playing combined file (each channel should have different frequency)..."
aplay -D hw:2,0 /tmp/test_8ch_raw.wav

echo
echo "7. Alternative: Create simple ALSA config without routing"
sudo tee /etc/asound.conf.simple << 'EOF'
# Simple OCTO configuration - no routing
pcm.!default {
    type hw
    card 2
}

ctl.!default {
    type hw
    card 2
}
EOF

echo
echo "8. Testing with simple config..."
sudo mv /etc/asound.conf /etc/asound.conf.complex
sudo mv /etc/asound.conf.simple /etc/asound.conf

echo "Playing test tone on channel 1 only..."
speaker-test -D hw:2,0 -c 8 -s 1 -f 1000 -t sine -l 1

echo
echo "Restoring original config..."
sudo mv /etc/asound.conf.complex /etc/asound.conf

echo
echo "If the sound still rotates, the OCTO hardware might be:"
echo "- In surround decode mode"
echo "- Expecting different channel layout"
echo "- Need firmware configuration"
echo
echo "Try checking the OCTO jumpers/switches on the board" 