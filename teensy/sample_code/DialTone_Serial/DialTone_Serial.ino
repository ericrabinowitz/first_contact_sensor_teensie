// Dial Tone (DTMF) decoding example.
//
// The audio with dial tones is connected to audio shield
// Left Line-In pin.  Dial tone output is produced on the
// Line-Out and headphones.
//
// Use the Arduino Serial Monitor to watch for incoming
// dial tones, and to send digits to be played as dial tones.
//
// This example code is in the public domain.


#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

#if 0
// Create the Audio components.  These should be created in the
// order data flows, inputs/sources -> processing -> outputs
//
AudioInputI2S            audioIn;
AudioAnalyzeToneDetect   row1;     // 7 tone detectors are needed
AudioAnalyzeToneDetect   row2;     // to receive DTMF dial tones
AudioAnalyzeToneDetect   row3;
AudioAnalyzeToneDetect   row4;
AudioAnalyzeToneDetect   column1;
AudioAnalyzeToneDetect   column2;
AudioAnalyzeToneDetect   column3;
AudioSynthWaveformSine   sine1;    // 2 sine wave
AudioSynthWaveformSine   sine2;    // to create DTMF
AudioMixer4              mixer;
AudioOutputI2S           audioOut;

// Create Audio connections between the components
//

AudioConnection patchCord01(audioIn, 0, row1, 0);
AudioConnection patchCord02(audioIn, 0, row2, 0);
AudioConnection patchCord03(audioIn, 0, row3, 0);
AudioConnection patchCord04(audioIn, 0, row4, 0);
AudioConnection patchCord05(audioIn, 0, column1, 0);
AudioConnection patchCord06(audioIn, 0, column2, 0);
AudioConnection patchCord07(audioIn, 0, column3, 0);
AudioConnection patchCord10(sine1, 0, mixer, 0);
AudioConnection patchCord11(sine2, 0, mixer, 1);
AudioConnection patchCord12(mixer, 0, audioOut, 0);
AudioConnection patchCord13(mixer, 0, audioOut, 1);
// Create an object to control the audio shield.
// 
AudioControlSGTL5000 audioShield;

#else
#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

// GUItool: begin automatically generated code
AudioSynthWaveformSine   sine1;          //xy=373,425
AudioSynthWaveformSine   sine3;          //xy=374,527
AudioSynthWaveformSine   sine2;          //xy=375,474
AudioMixer4              mixer;          //xy=638,355
AudioAnalyzeToneDetect   row3;           //xy=860,960
AudioAnalyzeToneDetect   row4;           //xy=865,814
AudioOutputI2S           audioOut;       //xy=880,475
AudioAnalyzeToneDetect   row1;           //xy=879,894
AudioAnalyzeToneDetect   row2;           //xy=894,727
AudioAnalyzeToneDetect   column2;        //xy=901,541
AudioAnalyzeToneDetect   column3;        //xy=922,666
AudioAnalyzeToneDetect   column1;        //xy=925,596
AudioConnection          patchCord1(sine1, 0, mixer, 0);
AudioConnection          patchCord2(sine3, 0, mixer, 2);
AudioConnection          patchCord3(sine2, 0, mixer, 1);
AudioConnection          patchCord4(mixer, 0, audioOut, 0);
AudioConnection          patchCord5(mixer, 0, audioOut, 1);
AudioConnection          patchCord6(mixer, column2);
AudioConnection          patchCord7(mixer, column1);
AudioConnection          patchCord8(mixer, column3);
AudioConnection          patchCord9(mixer, row2);
AudioConnection          patchCord10(mixer, row4);
AudioConnection          patchCord11(mixer, row1);
AudioConnection          patchCord12(mixer, row3);
AudioControlSGTL5000     audioShield;    //xy=278,345
// GUItool: end automatically generated code

#endif



long unsigned int loop_count = 0;


void setup() {

  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  AudioMemory(12);

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(0.5);
  
  while (!Serial) ;
  delay(100);
  
  // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.
  row1.frequency(697, 21);
  row2.frequency(770, 23);
  row3.frequency(852, 25);
  row4.frequency(941, 28);
  column1.frequency(1209, 36);
  column2.frequency(1336, 40);
  column3.frequency(1477, 44);


  loop_count = 0;

}

const float row_threshold = 0.2;
const float column_threshold = 0.2;


