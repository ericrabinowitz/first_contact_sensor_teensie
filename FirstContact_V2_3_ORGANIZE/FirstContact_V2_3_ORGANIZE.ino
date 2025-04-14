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

//
// OLED DISPLAY
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <SPI.h>
#include <Wire.h>

#define DISPLAY_ENABLED 1
#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
// The pins for I2C are defined by the Wire-library.
#define OLED_RESET -1 // Reset pin # (or -1 if sharing Arduino reset pin)
//#define SCREEN_ADDRESS 0x3D ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
#define SCREEN_ADDRESS                                                         \
  0xBC // NOTE: This value is not documented well and totally confusing when looking at the pcb silkcreen
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire2, OLED_RESET);
// OLED DISPLAY
//

#include "AudioSense.h" // moved sensing and audio code
#include "Networking.h"

unsigned long int contactCount = 0; // Cumulative count of contacts

void displayTimeCount() {
  static bool isInitialized = false;

#define STRING_BUFFER_LEN 128
  char str[STRING_BUFFER_LEN];

  long unsigned int startTimeMills = 0;
  long unsigned int secondsLapse = 0;
  long unsigned int mills = 0;
  long unsigned int millsLapse = 0;

  unsigned int count;

  // Initialize buffer;

  for (count = 0; count < STRING_BUFFER_LEN; ++count)
    str[count] = 0;

  if (!isInitialized) {
    startTimeMills = millis();
    isInitialized = true;
    return;
  }

  mills = millis();

  millsLapse = mills - startTimeMills;

  // Only update every 1/4 second
  if (millsLapse % 100)
    return;

  secondsLapse = millsLapse / 1000;

  //display.clearDisplay();
  display.fillRect(0, 54, 128, 10, SSD1306_BLACK);
  //display.display();

  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setTextSize(1);
  display.setCursor(0, 55);
  sprintf(str, "%07u    %02u:%02u:%02u", contactCount, secondsLapse / 3600,
          (secondsLapse % 3600) / 60, (secondsLapse % 3600) % 60);

  display.printf(str);

  display.display();
}

/*
  displayState() - Print the contact state to OLED display
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void displayState(bool isInitialized, bool wasLinked, bool isLinked) {
  char str[128];

  if (isInitialized && wasLinked == isLinked) {
    return;
  }

  if (isLinked) {
    ++contactCount;

    // Clear the buffer
    //display.clearDisplay();
    display.fillRect(0, 30, 128, 10, SSD1306_BLACK);
    display.setTextSize(3);              // Normal 1:1 pixel scale
    display.setTextColor(SSD1306_WHITE); // Draw white text
    display.setCursor(0, 30);

    sprintf(str, "%07u", contactCount);
    display.printf(str);
    display.display();
  } else {
    //display.clearDisplay();
    display.fillRect(0, 30, 128, 25, SSD1306_BLACK);
    display.display();
  }
}

/*
  publishState() - Publish via MQTT if we are on(Connected) or off
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void publishState(bool isInitialized, bool wasLinked, bool isLinked) {
  static bool publishSucceeded = false;

  if (publishSucceeded && isInitialized && wasLinked == isLinked) {
    // No change in state to report.
    return;
  }

  if (isLinked)
    publishSucceeded = client.publish("wled/all/api", "{\"on\": true, \
        \"bri\": 255, \
        \"seg\": \
      [{\"col\": [255, 255, 0],   \"fx\": 36},  \
        {\"col\": [0, 255, 255],   \"fx\": 36},   \
        {\"col\": [128, 128, 255], \"fx\": 36}]   \
        }");
  else
    publishSucceeded = client.publish("wled/all/api", "{\"on\": true, \
        \"bri\": 255, \
        \"seg\":  \
      [{\"col\": [255, 0, 0], \"fx\": 42},    \
        {\"col\": [0, 255, 0], \"fx\": 42},    \
        {\"col\": [0, 0, 255], \"fx\": 42}]    \
        }"

#if 0
        "wled/all/api",
        "{\"on\": false, \"bri\": 255, \"seg\": [{\"col\": [255, 0, 0], \"fx\": 0}, {\"col\": [0, 255, 0], \"fx\": 00}, {\"col\": [0, 0, 255], \"fx\": 00}]}"
#endif
    );
}

void displayHostname(char *hostname) {
  display.setCursor(0, 20);
  display.print("name:");
  display.print(hostname);
  display.display();
}

/*
 * displayActivityStatus() - display a wandering eye and show any acitivy
 */
