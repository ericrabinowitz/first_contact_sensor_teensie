// FIRST CONTACT  - SENSOR CODE FOR TEENSY 4.1


/*
  'EXTENDED' DTMF FREQUENCIES
 𝑓1 = 697, 770, 852, 941, 1040, 1149, 1270, 1404
 𝑓2 = 1209, 1336, 1477, 1633, 1805, 1995, 2206, 2438
 */


// This will be determined by the 3 address pins but for now hard coded
#define MY_SCULPTURE_NUMBER 2 

#if 0

#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

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

#define MAX_HANDS 10 // 5 figures with 2 hands each
#define MAX_FREQUENCY_INDEX 16
uint32_t frequency_table[MAX_FREQUENCY_INDEX] = { 697, 770, 852, 941, 1040, 1149, 1270, 1404, 1209, 1336, 1477, 1633, 1805, 1995, 2206, 2438 };


AudioSynthWaveformSine   sine1;          //xy=373,425
AudioSynthWaveformSine   sine3;          //xy=374,527
AudioSynthWaveformSine   sine4;          //xy=374,527
AudioSynthWaveformSine   sine2;          //xy=375,474
AudioMixer4              mixer;          //xy=638,355
AudioMixer4              mixerB;

AudioOutputI2S           audioOut;       //xy=880,475

AudioAnalyzeToneDetect   detect[MAX_HANDS];      
AudioAnalyzeToneDetect   row1;           //xy=879,894
AudioAnalyzeToneDetect   row2;           //xy=894,727
AudioAnalyzeToneDetect   row3;           //xy=860,960
AudioAnalyzeToneDetect   row4;           //xy=865,814
AudioAnalyzeToneDetect   column2;        //xy=901,541
AudioAnalyzeToneDetect   column3;        //xy=922,666
AudioAnalyzeToneDetect   column1;        //xy=925,596

AudioConnection          patchCord1(sine1, 0, mixer, 0);
AudioConnection          patchCord3(sine2, 0, mixer, 1);

AudioConnection          patchCord2(sine3, 0, mixerB, 0);
AudioConnection          patchCord4(sine4, 0, mixerB, 1);
AudioConnection          patchCord5(mixerB, 0, mixer, 2);

AudioConnection          patchCord5a(mixer, 0, audioOut, 0);
AudioConnection          patchCord5b(mixer, 0, audioOut, 1);

AudioConnection          patchCord6(mixer, detect[0]);
AudioConnection          patchCord7(mixer, detect[1]);
AudioConnection          patchCord8(mixer, detect[2]);
AudioConnection          patchCord9(mixer, detect[3]);
AudioConnection          patchCord10(mixer, detect[4]);
AudioConnection          patchCord11(mixer, detect[5]);
AudioConnection          patchCord12(mixer, detect[6]);
AudioConnection          patchCord13(mixer, detect[7]);
AudioConnection          patchCord14(mixer, detect[8]);
AudioConnection          patchCord15(mixer, detect[9]);

#if 0
AudioConnection          patchCord6(mixer, column2);
AudioConnection          patchCord7(mixer, column1);
AudioConnection          patchCord8(mixer, column3);
AudioConnection          patchCord9(mixer, row2);
AudioConnection          patchCord10(mixer, row4);
AudioConnection          patchCord11(mixer, row1);
AudioConnection          patchCord12(mixer, row3);
#endif
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

  unsigned int hand;
  for (hand = 0; hand < MAX_HANDS; hand++) {
     
     
     // XXX TRY THIS AFTER SYSTEM WORKS & Delete static connections above
     // new AudioConnection (mixer, detect[hand]); XXX These will never be deleted which is OK


     detect[hand].frequency(frequency_table[hand], 50);
  }

  loop_count = 0;

}

const float detect_threshold = 0.2;


void loop() {
  float detection[MAX_HANDS];

  char string[256];
  uint32_t hand;

  sprintf (string, "[%lu]tones: ", loop_count++);
  Serial.print(string);

  // read all seven tone detectors
  for ( hand = 0; hand < MAX_HANDS; hand++) {
    detection[hand] = detect[hand].read();

    Serial.print (" ");
    if ( detection[hand] > detect_threshold )
      Serial.print ("### ");
    else
      Serial.print ("--- ");
    Serial.print (detection[hand]);
    Serial.print ("  ");

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

      sine3.frequency(frequency_table[6]);
      sine3.amplitude(0.45);

      sine4.frequency(frequency_table[7]);
      sine4.amplitude(0.45);


      AudioInterrupts();    // enable, both tones will start together
      delay(100);           // let the sound play for 0.1 second

      

      AudioNoInterrupts();
      sine1.amplitude(0);
      sine2.amplitude(0);
      sine3.amplitude(0);
      sine4.amplitude(00);
      AudioInterrupts();
      delay(50); 
      AudioNoInterrupts();
      sine4.amplitude(0.0001);
      AudioInterrupts();
      delay(50);            // make sure we have 0.05 second silence after
    }
  }

  delay(25);
}


