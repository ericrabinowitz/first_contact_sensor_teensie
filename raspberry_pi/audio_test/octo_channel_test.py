#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy"]
# ///

# Channel diagnostic for OCTO - test each channel separately

import numpy as np
import sounddevice as sd
import time

def find_octo():
    """Find OCTO device."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'octo' in dev['name'].lower() or 'audioinjector' in dev['name'].lower():
            return i
    return None

def generate_tone(frequency, duration, sample_rate=48000):
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return 0.5 * np.sin(2 * np.pi * frequency * t)

def test_single_channel(device, channel, frequency=440, duration=2):
    """Play a tone on a single channel only."""
    print(f"\nTesting channel {channel + 1} at {frequency}Hz...")
    
    # Create 8-channel buffer with silence
    samples = int(48000 * duration)
    audio = np.zeros((samples, 8), dtype=np.float32)
    
    # Generate tone for one channel only
    tone = generate_tone(frequency, duration)
    audio[:, channel] = tone
    
    # Play it
    sd.play(audio, samplerate=48000, device=device)
    sd.wait()
    print(f"Channel {channel + 1} complete")

def main():
    print("OCTO Channel Diagnostic")
    print("=" * 50)
    
    octo = find_octo()
    if octo is None:
        print("ERROR: OCTO not found!")
        return
    
    info = sd.query_devices(octo)
    print(f"\nFound: {info['name']}")
    print(f"Device index: {octo}")
    print(f"Channels: {info['max_output_channels']}")
    print(f"Sample rate: {info['default_samplerate']}")
    
    # Test different configurations
    tests = [
        ("1. Individual channels (440Hz, 2 sec each)", 
         lambda: test_individual_channels(octo)),
        ("2. White noise burst (identify channels)",
         lambda: test_white_noise(octo)),
        ("3. Different frequencies simultaneously",
         lambda: test_multi_freq(octo)),
        ("4. Direct hardware test (bypass ALSA routing)",
         lambda: test_direct_hw(octo))
    ]
    
    for name, test_func in tests:
        print(f"\n{name}")
        print("-" * 40)
        input("Press Enter to start...")
        test_func()

def test_individual_channels(device):
    """Test each channel individually."""
    for ch in range(8):
        test_single_channel(device, ch, 440 + ch * 100)
        time.sleep(0.5)

def test_white_noise(device):
    """Short white noise burst on each channel."""
    print("Playing 0.5 sec white noise on each channel...")
    for ch in range(8):
        audio = np.zeros((24000, 8), dtype=np.float32)
        # White noise
        audio[:, ch] = np.random.normal(0, 0.1, 24000)
        print(f"Channel {ch + 1}...")
        sd.play(audio, samplerate=48000, device=device)
        sd.wait()
        time.sleep(0.5)

def test_multi_freq(device):
    """Play different frequencies on different channels."""
    print("Playing different frequencies on each channel for 3 seconds...")
    duration = 3
    samples = int(48000 * duration)
    audio = np.zeros((samples, 8), dtype=np.float32)
    
    # Different frequency for each channel
    for ch in range(8):
        freq = 200 + ch * 100  # 200, 300, 400, etc.
        t = np.linspace(0, duration, samples, False)
        audio[:, ch] = 0.3 * np.sin(2 * np.pi * freq * t)
        print(f"Channel {ch + 1}: {freq}Hz")
    
    sd.play(audio, samplerate=48000, device=device)
    sd.wait()

def test_direct_hw(device):
    """Test with explicit device string."""
    print("\nTrying direct hardware access...")
    
    # Test with aplay first
    import subprocess
    print("Testing with aplay (1kHz tone on all channels)...")
    try:
        # Generate test tone
        duration = 2
        t = np.linspace(0, duration, 48000 * duration, False)
        tone = 0.5 * np.sin(2 * np.pi * 1000 * t)
        
        # Create 8-channel file
        audio = np.zeros((len(tone), 8), dtype=np.float32)
        for ch in range(8):
            audio[:, ch] = tone
        
        # Save and play
        import soundfile as sf
        sf.write('/tmp/test_8ch.wav', audio, 48000)
        
        cmd = ['aplay', '-D', 'hw:2,0', '/tmp/test_8ch.wav']
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except Exception as e:
        print(f"aplay test failed: {e}")

if __name__ == "__main__":
    main() 