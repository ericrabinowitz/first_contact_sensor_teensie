#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice", "numpy", "matplotlib"]
# ///

# Test if OCTO is applying surround sound processing

import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
import time

def find_octo():
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'octo' in dev['name'].lower() or 'audioinjector' in dev['name'].lower():
            return i
    return None

def record_output_loopback(device, duration=2):
    """Record what's actually being output (requires loopback cable)."""
    print("Recording output through loopback...")
    print("Make sure you have outputs connected to inputs!")
    
    # Record 6 channels
    recording = sd.rec(int(48000 * duration), 
                      samplerate=48000, 
                      channels=6, 
                      device=device)
    sd.wait()
    return recording

def analyze_channel_behavior():
    """Play on one channel, record all, analyze."""
    octo = find_octo()
    if octo is None:
        print("OCTO not found!")
        return
    
    print("Channel Behavior Analysis")
    print("=" * 50)
    
    # Test each output channel
    for out_ch in range(6):  # Test first 6 outputs
        print(f"\nTesting output channel {out_ch + 1}")
        
        # Generate test signal - pure tone on one channel
        duration = 1
        freq = 1000
        t = np.linspace(0, duration, 48000, False)
        
        # 8 channel output, all zeros except one
        output = np.zeros((48000, 8), dtype=np.float32)
        output[:, out_ch] = 0.5 * np.sin(2 * np.pi * freq * t)
        
        # Play and record simultaneously if possible
        print("Playing tone on channel", out_ch + 1)
        recording = sd.playrec(output, samplerate=48000, 
                              channels=6, device=octo)
        sd.wait()
        
        # Analyze recording
        print("Analyzing recording...")
        for in_ch in range(6):
            rms = np.sqrt(np.mean(recording[:, in_ch]**2))
            if rms > 0.01:  # Threshold for detection
                print(f"  Input {in_ch + 1}: RMS = {rms:.3f} (ACTIVE)")
            else:
                print(f"  Input {in_ch + 1}: RMS = {rms:.3f}")
        
        time.sleep(0.5)

def visualize_surround_matrix():
    """Visualize potential surround sound matrix."""
    octo = find_octo()
    if octo is None:
        print("OCTO not found!")
        return
    
    print("\nSurround Matrix Visualization")
    print("=" * 50)
    
    # Create matrix to store results
    matrix = np.zeros((6, 6))  # 6 inputs x 6 outputs
    
    # Test each output
    for out_ch in range(6):
        print(f"Testing output {out_ch + 1}...")
        
        # Generate test signal
        duration = 0.5
        t = np.linspace(0, duration, int(48000 * duration), False)
        output = np.zeros((len(t), 8), dtype=np.float32)
        output[:, out_ch] = 0.5 * np.sin(2 * np.pi * 1000 * t)
        
        # Play and record
        recording = sd.playrec(output, samplerate=48000, 
                              channels=6, device=octo)
        sd.wait()
        
        # Measure energy in each input
        for in_ch in range(6):
            matrix[in_ch, out_ch] = np.sqrt(np.mean(recording[:, in_ch]**2))
    
    # Plot matrix
    plt.figure(figsize=(8, 6))
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar(label='Signal Level')
    plt.xlabel('Output Channel')
    plt.ylabel('Input Channel')
    plt.title('OCTO Channel Routing Matrix\n(Should be diagonal for 1:1 mapping)')
    
    # Add grid
    for i in range(7):
        plt.axhline(i - 0.5, color='white', linewidth=0.5)
        plt.axvline(i - 0.5, color='white', linewidth=0.5)
    
    plt.tight_layout()
    plt.savefig('/tmp/octo_matrix.png')
    print("\nMatrix saved to /tmp/octo_matrix.png")
    
    # Print interpretation
    print("\nInterpretation:")
    if np.allclose(matrix, np.diag(np.diag(matrix)), atol=0.1):
        print("✓ Channels appear to be mapped 1:1 (good)")
    else:
        print("✗ Channels are being mixed/routed (surround mode?)")
        print("\nActive routing detected:")
        for out in range(6):
            active_inputs = []
            for inp in range(6):
                if matrix[inp, out] > 0.05:
                    active_inputs.append(f"In{inp+1}({matrix[inp, out]:.2f})")
            if active_inputs:
                print(f"  Out{out+1} -> {', '.join(active_inputs)}")

def test_direct_passthrough():
    """Test if we can get clean passthrough."""
    octo = find_octo()
    if octo is None:
        print("OCTO not found!")
        return
    
    print("\nDirect Passthrough Test")
    print("=" * 50)
    print("Playing different frequency on each channel...")
    print("If in surround mode, you'll hear multiple frequencies per speaker")
    
    duration = 3
    samples = int(48000 * duration)
    output = np.zeros((samples, 8), dtype=np.float32)
    
    # Different frequency per channel
    for ch in range(6):
        freq = 200 + ch * 200  # 200, 400, 600, 800, 1000, 1200 Hz
        t = np.linspace(0, duration, samples, False)
        output[:, ch] = 0.3 * np.sin(2 * np.pi * freq * t)
        print(f"Channel {ch + 1}: {freq}Hz")
    
    print("\nPlaying...")
    sd.play(output, samplerate=48000, device=octo)
    sd.wait()

def main():
    print("OCTO Surround Mode Diagnostic")
    print("=" * 50)
    print("\nThis test requires loopback cables from outputs to inputs!")
    print("Connect Out1->In1, Out2->In2, etc.")
    
    while True:
        print("\nOptions:")
        print("1. Analyze channel behavior")
        print("2. Visualize routing matrix")
        print("3. Direct passthrough test")
        print("4. Exit")
        
        choice = input("\nSelect test: ")
        
        if choice == '1':
            analyze_channel_behavior()
        elif choice == '2':
            visualize_surround_matrix()
        elif choice == '3':
            test_direct_passthrough()
        elif choice == '4':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main() 