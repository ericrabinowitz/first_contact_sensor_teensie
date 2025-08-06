#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile", "paho-mqtt"]
# ///

"""
Controller for the Missing Link art installation. Receives contact events from
each statue's Teensy and configures their signal frequencies. In response to
events, it plays audio channels and controls the WLED lights and haptic motors.

Install:
wget -qO- https://astral.sh/uv/install.sh | sh

Execute: ./controller.py
"""

import json
import os
import re
import threading
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Set

import paho.mqtt.client as mqtt
import sounddevice as sd
import soundfile as sf

# TODO:
# move global variables separate store lib
# handle device selection


class Statue(Enum):
    ALL = "all"
    ARCHES = "arches"
    EROS = "eros"
    ELEKTRA = "elektra"
    SOPHIA = "sophia"
    ULTIMO = "ultimo"
    ARIEL = "ariel"


class Board(Enum):
    FIVE_V_1 = "five_v_1"
    FIVE_V_2 = "five_v_2"
    FIVE_V_3 = "five_v_3"
    TWELVE_V_1 = "twelve_v_1"


class Effect(Enum):
    SOLID = 0
    FIREWORKS = 42
    NOISE = 71


# ### Parameters

VERSION = "1.0"  # Version of the script
DEBUG_PORT = 8080  # Port for the debug server

# Folder for audio files
SONG_DIR = os.path.join(os.path.dirname(__file__), "../../audio_files")
ACTIVE_SONG = "Missing Link Playa 1 - 6 Channel 6-7.wav"
DNSMASQ_FILE = os.path.join(os.path.dirname(__file__), "../setup/dnsmasq.conf")

# MQTT server settings
LINK_MQTT_TOPIC = "missing_link/contact"  # Topic for link/ msgs
# {
#     "detector": "eros", # Statue that detected the contact
#     "emitters": ["elektra"], # Statues are currently linked to the detector
# }
# Topics for configuring the Teensy
CONFIG_REQ_MQTT_TOPIC = "missing_link/config/request"
# "true"       # request to send the Teensy config
CONFIG_RESP_MQTT_TOPIC = "missing_link/config/response"
# {
#     "eros": {
#         "emit": 10000,                 # Frequency in Hz to emit a tone on
#         "detect": ["elektra", ...],    # Statues to receive tones from
#         "mac_address": "aa:bb:cc:dd:ee:ff", # MAC address of the Teensy
#         "ip_address": "192.168.4.11",       # IP address of the Teensy
#     },
#     ... # Other statues
# }
HAPTIC_MQTT_TOPIC = "missing_link/haptic"  # Topic for haptic motor commands
# {
#     "statue": "eros",  # Statue to turn on the haptic motors for
# }
WLED_MQTT_TOPIC = "wled/{}/api"  # Topic template for WLED commands, fill in board name
MQTT_BROKER = "127.0.0.1"  # IP address of the MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None

# WLED settings
# TODO: test different palettes, like the default one
PALETTE_ID = 3
FADE_MS = 2000  # Fade time in milliseconds
COOL_DOWN_MS = 2000  # Audio recent song wait time in milliseconds

# Defaults to the settings for ALL
COLORS = {
    Statue.ELEKTRA: {
        "active": [[0, 25, 255], [0, 200, 255], [0, 25, 255]],
    },
    Statue.EROS: {
        "active": [[255, 0, 100], [225, 0, 255], [255, 0, 100]],
    },
    Statue.ALL: {
        "active": [[0, 25, 255], [0, 200, 255], [0, 25, 255]],
        "dormant": [[255, 255, 255], [0, 0, 0], [0, 0, 0]],
    },
}

# Defaults to the settings for ALL
EFFECTS = {
    Statue.ALL: {
        "active": Effect.FIREWORKS,
        "dormant": Effect.NOISE,
    },
}

# Maps statues to QuinLED boards and segment ids.
# The control pin to segment id mapping is done in the WLED app.
SEGMENT_MAP = {
    Statue.ARCHES: {
        Board.TWELVE_V_1: {
            "all": 0,  # WLED segment id
        },
    },
    Statue.ELEKTRA: {
        Board.FIVE_V_1: {
            "hands": 0,
            "rest": 1,
        },
    },
    Statue.EROS: {
        Board.FIVE_V_1: {
            "hands": 2,
            "rest": 3,
        },
    },
    Statue.SOPHIA: {
        Board.FIVE_V_2: {
            "hands": 0,
            "rest": 1,
        },
    },
    Statue.ULTIMO: {
        Board.FIVE_V_2: {
            "hands": 2,
            "rest": 3,
        },
    },
    Statue.ARIEL: {
        Board.FIVE_V_3: {
            "hands": 0,
            "rest": 1,
        },
    },
}

