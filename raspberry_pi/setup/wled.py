#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "backports.strenum", "numpy", "paho-mqtt", "requests",
#   "sounddevice", "soundfile", "ultraimport"
# ]
# ///

import json
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
    connect_to_mqtt,
    set_debug,
) = ui.ultraimport(
    "__dir__/../controller/controller.py",
    [
        "segment_map",
        "board_config",
        "extract_addresses",
        "initialize_leds",
        "leds_active",
        "leds_dormant",
        "connect_to_mqtt",
        "set_debug",
    ],
)


def cycle_all():
    for statue in Statue:
        print(f"Activating statue: {statue}")
        leds_active({statue})
        time.sleep(3)
        leds_dormant({statue})


if __name__ == "__main__":
    extract_addresses()
    connect_to_mqtt()
    initialize_leds()
    print(json.dumps(segment_map, indent=2))
    leds_dormant(
        {Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ARIEL, Statue.ULTIMO}
    )
    set_debug(True)

    # cycle_all()
    leds_active({Statue.EROS})
    time.sleep(5)
    leds_dormant({Statue.EROS})
    time.sleep(1)
