/*
AudioSense: The contact sensing and audio mixing logic.
*/

#ifndef AUDIO_SENSE_H
#define AUDIO_SENSE_H

#include <Audio.h>

// Bundle the state booleans in a struct.
struct ContactState {
  bool isInitialized;
  bool wasLinked;
  bool isLinked;
  // Helper method returning whether the state changed.
  bool isUnchanged() const { return isInitialized && isLinked == wasLinked; }
};

// Prototypes for the contact sensing code.
void audioSenseSetup();
bool audioSenseLoop();
ContactState getContactState();
void printState(const ContactState &state);
void audioMusicSetup();

// Make playSdWav1 addressable from other files.
extern AudioPlaySdWav playSdWav1;

#endif // AUDIO_SENSE_H
