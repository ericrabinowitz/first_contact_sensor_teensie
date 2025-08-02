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
import subprocess
import threading
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer

import paho.mqtt.client as mqtt


class Statue(Enum):
    ALL = "all"
    ARCHES = "arches"
    EROS = "eros"
    ELEKTRA = "elektra"
    SOPHIA = "sophia"
    ULTIMO = "ultimo"
    ARIEL = "ariel"


class Effect(Enum):
    SOLID = 0
    FIREWORKS = 42
    NOISE = 71


# ### Parameters

VERSION = "1.0"  # Version of the script
DEBUG_PORT = 8080  # Port for the debug server

# Folder for audio files
SRC_SONG_DIR = os.path.join(os.path.dirname(__file__), "../../audio_files")
# Use ramdisk to speed up file I/O
SONG_DIR = "/run/audio_files"
ACTIVE_SONG = "Missing Link Playa 1 - 6 Channel 6-7.wav"

FREQUENCIES = {
    Statue.ELEKTRA: 8_000,
    Statue.EROS: 10_000,
    Statue.ELEKTRA: 12_000,
    Statue.SOPHIA: 14_000,
    Statue.ULTIMO: 16_000,
    Statue.ARIEL: 18_000,
}

# MQTT server settings
LINK_MQTT_TOPIC = "missing_link/contact"  # Topic for link/unlink msgs
# {
#     "action": "link", # or "unlink"
#     "detector": "eros", # Statue that detected the contact
#     "emitters": ["elektra"], # List of statues were detected
# }
CONFIG_MQTT_TOPIC = "missing_link/config"  # Topic for configuring the Teensy
# {
#     "send_config": true,
# }
# {
#     "eros": {
#         "frequency": 10000,  # Frequency in Hz
#     }, ... # Other statues
# }
WLED_MQTT_TOPIC = "wled/{}/api"  # Topic template for WLED commands
MQTT_BROKER = "127.0.0.1"  # IP address of the MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None

# WLED settings
PALETTE_ID = 3
FADE_MS = 2000  # Fade time in milliseconds
COOL_DOWN_MS = 2000  # Audio recent song wait time in milliseconds
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
EFFECTS = {
    Statue.ALL: {
        "active": Effect.FIREWORKS,
        "dormant": Effect.NOISE,
    },
}

HAPTIC_FADE_MS = 1000  # Haptic motor fade time in milliseconds
HAPTIC_BRIGHTNESS = 170  # Haptic motor strength (out of 255)


# ### Global variables

debug = False  # Enable debug mode for verbose output

# MQTT client
mqttc = None


# ### Helper functions


def copy_files():
    src = os.path.join(SRC_SONG_DIR, "")
    subprocess.call(["sudo", "rsync", "-a", "--no-compress", src, SONG_DIR])
    subprocess.call(["sudo", "chmod", "-R", "777", SONG_DIR])
    print(f"Copied files from {src} to {SONG_DIR}")


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
    """Send configuration to the Teensy devices."""
    payload = {}
    for statue, freq in FREQUENCIES.items():
        payload[statue.value] = {"frequency": freq}
    return publish_mqtt(CONFIG_MQTT_TOPIC, payload)


def all_off():
    payload = {
        "tt": 0,
        "on": False,
        "bri": 0,
    }
    return publish_mqtt(WLED_MQTT_TOPIC.format(Statue.ALL.value), payload)


def haptic_on(statue: Statue) -> int:
    """Send WLED commands to turn the haptic motor on and then fade."""
    # TODO: map statue to a QuinLED board (client name) and segment id
    payload = {
        "tt": 0,
        "seg": [
            {
                "id": 0,
                "on": True,
                "bri": HAPTIC_BRIGHTNESS,
                "col": [[255, 255, 255, 255]],
            }
        ],
    }
    publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)
    payload = {
        "tt": HAPTIC_FADE_MS,
        "seg": [
            {
                "id": 0,
                "on": True,
                "bri": 0,
                "col": [[255, 255, 255, 255]],
            }
        ],
    }
    return publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)


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


def audio_active(statues: list[Statue]):
    # TODO: implement
    pass


def audio_dormant(statues: list[Statue]):
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
            code = haptic_on(statue)
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
    payload = json.loads(msg.payload)

    if msg.topic == CONFIG_MQTT_TOPIC:
        if "send_config" in payload:
            send_config()

    if msg.topic == LINK_MQTT_TOPIC:
        run_controller(payload)


def start_controller():
    all_off()
    leds_dormant(Statue.ALL)
    send_config()


def run_controller(msg: dict):
    action = msg.get("action", "")
    # TODO: fix, diff with current state

    if action == "link":
        statues = [Statue(name) for name in msg.get("statues", [])]
        audio_active(statues)
        for statue in statues:
            leds_active(statue)
            haptic_on(statue)

    elif action == "unlink":
        audio_dormant()
        leds_dormant()

    else:
        print(f"Unknown action: {action}")
        return


if __name__ == "__main__":
    copy_files()

    # Should be in the global scope, mqttc is a global variable
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_BROKER, MQTT_PORT)

    thread = threading.Thread(target=start_debug_server, args=(), daemon=True)
    thread.start()

    start_controller()

    try:
        print("Starting MQTT client")
        mqttc.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    mqttc.disconnect()
    print("Disconnected from MQTT broker")
