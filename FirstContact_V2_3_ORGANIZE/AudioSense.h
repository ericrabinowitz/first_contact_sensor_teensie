#ifndef AUDIO_SENSE_H
#define AUDIO_SENSE_H

#include <Audio.h>

// Prototypes for the contact sensing code.
void audioSenseSetup();
bool audioSenseLoop();
bool getStableIsLinked();
void printState(bool isInitialized, bool wasLinked, bool isLinked);
void audioMusicSetup();

// Make playSdWav1 addressable from other files.
extern AudioPlaySdWav playSdWav1;

#endif // AUDIO_SENSE_H
