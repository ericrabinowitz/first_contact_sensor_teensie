#!/bin/bash

echo "=== OCTO Channel Test Using speaker-test ==="
echo "============================================"
echo

# Check current ALSA configuration
echo "Current ALSA configuration:"
cat /etc/asound.conf
echo
echo "---"

# Direct hardware test
echo "1. Testing each channel individually (direct hardware)"
echo "This should play a tone on ONE speaker at a time"
echo

for i in {1..8}; do
    echo "Channel $i (press Ctrl+C to skip)..."
    speaker-test -D hw:2,0 -c 8 -s $i -f 440 -t sine -l 1 2>/dev/null || echo "Channel $i failed"
    sleep 1
done

echo
echo "2. Testing with plughw (plugin layer)"
echo

for i in {1..8}; do
    echo "Channel $i via plughw..."
    speaker-test -D plughw:2,0 -c 8 -s $i -f 440 -t sine -l 1 2>/dev/null || echo "Channel $i failed"
    sleep 1
done

echo
echo "3. Testing channel mapping"
echo "This will speak the channel names:"
speaker-test -D hw:2,0 -c 8 -t wav -l 1

echo
echo "4. Checking if ALSA routing is causing issues"
echo "Temporarily bypassing asound.conf..."

# Backup and remove asound.conf
sudo mv /etc/asound.conf /etc/asound.conf.backup 2>/dev/null

echo "Testing without ALSA routing..."
speaker-test -D hw:2,0 -c 2 -f 1000 -t sine -l 1

# Restore
sudo mv /etc/asound.conf.backup /etc/asound.conf 2>/dev/null

echo
echo "Test complete!"
echo
echo "If sounds rotated between speakers, the OCTO might be in:"
echo "- Surround sound mode"
echo "- Incorrect channel mapping mode"
echo "- Need different initialization" 