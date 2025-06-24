#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy"]
# ///

# Channel identification test for OCTO

import numpy as np
import sounddevice as sd
import time

def find_octo():
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'octo' in dev['name'].lower() or 'audioinjector' in dev['name'].lower():
            return i
    return None

def play_beep_pattern(device, channel, pattern):
    """Play a beep pattern on a specific channel."""
    sample_rate = 48000
    beep_duration = 0.2
    silence_duration = 0.2
    
    # Create silence for all channels
    total_duration = len(pattern) * (beep_duration + silence_duration)
    samples = int(sample_rate * total_duration)
    audio = np.zeros((samples, 8), dtype=np.float32)
    
    # Add beeps for the specified channel
    current_sample = 0
    for beep in pattern:
        if beep == 1:
            beep_samples = int(sample_rate * beep_duration)
            t = np.linspace(0, beep_duration, beep_samples, False)
            tone = 0.5 * np.sin(2 * np.pi * 1000 * t)
            audio[current_sample:current_sample + beep_samples, channel] = tone
        current_sample += int(sample_rate * (beep_duration + silence_duration))
    
    print(f"Channel {channel + 1}: {''.join(['BEEP ' if b else 'silence ' for b in pattern])}")
    sd.play(audio, samplerate=sample_rate, device=device)
    sd.wait()

def main():
    print("OCTO Channel Identification Test")
    print("=" * 50)
    
    octo = find_octo()
    if octo is None:
        print("ERROR: OCTO not found!")
        return
    
    info = sd.query_devices(octo)
    print(f"\nFound: {info['name']} at index {octo}")
    
    print("\nThis test will play distinct beep patterns on each channel.")
    print("Channel 1: 1 beep")
    print("Channel 2: 2 beeps")
    print("Channel 3: 3 beeps")
    print("etc...")
    print("\nListen carefully to identify if:")
    print("- Beeps come from one speaker (correct)")
    print("- Beeps rotate between speakers (surround processing)")
    print("- Beeps sound distorted (DSP issue)")
    
    input("\nPress Enter to start...")
    
    # Test each channel with different beep patterns
    for ch in range(8):
        print(f"\n--- Testing Channel {ch + 1} ---")
        pattern = [1] * (ch + 1) + [0] * (7 - ch)  # 1 beep for ch1, 2 for ch2, etc.
        play_beep_pattern(octo, ch, pattern)
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("Test 2: All channels with different continuous tones")
    input("Press Enter to continue...")
    
    # Play different frequency on each channel
    duration = 3
    samples = int(48000 * duration)
    audio = np.zeros((samples, 8), dtype=np.float32)
    
    print("\nPlaying simultaneously:")
    for ch in range(8):
        freq = 200 * (ch + 1)  # 200, 400, 600, 800, 1000, 1200, 1400, 1600 Hz
        t = np.linspace(0, duration, samples, False)
        audio[:, ch] = 0.2 * np.sin(2 * np.pi * freq * t)
        print(f"Channel {ch + 1}: {freq}Hz")
    
    sd.play(audio, samplerate=48000, device=octo)
    sd.wait()
    
    print("\n" + "=" * 50)
    print("Test 3: Single channel sweep")
    input("Press Enter to continue...")
    
    # Test just channel 0 with different approaches
    tests = [
        ("Pure numpy array", lambda: test_numpy_single_channel(octo)),
        ("Explicit zeros", lambda: test_explicit_zeros(octo)),
        ("Via callback", lambda: test_callback_single_channel(octo))
    ]
    
    for name, test_func in tests:
        print(f"\n{name}...")
        test_func()
        time.sleep(1)

def test_numpy_single_channel(device):
    """Test with pure numpy array."""
    audio = np.zeros((48000, 8), dtype=np.float32)
    t = np.linspace(0, 1, 48000, False)
    audio[:, 0] = 0.5 * np.sin(2 * np.pi * 440 * t)
    sd.play(audio, device=device)
    sd.wait()

def test_explicit_zeros(device):
    """Test with explicit channel assignment."""
    audio = np.zeros((48000, 8), dtype=np.float32)
    tone = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 1, 48000, False))
    for ch in range(8):
        if ch == 0:
            audio[:, ch] = tone
        else:
            audio[:, ch] = 0.0
    sd.play(audio, device=device)
    sd.wait()

def test_callback_single_channel(device):
    """Test using callback for single channel."""
    class SingleChannelPlayer:
        def __init__(self):
            self.phase = 0
            self.increment = 2 * np.pi * 440 / 48000
        
        def callback(self, outdata, frames, time, status):
            outdata[:] = 0
            t = np.arange(frames)
            outdata[:, 0] = 0.5 * np.sin(self.phase + t * self.increment)
            self.phase = (self.phase + frames * self.increment) % (2 * np.pi)
    
    player = SingleChannelPlayer()
    with sd.OutputStream(device=device, channels=8, callback=player.callback):
        sd.sleep(1000)

if __name__ == "__main__":
    main() 