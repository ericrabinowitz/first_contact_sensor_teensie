// Test of two channels with time multiplexing.

#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5

const int f_1 = 1047; // c6  1046.5
const int f_2 = 1109; // c6# 1108.7
const int f_3 = 1175; // d6  1174.7
const int f_4 = 1245; // d6# 1244.5

uint8_t thresh = 0.25;

// GUItool: begin automatically generated code
AudioSynthWaveformSine   sine2;          //xy=190.99998474121094,122.99998474121094
AudioInputI2S            audioIn;        //xy=192.99998474121094,369
AudioSynthWaveformSine   sine1;          //xy=207.99998474121094,60.99998474121094
AudioAnalyzeToneDetect   right_f_4; //xy=466.20001220703125,575.2000122070312
AudioAnalyzeToneDetect   right_f_3;        //xy=467,540
AudioAnalyzeToneDetect   right_f_2;        //xy=471,502
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_4;           //xy=474,384
AudioAnalyzeToneDetect   left_f_3;           //xy=475,348
AudioAnalyzeToneDetect   left_f_2;           //xy=477,313
AudioAnalyzeToneDetect   left_f_1;           //xy=483,276
AudioOutputI2S           audioOut;       //xy=711,92.99998474121094
AudioConnection          patchCord1(sine2, 0, audioOut, 1);
AudioConnection          patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection          patchCord3(audioIn, 0, left_f_2, 0);
AudioConnection          patchCord4(audioIn, 0, left_f_3, 0);
AudioConnection          patchCord5(audioIn, 0, left_f_4, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
AudioConnection          patchCord7(audioIn, 1, right_f_2, 0);
AudioConnection          patchCord8(audioIn, 1, right_f_3, 0);
AudioConnection          patchCord9(audioIn, 1, right_f_4, 0);
AudioConnection          patchCord10(sine1, 0, audioOut, 0);
AudioControlSGTL5000     audioShield;    //xy=709,177.99998474121094
// GUItool: end automatically generated code

elapsedMillis since_main = 0;
uint16_t main_period_ms = 60; 

void setup() {
  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  AudioMemory(12);

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(0.0);
  
  while (!Serial);
  delay(100);
  
  // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.
  
  const int sample_time_ms = main_period_ms/2;

  left_f_1.frequency(f_1,  sample_time_ms*f_1/1000);  //(1209, 36);
  left_f_2.frequency(f_2,  sample_time_ms*f_2/1000);
  left_f_3.frequency(f_3,  sample_time_ms*f_3/1000);
  left_f_4.frequency(f_4,  sample_time_ms*f_4/1000);
  right_f_1.frequency(f_1, sample_time_ms*f_1/1000);  // assuming the calcs get optomized out
  right_f_2.frequency(f_2, sample_time_ms*f_2/1000);
  right_f_3.frequency(f_3, sample_time_ms*f_3/1000);
  right_f_4.frequency(f_4, sample_time_ms*f_4/1000);

  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(LED3_PIN, OUTPUT);

  // start the outputs
  AudioNoInterrupts();  // disable audio library momentarily
  sine1.frequency(f_1); // left
  sine1.amplitude(1.0);
  sine2.frequency(f_4); // right
  sine2.amplitude(1.0);
  AudioInterrupts();    // enable, both tones will start together
}

const float row_threshold = 0.2;
const float column_threshold = 0.2;

void loop() {

  if (since_main >= main_period_ms) {
    since_main = 0;
    sine1.amplitude(1.0);
    sine2.amplitude(0.0);
    process_signal(2); // process the previous signal
  }

  if (since_main >= main_period_ms/2) {
    sine1.amplitude(0.0);
    sine2.amplitude(1.0);
    process_signal(1); // process the previous signal
  }
  
  //delay(25);
}

void process_signal(uint8_t signal_num) {
  float l1, l2, l3, l4, r1, r2, r3, r4;
  uint8_t led1_val, led2_val;

  // read all seven tone detectors
  l1 = left_f_1.read();
  l2 = left_f_2.read();
  l3 = left_f_3.read();
  l4 = left_f_4.read();
  r1 = right_f_1.read();
  r2 = right_f_2.read();
  r3 = right_f_3.read();
  r4 = right_f_4.read();

  // print the raw data, for troubleshooting
  //Serial.print("tones: ");
  Serial.print(l1);
  Serial.print(", ");
  Serial.print(l2);
  Serial.print(", ");
  Serial.print(l3);
  Serial.print(", ");
  Serial.print(l4);
  Serial.print(",   ");
  Serial.print(r1);
  Serial.print(", ");
  Serial.print(r2);
  Serial.print(", ");
  Serial.print(r3);
  Serial.print(", ");
  Serial.print(r4);
  Serial.print("\n");

 

  //uncomment these lines to see how much CPU time
  //the tone detectors and audio library are using
  // Serial.print("CPU=");
  // Serial.print(AudioProcessorUsage());
  // Serial.print("%, max=");
  // Serial.print(AudioProcessorUsageMax());
  // Serial.print("%   ");
  // Serial.print("\n");

 
  if (signal_num == 1) {
    led1_val = (r1 > thresh) ? 1 : 0;
  }
  
  if (signal_num == 2) {
    led2_val = (r2 > thresh) ? 1 : 0;
  }


  //analogWrite(LED1_PIN, (1-r1)*255); // write result to LED
  //analogWrite(LED2_PIN, (1-l4)*255); // write result to LED
  //analogWrite(LED3_PIN, (1-c3)*255); // write result to LED 
}


