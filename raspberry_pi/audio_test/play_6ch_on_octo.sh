#!/bin/bash

echo "=== Playing 6-Channel Audio on OCTO ==="
echo "======================================"
echo

# Check if file exists locally first
LOCAL_FILE="/home/pi/first_contact/audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"
SYSTEM_FILE="/run/audio_files/Missing Link Playa 1 - 6 Channel 6-7.wav"

if [ -f "$LOCAL_FILE" ]; then
    AUDIO_FILE="$LOCAL_FILE"
    echo "Using local file: $LOCAL_FILE"
elif [ -f "$SYSTEM_FILE" ]; then
    AUDIO_FILE="$SYSTEM_FILE"
    echo "Using system file: $SYSTEM_FILE"
else
    echo "ERROR: Audio file not found!"
    echo "Please copy the file to one of these locations:"
    echo "  $LOCAL_FILE"
    echo "  $SYSTEM_FILE"
    exit 1
fi

echo
echo "Playing 6-channel file on OCTO (8 outputs)..."
echo "Channels 1-6 will play on outputs 1-6"
echo "Channels 7-8 will be silent"
echo

# Play with direct hardware access
echo "Method 1: Direct hardware playback"
aplay -D hw:2,0 "$AUDIO_FILE"

# Alternative: use plughw for automatic format conversion if needed
# echo "Method 2: Using plughw for format conversion"
# aplay -D plughw:2,0 "$AUDIO_FILE" 