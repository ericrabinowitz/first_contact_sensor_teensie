#include <Adafruit_SSD1306.h>
#include <Audio.h>

#include "AudioSense.h"

// ------ Audio Contact Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5

//
// Frequencies to Transmit and listen for through hands (f_1 and f_2 are the tx frequencies)
const int f_1 = 20;
const int f_2 = 20;
const int f_3 = 20;
const int f_4 = 20;

// This is the tone dection sensitivity.  Currently set for maximum sensitivity.
// Edit with caution and experimentation.
float thresh = 0.01;

// GUItool: begin automatically generated code
//AudioSynthWaveformSine   sine2;          //xy=190.99998474121094,122.99998474121094
AudioInputI2S audioIn;        //xy=192.99998474121094,369
AudioSynthWaveformSine sine1; //xy=207.99998474121094,60.99998474121094

/*
AudioAnalyzeToneDetect   right_f_4; //xy=466.20001220703125,575.2000122070312
AudioAnalyzeToneDetect   right_f_3;        //xy=467,540
AudioAnalyzeToneDetect   right_f_2;        //xy=471,502
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_4;           //xy=474,384
AudioAnalyzeToneDetect   left_f_3;           //xy=475,348
AudioAnalyzeToneDetect   left_f_2;           //xy=477,313
*/
AudioAnalyzeToneDetect right_f_1; //xy=472,464
AudioAnalyzeToneDetect left_f_1;  //xy=483,276
AudioOutputI2S audioOut;          //xy=711,92.99998474121094
AudioMixer4 mixerRight;
AudioMixer4 mixerLeft;

AudioConnection patchCordM1L(sine1, 0, mixerLeft, 0);
//AudioConnection          patchCordM1R(sine1, 0, mixerRight, 0);

//AudioConnection          patchCordM2L(sine2, 0, mixerLeft, 1);
//AudioConnection          patchCordM2R(sine2, 0, mixerRight, 1);

//
// Audio Player
// NOTE: this is defined here to hook up to the connections mixer, but used in
// MusicPlayer.ino.
AudioPlaySdWav playSdWav1;
AudioConnection patchCord11(playSdWav1, 0, mixerLeft, 2);
AudioConnection patchCord12(playSdWav1, 1, mixerRight, 2);
// Audio Player
//

AudioConnection patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection patchCord6(audioIn, 1, right_f_1, 0);
/*
AudioConnection          patchCord3(audioIn, 0, left_f_2, 0);
AudioConnection          patchCord4(audioIn, 0, left_f_3, 0);
AudioConnection          patchCord5(audioIn, 0, left_f_4, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
AudioConnection          patchCord7(audioIn, 1, right_f_2, 0);
AudioConnection          patchCord8(audioIn, 1, right_f_3, 0);
AudioConnection          patchCord9(audioIn, 1, right_f_4, 0);
*/

AudioConnection patchCordMOL(mixerLeft, 0, audioOut, 0);
AudioConnection patchCordMOR(mixerRight, 0, audioOut, 1);

elapsedMillis since_main = 0;
uint16_t main_period_ms = 150;
// ------ Audio Contact Defines - End

// Contact Sense Start
//
void audioSenseSetup() {
  // NOTE this number is simply a guess.
  // Working: 12 for Sens, 8 for Wav Player + margin.
  AudioMemory(22);
  // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.

  const int sample_time_ms = main_period_ms / 2;

  left_f_1.frequency(f_1, sample_time_ms * f_1 / 1000); //(1209, 36);
  /*
  left_f_2.frequency(f_2,  sample_time_ms*f_2/1000);
  left_f_3.frequency(f_3,  sample_time_ms*f_3/1000);
  left_f_4.frequency(f_4,  sample_time_ms*f_4/1000);
  */
  // Assuming the calcs get optimized out.
  right_f_1.frequency(f_1, sample_time_ms * f_1 / 1000);
  /*
  right_f_2.frequency(f_2, sample_time_ms*f_2/1000);
  right_f_3.frequency(f_3, sample_time_ms*f_3/1000);
  right_f_4.frequency(f_4, sample_time_ms*f_4/1000);
*/
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(LED3_PIN, OUTPUT);

  // start the outputs
  AudioNoInterrupts();  // disable audio library momentarily
  sine1.frequency(f_1); // left
  sine1.amplitude(1.0);
  /*
  sine2.frequency(f_4); // right
  sine2.amplitude(1.0);
  */
  AudioInterrupts(); // enable, both tones will start together
}

