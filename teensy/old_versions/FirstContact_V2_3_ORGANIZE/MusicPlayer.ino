/*
MusicPlayer: Logic for playing songs.
*/

#include "AudioSense.h"
#include "MusicPlayer.h"
#include <SD.h>
#include <SPI.h>
#include <SerialFlash.h>
#include <Wire.h>

// Audio Playa Date End

// ------ Audio SD Card Start
//
// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN BUILTIN_SDCARD
#define SDCARD_MOSI_PIN 11 // not actually used
#define SDCARD_SCK_PIN 13  // not actually used

// Audio Files used for Contact and Idle States
#ifdef TEST_CONNECTION_ENABLE
#define SONG_NAME_IDLE "disconnected.wav"
// #define SONG_NAME_CONTACT "connected.wav" - removing this as we'll use an array instead
#else
#define SONG_NAME_IDLE "Missing Link Electra dormant with background.wav"
// #define SONG_NAME_CONTACT "eros_active1.wav" - removing this as we'll use an array instead
#endif

// Contact songs array.
const char *contactSongs[] = {
    "Missing Link unSCruz active 1 Remi Wolf Polo Pan Hello.wav",
    "Missing Link unSCruz active 2 MarchForth Gospel A.wav",
    "Missing Link unSCruz active 3 Saint Motel My Type A.wav",
    "Missing Link unSCruz active 4 Seth Lakeman Lady of the Sea 2.wav",
    "Missing Link unSCruz active 5 Jacques Greene Another Girl.wav",
    "Missing Link unSCruz active 6 Chrome Sparks Goddess.wav",
    "Missing Link unSCruz active 7 Jet Are You Gonna Be.wav",
    "Missing Link unSCruz active 8 M83 Midnight City Prydz.wav",
    "Missing Link unSCruz active 9 Flume The Difference.wav",
    "Missing Link unSCruz active 10 Doldinger Bastian.wav",
    "Missing Link unSCruz active 11 Yung Bae Straight Up.wav",
    "Missing Link unSCruz active 12 Purple Disco All My Life.wav"};

// Current song index
unsigned int currentSongIndex = 0;
//AudioPlaySdWav playSdWav1;
AudioControlSGTL5000 audioShield;
bool isPaused;
unsigned long pauseStartTime;

#define NUM_CONTACT_SONGS (sizeof(contactSongs) / sizeof(contactSongs[0]))
#define PLAYING_AUDIO_VOLUME 0.75
#define PAUSED_AUDIO_VOLUME 0.4
#define PAUSE_TIMEOUT_MS 2000
//
// Music Player Start

void musicPlayerSetup() {
  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  // AudioMemory(12 + 8); // 12 for Sens, 8 for Wav Player

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(PLAYING_AUDIO_VOLUME);
  //audioMemory(8); // NOTE:   This memory allocation should be combined with Audio Sense Setup
  //audioShield.enable();
  //audioShield.volume(0.5);

  // Setup the SPI driver for MicroSd Card
  // Our project uses the on board MicroSd, NOT the AudioShield's MicroSd slot
  SPI.setMOSI(SDCARD_MOSI_PIN);
  SPI.setSCK(SDCARD_SCK_PIN);
  if (!(SD.begin(SDCARD_CS_PIN))) {
    while (1) {
      Serial.println("Unable to access the SD card");
      delay(500);
    }
  }
}

void pauseMusic() {
  if (!isPaused && playSdWav1.isPlaying()) {
    // Set volume to zero (mute) but keep playing
    audioShield.volume(PAUSED_AUDIO_VOLUME);

    isPaused = true;
    pauseStartTime = millis(); // Record when pausing started
    Serial.println("Music paused (volume minimized)");
  }
}

void resumeMusic() {
  if (isPaused && playSdWav1.isPlaying()) {
    // Restore volume
    audioShield.volume(PLAYING_AUDIO_VOLUME);

    isPaused = false;
    Serial.println("Music resumed (volume restored)");
  } else {
    Serial.println("Music is not paused or not playing");
  }
}

void stopMusic() {
  if (playSdWav1.isPlaying()) {
    playSdWav1.stop();
  }
}

void advanceToNextSong() {
  // Advance to next song
  currentSongIndex = (currentSongIndex + 1) % NUM_CONTACT_SONGS;
  Serial.print("Next song will be: ");
  Serial.println(contactSongs[currentSongIndex]);
}

// Helper function to get the current song to play.
const char *getCurrentSong(bool isLinked) {
  if (isLinked) {
    return contactSongs[currentSongIndex];
  } else {
    return SONG_NAME_IDLE;
  }
}

// Helper function to determine the current state of music playback
MusicState getMusicState(bool isInitialized) {
  if (!isInitialized) {
    return MUSIC_STATE_NOT_STARTED;
  }
  if (isPaused) {
    // Check if pause has timed out
    if (millis() - pauseStartTime > PAUSE_TIMEOUT_MS) {
      Serial.println("Music paused timeout.");
      return MUSIC_STATE_PAUSE_TIMEOUT;
    } else if (!playSdWav1.isPlaying()) {
      // If music is paused but not playing it ended while paused.
      // Treat it as timed out.
      Serial.println("Music ended while paused.");
      return MUSIC_STATE_PAUSE_FINISHED;
    }
    return MUSIC_STATE_PAUSED;
  }

  if (!playSdWav1.isPlaying()) {
    return MUSIC_STATE_FINISHED;
  }

  return MUSIC_STATE_PLAYING;
}

/* Play Audio Based On State */
void playMusic(ContactState state) {
  MusicState musicState = getMusicState(state.isInitialized);

  // State transition: Connected -> Disconnected.
  if (state.wasLinked && !state.isLinked) {
    pauseMusic();
  }
  // State transition: Disconnected -> Connected.
  else if (!state.wasLinked && state.isLinked) {
    if (musicState == MUSIC_STATE_PAUSED) {
      // If we were paused (previous disconnect), resume playback
      Serial.println("Resuming paused music");
      resumeMusic();
    } else if (musicState == MUSIC_STATE_PLAYING) {
      // If we weren't paused, stop any currently playing song.
      // This is expected to be the idle song.
      Serial.println("Stopping current song to play contact song");
      stopMusic();
    }
  }

  // Handle pause timeout and finished states.
  switch (musicState) {
  case MUSIC_STATE_PAUSE_TIMEOUT:
  case MUSIC_STATE_PAUSE_FINISHED:
    Serial.println("Pause timed out. Stopping song to switch to dormant.");
    stopMusic();
    advanceToNextSong();

    // Reset isPaused since we're stopping the song
    isPaused = false;
    // Also reset the volume to the default
    audioShield.volume(PLAYING_AUDIO_VOLUME);
    break;
  case MUSIC_STATE_FINISHED:
    if (state.isLinked) {
      Serial.println("Song finished. Advancing to next song.");
      advanceToNextSong();
    } else {
      Serial.println("Idle song finished. Looping.");
    }
    break;
  default:
    // No action needed for other states
    break;
  }

  // Nothing is playing - start the appropriate song.
  if (!playSdWav1.isPlaying()) {
    // Start the appropriate song.
    Serial.print("Starting song: ");
    const char *songToPlay = getCurrentSong(state.isLinked);
    Serial.println(songToPlay);
    if (!playSdWav1.play(songToPlay)) {
      Serial.print("Error playing: ");
      Serial.println(songToPlay);
    }
  }
}
// Music Player End
