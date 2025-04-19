
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <Audio.h>
#include <SD.h>
#include <SerialFlash.h>

#include "SdFat.h"
#include <string>
#include <vector>
#include <algorithm>

#define DISPLAY_ENABLED 1

#define MAX_FILES 31

char file[100][40];
// some aliases to reduce typing....
using string = std::string;
using strVec = std::vector<string>;
SdFat sd;


strVec filenames;

AudioPlaySdWav           playSdWav1;
AudioOutputI2S           i2s1;
AudioConnection          patchCord1(playSdWav1, 0, i2s1, 0);
AudioConnection          patchCord2(playSdWav1, 1, i2s1, 1);
AudioControlSGTL5000     sgtl5000_1;

// Use these with the Teensy Audio Shield
//#define SDCARD_CS_PIN    10
//#define SDCARD_MOSI_PIN  7   // Teensy 4 ignores this, uses pin 11
//#define SDCARD_SCK_PIN   14  // Teensy 4 ignores this, uses pin 13

// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN    BUILTIN_SDCARD
#define SDCARD_MOSI_PIN  11  // not actually used
#define SDCARD_SCK_PIN   13  // not actually used


#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
// The pins for I2C are defined by the Wire-library. 
// On an arduino UNO:       A4(SDA), A5(SCL)
// On an arduino MEGA 2560: 20(SDA), 21(SCL)
// On an arduino LEONARDO:   2(SDA),  3(SCL), ...
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
//#define SCREEN_ADDRESS 0x3D ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
#define SCREEN_ADDRESS 0xBC
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire2, OLED_RESET);





void display_first_contact(void);

void setup() {
  Serial.begin(9600);

  // Get File Names

// ------------------------
 sd.begin(SdioConfig(FIFO_SDIO));

    // read filnames from some directory (here: root)
    SdFile dir("/", O_RDONLY);
    filenames = getFilenames(dir);

    // use the stl sorting algorithmus
    std::sort(filenames.begin(), filenames.end(), [](string a, string b) { return a < b; });

    // print the sorted names
    //for (string& name : filenames)
    //Serial.println(name.c_str());

    for (uint32_t index = 0; index < filenames.size()-1; ++index)
    {
        Serial.printf ("Index:%3d  Name(%s)", index, filenames[index].c_str());
        Serial.println("");
    }

// ---------------------------

  // AUDIO SETUP
  {
    AudioMemory(24);
    sgtl5000_1.enable();
    sgtl5000_1.volume(0.035);
    SPI.setMOSI(SDCARD_MOSI_PIN);
    SPI.setSCK(SDCARD_SCK_PIN);
    if (!(SD.begin(SDCARD_CS_PIN))) {
      while (1) {
        Serial.println("Unable to access the SD card");
        delay(500);
      }
    }
  }
  delay(1000);

#ifdef DISPLAY_ENABLED 
  Wire2.begin();
#endif

  Serial.println(F("Audio+SSD1306"));

#ifdef DISPLAY_ENABLED                                                                                                                                                                                                
  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  // Show initial display buffer contents on the screen --
  // the library initializes this with an Adafruit splash screen.
  //display.display();
  //delay(2000); // Pause for 2 seconds

  // Clear the buffer
  display.clearDisplay();

  // Draw a single pixel in white
  display.drawPixel(10, 10, SSD1306_WHITE);

  // Show the display buffer on the screen. You MUST call display() after
  // drawing commands to make them visible on screen!
  display.display();
  //delay(2000);
  // display.display() is NOT necessary after every single drawing command,
  // unless that's what you want...rather, you can batch up a bunch of
  // drawing operations and then update the screen all at once by calling
  // display.display(). These examples demonstrate both approaches...

  //for (;;) 
  {
    display_first_contact();delay(1000);
    //testdrawstyles();     delay(1000);

  }

#endif

}

void display_first_contact(void) {
  display.clearDisplay();

  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,0);             // Start at top-left corner
  display.println(F("      1st CONTACT!"));
  display.println(F(""));
  display.println(F(""));


  display.setTextSize(2);             // Draw 2X-scale text
  display.setTextColor(SSD1306_WHITE);
  display.print(F("NODE: 1")); 



  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,55); 

  display.println(F(__DATE__ "  " __TIME__));
 

  display.display();
  delay(2000);
}






//-----------------------------------------------
strVec getFilenames(SdFile& dir)
{
    strVec filenames;

    SdFile file;
    while (file.openNext(&dir, O_RDONLY))
    {
        constexpr size_t maxFileLen = 30;

        char buf[maxFileLen];
        file.getName(buf, maxFileLen);
        filenames.emplace_back(buf);  // directly construct the string in the vector to avoid copies
    }
    return filenames;  // Ok, std::vector implements move semantics -> nothing will be copied here
}

void play (const char * song) {
  // Wait for previous song to finish
  while (playSdWav1.isPlaying() == true ) {
    delay(20); // wait for library to parse WAV info
  }


if (song[0] == '.')
  return;

// A brief delay for the library read WAV info
  delay(25);


#ifdef DISPLAY_ENABLED
  //display.clearDisplay();
  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,0);             // Start at top-left corner
  display.print("SNG: " );
  display.println(song);
  display.display();
#endif

  Serial.println( song);

  uint32_t retry = 100;
  while (retry)
  {
    if (playSdWav1.play(song) == false) {
      Serial.print ("### Error playing (");
      Serial.print (song);
      Serial.print (") ");
      Serial.println ( retry );
      delay(200); 
      --retry;
    }
    else
      retry = 0;
  }
}

void loop() {
  uint32_t index;

    display.fillRoundRect(0, 31, 128,                                  10, display.height()/4, SSD1306_WHITE);
    display.display();
    delay (10000);

    display.fillRoundRect(0, 31, 128,                                 10, display.height()/4, SSD1306_INVERSE);
    display.display();
    delay (10000);

  Serial.println("----------------------------");
  for (;;) {

    index = random(1, filenames.size()-1);
    display.clearDisplay();
    //Serial.printf (" Files:%d ", filenames.size()-1);
    Serial.printf ( "Playing %3d ", index);

    //display.fillRoundRect(0, 31, 128,                                  10, display.height()/4, SSD1306_WHITE);
    display.fillRoundRect(0, 31, 128 * index / (filenames.size() + 1), 10, display.height()/4, SSD1306_INVERSE);

    play(filenames[index].c_str());

    delay(10); // wait for library to parse WAV info

  }
  // do nothing while playing...
}


