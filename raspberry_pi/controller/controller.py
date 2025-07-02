#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["deepmerge", "just-playback", "paho-mqtt"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./controller.py

import json
import os
import subprocess
import threading
import time
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer

import paho.mqtt.client as mqtt
from deepmerge import Merger
from just_playback import Playback

# ### Reference docs
# https://docs.google.com/document/d/107ZdOsc81E29lZZVTtqirHpqJKrvnqui0-EGSTGGslk/edit?tab=t.0
# https://docs.google.com/document/d/1Ke_J2RJw4KxdZ-_T9ig0PT2Xt90lASSOVepb4xZkUKM/edit?tab=t.0
# https://blog.dusktreader.dev/2025/03/29/self-contained-python-scripts-with-uv/
# https://docs.astral.sh/uv/
# https://github.com/cheofusi/just_playback
# https://pypi.org/project/deepmerge/
# https://www.raspberrypi.com/documentation/computers/configuration.html#audio-3
# https://www.raspberrypi.com/documentation/accessories/audio.html


# ### Parameters

VERSION = "0.2.0"  # Version of the script
DEBUG_PORT = 8080  # Port for the debug server
# Folder for audio files
SRC_SONG_DIR = os.path.join(os.path.dirname(__file__), "../../audio_files")
# Use ramdisk to speed up startup
SONG_DIR = "/run/audio_files"

# MQTT server settings
LINK_MQTT_TOPIC = "missing_link/touch"  # Topic for link/unlink msgs
# {
#     "action": "link", # or "unlink"
#     "statues": ["eros", "elektra"], # List of statues that are affected
# }
HAPTIC_MQTT_TOPIC = "missing_link/haptic"  # Topic for haptic motor commands
# {
#     "statue": "eros",  # Statue to turn on the haptic motors for
# }
WLED_MQTT_TOPIC = "wled/{}/api"  # Topic template for WLED commands
MQTT_BROKER = "127.0.0.1"  # IP address of the MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None

# WLED settings
PALETTE_ID = 3


class Statue(Enum):
    ALL = "all"
    EROS = "eros"
    ELEKTRA = "elektra"


class Mode(Enum):
    BASIC = "basic"


# value = effect id in WLED
class Effect(Enum):
    SOLID = 0
    FIREWORKS = 42
    NOISE_1 = 71


dynConfig = {
    "debug": False,
    "dormant_songs": [],
    "active_songs": [],
    "fade_ms": 2000,  # Fade time in milliseconds
    "cool_down_ms": 2000,  # Audio recent song wait time in milliseconds
    "current": {
        "active_song": "",
        "dormant_song": "",
        "mode": Mode.BASIC.value,
        "active_effect": Effect.NOISE_1.value,
        "dormant_effect": Effect.FIREWORKS.value,
    },
    Statue.ELEKTRA.value: {
        "active_colors": [[0, 25, 255], [0, 200, 255], [0, 25, 255]],
    },
    Statue.EROS.value: {
        "active_colors": [[255, 0, 100], [225, 0, 255], [255, 0, 100]],
    },
    Statue.ALL.value: {
        "dormant_colors": [[255, 255, 255], [0, 0, 0], [0, 0, 0]],
    },
}

config_merger = Merger(
    [  # merge strategies for each type
        (list, ["override"]),
        (dict, ["merge"]),
        (set, ["override"]),
    ],
    ["override"],  # fallback strategy
    ["override"],  # strategy for conflicting types
)

# MQTT client
mqttc = None

songs_to_playback = {}
current_playback = None
last_played_s = 0


# ### Helper functions


def copy_files():
    src = os.path.join(SRC_SONG_DIR, "")
    subprocess.call(["sudo", "rsync", "-a", "--no-compress", src, SONG_DIR])
    subprocess.call(["sudo", "chmod", "-R", "777", SONG_DIR])
    print(f"Copied files from {src} to {SONG_DIR}")


def setup_config_and_songs():
    global dynConfig
    global current_playback
    global songs_to_playback

    if not os.path.isdir(SONG_DIR):
        raise Exception(f"Error: '{SONG_DIR}' is not a valid directory.")

    entries = os.listdir(SONG_DIR)
    files = [f for f in entries if os.path.isfile(os.path.join(SONG_DIR, f))]
    files.sort()

    dynConfig["active_songs"] = [f for f in files if " active " in f.lower()]
    dynConfig["dormant_songs"] = [f for f in files if " dormant " in f.lower()]
    dynConfig["current"]["active_song"] = dynConfig["active_songs"][0]
    dynConfig["current"]["dormant_song"] = dynConfig["dormant_songs"][0]

    for f in files:
        # Manages playback of a single audio file
        playback = Playback(os.path.join(SONG_DIR, f))
        playback.loop_at_end(True)
        playback.set_volume(1.0)
        songs_to_playback[f] = playback

    current_playback = songs_to_playback[dynConfig["current"]["dormant_song"]]

    if dynConfig["debug"]:
        print("Dynamic config:", json.dumps(dynConfig, indent=2))