# HAPTIC_FADE_MS = 1000  # Haptic motor fade time in milliseconds
# HAPTIC_BRIGHTNESS = 170  # Haptic motor strength (out of 255)


# ### Global variables

debug = False  # Enable debug mode for verbose output

# MQTT client
mqttc: Any = None

# Derived from audio file
audio = {
    "data": None,  # Loaded audio data
    "sample_rate": 0,
}

devices = {
    Statue.EROS: {
        "port_id": "hw:3,0",
        "output": 0,
        "type": "",  # Derived from device info, ie "c-media usb headphone set"
        "sample_rate": 0,  # Derived from device info, ie 44100
    },
    Statue.ELEKTRA: {
        "port_id": "hw:3,0",
        "output": 1,
        "type": "",
        "sample_rate": 0,
    },
    Statue.SOPHIA: {
        "port_id": "hw:3,1",
        "output": 0,
        "type": "",
        "sample_rate": 0,
    },
    Statue.ULTIMO: {
        "port_id": "hw:3,1",
        "output": 1,
        "type": "",
        "sample_rate": 0,
    },
    Statue.ARIEL: {
        "port_id": "hw:3,2",
        "output": 0,
        "type": "",
        "sample_rate": 0,
    },
}

# Teensy configuration
teensy_config = {
    Statue.EROS: {
        "emit": 10077,
        "detect": [Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL],
        "mac_address": "",  # derived from the dnsmasq.conf file
        "ip_address": "",  # derived from the dnsmasq.conf file
    },
    Statue.ELEKTRA: {
        "emit": 12274,
        "detect": [Statue.EROS, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL],
        "mac_address": "",
        "ip_address": "",
    },
    Statue.SOPHIA: {
        "emit": 17227,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.ULTIMO, Statue.ARIEL],
        "mac_address": "",
        "ip_address": "",
    },
    Statue.ULTIMO: {
        "emit": 19467,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ARIEL],
        "mac_address": "",
        "ip_address": "",
    },
    Statue.ARIEL: {
        "emit": 14643,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO],
        "mac_address": "",
        "ip_address": "",
    },
}

# Detected contact pairings
linked_statues: Dict[Statue, List[Statue]] = {
    Statue.ELEKTRA: [],
    Statue.EROS: [],
    Statue.SOPHIA: [],
    Statue.ULTIMO: [],
    Statue.ARIEL: [],
}
# Statues that are currently active
active_statues: Set[Statue] = set()


# ### Helper functions


def extract_addresses():
    """Extracts MAC and IP addresses from the dnsmasq.conf file."""
    global teensy_config
    if not os.path.exists(DNSMASQ_FILE):
        print(f"DNSMASQ file not found: {DNSMASQ_FILE}")
        return

    with open(DNSMASQ_FILE, "r") as f:
        lines = f.readlines()

    statues = teensy_config.keys()
    for line in lines:
        if "dhcp-host" in line:
            parts = line.split("=")
            parts = parts[1].split(",")
            mac_address = parts[0].strip()
            ip_address = parts[1].strip()
            statue_name = parts[2].strip() if len(parts) >= 3 else ""
            if statue_name in statues:
                try:
                    statue = Statue(statue_name)
                    teensy_config[statue].update(
                        {
                            "mac_address": mac_address,
                            "ip_address": ip_address,
                        }
                    )
                except ValueError:
                    print(f"Unknown statue name: {statue_name}")


def load_audio():
    """Load audio files into memory."""
    global audio
    file = os.path.join(SONG_DIR, ACTIVE_SONG)
    if not os.path.exists(file):
        print(f"Audio file not found: {file}")
        return
    try:
        audio_data, sample_rate = sf.read(file)
        # Ensure audio_data is 2D
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        if debug:
            print(f"\nLoaded: {os.path.basename(file)}")
            print(f"Duration: {len(audio_data) / sample_rate:.1f} seconds")
            print(f"Channels: {audio_data.shape[1]}")
    except Exception as e:
        print(f"Error loading audio file: {e}")
        return
    audio["data"] = audio_data
    audio["sample_rate"] = sample_rate


