/*

2/1/2025
FIRST CONTACT ART PROJECT 
Contact Sensor and Music Player - Eric Linn Rabinowitz. 415-336-6938

This code is the contact sensor + Music Player that runs in each sculpture.

Details:
========
  Human Contact Sensing
  The contact sensing is performed by sending a sine wave through the line out pin(s)
  of the Audio Shield DAC to the sculpture hands.
  The receiving side listens for the sinewave tone.
  The sinewave generation, tone detection and DAC drivers are part of the PJRC audio library.

Audio Player:
-------------
  Audio wave files are stored in a MicroSd card on the Teensy board with a DOS-format.
  There is another MicroSd slot on the Audio but it is not used.

  Audio is played using using thr PJRC audio library

Audio Mixing:
-------------
  Both the sensing and audio player share the PJRC audio library and send their outputs through the same
  DAC (Digital to Analog Converter).   Mixing of the signals is performed with the PJRC Audio Library.

Networking
-----------
  A  CAT-5 network interface is connected to an external, on-board ethernet chip via a SPI in interface.
  A full TCP/UDP-IP stack is utilized using the QNEthernet library
  The network address is obtained using DHCP from the Rasspberry PI.
  DNS is used for all network devices.
  We employed MQTT (aka 'Mosquito') for messaging.
  This software acts as both a MQTT publisher and subscriber for events.
  The MQTT Broker (databasde server) is running on a Raspberry PI on the network.

Hardware:  
---------
          Teensy 4.1 + Teensy Audio Shield (DAC)
          Ethernet adapter and cable
          SSD1307 OledDisplay


Software Requirements:
======================
          Arduino IDE 2.3.4

Boards Support:
          Teensy (for Arduino IDE 2.0.4 or later). v.1.59.0
            Instructions to install: https://www.pjrc.com/teensy/td_download.html 
            Installer For IDE: https://www.pjrc.com/teensy/package_teensy_index.json
            NOTE: I think this also installs the Audio library
Libraries:
        - These need to be installed via library manager:
          Using library Adafruit GFX Library at version 1.12.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_GFX_Library
          Using library Adafruit BusIO at version 1.17.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_BusIO
          Using library Adafruit SSD1306 at version 2.5.13 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_SSD1306
          Using library QNEthernet at version 0.31.0 in folder: /Users/eric/work/FirstContact/libraries/QNEthernet
          Using library PubSubClient at version 2.8 in folder: /Users/eric/work/FirstContact/libraries/PubSubClient
        - These should already be installed alongsuide teensyduino. Do not install these libraries:
          Using library SPI at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SPI 
          Using library Wire at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Wire 
          Using library Audio at version 1.3 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Audio 
          Using library SD at version 2.0.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SD 
          Using library SdFat at version 2.1.2 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SdFat 
          Using library SerialFlash at version 0.5 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SerialFlash 
*/

#include "AudioSense.h"
#include "Display.h"
#include "Networking.h"

void setup() {
  // Display Setup
  displaySetup();

  Serial.printf("_______FIRST CONTACT_______ ");
  Serial.printf("%s %sd \n", __DATE__, __TIME__);

  // TCP/IP Setup
  Serial.printf("_______Init Ethernet_______\n");
  initEthernet();

  // MQTT Setup
  Serial.printf("_______Init MQTT Publisher_______\n");
  initMqtt();

  // Allow the hardware to sort itself out
  // delay(1500); XXX

  // Audio Sense Setup
  Serial.printf("_______Audio Memory/Sense Init________\n");
  audioSenseSetup();

  // Audio Music Setup
  Serial.printf("_______Audio Music Init________\n");
  audioMusicSetup();
}

bool audioSenseLoop() {
  // Use helper to determine the buffered isLinked state.
  bool isLinked = getStableIsLinked();

  // Propagate the stable state downstream.
  static bool isInitialized = false;
  static bool wasLinked = false;
  publishState(isInitialized, wasLinked, isLinked);
  playMusic(isInitialized, wasLinked, isLinked);
  printState(isInitialized, wasLinked, isLinked);
  displayState(isInitialized, wasLinked, isLinked);

  isInitialized = true;
  wasLinked = isLinked;
  return isLinked;
}

void loop() {
  // Make sure we're connected to MQTT broker.
  mqttLoop();

  // Sense contact and update the state.
  bool isLinked = audioSenseLoop();

  // During Idle Time, animate something to show we are alive.
  displayActivityStatus(isLinked);

  displayTimeCount();
}
