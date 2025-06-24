#!/bin/bash

echo "=== Testing Audio Injector OCTO Output ==="
echo "========================================="
echo

echo "OCTO detected as card 2!"
echo

# Update ALSA config to use OCTO
echo "Updating ALSA configuration to use OCTO..."
sudo tee /etc/asound.conf << 'EOF'
# Audio Injector OCTO as default
pcm.!default {
    type plug
    slave.pcm "anyChannelCount"
}

ctl.!default {
    type hw
    card 2
}

pcm.anyChannelCount {
    type route
    slave.pcm "hw:2"
    slave.channels 8;
    ttable {
        0.0 1
        1.1 1
        2.2 1
        3.3 1
        4.4 1
        5.5 1
        6.6 1
        7.7 1
    }
}

ctl.anyChannelCount {
    type hw;
    card 2;
}
EOF

echo
echo "Testing 8-channel output..."
echo "This will play test sounds on each channel in sequence."
echo "You have speakers on 2 of the 8 channels."
echo

# Test each channel individually
for i in {1..8}; do
    echo "Testing channel $i..."
    speaker-test -D hw:2,0 -c 8 -s $i -f 440 -t sine -l 1
    sleep 1
done

echo
echo "Now testing all 8 channels with voice prompts..."
speaker-test -D hw:2,0 -c 8 -t wav -l 1

echo
echo "Test complete! Did you hear audio on your connected speakers?"
echo
echo "To play your 6-channel file on the OCTO:"
echo "aplay -D hw:2,0 /run/audio_files/Missing\ Link\ Playa\ 1\ -\ 6\ Channel\ 6-7.wav" 