void displayActivityStatus(bool isLinked) {
  long unsigned mod;

#define ACTIVITY_BAR_FRACTIONS 32

  static bool isInitialized = false;

  unsigned long int mills;
  static unsigned long time;
  static unsigned long deltaTime = 0;
  static bool direction = true;

  unsigned int Xposition;
  static unsigned int Xposition_last = 0;

  // Only display during idle time
  if (isLinked) {
    isInitialized = false;
    return;
  }

  if (!isInitialized) {
    time = millis();
    isInitialized = true;
  }

  mills = millis();

  // Handle wrap-around
  if (time > mills)
    time = mills;

  deltaTime = (mills - time) % 1000;

  mod = deltaTime % (1000 / ACTIVITY_BAR_FRACTIONS);
  if (mod != 0)
    return;

  unsigned int x_unscaled;
  unsigned int x_scaled;

  x_unscaled = deltaTime / ACTIVITY_BAR_FRACTIONS;
  x_scaled = x_unscaled * 128 / ACTIVITY_BAR_FRACTIONS;

  if (direction) {
    Xposition = x_scaled;
  } else {
    Xposition = 124 - x_scaled;
  }

#ifdef ACTIVITY_DEBUG_ENABLE
  printf("Direction:%s time:%u delta_t:%u x_unscaled:%u Xpos:%u\n",
         direction ? "F" : "B", time, deltaTime, x_unscaled, Xposition);
#endif
  /* 
    Clear the  previous activity block 
  */
  display.setTextColor(SSD1306_WHITE);

  display.fillRect(Xposition_last, 30, 10, 10, SSD1306_BLACK);

  /*
    Draw a small box on the line position it based on the fraction of a second
  */

  display.fillRect(Xposition, 30, 10, 10, SSD1306_WHITE); // New Block
  display.display();

  /* Flip the direction */
  if (x_unscaled == (ACTIVITY_BAR_FRACTIONS - 1)) {
    direction = direction ? false : true;
  }

  Xposition_last = Xposition;

#if 0
  {
    display.setTextSize(1);             // Normal 1:1 pixel scale
    display.setCursor(0,55); 
    display.println(F(__DATE__ "  " __TIME__));
  }
#endif
}

void displayNetworkStatus(const char string[]) {
  display.setTextColor(SSD1306_WHITE);
  display.fillRect(0, 10, 128, 20, SSD1306_BLACK); // Erase text area

  display.setCursor(0, 10);
  display.print(string);

  display.display();
}

void displaySplashScreen(void) {
  display.clearDisplay();

  display.setTextSize(1);              // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 0);             // Start at top-left corner
  display.println(F("    1st CONTACT!!"));
  display.println(F(""));
  display.println(F(""));

  display.setCursor(0, 10);
  //display.setTextSize(2);             // Draw 2X-scale text
  display.setTextColor(SSD1306_WHITE);
  display.print(F("IP:"));
  display.print(getLocalIp());

  display.setTextSize(1);              // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 55);
  display.println(F(__DATE__ "  " __TIME__));

  display.display();
  //delay(2000); XXX
}

void displaySetup() {
  Wire2.begin();

  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    //for(;;); // Don't proceed, loop forever
  }

  // Show initial display buffer contents on the screen --
  // the library initializes this with an Adafruit splash screen.
  //display.display();
  //delay(2000); // Pause for 2 seconds

  // Clear the buffer
  display.clearDisplay();

  // Draw a single pixel in white
  //display.drawPixel(10, 10, SSD1306_WHITE);

  // Show the display buffer on the screen. You MUST call display() after
  // drawing commands to make them visible on screen!
  display.display();
  //delay(750);

  displaySplashScreen();

  // display.display() is NOT necessary after every single drawing command,
  // unless that's what you want...rather, you can batch up a bunch of
  // drawing operations and then update the screen all at once by calling
  // display.display(). These examples demonstrate both approaches...
}

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