def load_devices():
    """Query audio devices and map them to statues."""
    global devices
    all_devices = sd.query_devices()
    if debug:
        print("Available audio devices:")
        for d in all_devices:
            print(
                f"  {d['index']}: {d['name']} ({d['max_input_channels']} in, {d['max_output_channels']} out)"
            )

    # Updated pattern for "USB PnP Sound Device: Audio (hw:2,0)" format
    pattern = r"^([^:]*): [^(]* \((hw:\d+,\d+)\)$"

    transformed_devices = []
    for device in all_devices:
        match = re.search(pattern, device["name"])
        if match:
            transformed_devices.append(
                {
                    "index": device["index"],
                    "type": match.group(1).lower(),
                    "port_id": match.group(2),
                    "num_outputs": int(device["max_output_channels"]),
                    "sample_rate": int(device["default_samplerate"]),
                }
            )

    total_outputs = sum(d["num_outputs"] for d in transformed_devices)
    if total_outputs < len(devices.keys()):
        print(
            f"Warning: Not enough audio outputs available ({total_outputs} < {len(devices.keys())})"
        )
        return

    for device in transformed_devices:
        curr_output = 0
        for statue, config in devices.items():
            if (
                config["port_id"] == device["port_id"]
                and curr_output == device["output"]
            ):
                config["type"] = device["type"]
                config["sample_rate"] = device["sample_rate"]
                curr_output += 1
                if curr_output >= device["num_outputs"]:
                    break

    for statue, config in devices.items():
        if config["type"] == "" or config["sample_rate"] == 0:
            print(f"Warning: No device found for {statue.value} ({config['port_id']})")
            continue


def get_statue(path: str, default: Statue | None = None) -> Statue | None:
    parts = path.split("/")
    if len(parts) < 3:
        return default
    if len(parts) > 3:
        print(f"Invalid path: {path}")
        return None
    param = parts[-1]
    if param == "":
        return default
    try:
        return Statue(param)
    except ValueError:
        print(f"Unknown statue: {path}")
        return None


def update_active_statues(payload: dict) -> tuple[Set[Statue], Set[Statue]]:
    """Update the list of active statues based on the received payload."""
    global active_statues
    global linked_statues

    statue_name = payload.get("detector", "")
    try:
        detector = Statue(statue_name)
    except ValueError:
        print(f"Unknown statue: {statue_name}")
    emitters = []
    for statue_name in payload.get("emitters", []):
        try:
            statue = Statue(statue_name)
            emitters.append(statue)
        except ValueError:
            print(f"Unknown statue: {statue_name}")

    linked_statues[detector] = emitters
    old_actives = active_statues.copy()
    active_statues = set()
    for statue, emitters in linked_statues.items():
        if len(emitters) > 0:
            active_statues.add(statue)
            continue

        has_reverse_contact = False
        for other_emitters in linked_statues.values():
            if statue in other_emitters:
                has_reverse_contact = True
                break

        if has_reverse_contact:
            active_statues.add(statue)

    if debug:
        print(f"Active statues: {active_statues}")

    new_actives = active_statues - old_actives
    new_dormants = old_actives - active_statues
    return new_actives, new_dormants


def publish_mqtt(topic: str, payload: dict) -> int:
    """Publish a message to the MQTT broker."""
    if debug:
        print(f"Publishing to {topic}: {json.dumps(payload, indent=2)}")
    r = mqttc.publish(topic, json.dumps(payload))
    try:
        r.wait_for_publish(1)
    except Exception as e:
        print(f"Failed to publish message: {e}")
    return r.rc


def send_led_cmd(statue: Statue, seg_payload: dict) -> int:
    """Send a WLED command to control the LEDs of a statue."""
    # TODO: map statue to a QuinLED board (client name) and segment ids
    seg0 = seg_payload.copy()
    seg0["id"] = 0
    payload = {
        "tt": 0,
        "seg": [seg0],
    }
    return publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)


# ### Actions


def send_config():
    config = {}
    for statue, config in teensy_config.items():
        config[statue.value] = {
            "emit": config["emit"],
            "detect": [s.value for s in config.get("detect", [])],
            "ip_address": config["ip_address"],
            "mac_address": config["mac_address"],
        }
    return publish_mqtt(CONFIG_RESP_MQTT_TOPIC, config)


def all_off():
    payload = {
        "tt": 0,
        "on": False,
        "bri": 0,
    }
    # TODO: send to all boards
    return publish_mqtt(WLED_MQTT_TOPIC.format(Statue.ALL.value), payload)


# def haptics_on(statue: Statue) -> int:
#     """Send WLED commands to turn the haptic motor on and then fade."""
#     # TODO: map statue to a QuinLED board (client name) and segment id
#     payload = {
#         "tt": 0,
#         "seg": [
#             {
#                 "id": 0,
#                 "on": True,
#                 "bri": HAPTIC_BRIGHTNESS,
#                 "col": [[255, 255, 255, 255]],
#             }
#         ],
#     }
#     publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)
#     payload = {
#         "tt": HAPTIC_FADE_MS,
#         "seg": [
#             {
#                 "id": 0,
#                 "on": True,
#                 "bri": 0,
#                 "col": [[255, 255, 255, 255]],
#             }
#         ],
#     }
#     return publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)


