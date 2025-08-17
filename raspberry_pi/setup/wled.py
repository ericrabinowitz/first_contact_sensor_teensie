#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "backports.strenum", "numpy", "paho-mqtt", "requests",
#   "sounddevice", "soundfile", "ultraimport"
# ]
# ///

import time
import ultraimport as ui

Statue, Board, Effect = ui.ultraimport(
    "__dir__/../config/constants.py", ["Statue", "Board", "Effect"]
)

(
    segment_map,
    board_config,
    extract_addresses,
    initialize_leds,
    leds_active,
    leds_dormant,
) = ui.ultraimport(
    "__dir__/../config/constants.py",
    [
        "segment_map",
        "board_config",
        "extract_addresses",
        "initialize_leds",
        "leds_active",
        "leds_dormant",
    ],
)

if __name__ == "__main__":
    extract_addresses()
    initialize_leds()
    for statue in Statue:
        print(f"Activating statue: {statue}")
        leds_active(statue)
        time.sleep(3)
        leds_dormant()
