#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["httpx", "paho-mqtt"]
# ///

# Installation
# wget -qO- https://astral.sh/uv/install.sh | sh

# Led strings:
# arch
# heart, head, snake (optional)
# hand - always on?

from enum import Enum
import json
import math
import os
import threading

import httpx
import paho.mqtt.client as mqtt
from http.server import BaseHTTPRequestHandler, HTTPServer

### Reference docs
# https://docs.google.com/document/d/107ZdOsc81E29lZZVTtqirHpqJKrvnqui0-EGSTGGslk/edit?tab=t.0
# https://docs.google.com/document/d/1Ke_J2RJw4KxdZ-_T9ig0PT2Xt90lASSOVepb4xZkUKM/edit?tab=t.0

### Parameters
# TODO: replace with real values

DEBUG = True
DEBUG_PORT = 8080  # Port for the debug server
WLED_URL = "192.168.4.100"
TEENSY_URL = "192.168.4.101"
FADE_MS = 2000  # Fade time in milliseconds
COOL_DOWN_MS = 2000  # Audio recent song wait time in milliseconds

# MQTT server settings
MQTT_BROKER = "127.0.0.1"  # IP address of your MQTT broker
MQTT_PORT = 1883  # Default MQTT port
# Topic that the Teensy will send and receive msgs on
MQTT_TOPIC = "missing_link/control"
MQTT_USER = None  # If using authentication, otherwise set as None
MQTT_PASSWORD = None  # If using authentication, otherwise set as None


class Mode(Enum):
    BASIC_NO_FADE = 1
    BASIC_FADE = 2
    RECENT_CONN = 3


class Effect(Enum):
    SOLID = 1
    BLINK = 2
    BREATHE = 3
    WIPE = 4
    SCAN = 5
    TWINKLE = 6
    CHASE = 7


currentMode = Mode.BASIC_NO_FADE

# TODO: eventually change to rotate through songs
# TODO: play music when inactive
currentSong = "Missing Link unSCruz active 1 Remi Wolf Polo Pan Hello.wav"

# Initialize on startup
effectToId = {}

hapticMotor = {
    "id": 0,
    "ledStart": 0,
    "ledEnd": 1,
    "brightnessPerc": 0.5,
}

# TODO: determine how to set the color of the LEDs (or use palettes)
leds = {
    "body": {
        "id": 1,
        "ledStart": 1,
        "ledEnd": 20,
        "brightnessPerc": 0.7,
        "effect": Effect.SOLID,
    },
    "arch": {
        "id": 2,
        "ledStart": 21,
        "ledEnd": 60,
        "brightnessPerc": 0.7,
        "effect": Effect.SOLID,
    },
    "hand": {
        "id": 3,
        "ledStart": 61,
        "ledEnd": 80,
        "brightnessPerc": 0.7,
        "effect": Effect.SOLID,
    },
}


### Helper functions


def publishMqtt(client, payload):
    r = client.publish(MQTT_TOPIC, json.dumps(payload))
    try:
        r.wait_for_publish(1)
    except Exception as e:
        print(f"Failed to publish message: {e}")
    return r.rc


# Throw exception if wled device isn't running
def initializeWled():
    url = f"http://{WLED_URL}/json"
    r = httpx.get(url).raise_for_status()
    info = r.json()
    if DEBUG:
        print(info)

    effects = [e.lower() for e in info["effects"]]
    for effect in Effect:
        try:
            index = effects.index(effect.name.lower())
            effectToId[effect.value] = index
        except Exception as e:
            print(f"Effect {effect.name} not found in WLED effects list: {e}")
            effectToId[effect.value] = 0

    # TODO: repeat for palettes?


def postToWled(payload):
    url = f"http://{WLED_URL}/json"
    try:
        r = httpx.post(url, json=payload).raise_for_status()
    except Exception as e:
        print(e)
        return 400  # TODO: get real code
    if DEBUG:
        print(r.json())
    return r.status_code


def wledOff(segmentId):
    postToWled({
        "seg": [
            {
                "id": segmentId,
                "on": "f",
            }
        ]
    })


def wledFadeOff(segmentId):
    postToWled({
        "seg": [
            {
                "id": segmentId,
                "on": "f",
                "tt": FADE_MS / 100,  # transition time, in units of 100ms
            }
        ]
    })


### Actions


def hapticMotorOn():
    postToWled({
        "seg": [
            {
                "id": hapticMotor.id,
                "on": "t",
                "bri": math.round(255 * hapticMotor.brightnessPerc),
                "col": [[0, 0, 0, 255]],
            }
        ]
    })


def hapticMotorOff():
    wledOff(hapticMotor.id)


def ledsOn(name):
    # TODO: palettes?
    postToWled({
        "seg": [
            {
                "id": leds[name].id,
                "on": "t",
                "bri": math.round(255 * leds[name].brightnessPerc),
                "col": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
                "fx": effectToId[leds[name].effect.value],
            }
        ]
    })


def ledsOff(name):
    wledOff(leds[name].id)


def ledsFadeOn(name):
    postToWled({
        "seg": [
            {
                "id": leds[name].id,
                "on": "t",
                "bri": math.round(255 * leds[name].brightnessPerc),
                "col": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
                "fx": effectToId[leds[name].effect.value],
                "tt": FADE_MS / 100,  # transition time, in units of 100ms
            }
        ]
    })


