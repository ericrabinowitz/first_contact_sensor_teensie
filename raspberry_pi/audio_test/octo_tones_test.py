#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy"]
# ///

# Test tone player for OCTO - works over SSH
# Type commands and press Enter

import numpy as np
import sounddevice as sd
import threading
import sys

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
running = True


def find_octo_device():
    """Find the OCTO device index."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        name = dev['name'].lower()
        if 'octo' in name or 'audioinjector' in name:
            return i
    # Fallback: look for device with 8 output channels
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] == 8:
            return i
    return None


class MultiToneGenerator:
    def __init__(self):
        self.phases = np.zeros(8)
        self.phase_increments = np.array([
            2 * np.pi * freq / SAMPLE_RATE for freq in FREQUENCIES
        ])
    
    def callback(self, outdata, frames, time_info, status):
        if status:
            print(f"\rStream status: {status}")
        
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


def display_status():
    """Display current channel status."""
    print("\nActive channels: ", end='')
    active = []
    for i in range(8):
        if active_channels[i]:
            active.append(str(i))
    if active:
        print(", ".join(active))
    else:
        print("None")


def main():
    global running
    
    print("OCTO Tone Test")
    print("=" * 50)
    
    # Find OCTO device
    octo_device = find_octo_device()
    if octo_device is None:
        print("\n✗ Could not find OCTO device!")
        print("\nAvailable devices:")
        for i, dev in enumerate(sd.query_devices()):
            print(f"  {i}: {dev['name']} ({dev['max_output_channels']} out)")
        return
    
    device_info = sd.query_devices(octo_device)
    print(f"\n✓ Found OCTO: {device_info['name']} at index {octo_device}")
    print(f"  Output channels: {device_info['max_output_channels']}")
    
    print("\nChannel frequencies:")
    for i, freq in enumerate(FREQUENCIES):
        print(f"  {i} → {freq:.1f} Hz")
    
    generator = MultiToneGenerator()
    
    print("\nCommands:")
    print("  0-7     : Toggle channel on/off")
    print("  all     : Turn all channels on")
    print("  none    : Turn all channels off")
    print("  test    : Play each channel for 1 second")
    print("  quit    : Exit")
    print("\nType command and press Enter:")
    print("-" * 50)
    
    # Start audio stream
    with sd.OutputStream(
        device=octo_device,
        channels=8,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        callback=generator.callback
    ):
        while running:
            try:
                display_status()
                cmd = input("> ").strip().lower()
                
                if cmd == 'quit' or cmd == 'q':
                    running = False
                elif cmd == 'all':
                    with lock:
                        active_channels[:] = [True] * 8
                elif cmd == 'none' or cmd == 'clear':
                    with lock:
                        active_channels[:] = [False] * 8
                elif cmd == 'test':
                    print("Testing each channel...")
                    with lock:
                        active_channels[:] = [False] * 8
                    for i in range(8):
                        print(f"  Channel {i+1} ({FREQUENCIES[i]:.1f} Hz)...")
                        with lock:
                            active_channels[i] = True
                        sd.sleep(1000)
                        with lock:
                            active_channels[i] = False
                    print("Test complete!")
                elif cmd in '01234567' and len(cmd) == 1:
                    ch = int(cmd)
                    with lock:
                        active_channels[ch] = not active_channels[ch]
                        state = "ON" if active_channels[ch] else "OFF"
                    print(f"Channel {ch} → {state}")
                elif cmd:
                    print("Unknown command. Try: 0-7, all, none, test, quit")
                    
            except KeyboardInterrupt:
                running = False
            except EOFError:
                running = False
    
    print("\nGoodbye!")


if __name__ == "__main__":
    main() 