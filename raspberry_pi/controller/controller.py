#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["backports.strenum", "numpy", "paho-mqtt", "requests", "sounddevice", "soundfile", "ultraimport"]
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
import sys
import time
from enum import IntEnum, auto
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Set, Union

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum

import paho.mqtt.client as mqtt
import requests
import sounddevice as sd
import soundfile as sf
import ultraimport as ui

# from ..audio.music import ToggleableMultiChannelPlayback
ToggleableMultiChannelPlayback = ui.ultraimport(
    "__dir__/../audio/music.py", "ToggleableMultiChannelPlayback"
)


class Statue(StrEnum):
    DEFAULT = auto()
    ARCHES = auto()
    EROS = auto()
    ELEKTRA = auto()
    ARIEL = auto()
    SOPHIA = auto()
    ULTIMO = auto()


class Board(StrEnum):
    ALL = auto()
    FIVE_V_1 = auto()
    FIVE_V_2 = auto()
    TWELVE_V_1 = auto()


class Effect(IntEnum):
    SOLID = 0
    FIREWORKS = 42
    NOISE = 71


# TODO:
# Support multiple output channels.
# Update Teensy to support auto-provisioning. Mainly, which Teensy maps to which statue.
# Turn off lights during the day.
# Decide if we need to send haptic commands to the Teensy.
# Check if we can improve audio device to port id map stability. If not initialize mapping on startup.
# Optional:
# Support more complex audio channel to audio device mappings.
# Support playing different audio when in dormant mode.
# In segment_map, track part that each segment controls.

# ### Parameters

VERSION = "1.1"  # Version of the script
DEBUG_PORT = 8080  # Port for the debug server
STARTUP_DELAY = 5  # Delay to allow MQTT clients to connect, seconds

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
#         "emit": 10000,              # Frequency in Hz to emit a tone on
#         "detect": ["elektra", ...], # Statues to receive tones from
#         "threshold": 0.01,          # Detection threshold, using the Goertzel algorithm
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
STATUS_TOPIC = "$SYS/broker/clients/connected"  # Topic for MQTT client status
MQTT_BROKER = "127.0.0.1"  # IP address of the MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None

# WLED settings
# TODO: test different palettes, like the default one
PALETTE_ID = 3
FADE_MS = 2000  # Fade time in milliseconds
COOL_DOWN_MS = 2000  # Audio recent song wait time in milliseconds

# Defaults to the settings for DEFAULT
# TODO: pick colors
COLORS = {
    Statue.EROS: {
        # red
        "active": [[255, 0, 100], [225, 0, 255], [255, 0, 100]],
    },
    Statue.ELEKTRA: {
        # blue
        "active": [[0, 25, 255], [0, 200, 255], [0, 25, 255]],
    },
    Statue.ARIEL: {
        # yellow
        "active": [[255, 200, 0], [255, 255, 0], [255, 255, 0]],
    },
    Statue.SOPHIA: {
        # green
        "active": [[8, 255, 0], [66, 237, 160], [66, 237, 160]],
    },
    Statue.ULTIMO: {
        # orange
        "active": [[255, 165, 0], [255, 199, 94], [255, 199, 94]],
    },
    Statue.DEFAULT: {
        "active": [[0, 25, 255], [0, 200, 255], [0, 25, 255]],
        "dormant": [[255, 255, 255], [0, 0, 0], [0, 0, 0]],
    },
}

# Defaults to the settings for DEFAULT
EFFECTS = {
    Statue.DEFAULT: {
        "active": Effect.FIREWORKS,
        "dormant": Effect.NOISE,
    },
}


# ### Global variables

# Enable debug logging
debug = False

# Disable all LED/WLED functionality
no_leds = False

# MQTT client
mqttc: Any = None

# Derived from audio file
audio = {
    "data": None,  # Loaded audio data
    "sample_rate": 0,
}

