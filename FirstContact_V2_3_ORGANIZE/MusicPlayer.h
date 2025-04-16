/*
MusicPlayer: Logic for playing songs.
*/

#ifndef MUSIC_PLAYER_H
#define MUSIC_PLAYER_H

#include "AudioSense.h"
#include <Audio.h>

typedef enum {
  MUSIC_STATE_NOT_STARTED,    // No music has started yet.
  MUSIC_STATE_PLAYING,        // Music is playing at normal volume.
  MUSIC_STATE_PAUSED,         // Music is playing but at lower volume.
  MUSIC_STATE_PAUSE_TIMEOUT,  // Music was paused but timeout occurred.
  MUSIC_STATE_PAUSE_FINISHED, // Music was paused and finished.
  MUSIC_STATE_FINISHED        // A song has finished playing.
} MusicState;

// Function prototypes for Music Player
MusicState getMusicState(bool isInitialized);
void musicPlayerSetup();
void pauseMusic();
void resumeMusic();
void stopMusic();
void advanceToNextSong();
const char *getCurrentSong(bool isLinked);
void playMusic(ContactState state);

#endif // MUSIC_PLAYER_H
