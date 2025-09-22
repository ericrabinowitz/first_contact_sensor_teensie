#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "backports.strenum", "gpiozero", "numpy", "paho-mqtt", "requests",
#   "sounddevice", "soundfile", "ultraimport", "lgpio"
# ]
# ///
"""
Controller for the Missing Link art installation. Receives contact events from
each statue's Teensy and configures their signal frequencies. In response to
events, it plays audio channels and controls the WLED lights.

Install:
wget -qO- https://astral.sh/uv/install.sh | sh

Execute: ./controller.py
"""

import datetime
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Set, Union

import paho.mqtt.client as mqtt
import requests
from gpiozero import OutputDevice
import soundfile as sf
import ultraimport as ui

Statue, Board, Effect = ui.ultraimport(
    "__dir__/../config/constants.py", ["Statue", "Board", "Effect"]
)
ToggleableMultiChannelPlayback = ui.ultraimport(
    "__dir__/../audio/music.py", "ToggleableMultiChannelPlayback"
)
configure_devices = ui.ultraimport("__dir__/../audio/devices.py", "configure_devices")


# ### Parameters

VERSION = "2.1"  # Version of the script
DEBUG_PORT = 8080  # Port for the debug server
STARTUP_DELAY = 5  # Delay to allow MQTT clients to connect, seconds

# Roughly match sunrise/sunset times in SF in August 2025
SUNRISE = datetime.time(7, 00)  # 7:00 AM
SUNSET = datetime.time(19, 00)  # 7:00 PM
POWER_CHECK_INTERVAL_SECS = 60

# Relay configuration
RELAY_GPIO_PIN = 17  # GPIO 17 (Pin 11) - Main relay
RELAY2_GPIO_PIN = 27  # GPIO 27 (Pin 13) - Timed relay
RELAY_ACTIVE_HIGH = False  # True = HIGH activates relay, False = LOW activates relay
RELAY2_MAX_DURATION = 3.0  # Maximum duration in seconds for relay 2

# Folder for audio files
SONG_DIR = os.path.join(os.path.dirname(__file__), "../../audio_files")
ACTIVE_SONGS = [
    "Missing Link Playa 1 - 6 channel.wav",
    "Missing Link Playa 2 - 6 Channel.wav",
    "Missing Link Playa 3 - 6 Channel.wav",
    #    "Missing Link Playa 1 - 6 Channel 6-7.wav",
    #    "Missing Link Playa 3 - Five Channel.wav",
]
DORMANT_SONG = "Missing Link Playa Dormant - 5 channel deux.wav"
DORMANT_TIMEOUT_SECONDS = 10  # Time in dormant before advancing to next song
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
# For unix socket grant permission to file
# MQTT_BROKER = "/tmp/mosquitto.sock"  # unix socket of the MQTT broker
# MQTT_PORT = 0  # MQTT port, not used with unix socket
MQTT_BROKER = "127.0.0.1"  # IP address of the MQTT broker
MQTT_PORT = 1883  # Default MQTT port
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None
MQTT_QOS = 0  # Quality of Service
# 0 (at most once, fastest)
# 1 (at least once, expects ack)
# 2 (exactly once, 4 step handshake, reliable)

# WLED settings
# TODO: test different palettes, like the default one
PALETTE_ID = 3

# TODO: pick colors
COLORS = {
    Statue.EROS: [[255, 0, 100], [225, 0, 255], [255, 0, 100]],  # red
    Statue.ELEKTRA: [[0, 25, 255], [0, 200, 255], [0, 25, 255]],  # blue
    Statue.ARIEL: [[255, 200, 0], [255, 255, 0], [255, 255, 0]],  # yellow
    Statue.SOPHIA: [[8, 255, 0], [66, 237, 160], [66, 237, 160]],  # green
    Statue.ULTIMO: [[255, 100, 0], [255, 199, 94], [255, 199, 94]],  # orange
    "dormant": [[255, 255, 255], [0, 0, 0], [0, 0, 0]],
}