# Maps statues to QuinLED boards and segment ids.
# The control pin to segment id mapping is done in the WLED app.
segment_map = {
    Statue.ARCHES: {
        # Board.TWELVE_V_1: [0],  # WLED segment ids
    },
    Statue.EROS: {},
    Statue.ELEKTRA: {},
    Statue.ARIEL: {},
    Statue.SOPHIA: {},
    Statue.ULTIMO: {},
}

board_config = {
    Board.FIVE_V_1: {
        "mac_address": "",
        "ip_address": "",
    },
    Board.FIVE_V_2: {
        "mac_address": "",
        "ip_address": "",
    },
    Board.TWELVE_V_1: {
        "mac_address": "",
        "ip_address": "",
    },
}

# Maps statues to detailed info about its audio device and channels.
device_map = {
    Statue.EROS: {
        "port_id": "hw:2,0",  # ID of (USB) port that the device is connected to
        "output": 0,  # Output channel index, ie 0 for first output
        "input": 0,  # Input channel index of the audio file, ie 0 for first channel
        "type": "",  # Derived from device info, ie "c-media usb headphone set"
        "index": -1,  # Derived from device info, ie 0
        "sample_rate": 0,  # Derived from device info, ie 44100
    },
    Statue.ELEKTRA: {
        "port_id": "hw:3,0",
        "output": 0,
        "input": 1,
        "type": "",
        "index": -1,
        "sample_rate": 0,
    },
    Statue.ARIEL: {
        "port_id": "hw:4,0",
        "output": 0,
        "input": 2,
        "type": "",
        "index": -1,
        "sample_rate": 0,
    },
    Statue.SOPHIA: {
        "port_id": "hw:5,0",
        "output": 0,
        "input": 3,
        "type": "",
        "index": -1,
        "sample_rate": 0,
    },
    Statue.ULTIMO: {
        "port_id": "hw:6,0",
        "output": 0,
        "input": 4,
        "type": "",
        "index": -1,
        "sample_rate": 0,
    },
}

# Teensy configuration. Maps statues to their Teensy settings.
teensy_config = {
    Statue.EROS: {
        "emit": 10077,
        "detect": [Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL],
        "threshold": 0.01,
        "mac_address": "",  # derived from the dnsmasq.conf file
        "ip_address": "",  # derived from the dnsmasq.conf file
    },
    Statue.ELEKTRA: {
        "emit": 12274,
        "detect": [Statue.EROS, Statue.SOPHIA, Statue.ULTIMO, Statue.ARIEL],
        "threshold": 0.01,
        "mac_address": "",
        "ip_address": "",
    },
    Statue.ARIEL: {
        "emit": 14643,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ULTIMO],
        "threshold": 0.01,
        "mac_address": "",
        "ip_address": "",
    },
    Statue.SOPHIA: {
        "emit": 17227,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.ULTIMO, Statue.ARIEL],
        "threshold": 0.01,
        "mac_address": "",
        "ip_address": "",
    },
    Statue.ULTIMO: {
        "emit": 19467,
        "detect": [Statue.EROS, Statue.ELEKTRA, Statue.SOPHIA, Statue.ARIEL],
        "threshold": 0.01,
        "mac_address": "",
        "ip_address": "",
    },
}

# Detected contact pairings
linked_statues: Dict[Statue, List[Statue]] = {
    Statue.EROS: [],
    Statue.ELEKTRA: [],
    Statue.ARIEL: [],
    Statue.SOPHIA: [],
    Statue.ULTIMO: [],
}
# Statues that are currently active
active_statues: Set[Statue] = set()

music_playback: Any = None

mqtt_num_connected = 0

# ### Helper functions


def bool_env_var(env_var: str) -> bool:
    var_str = os.environ.get(env_var, "false").strip().lower()
    val = var_str in ["t", "true", "1"]
    if val:
        print(f"Environment variable {env_var} is enabled!")
    return val


