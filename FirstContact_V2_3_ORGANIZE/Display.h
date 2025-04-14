#ifndef DISPLAY_H
#define DISPLAY_H

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

// OLED DISPLAY

// Screen dimensions and OLED parameters
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define DISPLAY_ENABLED 1
// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
// The pins for I2C are defined by the Wire-library.
// Reset pin # (or -1 if sharing Arduino reset pin)
#define OLED_RESET -1
// NOTE: This value is not documented well and totally confusing when looking at the pcb silkcreen
#define SCREEN_ADDRESS 0xBC

extern Adafruit_SSD1306 display;

// Display function prototypes
void displaySetup();
void displaySplashScreen();
void displayHostname(char *hostname);
void displayNetworkStatus(const char *status);
void displayTimeCount();
void displayState(bool isInitialized, bool wasLinked, bool isLinked);
void displayActivityStatus(bool isLinked);

#endif // DISPLAY_H