void debugPrintAudioSense(float l1, float r1) {
  /*
  float l1, l2, l3, l4, r1, r2, r3, r4;
  // read all seven tone detectors
  l1 = left_f_1.read();
  r1 = right_f_1.read();
  l2 = left_f_2.read();
  l3 = left_f_3.read();
  l4 = left_f_4.read();
  r1 = right_f_1.read();
  r2 = right_f_2.read();
  r3 = right_f_3.read();
  r4 = right_f_4.read();
*/
#ifdef DEBUG_PRINT
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
#endif
}

#define TRANSITION_BUFFER_MS 100

void printTransition(bool buffering, bool stableIsLinked,
                     bool candidateIsLinked) {
  if (buffering) {
    Serial.print("Pending Transition: ");
  } else {
    Serial.print("Transition: ");
  }
  Serial.print(stableIsLinked ? "Linked" : "Unlinked");
  Serial.print(" to ");
  Serial.print(candidateIsLinked ? "Linked" : "Unlinked");
  if (buffering) {
    Serial.println(" while buffering...");
  } else {
    Serial.print(" after buffering for ");
    Serial.print(TRANSITION_BUFFER_MS);
    Serial.println("ms.");
  }
}

// Get the isLinked state, buffering over ~100ms for stable readings.
bool getStableIsLinked() {
  // Send signal?
  sine1.amplitude(1.0);

  // Read signal.
  float l1, r1;
  l1 = left_f_1.read();
  r1 = right_f_1.read();
  debugPrintAudioSense(l1, r1);

  // Process signal for a stable reading.
  static bool stableIsLinked = false;
  static unsigned long bufferStartTime = 0;
  static bool buffering = false;
  bool candidateIsLinked = (l1 > thresh || r1 > thresh);

  if (!stableIsLinked && candidateIsLinked) {
    // Immediate transition to Linked for quick contact latency.
    printTransition(buffering, stableIsLinked, candidateIsLinked);
    stableIsLinked = true;
    buffering = false;
  } else if (stableIsLinked && !candidateIsLinked) {
    // Buffer transition to Unlinked to mitigate flakiness.
    if (!buffering) {
      buffering = true;
      bufferStartTime = millis();
      printTransition(buffering, stableIsLinked, candidateIsLinked);
    } else if (millis() - bufferStartTime >= TRANSITION_BUFFER_MS) {
      // Finished buffering. Finalize the transition to the new state.
      buffering = false;
      printTransition(buffering, stableIsLinked, candidateIsLinked);
      stableIsLinked = candidateIsLinked;
    } else {
      // Still buffering. Do not change stableIsLinked.
    }
  } else {
    // If stable and candidate are the same, do nothing and stop buffering.
    buffering = false;
  }
  return stableIsLinked;
}

// Contact Sense End
//

/*
  printState() - Print the contact state to the serial console
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void printState(bool isInitialized, bool wasLinked, bool isLinked) {
  if (isInitialized && wasLinked == isLinked) {
    return;
  }

  if (isLinked) {
    Serial.print("CONTACT\n");
  } else {
    Serial.print("--OFF---\n");
  }

  //uncomment these lines to see how much CPU time
  //the tone detectors and audio library are using

  Serial.print("CPU=");
  Serial.print(AudioProcessorUsage());
  Serial.print("%, max=");
  Serial.print(AudioProcessorUsageMax());
  Serial.print("%   ");
  Serial.print("\n");
}