def extract_addresses():
    """Extracts MAC and IP addresses from the dnsmasq.conf file."""
    global teensy_config
    global board_config
    if not os.path.exists(DNSMASQ_FILE):
        print(f"Error: DNSMASQ file not found: {DNSMASQ_FILE}")
        return

    with open(DNSMASQ_FILE, "r") as f:
        lines = f.readlines()

    statues = teensy_config.keys()
    boards = board_config.keys()
    for line in lines:
        if "dhcp-host" in line:
            parts = line.split("=")
            parts = parts[1].split(",")
            mac_address = parts[0].strip()
            ip_address = parts[1].strip()
            hostname = parts[2].strip() if len(parts) >= 3 else ""
            if hostname in statues:
                statue = Statue(hostname)
                teensy_config[statue].update(
                    {
                        "mac_address": mac_address,
                        "ip_address": ip_address,
                    }
                )
            if hostname in boards:
                board = Board(hostname)
                board_config[board] = {
                    "mac_address": mac_address,
                    "ip_address": ip_address,
                }


def load_audio():
    """Load audio files into memory."""
    global audio
    file = os.path.join(SONG_DIR, ACTIVE_SONG)
    if not os.path.exists(file):
        print(f"Error: Audio file not found: {file}")
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
        print(f"Error: Failed to load audio file: {e}")
        return
    audio["data"] = audio_data
    audio["sample_rate"] = int(sample_rate)


def load_audio_devices():
    """Query audio devices and map them to statues."""
    global device_map
    all_devices = sd.query_devices()
    if debug:
        print("Available audio devices:")
        for d in all_devices:
            print(
                f"  {d['index']}: {d['name']} ({d['max_input_channels']} in, {d['max_output_channels']} out)"  # noqa: E501
            )

    # Updated pattern for "USB PnP Sound Device: Audio (hw:2,0)" format
    pattern = r"^([^:]*): [^(]* \((hw:\d+,\d+)\)$"

    transformed_devices = []
    for d in all_devices:
        match = re.search(pattern, d["name"])
        if match:
            transformed_devices.append(
                {
                    "index": d["index"],
                    "type": match.group(1).lower(),
                    "port_id": match.group(2),
                    "num_outputs": int(d["max_output_channels"]),
                    "sample_rate": int(d["default_samplerate"]),
                }
            )

    total_outputs = sum(d["num_outputs"] for d in transformed_devices)
    if total_outputs < len(device_map.keys()):
        print(
            f"Error: Not enough audio outputs ({total_outputs} < {len(device_map.keys())})"
        )
        return

    for device in transformed_devices:
        for statue, config in device_map.items():
            if config["port_id"] == device["port_id"]:
                if config["output"] >= device["num_outputs"]:
                    print(
                        f"Error: Device {device['port_id']} does not have output {config['output']}"
                    )
                    continue
                if config["input"] >= audio["data"].shape[1]:
                    print(
                        f"Error: {statue.value} does not have music channel {config['input']}"
                    )
                    continue
                if device["sample_rate"] != audio["sample_rate"]:
                    print(
                        f"Error: Device {device['port_id']} default sample rate ({device['sample_rate']}) != audio file ({audio['sample_rate']})"  # noqa: E501
                    )
                    continue

                config["type"] = device["type"]
                config["sample_rate"] = device["sample_rate"]
                config["index"] = device["index"]

    for statue, config in device_map.items():
        if config["type"] == "" or config["sample_rate"] == 0:
            print(
                f"Error: No device found for {statue.value} ({config['port_id']}, {config['output']})"  # noqa: E501
            )
            continue


def initialize_playback():
    """Initialize the music playback object."""
    global music_playback

    devices = []
    for statue, config in device_map.items():
        devices.append(
            {
                "statue": statue.value,
                "device_index": config["index"],
                "sample_rate": config["sample_rate"],
                "channel_index": config["input"],
            }
        )
    devices.sort(key=lambda d: d["channel_index"])

    music_playback = ToggleableMultiChannelPlayback(
        audio["data"], audio["sample_rate"], devices
    )
    music_playback.start()