def ledsFadeOff(name):
    wledFadeOff(leds[name].id)


def audioOn(client):
    publishMqtt(client, {
        "action": "play",
        "song": currentSong,
        "transitionMs": 0,
        "volume": 100,
    })


def audioOff(client):
    publishMqtt(client, {
        "action": "pause",
        "transitionMs": 0,
        "coolDownMs": 0,
    })


def audioFadeOn(client):
    publishMqtt(client, {
        "action": "play",
        "song": currentSong,
        "transitionMs": FADE_MS,
        "volume": 100,
    })


def audioFadeOff(client):
    publishMqtt(client, {
        "action": "pause",
        "transitionMs": FADE_MS,
        "coolDownMs": 0,
    })


def audioRecentOff(client):
    publishMqtt(client, {
        "action": "pause",
        "transitionMs": 0,
        "coolDownMs": COOL_DOWN_MS,
    })


### Debug server


class ControllerDebugHandler(BaseHTTPRequestHandler):
    def _send_response(self, payload):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(payload), "utf-8"))

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
        if self.path == "/":
            self._send_response({
                "description": "Missing Link rpi controller script",
                "current_mode": currentMode.value,
                "current_song": currentSong,
                "haptic_motor": hapticMotor,
                "leds": leds,
                "effectToId": effectToId,
            })
        else:
            self._send_404()

    def do_POST(self):
        global currentMode
        global currentSong
        global hapticMotor
        global leds

        dataStr = self.rfile.read(int(self.headers["Content-Length"]))
        data = json.loads(dataStr)

        if self.path == "/mode":
            try:
                currentMode = Mode(data["mode"])
                self._send_response({
                    "current_mode": currentMode.value,
                })
                print("current operating mode:", currentMode.name)
            except Exception as e:
                print(e)
                self._send_400()
        elif self.path == "/song":
            currentSong = data.get("song", currentSong)
            self._send_response({
                "current_mode": currentMode.value,
            })
            print("current contact song:", currentSong)
        elif self.path == "/effect":
            try:
                effect = Effect[data["effect"].upper()]
                led = data["led"]
                leds[led].effect = effect
                self._send_response({
                    "current_mode": currentMode.value,
                })
                print(f"current effect for {led}: {effect.name}")
            except Exception as e:
                print(e)
                self._send_400()
        elif self.path == "/touch":
            action = data.get("action", "start")
            code = publishMqtt({
                "type": "touch",
                "action": action,
            })
            self._send_response({
                "status_code": code,
            })
            print(f"triggered a touch {action} event")
        elif self.path == "/wled":
            code = postToWled(data)
            self._send_response({
                "status_code": code,
            })
            print("sent the following to WLED:", json.dumps(data))
        elif self.path == "/mqtt":
            code = publishMqtt(data)
            self._send_response({
                "status_code": code,
            })
            print("sent the following to MQTT:", json.dumps(data))
        else:
            self._send_404()


def start_debug_server():
    httpd = HTTPServer(("", DEBUG_PORT), ControllerDebugHandler)
    try:
        print(f"Starting debug server on port {DEBUG_PORT}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)


### MQTT client


# The callback for when the client receives a CONNACK response from the server.
def on_connect(mqttc, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mqttc.subscribe(MQTT_TOPIC)


# The callback for when a PUBLISH message is received from the server.
def on_message(mqttc, userdata, msg):
    if DEBUG:
        print(msg.topic+" "+str(msg.payload))
    payload = json.loads(msg.payload)
    run_controller(mqttc, payload)


def run_controller(mqttc, payload):
    if payload.get("type", "") != "touch":
        return

    action = payload.get("action", "")
    ledsOn("hand")
    if action == "start":
        hapticMotorOn()
        if currentMode == Mode.BASIC_NO_FADE:
            ledsOn("body")
            ledsOn("arch")
            audioOn(mqttc)
        elif currentMode == Mode.BASIC_FADE:
            ledsFadeOn("body")
            ledsFadeOn("arch")
            audioFadeOn(mqttc)
        elif currentMode == Mode.RECENT_CONN:
            ledsOn("body")
            ledsOn("arch")
            audioOn(mqttc)
    elif action == "stop":
        hapticMotorOff()
        if currentMode == Mode.BASIC_NO_FADE:
            ledsOff("body")
            ledsOff("arch")
            audioOff(mqttc)
        elif currentMode == Mode.BASIC_FADE:
            ledsFadeOff("body")
            ledsFadeOff("arch")
            audioFadeOff(mqttc)
        elif currentMode == Mode.RECENT_CONN:
            ledsOff("body")
            ledsOff("arch")
            audioRecentOff(mqttc)


if __name__ == "__main__":
    if "MODE" in os.environ:
        currentMode = Mode(int(os.environ["MODE"]))
    print("current operating mode:", currentMode.name)
    if "SONG" in os.environ:
        currentSong = os.environ["MODE"]
    print("current contact song:", currentSong)

    initializeWled()

    thread = threading.Thread(target=start_debug_server, args=(), daemon=True)
    thread.start()

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_BROKER, MQTT_PORT)

    try:
        mqttc.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    mqttc.disconnect()
