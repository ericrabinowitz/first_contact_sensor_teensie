#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy"]
# ///

# Simple terminal-based tone player for OCTO
# Press keys 0-7 followed by Enter to toggle tones

import numpy as np
import sounddevice as sd
import threading
import sys
import termios
import tty
import select

OCTO_DEVICE = 2
SAMPLE_RATE = 48000
BLOCK_SIZE = 256

# Musical frequencies (pentatonic scale)
FREQUENCIES = [
    261.63,  # C4 - Channel 1 (key 0)
    293.66,  # D4 - Channel 2 (key 1)
    329.63,  # E4 - Channel 3 (key 2)
    392.00,  # G4 - Channel 4 (key 3)
    440.00,  # A4 - Channel 5 (key 4)
    523.25,  # C5 - Channel 6 (key 5)
    587.33,  # D5 - Channel 7 (key 6)
    659.25,  # E5 - Channel 8 (key 7)
]

# Track active channels
active_channels = [False] * 8
lock = threading.Lock()


class MultiToneGenerator:
    def __init__(self):
        self.phases = np.zeros(8)
        self.phase_increments = np.array([
            2 * np.pi * freq / SAMPLE_RATE for freq in FREQUENCIES
        ])
    
    def callback(self, outdata, frames, time_info, status):
        if status:
            print(f"\rStream status: {status}", end='')
        
        # Clear output
        outdata[:] = 0
        
        with lock:
            # Generate tones for active channels
            for ch in range(8):
                if active_channels[ch]:
                    # Generate sine wave
                    t = np.arange(frames)
                    signal = 0.3 * np.sin(self.phases[ch] + t * self.phase_increments[ch])
                    outdata[:, ch] = signal
                    
                    # Update phase
                    self.phases[ch] = (self.phases[ch] + 
                                     frames * self.phase_increments[ch]) % (2 * np.pi)


def get_key():
    """Get a single keypress without waiting for Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        if select.select([sys.stdin], [], [], 0.1)[0]:
            key = sys.stdin.read(1)
            return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None


def display_status():
    """Display current channel status."""
    print("\r", end='')
    print("Channels: ", end='')
    for i in range(8):
        if active_channels[i]:
            print(f"[{i}]", end='')
        else:
            print(f" {i} ", end='')
    print("  (0-7: toggle, q: quit)    ", end='', flush=True)


def main():
    print("OCTO Simple Tone Player")
    print("=" * 50)
    print("\nChannel frequencies:")
    for i, freq in enumerate(FREQUENCIES):
        print(f"  Key {i} → Channel {i+1}: {freq:.1f} Hz")
    
    # Check device
    try:
        info = sd.query_devices(OCTO_DEVICE)
        print(f"\n✓ Using: {info['name']}")
    except:
        print("\n✗ OCTO not found at device index 2")
        print("Available devices:")
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_output_channels'] > 0:
                print(f"  {i}: {dev['name']}")
        return
    
    generator = MultiToneGenerator()
    
    print("\nControls:")
    print("  Press 0-7 to toggle tones on/off")
    print("  Press 'q' to quit")
    print("  Press 'c' to clear all")
    print("\nReady!")
    print("-" * 50)
    
    with sd.OutputStream(
        device=OCTO_DEVICE,
        channels=8,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        callback=generator.callback
    ):
        display_status()
        
        while True:
            key = get_key()
            if key:
                if key == 'q':
                    print("\n\nGoodbye!")
                    break
                elif key == 'c':
                    with lock:
                        active_channels[:] = [False] * 8
                    display_status()
                elif key in '01234567':
                    ch = int(key)
                    with lock:
                        active_channels[ch] = not active_channels[ch]
                    display_status()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted!")
    finally:
        # Reset terminal
        print("\033[?25h", end='')  # Show cursor 