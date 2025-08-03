/*
AudioSense: The contact sensing and audio mixing logic.
*/

#include <Audio.h>

#include "AudioSense.h"
#include "StatueConfig.h"

// ------ Audio Contact Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5
// This is the volume tuned for the sense signal sensitivity.
#define SIGNAL_AUDIO_VOLUME 0.75

// Use configured frequencies from StatueConfig.h
const int tx_freq = MY_TX_FREQ; // This statue's transmit frequency

// This is the tone dection sensitivity.  Currently set for maximum sensitivity.
// Edit with caution and experimentation.
float thresh = 0.01;

// The controller for the audio shield.
AudioControlSGTL5000 audioShield;

// The audio input used for sensing.
AudioInputI2S audioIn;

// The sine wave signal generator.
AudioSynthWaveformSine sine1;

// The input signal detectors - create 2 detectors (one pair for each of the other 2 statues)
// We need NUM_STATUES-1 pairs of detectors
AudioAnalyzeToneDetect left_det_0; // First other statue
AudioAnalyzeToneDetect right_det_0;
AudioAnalyzeToneDetect left_det_1; // Second other statue
AudioAnalyzeToneDetect right_det_1;

// Arrays to hold detector pointers for easier access
AudioAnalyzeToneDetect *leftDetectors[NUM_STATUES - 1];
AudioAnalyzeToneDetect *rightDetectors[NUM_STATUES - 1];

// The mixer to use for audio sensing.
AudioMixer4 mixerSensingOutput;

// Connect the sine wave generator to sensing mixer.
AudioConnection patchCordM1L(sine1, 0, mixerSensingOutput, 0);

// Connect the audio input to all the detectors
AudioConnection patchCordL0(audioIn, 0, left_det_0, 0);
AudioConnection patchCordR0(audioIn, 1, right_det_0, 0);
AudioConnection patchCordL1(audioIn, 0, left_det_1, 0);
AudioConnection patchCordR1(audioIn, 1, right_det_1, 0);

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
  // NOTE: Increased for multiple detectors
  AudioMemory(30);

  // Add debug output for statue identity
  Serial.printf("Configuring Statue %c (%s)\n", THIS_STATUE_ID, MY_STATUE_NAME);
  Serial.printf("  TX Frequency: %d Hz\n", tx_freq);
  Serial.println("  RX Frequencies:");

  // Initialize detector arrays
  leftDetectors[0] = &left_det_0;
  rightDetectors[0] = &right_det_0;
  leftDetectors[1] = &left_det_1;
  rightDetectors[1] = &right_det_1;

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

  // Configure each detector for the appropriate frequency
  int detectorIndex = 0;
  for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
    if (statue_idx != MY_STATUE_INDEX) {
      int freq = STATUE_FREQUENCIES[statue_idx];
      int cycles = sample_time_ms * freq / 1000;
      leftDetectors[detectorIndex]->frequency(freq, cycles);
      rightDetectors[detectorIndex]->frequency(freq, cycles);
      Serial.printf("    Detector %d: %s at %dHz\n", detectorIndex,
                    STATUE_NAMES[statue_idx], freq);
      detectorIndex++;
    }
  }

  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(LED3_PIN, OUTPUT);

  // Configure sine generator to transmit THIS statue's frequency
  AudioNoInterrupts(); // disable audio library momentarily
  sine1.frequency(tx_freq);
  sine1.amplitude(1.0);
  AudioInterrupts(); // enable, tone will start
}

void debugPrintAudioSense(float l1, float r1) {
#ifdef DEBUG_PRINT
  Serial.print("Detecting ");
  Serial.print(rx_freq);
  Serial.print("Hz: L=");
  Serial.print(l1);
  Serial.print(", R=");
  Serial.print(r1);
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

// Get the linked state bitmask, buffering over ~100ms for stable readings.
uint8_t getStableLinkedMask() {
  // Send signal
  sine1.amplitude(1.0);

  // Static state for buffering per statue
  static uint8_t stableLinkedMask = 0;
  static unsigned long bufferStartTime[NUM_STATUES] = {0};
  static bool buffering[NUM_STATUES] = {false};

  uint8_t candidateLinkedMask = 0;

  // Check all detectors
  int detectorIndex = 0;
  for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
    if (statue_idx != MY_STATUE_INDEX) {
      float left = leftDetectors[detectorIndex]->read();
      float right = rightDetectors[detectorIndex]->read();

      bool isDetected = (left > thresh || right > thresh);
      if (isDetected) {
        candidateLinkedMask |= (1 << statue_idx);
      }

// Debug output for each detector
#ifdef DEBUG_PRINT
      if (isDetected) {
        Serial.printf("Detected %s: L=%.3f R=%.3f\n", STATUE_NAMES[statue_idx],
                      left, right);
      }
#endif

      // Handle buffering for this specific statue
      bool wasLinked = (stableLinkedMask & (1 << statue_idx)) != 0;
      bool nowLinked = (candidateLinkedMask & (1 << statue_idx)) != 0;

      if (!wasLinked && nowLinked) {
        // Immediate transition to Linked for quick contact latency
        stableLinkedMask |= (1 << statue_idx);
        buffering[statue_idx] = false;
        Serial.printf("Link detected: %s\n", STATUE_NAMES[statue_idx]);
      } else if (wasLinked && !nowLinked) {
        // Buffer transition to Unlinked
        if (!buffering[statue_idx]) {
          buffering[statue_idx] = true;
          bufferStartTime[statue_idx] = millis();
        } else if (millis() - bufferStartTime[statue_idx] >=
                   TRANSITION_BUFFER_MS) {
          // Finished buffering, unlink
          stableLinkedMask &= ~(1 << statue_idx);
          buffering[statue_idx] = false;
          Serial.printf("Link lost: %s\n", STATUE_NAMES[statue_idx]);
        }
      } else {
        // No transition needed
        buffering[statue_idx] = false;
      }

      detectorIndex++;
    }
  }

  return stableLinkedMask;
}

// Static state variables.
bool isInitialized = false;
uint8_t wasLinkedMask = 0;

// This function gets the contact state with multi-statue support.
ContactState getContactState() {
  ContactState state;

  // Get the current linked mask
  state.isLinkedMask = getStableLinkedMask();
  state.wasLinkedMask = wasLinkedMask;
  state.isInitialized = isInitialized;

  // Update our persistent state for next call.
  isInitialized = true;
  wasLinkedMask = state.isLinkedMask;

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

  // Print overall status
  if (state.isLinked()) {
    Serial.print("CONTACT with: ");
    bool first = true;
    for (int statue_idx = 0; statue_idx < NUM_STATUES; statue_idx++) {
      if (state.isLinkedTo(statue_idx)) {
        if (!first)
          Serial.print(", ");
        Serial.print(STATUE_NAMES[statue_idx]);
        first = false;
      }
    }
    Serial.println();
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
