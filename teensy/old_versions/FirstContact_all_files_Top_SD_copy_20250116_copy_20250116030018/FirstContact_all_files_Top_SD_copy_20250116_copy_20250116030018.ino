#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

#include "SdFat.h"
#include <string>
#include <vector>
#include <algorithm>

// some aliases to reduce typing....
using string = std::string;
using strVec = std::vector<string>;
SdFat sd;



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

// Use these for the SD+Wiz820 or other adaptors
//#define SDCARD_CS_PIN    4
//#define SDCARD_MOSI_PIN  11
//#define SDCARD_SCK_PIN   13

strVec filenames;

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



void setup() {
  Serial.begin(9600);

// ------------------------
 sd.begin(SdioConfig(FIFO_SDIO));

    // read filnames from some directory (here: root)
    SdFile dir("/", O_RDONLY);
    filenames = getFilenames(dir);

    // use the stl sorting algorithmus
    std::sort(filenames.begin(), filenames.end(), [](string a, string b) { return a < b; });

    // print the sorted names
    for (string& name : filenames)
    {
        Serial.println(name.c_str());
    }

// ---------------------------







  AudioMemory(8);
  sgtl5000_1.enable();
  sgtl5000_1.volume(0.5);
  SPI.setMOSI(SDCARD_MOSI_PIN);
  SPI.setSCK(SDCARD_SCK_PIN);
  if (!(SD.begin(SDCARD_CS_PIN))) {
    while (1) {
      Serial.println("Unable to access the SD card");
      delay(500);
    }
  }
  delay(1000);
}



void play (const char * song) {
  while (playSdWav1.isPlaying() == true ) {
    delay(10); // wait for library to parse WAV info
  }
  //Serial.println("Playing ");
  Serial.println( song);
  if (playSdWav1.play(song) == false) {
    Serial.println("Error playing ");
    Serial.println(song);
  }
} 

void loop() {
  Serial.println("----------------------------");
  for (;;) {
   

  play(filenames[random(0, filenames.size()-1)].c_str());

    //play("SDTEST1.wav");
    delay(10); // wait for library to parse WAV info

  }
  // do nothing while playing...
}