def haptics_on(statue: Statue) -> int:
    return publish_mqtt(HAPTIC_MQTT_TOPIC, {"statue": statue.value})


def leds_active(statue: Statue):
    send_led_cmd(
        statue,
        {
            "on": True,
            "bri": 255,
            "col": COLORS.get(statue, {}).get("active", COLORS[Statue.ALL]["active"]),
            "fx": EFFECTS.get(statue, {})
            .get("active", EFFECTS[Statue.ALL]["active"])
            .value,
            "pal": PALETTE_ID,
        },
    )


def leds_dormant(statue: Statue):
    send_led_cmd(
        statue,
        {
            "fx": 0,
            "bri": 255,
            "col": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        },
    )
    send_led_cmd(
        statue,
        {
            "on": True,
            "bri": 255,
            "col": COLORS.get(statue, {}).get("dormant", COLORS[Statue.ALL]["dormant"]),
            "fx": EFFECTS.get(statue, {})
            .get("dormant", EFFECTS[Statue.ALL]["dormant"])
            .value,
            "pal": PALETTE_ID,
        },
    )


def audio_active(statue: Statue):
    # TODO: implement
    pass


def audio_dormant(statue: Statue):
    # TODO: implement
    pass


# ### Debug server


class ControllerDebugHandler(BaseHTTPRequestHandler):
    def _send_response(self, payload):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(payload, indent=2), "utf-8"))

    def _send_404(self):
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "not found"}')

    def _send_400(self):
        self.send_response(400)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "bad request"}')

    # TODO: report network status of various connected devices
    def do_GET(self):
        if debug:
            print(f"Received GET request on {self.path}")

        if self.path == "/" or self.path == "/info":
            self._send_response(
                {
                    "description": "Missing Link rpi controller script",
                    "version": VERSION,
                }
            )
        else:
            self._send_404()

    def do_POST(self):
        global debug

        dataStr = self.rfile.read(int(self.headers["Content-Length"]))
        data = json.loads(dataStr)
        if debug:
            print(f"Received POST request on {self.path}: {data}")

        if self.path == "/debug":
            if isinstance(data, bool):
                debug = data
            else:
                self._send_400()
        elif self.path == "/contact":
            code = publish_mqtt(LINK_MQTT_TOPIC, data)
            self._send_response(
                {
                    "status_code": code,
                }
            )
            print("triggered a contact event")
        elif self.path.startswith("/led"):
            statue = get_statue(self.path, Statue.ALL)
            if statue is None:
                self._send_400()
                return
            code = send_led_cmd(statue, data)
            self._send_response(
                {
                    "status_code": code,
                }
            )
            print("sent a LED cmd to:", statue)
        elif self.path.startswith("/haptic"):
            statue = get_statue(self.path, Statue.ALL)
            if statue is None:
                self._send_400()
                return
            code = haptics_on(statue)
            self._send_response(
                {
                    "status_code": code,
                }
            )
            print("sent a haptic motor cmd to:", statue)
        else:
            self._send_404()


def start_debug_server():
    server = HTTPServer(("", DEBUG_PORT), ControllerDebugHandler)
    try:
        print(f"Starting debug server on port {DEBUG_PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        server.server_close()
        print("Debug server stopped")


# ### MQTT client


# The callback for when the client receives a CONNACK response from the server.
def on_connect(mqttc, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mqttc.subscribe(LINK_MQTT_TOPIC)


# The callback for when a PUBLISH message is received from the server.
def on_message(mqttc, userdata, msg):
    if debug:
        print(f"Received message on topic {msg.topic}: {msg.payload}")
    try:
        payload = json.loads(msg.payload)
    except Exception as e:
        print(e)
        return

    if msg.topic == CONFIG_REQ_MQTT_TOPIC:
        send_config()

    if msg.topic == LINK_MQTT_TOPIC:
        new_actives, new_dormants = update_active_statues(payload)
        for statue in new_actives:
            audio_active(statue)
            leds_active(statue)
            haptics_on(statue)
        for statue in new_dormants:
            audio_dormant(statue)
            leds_dormant(statue)


if __name__ == "__main__":
    extract_addresses()
    load_audio()
    load_devices()

    # Should be in the global scope, mqttc is a global variable
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_BROKER, MQTT_PORT)

    thread = threading.Thread(target=start_debug_server, args=(), daemon=True)
    thread.start()

    all_off()
    leds_dormant(Statue.ALL)
    send_config()

    try:
        print("Starting MQTT client")
        mqttc.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    mqttc.disconnect()
    print("Disconnected from MQTT broker")
