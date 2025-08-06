#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["sounddevice"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./print_devices.py

import json
import sounddevice as sd

devices = sd.query_devices()
print("Available audio devices:")
print(json.dumps(devices, indent=2))