def get_statue(path: str) -> Union[Statue, None]:
    parts = path.split("/")
    if len(parts) != 3:
        print(f"Warning: Invalid path: {path}")
        return None
    param = parts[-1]
    if param == "":
        print("Warning: Empty statue")
        return None
    try:
        return Statue(param)
    except ValueError:
        print(f"Warning: Unknown statue: {path}")
        return None


def update_active_statues(payload: dict) -> tuple[Set[Statue], Set[Statue]]:
    """Update the list of active statues based on the received payload."""
    global active_statues
    global linked_statues

    statue_name = payload.get("detector", "")
    try:
        detector = Statue(statue_name)
    except ValueError:
        print(f"Error: Unknown statue: {statue_name}")
        return set(), set()

    emitters = []
    for statue_name in payload.get("emitters", []):
        try:
            statue = Statue(statue_name)
            emitters.append(statue)
        except ValueError:
            print(f"Error: Unknown statue, ignoring: {statue_name}")

    linked_statues[detector] = emitters
    old_actives = active_statues.copy()
    active_statues = set()
    for statue, emitters in linked_statues.items():
        if len(emitters) > 0:
            active_statues.add(statue)
        for emitter in emitters:
            active_statues.add(emitter)

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
        print(f"Warning: Failed to publish message: {e}")
    return r.rc


def send_led_cmd(statue: Statue, seg_payload: dict) -> int:
    """Send a WLED command to control the LEDs of a statue."""
    if no_leds:
        return 0
    if statue == Statue.DEFAULT:
        print("Error: Cannot send LED command to DEFAULT statue")
        return -1

    last_rc = 0
    for board, seg_ids in segment_map[statue].items():
        if len(seg_ids) == 0:
            continue
        payload = {
            "tt": 0,
            "seg": [],
        }
        for seg_id in seg_ids:
            payload["seg"].append(
                {
                    "id": seg_id,
                    **seg_payload,
                }
            )
        last_rc = publish_mqtt(WLED_MQTT_TOPIC.format(board), payload)
    return last_rc


def send_config():
    """Send the Teensy configuration via MQTT."""
    return publish_mqtt(CONFIG_RESP_MQTT_TOPIC, teensy_config)


def initialize_leds():
    """Initialize the segment map and turn the LEDs on."""
    if no_leds:
        print("TEST MODE: Skipping LED initialization (WLED disabled)")
        return

    global segment_map
    payload = {
        "tt": 0,
        "on": True,
        "bri": 0,
        "v": True,
    }
    statues = segment_map.keys()

    for board in board_config.keys():
        resp = requests.post(
            "http://{}/json/state".format(board_config[board]["ip_address"]),
            json=payload,
        )
        if resp.status_code != 200:
            print(f"Error: Failed to initialize board {board}: {resp.text}")
            continue

        segments = resp.json().get("seg", [])
        for segment in segments:
            # "n" field only exists if the segment has been renamed
            name = segment.get("n", "").strip().lower()
            parts = name.split(" ")
            if len(parts) < 1:
                continue
            for parts[0] in statues:
                segment_map[Statue(parts[0])].setdefault(board, []).append(
                    segment["id"]
                )


# ### Actions


def haptics_on(statue: Statue) -> int:
    return publish_mqtt(HAPTIC_MQTT_TOPIC, {"statue": statue})


def leds_active(statue: Statue):
    send_led_cmd(
        statue,
        {
            "on": True,
            "bri": 255,
            "col": COLORS.get(statue, {}).get(
                "active", COLORS[Statue.DEFAULT]["active"]
            ),
            "fx": EFFECTS.get(statue, {}).get(
                "active", EFFECTS[Statue.DEFAULT]["active"]
            ),
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
            "col": COLORS.get(statue, {}).get(
                "dormant", COLORS[Statue.DEFAULT]["dormant"]
            ),
            "fx": EFFECTS.get(statue, {}).get(
                "dormant", EFFECTS[Statue.DEFAULT]["dormant"]
            ),
            "pal": PALETTE_ID,
        },
    )


