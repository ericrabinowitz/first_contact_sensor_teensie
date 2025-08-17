#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "backports.strenum", "numpy", "paho-mqtt", "requests",
#   "sounddevice", "soundfile", "ultraimport"
# ]
# ///
"""
WLED test script.

Cycle through all statues: ./wled.py
Activate then deactivate a single statue: ./wled.py <statue>

HOW TO USE:

First ssh onto the pi:
ssh rpi5b
cd ~/first_contact_sensor_teensie/raspberry_pi/setup

Then run the script:
./wled.py <statue>

Take the payload from the script output, make sure to select the correct board.
Then copy paste the payload into the following curl command:

five_v_1 (eros, elektra) = 192.168.4.11
five_v_2 (sophia, ariel, ultimo) = 192.168.4.12
twelve_v_1 (arches) = 192.168.4.13

curl http://192.168.4.11/json/state -X POST -H "Content-Type: application/json" -d 'PAYLOAD'

Example from eros, active:

curl http://192.168.4.11/json/state -X POST -H "Content-Type: application/json" -d \
  '{"tt": 0, "on": true, "seg": [{"id": 0, "bri": 255, "col": [[255, 0, 100], [225, 0, 255], [255, 0, 100]], "fx": 42, "pal": 3}, {"id": 1, "bri": 255, "col": [[255, 0, 100], [225, 0, 255], [255, 0, 100]], "fx": 42, "pal": 3}]}'

"""

import json
import sys
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
        time.sleep(5)
        leds_dormant({statue})


if __name__ == "__main__":
    statue = None
    if len(sys.argv) > 1:
        try:
            statue = Statue(sys.argv[1].lower().strip())
        except ValueError:
            print(f"Error: Unknown statue: {sys.argv[1]}")
            exit(1)

    extract_addresses()
    connect_to_mqtt()
    initialize_leds()
    print(json.dumps(segment_map, indent=2))
    leds_dormant(
        {Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ARIEL, Statue.ULTIMO}
    )
    set_debug(True)

    if statue is None:
        cycle_all()
    else:
        leds_active({statue})
        time.sleep(5)
        leds_dormant({statue})
        time.sleep(1)
