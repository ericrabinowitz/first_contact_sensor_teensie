#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy", "pynput"]
# ///

# Interactive tone player for Audio Injector OCTO
# Keys 0-7 play different tones on channels 1-8

import numpy as np
import sounddevice as sd
import threading
import time
from pynput import keyboard

OCTO_DEVICE = 2  # OCTO device index
SAMPLE_RATE = 48000
BLOCK_SIZE = 256

# Map keys to frequencies (musical notes)
# Using a pentatonic scale for pleasant harmonies
KEY_FREQUENCIES = {
    '0': 261.63,  # C4
    '1': 293.66,  # D4
    '2': 329.63,  # E4
    '3': 392.00,  # G4
    '4': 440.00,  # A4
    '5': 523.25,  # C5
    '6': 587.33,  # D5
    '7': 659.25,  # E5
}

# Track which keys are pressed
active_keys = set()
lock = threading.Lock()


class ToneGenerator:
    def __init__(self):
        self.phase = np.zeros(8)
        self.phase_increment = np.zeros(8)
        
        # Pre-calculate phase increments for each frequency
        for i in range(8):
            key = str(i)
            if key in KEY_FREQUENCIES:
                freq = KEY_FREQUENCIES[key]
                self.phase_increment[i] = 2 * np.pi * freq / SAMPLE_RATE
    
    def callback(self, outdata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        
        # Clear output buffer
        outdata[:] = 0
        
        # Generate tones for active keys
        with lock:
            for key in active_keys:
                if key in KEY_FREQUENCIES:
                    channel = int(key)
                    
                    # Generate sine wave
                    t = np.arange(frames)
                    signal = 0.3 * np.sin(self.phase[channel] + t * self.phase_increment[channel])
                    
                    # Add to output channel
                    outdata[:, channel] += signal
                    
                    # Update phase (with wrapping to prevent overflow)
                    self.phase[channel] = (self.phase[channel] + 
                                         frames * self.phase_increment[channel]) % (2 * np.pi)


def on_press(key):
    try:
        # Get the character
        if hasattr(key, 'char') and key.char in KEY_FREQUENCIES:
            with lock:
                if key.char not in active_keys:
                    active_keys.add(key.char)
                    channel = int(key.char) + 1
                    freq = KEY_FREQUENCIES[key.char]
                    print(f"Playing {freq:.1f}Hz on channel {channel}")
    except:
        pass


def on_release(key):
    try:
        # Check for escape key
        if key == keyboard.Key.esc:
            print("\nStopping...")
            return False
        
        # Handle number keys
        if hasattr(key, 'char') and key.char in KEY_FREQUENCIES:
            with lock:
                if key.char in active_keys:
                    active_keys.remove(key.char)
                    channel = int(key.char) + 1
                    print(f"Stopped channel {channel}")
    except:
        pass


def main():
    print("OCTO Keyboard Tone Player")
    print("=" * 50)
    print("\nControls:")
    print("  Keys 0-7: Play tones on channels 1-8")
    print("  ESC: Exit")
    print("\nFrequencies:")
    for key, freq in sorted(KEY_FREQUENCIES.items()):
        channel = int(key) + 1
        print(f"  Key {key} → Channel {channel}: {freq:.1f} Hz")
    
    # Check OCTO device
    print("\nChecking Audio Injector OCTO...")
    try:
        info = sd.query_devices(OCTO_DEVICE)
        print(f"✓ Found: {info['name']}")
        print(f"  Channels: {info['max_output_channels']}")
    except:
        print("✗ OCTO not found!")
        print("\nAvailable devices:")
        print(sd.query_devices())
        return
    
    # Create tone generator
    generator = ToneGenerator()
    
    # Start audio stream
    print("\nStarting audio stream...")
    stream = sd.OutputStream(
        device=OCTO_DEVICE,
        channels=8,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        callback=generator.callback
    )
    
    # Start keyboard listener
    print("Ready! Press keys 0-7 to play tones. Press ESC to exit.")
    print("-" * 50)
    
    with stream:
        # Start keyboard listener
        with keyboard.Listener(
            on_press=on_press,
            on_release=on_release) as listener:
            listener.join()
    
    print("\nGoodbye!")


if __name__ == "__main__":
    main() 