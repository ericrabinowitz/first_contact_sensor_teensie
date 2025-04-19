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

// The audio out shared between the audio sensing and music player.
extern AudioOutputI2S audioOut;

#endif // AUDIO_SENSE_H