def get_statue(path: str, default: Statue = None) -> Statue | None:
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


def publish_mqtt(topic: str, payload: dict):
    if dynConfig["debug"]:
        print(f"Publishing to {topic}: {json.dumps(payload, indent=2)}")
    r = mqttc.publish(topic, json.dumps(payload))
    try:
        r.wait_for_publish(1)
    except Exception as e:
        print(f"Failed to publish message: {e}")
    return r.rc


def send_to_wled(statue: Statue, payload: dict):
    return publish_mqtt(WLED_MQTT_TOPIC.format(statue.value), payload)


# TODO: doesn't handle pause / resume currently
def play_song(mode: Mode, song: str):
    global current_playback
    global last_played_s

    new_playback = songs_to_playback.get(song)
    if new_playback is None:
        print(f"Error: '{song}' is not a valid song.")
        return
    if new_playback is current_playback:
        if not current_playback.playing:
            current_playback.play()
        return

    if mode == Mode.BASIC:
        new_playback.play()
        if current_playback.playing:
            # TODO: test pausing first
            current_playback.pause()
            current_playback.stop()
        current_playback = new_playback

    last_played_s = time.time()
    if dynConfig["debug"]:
        print(f"Playing song: {song}")


# ### Actions


def haptics_on(statue: Statue):
    publish_mqtt(HAPTIC_MQTT_TOPIC, {"statue": statue.value})


def leds_active(statue: Statue):
    send_to_wled(
        statue,
        {
            "tt": 0,
            "seg": [
                {
                    "id": 0,
                    "on": True,
                    "bri": 255,
                    "col": dynConfig[statue.value]["active_colors"],
                    "fx": dynConfig["current"]["active_effect"],
                    "pal": PALETTE_ID,
                },
            ],
        },
    )


def leds_dormant():
    send_to_wled(
        Statue.ALL,
        {
            "tt": 0,
            "seg": [
                {
                    "id": 0,
                    "fx": 0,
                    "bri": 255,
                    "col": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                },
            ],
        },
    )
    send_to_wled(
        Statue.ALL,
        {
            "tt": 0,
            "seg": [
                {
                    "id": 0,
                    "on": True,
                    "bri": 255,
                    "col": dynConfig[Statue.ALL.value]["dormant_colors"],
                    "fx": dynConfig["current"]["dormant_effect"],
                    "pal": PALETTE_ID,
                },
            ],
        },
    )


def audio_active(statues: list[Statue]):
    # TODO: cycle through active songs
    mode = Mode(dynConfig["current"]["mode"])
    if mode == Mode.BASIC:
        play_song(mode, dynConfig["current"]["active_song"])


def audio_dormant():
    # TODO: cycle through dormant songs
    mode = Mode(dynConfig["current"]["mode"])
    if mode == Mode.BASIC:
        play_song(mode, dynConfig["current"]["dormant_song"])


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
        if dynConfig["debug"]:
            print(f"Received GET request on {self.path}")

        if self.path == "/" or self.path == "/info":
            self._send_response(
                {
                    "description": "Missing Link rpi controller script",
                    "version": VERSION,
                }
            )
        elif self.path == "/config":
            self._send_response(dynConfig)
        else:
            self._send_404()

    def do_POST(self):
        global dynConfig

        dataStr = self.rfile.read(int(self.headers["Content-Length"]))
        data = json.loads(dataStr)
        if dynConfig["debug"]:
            print(f"Received POST request on {self.path}: {data}")

        if self.path == "/config":
            try:
                config_merger.merge(dynConfig, data)
                self._send_response(dynConfig)
                print("new config settings:", json.dumps(data, indent=2))
            except Exception as e:
                print(e)
                self._send_400()
        elif self.path == "/touch":
            code = publish_mqtt(LINK_MQTT_TOPIC, data)
            self._send_response(
                {
                    "status_code": code,
                }
            )
            print("triggered a touch event")
        elif self.path.startswith("/wled"):
            statue = get_statue(self.path, Statue.ALL)
            if statue is None:
                self._send_400()
                return
            code = send_to_wled(statue, data)
            self._send_response(
                {
                    "status_code": code,
                }
            )
            print("sent a WLED cmd to:", statue)
        elif self.path.startswith("/haptic/"):
            statue = get_statue(self.path)
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
    if dynConfig["debug"]:
        print(f"Received message on topic {msg.topic}: {msg.payload}")
    payload = json.loads(msg.payload)

    if msg.topic == LINK_MQTT_TOPIC:
        run_controller(payload)


def start_controller():
    audio_dormant()
    leds_dormant()


def run_controller(msg: dict):
    action = msg.get("action", "")

    if action == "link":
        statues = [Statue(name) for name in msg.get("statues", [])]
        audio_active(statues)
        for statue in statues:
            leds_active(statue)
            haptics_on(statue)

    elif action == "unlink":
        audio_dormant()
        leds_dormant()

    else:
        print(f"Unknown action: {action}")
        return


if __name__ == "__main__":
    copy_files()
    setup_config_and_songs()

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