void loop() {
  float r1, r2, r3, r4, c1, c2, c3;
  char digit=0;

  // read all seven tone detectors
  r1 = row1.read();
  r2 = row2.read();
  r3 = row3.read();
  r4 = row4.read();
  c1 = column1.read();
  c2 = column2.read();
  c3 = column3.read();


  char string[256];

  sprintf (string, "[%lu]tones: ", loop_count++);
  Serial.print(string);

  /* print the raw data, for troubleshooting. */
  Serial.print("tones: ");
  Serial.print(r1);
  Serial.print(", ");
  Serial.print(r2);
  Serial.print(", ");
  Serial.print(r3);
  Serial.print(", ");
  Serial.print(r4);
  Serial.print(",   ");
  Serial.print(c1);
  Serial.print(", ");
  Serial.print(c2);
  Serial.print(", ");
  Serial.print(c3);

  // check all 12 combinations for key press
  if (r1 >= row_threshold) {
    if (c1 > column_threshold) {
      digit = '1';
    } else if (c2 > column_threshold) {
      digit = '2';
    } else if (c3 > column_threshold) {
      digit = '3';
    }
  } else if (r2 >= row_threshold) { 
    if (c1 > column_threshold) {
      digit = '4';
    } else if (c2 > column_threshold) {
      digit = '5';
    } else if (c3 > column_threshold) {
      digit = '6';
    }
  } else if (r3 >= row_threshold) { 
    if (c1 > column_threshold) {
      digit = '7';
    } else if (c2 > column_threshold) {
      digit = '8';
    } else if (c3 > column_threshold) {
      digit = '9';
    }
  } else if (r4 >= row_threshold) { 
    if (c1 > column_threshold) {
      digit = '*';
    } else if (c2 > column_threshold) {
      digit = '0';
    } else if (c3 > column_threshold) {
      digit = '#';
    }
  }

  // print the key, if any found
  if (digit > 0) {
    Serial.print("  --> Key: ");
    Serial.print(digit);
  }
  Serial.println();

  // uncomment these lines to see how much CPU time
  // the tone detectors and audio library are using
  //Serial.print("CPU=");
  //Serial.print(AudioProcessorUsage());
  //Serial.print("%, max=");
  //Serial.print(AudioProcessorUsageMax());
  //Serial.print("%   ");

  // check if any data has arrived from the serial monitor
  if (Serial.available()) {
    char key = Serial.read();
    int low=0;
    int high=0;
    if (key == '1') {
      low = 697;
      high = 1209;
    } else if (key == '2') {
      low = 697;
      high = 1336;
    } else if (key == '3') {
      low = 697;
      high = 1477;
    } else if (key == '4') {
      low = 770;
      high = 1209;
    } else if (key == '5') {
      low = 770;
      high = 1336;
    } else if (key == '6') {
      low = 770;
      high = 1477;
    } else if (key == '7') {
      low = 852;
      high = 1209;
    } else if (key == '8') {
      low = 852;
      high = 1336;
    } else if (key == '9') {
      low = 852;
      high = 1477;
    } else if (key == '*') {
      low = 941;
      high = 1209;
    } else if (key == '0') { 
      low = 941;
      high = 1336;
    } else if (key == '#') {
      low = 941;
      high = 1477;
    }
    else if (key == '#') { low = 941; high = 1477; }

    else if (key == 'A') { low = 1633; high = 697; }
    else if (key == 'B') { low = 1633; high = 770; }
    else if (key == 'C') { low = 1633; high = 852; }
    else if (key == 'D') { low = 1633; high = 941; }
    else if (key == 'E') { low = 1805; high = 697; }
    else if (key == 'F') { low = 1805; high = 770; }
    else if (key == 'G') { low = 1805; high = 852; }
    else if (key == 'H') { low = 1805; high = 941; }
    else if (key == 'I') { low = 1995; high = 697; }
    else if (key == 'J') { low = 1995; high = 770; }
    else if (key == 'K') { low = 1995; high = 852; }
    else if (key == 'L') { low = 1995; high = 941; }
    else if (key == 'M') { low = 2206; high = 697; }
    else if (key == 'N') { low = 2206; high = 770; }
    else if (key == 'O') { low = 2206; high = 1477; }
    else if (key == 'P') { low = 2206; high = 941; }
    else if (key == 'Q') { low = 2438; high = 697; }
    else if (key == 'R') { low = 2438; high = 852; }
    else if (key == 'S') { low = 2438; high = 1477; }
    else if (key == 'T') { low = 2438; high = 941; }
    else if (key == 'U') { low = 1209; high = 1040; }
    else if (key == 'V') { low = 1209; high = 1149; }
    else if (key == 'W') { low = 1209; high = 1270; }
    else if (key == 'X') { low = 1209; high = 1477; }
    else if (key == 'Y') { low = 1336; high = 1040; }
    else if (key == 'Z') { low = 1336; high = 1149; }

    // play the DTMF tones, if characters send from the Arduino Serial Monitor
    if (low > 0 && high > 0) {
      Serial.print("Output sound for key ");
      Serial.print(key);
      Serial.print(", low freq=");
      Serial.print(low);
      Serial.print(", high freq=");
      Serial.print(high);
      Serial.println();
      AudioNoInterrupts();  // disable audio library momentarily
      sine1.frequency(low);
      sine1.amplitude(0.4);
      sine2.frequency(high);
      sine2.amplitude(0.45);

      sine3.frequency(1209);
      sine3.amplitude(0.45);

      AudioInterrupts();    // enable, both tones will start together
      delay(100);           // let the sound play for 0.1 second
      AudioNoInterrupts();
      sine1.amplitude(0);
      sine2.amplitude(0);
      sine3.amplitude(0);
      AudioInterrupts();
      delay(50);            // make sure we have 0.05 second silence after
    }
  }

  delay(25);
}