BRIGHTNESS = {
    "active": 255,  # Max
    "dormant": 127,  # 1/2 max
}

EFFECTS = {
    "active": Effect.FIREWORKS,
    "dormant": Effect.NOISE,
    "arch": Effect.LIGHTHOUSE,
    "hand": Effect.SOLID,
}


# ### Global variables

# Enable debug logging
debug = True

# Disable all LED/WLED functionality
no_leds = False

# Global timer for power
power_timer_thread = None

# Global timer for relay 2 auto-off
relay2_timer_thread = None

# Relay device objects
relay1_device = None
relay2_device = None

# MQTT client
mqttc: Any = None

start_time = time.time()  # Track when the script started

# Derived from audio file
active_audio = {
    "data": None,  # Loaded active song data
    "sample_rate": 0,
}
dormant_audio = {
    "data": None,  # Loaded dormant song data
    "sample_rate": 0,
}
is_dormant = True  # Track whether we're playing dormant or active song
current_active_song_index = 0  # Track which active song to play
dormant_start_time = None  # Track when we entered dormant state

# Maps a statue to QuinLED boards to body parts to a segment id.
# The control pin to segment id mapping is done in the WLED app.
segment_map = {
    Statue.EROS: {},
    Statue.ELEKTRA: {},
    Statue.ARIEL: {},
    Statue.SOPHIA: {},
    Statue.ULTIMO: {},
    # Statue.EROS: {
    #     Board.FIVE_V_1: {
    #         "heart head": 0, # WLED segment id
    #         ...
    #     }
    # },
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

# List of configured audio devices
audio_devices: List[dict[str, Any]] = []

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
linked_statues: Dict[Statue, List[Statue]] = {  # pyright: ignore[reportInvalidTypeForm]
    Statue.EROS: [],
    Statue.ELEKTRA: [],
    Statue.ARIEL: [],
    Statue.SOPHIA: [],
    Statue.ULTIMO: [],
}
# Statues that are currently active
active_statues: Set[Statue] = set()  # pyright: ignore[reportInvalidTypeForm]

# Climax event tracking
climax_is_active: bool = False
active_links: Set[tuple[Statue, Statue]] = set()  # pyright: ignore[reportInvalidTypeForm]

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
        exit(1)

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


def load_audio_files():
    """Load both active and dormant audio files into memory."""
    global active_audio, dormant_audio

    # Load active song
    active_file = os.path.join(SONG_DIR, ACTIVE_SONGS[current_active_song_index])
    if not os.path.exists(active_file):
        print(f"Error: Active audio file not found: {active_file}")
        exit(1)

    # Load dormant song
    dormant_file = os.path.join(SONG_DIR, DORMANT_SONG)
    if not os.path.exists(dormant_file):
        print(f"Error: Dormant audio file not found: {dormant_file}")
        exit(1)

    try:
        # Load active song
        audio_data, sample_rate = sf.read(active_file)
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        active_audio["data"] = audio_data
        active_audio["sample_rate"] = int(sample_rate)

        # Load dormant song
        dormant_data, dormant_rate = sf.read(dormant_file)
        if dormant_data.ndim == 1:
            dormant_data = dormant_data.reshape(-1, 1)

        dormant_audio["data"] = dormant_data
        dormant_audio["sample_rate"] = int(dormant_rate)

        if debug:
            print(f"\nLoaded active: {os.path.basename(active_file)}")
            print(
                f"  Duration: {len(audio_data) / sample_rate:.1f}s, Channels: {audio_data.shape[1]}"
            )
            print(f"Loaded dormant: {os.path.basename(dormant_file)}")
            print(
                f"  Duration: {len(dormant_data) / dormant_rate:.1f}s, Channels: {dormant_data.shape[1]}"  # noqa: E501
            )

    except Exception as e:
        print(f"Error: Failed to load audio files: {e}")
        exit(1)


def load_audio_devices():
    """Query audio devices and map them to statues using devices.py."""
    global audio_devices

    # Use the devices.py configuration which handles HiFiBerry
    audio_devices = configure_devices(debug=debug)  # max_devices=X for testing
    audio_devices.sort(key=lambda d: d["channel_index"])
    if debug:
        print(f"Audio devices: {json.dumps(audio_devices, indent=2)}")
    if len(audio_devices) == 0:
        exit(1)


def initialize_playback():
    """Initialize the music playback object."""
    global music_playback, is_dormant

    print(f"Initializing playback with {len(audio_devices)} channels")
    # Start with dormant song since no connections at startup
    is_dormant = True
    music_playback = ToggleableMultiChannelPlayback(
        dormant_audio["data"],  # Start with dormant song
        dormant_audio["sample_rate"],
        audio_devices,
        loop=True,
        debug=debug,
    )
    music_playback.start()

    # Enable all channels for dormant mode
    music_playback.enable_all_music_channels()

    # Disable climax channel (5) since climax is not active at startup
    if len(audio_devices) > 5:
        music_playback.set_music_channel(5, False)
        if debug:
            print("Disabled climax channel 5 at startup")

    if debug:
        print("Playback initialized with dormant song on all channels")


def get_statue(
    path: str,
) -> Union[Statue, None]:  # pyright: ignore[reportInvalidTypeForm]
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


def update_active_statues(
    payload: dict,
) -> tuple[Set[Statue], Set[Statue], bool]:  # pyright: ignore[reportInvalidTypeForm]
    """Update the list of active statues based on the received payload.
    Returns a tuple of new active and dormant statues, and whether the playback state changed.
    """
    global active_statues, linked_statues

    statue_name = payload.get("detector", "")
    try:
        detector = Statue(statue_name)
    except ValueError:
        print(f"Error: Unknown statue: {statue_name}")
        return set(), set(), False

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

    # Song switching logic
    was_dormant = len(old_actives) == 0
    now_dormant = len(active_statues) == 0

    new_actives = active_statues - old_actives
    new_dormants = old_actives - active_statues
    return new_actives, new_dormants, was_dormant != now_dormant


def update_active_links() -> tuple[bool, bool, Set[tuple[Statue, Statue]]]:  # pyright: ignore[reportInvalidTypeForm]
    """Update the active links between neighboring statues and detect climax events.

    Returns:
        climax_started: True if climax just began
        climax_stopped: True if climax just ended
        active_links: Set of currently connected neighbor pairs (normalized tuples)
    """
    global climax_is_active, active_links

    # Get all statues in enum order
    all_statues = list(Statue)
    num_statues = len(all_statues)

    # Define neighbor pairs (with wraparound)
    neighbor_pairs = []
    for i in range(num_statues):
        current = all_statues[i]
        next_statue = all_statues[(i + 1) % num_statues]
        neighbor_pairs.append((current, next_statue))

    # Check which neighbor pairs have active links (bidirectional)
    new_active_links = set()
    for statue1, statue2 in neighbor_pairs:
        # Check if either statue detects the other
        has_link = False

        # Check if statue1 detects statue2
        if statue2 in linked_statues.get(statue1, []):
            has_link = True

        # Check if statue2 detects statue1
        if statue1 in linked_statues.get(statue2, []):
            has_link = True

        if has_link:
            # Normalize the tuple (smaller statue first) to avoid duplicates
            if statue1.value < statue2.value:
                new_active_links.add((statue1, statue2))
            else:
                new_active_links.add((statue2, statue1))

    # Determine if climax is active (all 5 neighbor pairs connected)
    new_climax_active = len(new_active_links) == num_statues

    # Detect state transitions
    climax_started = new_climax_active and not climax_is_active
    climax_stopped = not new_climax_active and climax_is_active

    # Update global state
    climax_is_active = new_climax_active
    active_links = new_active_links

    # Print state changes
    if climax_started:
        print("Climax happening!")
    elif climax_stopped:
        print("Climax has stopped.")

    return climax_started, climax_stopped, new_active_links


def get_channel(statue: Statue) -> int:  # pyright: ignore[reportInvalidTypeForm]
    """Get the audio channel index for a statue."""
    for device in audio_devices:
        if device["statue"] == statue:
            return device["channel_index"]
    return -1


def publish_mqtt(topic: str, payload: dict):
    """Publish a message to the MQTT broker."""
    if debug:
        print(f"Publishing to {topic}: {json.dumps(payload)}")
    mqttc.publish(topic, json.dumps(payload), qos=MQTT_QOS)


def send_config():
    """Send the Teensy configuration via MQTT."""
    publish_mqtt(CONFIG_RESP_MQTT_TOPIC, teensy_config)


def set_debug(enable: bool):
    """Enable or disable debug mode."""
    global debug
    debug = enable


def initialize_gpio():
    """Initialize GPIO for relay control."""
    global relay1_device, relay2_device
    try:
        # active_high=False because it's low-level trigger
        # initial_value=False means relay starts OFF
        relay1_device = OutputDevice(RELAY_GPIO_PIN, active_high=not RELAY_ACTIVE_HIGH, initial_value=False)
        relay2_device = OutputDevice(RELAY2_GPIO_PIN, active_high=not RELAY_ACTIVE_HIGH, initial_value=False)
        print(f"GPIO initialized: Relay 1 on pin {RELAY_GPIO_PIN} is OFF")
        print(f"GPIO initialized: Relay 2 on pin {RELAY2_GPIO_PIN} is OFF")
    except Exception as e:
        print(f"ERROR: Failed to initialize GPIO: {e}")
        print("Relay control will be disabled")


def control_relay_1(activate: bool):
    """Control the main relay state."""
    global relay1_device
    if not relay1_device:
        print("WARNING: Relay 1 not initialized")
        return
    try:
        if activate:
            relay1_device.on()  # Sends appropriate signal based on active_high setting
            print(f"Relay 1 on pin {RELAY_GPIO_PIN} is ON")
        else:
            relay1_device.off()
            print(f"Relay 1 on pin {RELAY_GPIO_PIN} is OFF")
    except Exception as e:
        print(f"ERROR: Failed to control relay 1: {e}")


def control_relay_2(activate: bool):
    """Control the timed relay state."""
    global relay2_device
    if not relay2_device:
        print("WARNING: Relay 2 not initialized")
        return
    try:
        if activate:
            relay2_device.on()  # Sends appropriate signal based on active_high setting
            print(f"Relay 2 on pin {RELAY2_GPIO_PIN} is ON")
        else:
            relay2_device.off()
            print(f"Relay 2 on pin {RELAY2_GPIO_PIN} is OFF")
    except Exception as e:
        print(f"ERROR: Failed to control relay 2: {e}")


def relay2_timeout():
    """Callback to turn off relay 2 after timeout."""
    global relay2_timer_thread
    print(f"Relay 2 timeout reached ({RELAY2_MAX_DURATION} seconds)")
    control_relay_2(False)
    relay2_timer_thread = None


def control_relay(activate: bool):
    """Control both relays for climax events."""
    global relay2_timer_thread

    if activate:
        # Turn on both relays
        control_relay_1(True)
        control_relay_2(True)

        # Start timer for relay 2
        if relay2_timer_thread:
            relay2_timer_thread.cancel()
        relay2_timer_thread = threading.Timer(RELAY2_MAX_DURATION, relay2_timeout)
        relay2_timer_thread.start()
        print(f"Started {RELAY2_MAX_DURATION}s timer for relay 2")
    else:
        # Turn off both relays
        control_relay_1(False)
        control_relay_2(False)

        # Cancel timer if it's still running
        if relay2_timer_thread:
            relay2_timer_thread.cancel()
            relay2_timer_thread = None
            print("Cancelled relay 2 timer")


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
        preset = payload.copy()
        preset_file = os.path.join(
            os.path.dirname(__file__), "../../quinled", f"{board}_preset.json"
        )
        if not os.path.exists(preset_file):
            print(f"Error: Preset file not found for board {board}: {preset_file}")
            exit(1)
        with open(preset_file, "r") as f:
            preset = json.load(f)
            preset["v"] = True

        resp = requests.post(
            "http://{}/json/state".format(board_config[board]["ip_address"]),
            json=preset,
        )
        if resp.status_code != 200:
            print(f"Error: Failed to initialize board {board}: {resp.text}")
            exit(1)

        # Delay to help propagate?
        time.sleep(1)
        # Activate preset 1 to ensure it's properly set
        resp_preset = requests.post(
            "http://{}/json/state".format(board_config[board]["ip_address"]),
            json={"ps": 1},
        )
        if resp_preset.status_code != 200:
            print(f"Warning: Failed to activate preset 1 for board {board}: {resp_preset.text}")
        else:
            print(f"Activated preset 1 for board {board}")

        segments = resp.json().get("seg", [])
        for segment in segments:
            # "n" field only exists if the segment has been renamed
            name = segment.get("n", "").strip().lower()
            parts = name.split(" ")
            if len(parts) < 1:
                continue
            if parts[0] in statues:
                rest = " ".join(parts[1:]).strip()
                if rest == "":
                    rest = "default"
                segment_map[Statue(parts[0])].setdefault(board, {})[rest] = segment[
                    "id"
                ]


def manage_power():
    """Manage power consumption by turning off LEDs during the day."""
    global no_leds
    global power_timer_thread
    if debug:
        print("Checking power management...")

    now = datetime.datetime.now().time()
    is_daytime = SUNRISE <= now <= SUNSET
    if is_daytime and not no_leds:
        print("Daytime detected - turning off LEDs")
        no_leds = True
        publish_mqtt(
            WLED_MQTT_TOPIC.format("all"),
            {
                "tt": 0,
                "on": False,
                "bri": 0,
            },
        )
    elif not is_daytime and no_leds:
        print("Nighttime detected - turning on LEDs")
        no_leds = False
        publish_mqtt(
            WLED_MQTT_TOPIC.format("all"),
            {
                "tt": 0,
                "on": True,
                "bri": 0,
            },
        )
        leds_dormant(set(segment_map.keys()))

    # Restart the timer thread.
    power_timer_thread = threading.Timer(POWER_CHECK_INTERVAL_SECS, manage_power)
    power_timer_thread.start()


# ### Actions


def leds_active(statues: Set[Statue]):  # pyright: ignore[reportInvalidTypeForm]
    if no_leds:
        return
    if debug:
        print(f"Activating LEDs for statues: {statues}")

    board_payloads = {}
    for board in board_config.keys():
        board_payloads[board] = {
            "tt": 0,
            "on": True,
            "seg": [],
        }

    for statue in statues:
        color = COLORS.get(statue, COLORS["dormant"])
        for board, seg_map in segment_map[statue].items():
            for part, seg_id in seg_map.items():
                board_payloads[board]["seg"].append(
                    {
                        "id": seg_id,
                        "bri": BRIGHTNESS["active"],
                        "col": color,
                        "fx": EFFECTS["active"],
                        "pal": PALETTE_ID,
                    }
                )

    for board, payload in board_payloads.items():
        if len(payload["seg"]) == 0:
            continue
        # thread = threading.Thread(
        #     target=publish_mqtt, args=(WLED_MQTT_TOPIC.format(board), payload)
        # )
        # thread.start()
        publish_mqtt(WLED_MQTT_TOPIC.format(board), payload)


def leds_dormant(statues: Set[Statue]):  # pyright: ignore[reportInvalidTypeForm]
    if no_leds:
        print("No leds: skipping dormant")
        return
    if debug:
        print(f"Deactivating LEDs for statues: {statues}")

    board_payloads = {}
    for board in board_config.keys():
        board_payloads[board] = {
            "tt": 0,
            "on": True,
            "seg": [],
        }

    for statue in statues:
        for board, seg_map in segment_map[statue].items():
            for part, seg_id in seg_map.items():
                fx = EFFECTS["dormant"]
                color = COLORS["dormant"]
                bri = BRIGHTNESS["dormant"]
                if "hand" in part:
                    color = COLORS.get(statue, COLORS["dormant"])
                    bri = BRIGHTNESS["active"]
                    fx = EFFECTS["hand"]
                #if "arch" in part:
                #    fx = EFFECTS["arch"]

                board_payloads[board]["seg"].append(
                    {
                        "id": seg_id,
                        "bri": bri,
                        "col": color,
                        "fx": fx,
                        "pal": PALETTE_ID,
                    }
                )

    for board, payload in board_payloads.items():
        if len(payload["seg"]) == 0:
            continue
        # thread = threading.Thread(
        #     target=publish_mqtt, args=(WLED_MQTT_TOPIC.format(board), payload)
        # )
        # thread.start()
        publish_mqtt(WLED_MQTT_TOPIC.format(board), payload)


def change_playback_state():
    global is_dormant, dormant_start_time, current_active_song_index

    if len(active_statues) == 0:
        # Transition to dormant: all statues disconnected
        if debug:
            print("All statues dormant - switching to dormant song")

        music_playback.switch_to_song(dormant_audio["data"], enable_all=True)
        is_dormant = True
        dormant_start_time = time.time()  # Record when we entered dormant state

    else:
        # Transition to active: first connection made
        # Check if we should advance to next song
        if dormant_start_time and (
            time.time() - dormant_start_time >= DORMANT_TIMEOUT_SECONDS
        ):
            # Advance to next song
            current_active_song_index = (current_active_song_index + 1) % len(
                ACTIVE_SONGS
            )
            if debug:
                print(
                    f"Advancing to next active song: {ACTIVE_SONGS[current_active_song_index]}"
                )
            # Reload the new active song
            load_audio_files()

        if debug:
            print(
                f"Connection detected - switching to active song: {ACTIVE_SONGS[current_active_song_index]}"  # noqa: E501
            )
        music_playback.switch_to_song(active_audio["data"], enable_all=False)
        is_dormant = False
        dormant_start_time = None  # Reset timer


def audio_active(statue: Statue) -> bool:  # pyright: ignore[reportInvalidTypeForm]
    """Enable audio playback for a statue."""
    # In dormant mode, all channels are already enabled
    if is_dormant:
        return True

    input_channel = get_channel(statue)
    if input_channel < 0:
        print(f"Error: No audio input configured for statue {statue}")
        return False

    return music_playback.set_music_channel(input_channel, True)


def audio_dormant(statue: Statue):  # pyright: ignore[reportInvalidTypeForm]
    """Disable audio playback for a statue."""
    # In dormant mode, all channels stay enabled
    if is_dormant:
        return True

    input_channel = get_channel(statue)
    if input_channel < 0:
        print(f"Error: No audio input configured for statue {statue}")
        return False

    return music_playback.set_music_channel(input_channel, False)


def handle_contact_event(payload: dict):
    """Handle a contact event from a statue."""
    new_actives, new_dormants, transitioned = update_active_statues(payload)

    # Check for climax events
    climax_started, climax_stopped, current_active_links = update_active_links()

    if transitioned:
        change_playback_state()

    # active statues
    if debug:
        print(f"Activating the following statues: {new_actives}")
    for statue in new_actives:
        audio_active(statue)
    leds_active(new_actives)

    # dormant statues
    if debug:
        print(f"Deactivating the following statues: {new_dormants}")
    for statue in new_dormants:
        audio_dormant(statue)
    leds_dormant(new_dormants)

    # Handle climax-specific effects
    if climax_started:
        control_relay(activate=True)
        # Enable climax audio on channel 5
        if music_playback:
            music_playback.set_music_channel(5, True)
            if debug:
                print("Enabled climax audio on channel 5")
        # Future: publish_mqtt("missing_link/climax", {"state": "active", "links": list(current_active_links)})
    elif climax_stopped:
        control_relay(activate=False)
        # Disable climax audio on channel 5
        if music_playback:
            music_playback.set_music_channel(5, False)
            if debug:
                print("Disabled climax audio on channel 5")
        # Future: publish_mqtt("missing_link/climax", {"state": "inactive"})


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
                    "uptime_sec": round(time.time() - start_time),
                }
            )
        elif self.path == "/config/static":
            self._send_response(
                {
                    "board_config": board_config,
                    "teensy_config": teensy_config,
                    "segment_map": segment_map,
                    "audio_devices": audio_devices,
                }
            )
        elif self.path == "/config/dynamic":
            self._send_response(
                {
                    "debug": debug,
                    "active_song": ACTIVE_SONGS[current_active_song_index],
                    "dormant_time": (
                        time.time() - dormant_start_time if dormant_start_time else 0
                    ),
                    "linked_statues": linked_statues,
                    "active_statues": list(active_statues),
                    "climax_is_active": climax_is_active,
                    "active_links": [list(link) for link in active_links],
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
            publish_mqtt(LINK_MQTT_TOPIC, data)
            self._send_response({})
            print("triggered a contact event")
        else:
            self._send_404()


# ### MQTT client


def connect_to_mqtt():
    """Connect to the MQTT broker and set up callbacks."""
    global mqttc

    # Should be in the global scope, mqttc is a global variable
    if MQTT_PORT == 0:
        mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTProtocolVersion.MQTTv311,
            clean_session=False,
            client_id="controller",
            transport="unix",
        )
    else:
        mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTProtocolVersion.MQTTv311,
            clean_session=False,
            client_id="controller",
        )
    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    if MQTT_PORT == 0:
        mqttc.connect(MQTT_BROKER)
    else:
        mqttc.connect(MQTT_BROKER, MQTT_PORT)

    print("Starting MQTT client")
    mqttc.loop_start()


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
    load_audio_files()
    load_audio_devices()
    initialize_playback()
    initialize_gpio()  # Initialize GPIO for relay control

    connect_to_mqtt()

    # Give some time for other clients to connect
    time.sleep(STARTUP_DELAY)

    # Initialize Teensy config and WLED segments
    initialize_leds()
    send_config()

    # Start in the dormant state
    leds_dormant(set(segment_map.keys()))
    for d in audio_devices:
        audio_dormant(d["statue"])
    time.sleep(1)
    leds_dormant(set(segment_map.keys()))

    if bool_env_var("CONSERVE_POWER") and not no_leds:
        print(f"CONSERVE_POWER is {bool_env_var('CONSERVE_POWER')}. Starting manage_power")
        now = datetime.datetime.now().time()
        print(f"Lights turn on at {SUNSET} and off at {SUNRISE}. It is now {now}")
        # Run power management once a minute
        power_timer_thread = threading.Timer(10, manage_power)
        power_timer_thread.start()
    else:
        print(f"CONSERVE_POWER is {bool_env_var('CONSERVE_POWER')}. No power management.")

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

        music_playback.stop()

        mqttc.loop_stop()
        print("Disconnected from MQTT broker")

        if power_timer_thread is not None:
            power_timer_thread.cancel()
            print("Timer thread stopped")

        # Cleanup relays and GPIO
        try:
            # Cancel relay 2 timer if active
            if relay2_timer_thread:
                relay2_timer_thread.cancel()
                print("Cancelled relay 2 timer")

            # Turn off both relays
            control_relay(False)  # This turns off both relays and cancels timer

            # Close GPIO devices
            if relay1_device:
                relay1_device.close()
                print("Relay 1 device closed")
            if relay2_device:
                relay2_device.close()
                print("Relay 2 device closed")
        except Exception as e:
            print(f"GPIO cleanup error: {e}")
