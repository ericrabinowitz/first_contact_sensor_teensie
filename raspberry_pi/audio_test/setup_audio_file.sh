#!/bin/bash

echo "=== Setting up Audio File on Pi ==="
echo

# Create audio directory
mkdir -p /home/pi/first_contact/audio_files

# Check if file already exists
if [ -f "/home/pi/first_contact/audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav" ]; then
    echo "Audio file already exists on Pi!"
else
    echo "Audio file not found. Please copy it using:"
    echo
    echo "From your Mac, run:"
    echo 'scp "audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav" pi@rpi:~/first_contact/audio_files/'
    echo
    echo "Or if the file is in /run/audio_files on the Pi, copy it:"
    echo 'cp "/run/audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav" ~/first_contact/audio_files/'
fi

echo
echo "Checking file size..."
ls -lh ~/first_contact/audio_files/*.wav 2>/dev/null || echo "No WAV files found" 