def audio_active(statue: Statue) -> bool:
    """Enable audio playback for a statue."""
    input_channel = device_map.get(statue, {}).get("input", -1)
    if input_channel < 0:
        print(f"Error: No audio input configured for statue {statue}")
        return False

    return music_playback.set_music_channel(input_channel, True)


def audio_dormant(statue: Statue):
    """Disable audio playback for a statue."""
    input_channel = device_map.get(statue, {}).get("input", -1)
    if input_channel < 0:
        print(f"Error: No audio input configured for statue {statue}")
        return False

    return music_playback.set_music_channel(input_channel, False)


def handle_contact_event(payload: dict):
    """Handle a contact event from a statue."""
    new_actives, new_dormants = update_active_statues(payload)
    # active statues
    if debug:
        print(f"Activating the following statues: {new_actives}")
    for statue in new_actives:
        haptics_on(statue)
        leds_active(statue)
        leds_active(Statue.ARCHES)
    for statue in new_actives:
        audio_active(statue)

    # dormant statues
    if debug:
        print(f"Deactivating the following statues: {new_dormants}")
    for statue in new_dormants:
        leds_dormant(statue)
        leds_dormant(Statue.ARCHES)
    for statue in new_dormants:
        audio_dormant(statue)


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
                    "mqtt_num_connected": mqtt_num_connected,
                }
            )
        elif self.path == "/config/static":
            self._send_response(
                {
                    "colors": COLORS,
                    "effects": EFFECTS,
                    "board_config": board_config,
                    "teensy_config": teensy_config,
                    "segment_map": segment_map,
                    "device_map": device_map,
                }
            )
        elif self.path == "/config/dynamic":
            self._send_response(
                {
                    "debug": debug,
                    "active_song": ACTIVE_SONG,
                    "linked_statues": linked_statues,
                    "active_statues": list(active_statues),
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
        elif self.path.startswith("/led/"):
            statue = get_statue(self.path)
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


# ### MQTT client


# The callback for when the client receives a CONNACK response from the server.
def on_connect(mqttc, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mqttc.subscribe(LINK_MQTT_TOPIC)
    mqttc.subscribe(CONFIG_REQ_MQTT_TOPIC)
    mqttc.subscribe(STATUS_TOPIC)


# The callback for when a PUBLISH message is received from the server.
def on_message(mqttc, userdata, msg):
    """Handle incoming MQTT messages."""
    if debug:
        print(f"Received message on topic {msg.topic}: {msg.payload}")

    if msg.topic == CONFIG_REQ_MQTT_TOPIC:
        send_config()

    if msg.topic == LINK_MQTT_TOPIC:
        try:
            payload = json.loads(msg.payload)
            handle_contact_event(payload)
        except Exception as e:
            print(e)

    if msg.topic == STATUS_TOPIC:
        global mqtt_num_connected
        mqtt_num_connected = int(msg.payload)


if __name__ == "__main__":
    # Set DEBUG=1 to enable verbose logging
    debug = bool_env_var("DEBUG")
    # Set TEST_MODE_NO_LEDS=1 to disable all LED/WLED functionality
    no_leds = bool_env_var("TEST_MODE_NO_LEDS")

    extract_addresses()
    load_audio()
    load_audio_devices()
    initialize_playback()

    # Should be in the global scope, mqttc is a global variable
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_BROKER, MQTT_PORT)

    print("Starting MQTT client")
    mqttc.loop_start()

    # Give some time for other clients to connect
    time.sleep(STARTUP_DELAY)

    initialize_leds()
    for statue in segment_map.keys():
        leds_dormant(statue)
    send_config()

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

        mqttc.loop_stop()
        print("Disconnected from MQTT broker")
