#ifndef AUDIO_SENSE_H
#define AUDIO_SENSE_H

// Prototypes for the contact sensing code.
void audioSenseSetup();
bool audioSenseLoop();
bool getStableIsLinked();
void printState(bool isInitialized, bool wasLinked, bool isLinked);
void audioMusicSetup();

typedef enum {
  MUSIC_STATE_NOT_STARTED,    // No music has started yet.
  MUSIC_STATE_PLAYING,        // Music is playing at normal volume.
  MUSIC_STATE_PAUSED,         // Music is playing but at lower volume.
  MUSIC_STATE_PAUSE_TIMEOUT,  // Music was paused but timeout occurred.
  MUSIC_STATE_PAUSE_FINISHED, // Music was paused and finished.
  MUSIC_STATE_FINISHED        // A song has finished playing.
} MusicState;

// Prototypes for the music player code.
MusicState getMusicState(unsigned int init);
void playMusic(bool isInitialized, bool wasLinked, bool isLinked);
void stopMusic();
void pauseMusic();
void resumeMusic();
void advanceToNextSong();
const char *getCurrentSong(bool isLinked);

#endif // AUDIO_SENSE_H
