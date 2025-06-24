#!/usr/bin/env python3

import subprocess
import os
import sys

print("=== Audio Injector OCTO Troubleshooting ===")
print("=" * 50)

# Function to run command and print output
def run_cmd(cmd, description):
    print(f"\n{description}")
    print("-" * 40)
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        if result.returncode != 0:
            print(f"Command failed with return code: {result.returncode}")
    except Exception as e:
        print(f"Error running command: {e}")

# 1. Check audio devices
run_cmd("aplay -l", "1. Current audio devices:")

# 2. Check dmesg for audio-related messages
run_cmd("dmesg | grep -i audio | tail -20", "2. Recent audio-related kernel messages:")

# 3. Check for Audio Injector specific messages
run_cmd("dmesg | grep -i injector", "3. Audio Injector specific messages:")

# 4. Check loaded modules
run_cmd("lsmod | grep -E 'snd|audio|i2s'", "4. Loaded audio modules:")

# 5. Check device tree overlays
run_cmd("ls /boot/overlays/ | grep -E 'audio.*inject|inject.*audio|octo'", "5. Available Audio Injector overlays:")

# 6. Check if overlay is loaded
print("\n6. Checking device tree for Audio Injector:")
print("-" * 40)
try:
    # Check for any audioinjector devices in device tree
    dt_files = subprocess.run("find /proc/device-tree -name '*audio*inject*' 2>/dev/null", 
                             shell=True, capture_output=True, text=True)
    if dt_files.stdout:
        print("Found in device tree:")
        print(dt_files.stdout)
    else:
        print("No Audio Injector devices found in device tree")
except:
    print("Could not check device tree")

# 7. Check I2C devices (OCTO uses I2C)
run_cmd("i2cdetect -y 1 2>/dev/null || echo 'i2cdetect not installed or I2C not enabled'", 
        "7. I2C devices (OCTO uses I2C for control):")

# 8. Check /proc/asound
run_cmd("cat /proc/asound/cards", "8. ALSA cards in /proc/asound/cards:")

# 9. Check boot config
print("\n9. Current boot config (audio-related lines):")
print("-" * 40)
try:
    with open('/boot/config.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if 'audio' in line.lower() or 'i2s' in line or 'i2c' in line or 'inject' in line.lower():
                print(line)
except:
    print("Could not read /boot/config.txt")

# 10. GPIO status
run_cmd("gpio readall 2>/dev/null | head -20 || echo 'GPIO command not available'", 
        "10. GPIO pin status (first 20 pins):")

print("\n" + "=" * 50)
print("Troubleshooting complete.")
print("\nRecommendations based on common issues:")
print("1. Make sure the OCTO HAT is properly seated on all 40 GPIO pins")
print("2. Enable I2C and I2S in /boot/config.txt:")
print("   dtparam=i2c_arm=on")
print("   dtparam=i2s=on")
print("3. Try alternative overlay names:")
print("   dtoverlay=audioinjector-octo")
print("   dtoverlay=audioinjector-wm8731-audio")
print("4. Check the specific overlay documentation:")
print("   /boot/overlays/README") 