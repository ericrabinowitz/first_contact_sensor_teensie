/*
AudioSense: The contact sensing and audio mixing logic.
*/

#ifndef AUDIO_SENSE_H
#define AUDIO_SENSE_H

#include <Audio.h>

// Bundle the state with multi-statue support.
struct ContactState {
  bool isInitialized;
  uint8_t wasLinkedMask; // Bitmask of previously connected statues
  uint8_t isLinkedMask;  // Bitmask of currently connected statues

  // Check if ANY statue is connected
  bool isLinked() const { return isLinkedMask != 0; }

  // Check if specific statue is connected (0-based index)
  bool isLinkedTo(int statueIndex) const {
    return (isLinkedMask & (1 << statueIndex)) != 0;
  }

  // Helper method returning whether the state changed.
  bool isUnchanged() const {
    return isInitialized && isLinkedMask == wasLinkedMask;
  }
};

// Prototypes for the contact sensing code.
void audioSenseSetup();
bool audioSenseLoop();
ContactState getContactState();
void printState(const ContactState &state);
void audioMusicSetup();
void setToneEnabled(bool enabled);
void updateDetectionThreshold(float threshold);
void updateAudioVolumes(float signalVolume, float musicVolume);
void updateMainPeriod(uint16_t periodMs);

// The audio out shared between the audio sensing and music player.
extern AudioOutputI2S audioOut;

#endif // AUDIO_SENSE_H
