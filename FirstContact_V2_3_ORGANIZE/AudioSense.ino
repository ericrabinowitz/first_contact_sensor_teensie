/*
AudioSense: The contact sensing and audio mixing logic.
*/

#include <Audio.h>

#include "AudioSense.h"

// ------ Audio Contact Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5
// This is the volume tuned for the sense signal sensitivity.
#define SIGNAL_AUDIO_VOLUME 0.75

// Frequencies to Transmit and listen for through hands (f_1 and f_2 are the tx frequencies)
const int f_1 = 20;
// These are unused.
const int f_2 = 20;
const int f_3 = 20;
const int f_4 = 20;

// This is the tone dection sensitivity.  Currently set for maximum sensitivity.
// Edit with caution and experimentation.
float thresh = 0.01;

// The controller for the audio shield.
AudioControlSGTL5000 audioShield;

// The audio input used for sensing.
AudioInputI2S audioIn;

// The sine wave signal generator.
AudioSynthWaveformSine sine1;

// The input signal detectors.
AudioAnalyzeToneDetect left_f_1;
AudioAnalyzeToneDetect right_f_1;

// The mixer to use for audio sensing.
AudioMixer4 mixerSensingOutput;

// Connect the sine wave generator to sensing mixer.
AudioConnection patchCordM1L(sine1, 0, mixerSensingOutput, 0);

// Connect the audio input to the left/right sensing detectors
AudioConnection patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection patchCord6(audioIn, 1, right_f_1, 0);

// This audio output is shared between the audio sensing and the music player.
AudioOutputI2S audioOut;

// Left channel (sense signal) plays on the left audio out channel.
AudioConnection patchCordMOL(mixerSensingOutput, 0, audioOut, 0);

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

  // Enable the audio shield and set the output volume.
  // NOTE: This volume is shared between mixers, so is important not just for
  // the music volume but also the signal sensitivity.
  audioShield.enable();
  // TODO: Can we just set the gain of the mixer instead of the audio shield?
  // Then we can play music at full volume.
  audioShield.volume(SIGNAL_AUDIO_VOLUME);

  const int sample_time_ms = main_period_ms / 2;

  // Configure the left/right tone analyzers to detect tone.
  left_f_1.frequency(f_1, sample_time_ms * f_1 / 1000);
  right_f_1.frequency(f_1, sample_time_ms * f_1 / 1000);

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

// Static state variables.
bool isInitialized = false;
bool wasLinked = false;

// This function wraps getStableIsLinked() and returns all state info.
ContactState getContactState() {
  ContactState state;
  state.isLinked = getStableIsLinked();
  state.isInitialized = isInitialized;
  state.wasLinked = wasLinked;

  // Update our persistent state for next call.
  isInitialized = true;
  wasLinked = state.isLinked;

  return state;
}

// Contact Sense End
//

/*
  printState() - Print the contact state to the serial console
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/

// Modify printState to accept the struct.
void printState(const ContactState &state) {
  if (state.isUnchanged()) {
    return;
  }
  if (state.isLinked) {
    Serial.println("CONTACT");
  } else {
    Serial.println("--OFF---");
  }

  Serial.print("CPU=");
  Serial.print(AudioProcessorUsage());
  Serial.print("%, max=");
  Serial.print(AudioProcessorUsageMax());
  Serial.print("%   ");
  Serial.print("\n");
}
