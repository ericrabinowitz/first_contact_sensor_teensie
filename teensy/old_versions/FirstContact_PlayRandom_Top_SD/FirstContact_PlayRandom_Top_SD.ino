#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

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


void setup() {
  Serial.begin(9600);
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

char file[][40] {
    "Formant Squish2.wav",
    "fire.wav",
    "venus.wav",
    "mars.wav",
    "hold_on.wav",
    "thats_it.wav",
    "connected.wav",
    "disconnected.wav",
    "0.wav",
    "1.wav",
    "2.wav",
    "3.wav",
    "4.wav",
    "5.wav",
    "6.wav",
    "7.wav",
    "8.wav",
    "9.wav",
    "10.wav",
    "comeon.wav",
    "come_here.wav",
    "are_you_from.wav",
    "commander2.wav",
    "standing_by2.wav",
    "Alternating Harmonics2.wav",
    "sample_022.wav",
    "Formant Squish2.wav",
    "Hollow Distorted FM2.wav",
    "wow.wav",
    "feelsreallygood.wav",
    "feelsgood.wav",
};

#define MAX_FILES 31




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
   


  play (file[random(0, MAX_FILES-1)]);
#if 0
    play("Formant Squish2.wav");
    play("wind.wav");
    play("venus.wav");
    play("mars.wav");
    play("hold_on.wav");
    play("thats_it.wav");
    play("connected.wav");
    play("disconnected.wav");
    play("0.wav");
    play("1.wav");
    play("2.wav");
    play("3.wav");
    play("4.wav");
    play("5.wav");
    play("6.wav");
    play("7.wav");
    play("8.wav");
    play("9.wav");
    play("10.wav");
    play("wind.wav");
    play("come_here.wav");
    play("are_you_from.wav");
    play("commander2.wav");
    play("standing_by2.wav");
    play("Alternating Harmonics2.wav");
    play("sample_022.wav");
    play("Formant Squish2.wav");
    play("Hollow Distorted FM2.wav");
#endif
    //play("SDTEST1.wav");
    delay(10); // wait for library to parse WAV info

  }
  // do nothing while playing...
}




