// Test of two channels with time multiplexing.

#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>


float detectionThreshold = 0.25;

#define MY_NODE 4
#define NODE_MAX 5

const int frequency_by_node[NODE_MAX] = { 852, 941, 1209, 1336, 1477};


// GUItool: begin automatically generated code
AudioInputI2S            audioIn;        //xy=292,564
AudioSynthWaveformSine   sine1;          //xy=377,134

AudioAnalyzeToneDetect   toneDetect[NODE_MAX]; //xy=633,691



AudioOutputI2S           audioOut;       //xy=881,166
AudioConnection          patchCord1(audioIn, 1, toneDetect[0], 0); //xy=636,649
AudioConnection          patchCord2(audioIn, 1, toneDetect[1], 0); //xy=637,614
AudioConnection          patchCord3(audioIn, 1, toneDetect[2], 0);  //xy=640,620
AudioConnection          patchCord4(audioIn, 1, toneDetect[3], 0); //xy=641,576
AudioConnection          patchCord5(audioIn, 1, toneDetect[4], 0); //xy=642,538
AudioConnection          patchCord6(sine1, 0, audioOut, 1); //xy=642,538
AudioControlSGTL5000     audioShield;    //xy=84,325
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

  
  if ( MY_NODE != 0)
    toneDetect[0].frequency(frequency_by_node[0], sample_time_ms* frequency_by_node[0]/1000);  // assuming the calcs get optomized out

  if ( MY_NODE != 1)  
    toneDetect[1].frequency(frequency_by_node[1], sample_time_ms* frequency_by_node[1]/1000);

  if ( MY_NODE != 2)
    toneDetect[2].frequency(frequency_by_node[2], sample_time_ms* frequency_by_node[2]/1000);

  if ( MY_NODE != 3)
    toneDetect[3].frequency(frequency_by_node[3], sample_time_ms* frequency_by_node[3]/1000);

  if ( MY_NODE != 4)
    toneDetect[4].frequency(frequency_by_node[4], sample_time_ms* frequency_by_node[4]/1000);
  
  // start the outputs
  AudioNoInterrupts();  // disable audio library momentarily


  sine1.frequency(frequency_by_node[MY_NODE]); // RIGHT
  sine1.amplitude(1.0);

  AudioInterrupts();    // enable, both tones will start together
}

const float row_threshold = 0.2;
const float column_threshold = 0.2;

void loop() {

  if (since_main >= main_period_ms) {
    since_main = 0;
    sine1.amplitude(1.0);
    process_signal(2); // process the previous signal
  }

  if (since_main >= main_period_ms/2) {
    sine1.amplitude(0.0);
    process_signal(1); // process the previous signal
  }
  
  //delay(25);
}

void process_signal(uint8_t signal_num) {
  unsigned int node;
  float detectLevel[NODE_MAX];
  //uint8_t led1_val, led2_val;

  
  // read all seven tone detectors
  for ( node = 0; node < NODE_MAX; ++node) {
    if ( node != MY_NODE)
      detectLevel[node] = toneDetect[node].read();
    else 
      detectLevel[node] = 0;
  }

  // print the raw data, for troubleshooting
  Serial.print("Node:");
  Serial.print(MY_NODE);
  Serial.print(" Thresh:");
  Serial.print (detectionThreshold);
  Serial.print(" Tones: ");
  for ( node = 0; node < NODE_MAX; ++node) {
    Serial.print(node);
    Serial.print(":");
    Serial.print(detectLevel[node]);
    Serial.print(":");
    Serial.print( (detectLevel[node] >= detectionThreshold) ? "*" : "-" );
    Serial.print("   ");
  }
  Serial.print("\n");

 
#if 0
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
#endif
}


