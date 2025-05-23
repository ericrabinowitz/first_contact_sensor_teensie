/*
MusicPlayer: Logic for playing songs.
*/

#include "AudioSense.h"
#include "MusicPlayer.h"

#include <Audio.h>
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

// Active songs array.
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
    "Missing Link unSCruz active 12 Purple Disco All My Life.wav",
};

// Dormant songs array.
const char *idleSongs[] = {"Missing Link dormant Eros.wav",
                           "Missing Link dormant Electra.wav"};

// Current song index
unsigned int currentSongIndex = 0;
unsigned int currentIdleSongIndex = 0;

// Rename isPaused to isFading and pauseStartTime to fadeStartTime
bool isFading;
unsigned long fadeStartTime;

#define NUM_CONTACT_SONGS (sizeof(contactSongs) / sizeof(contactSongs[0]))
#define NUM_IDLE_SONGS (sizeof(idleSongs) / sizeof(idleSongs[0]))
#define PLAYING_MUSIC_VOLUME 1.0
#define FADE_MUSIC_INIT_VOLUME 0.15
#define PAUSE_TIMEOUT_MS 2000
#define IDLE_OUT_TIMEOUT_MS 10000 // new 10s idle-out

static unsigned long idleOutStartTime = 0;    // new
static bool idleOutTimerStarted = false;      // new

// The wav player interface.
AudioPlaySdWav playSdWav1;
// The music mixer, used to adjust music volume before sending to audio output.
AudioMixer4 mixerMusicOutput;
// Have them both go to the right mixer.
AudioConnection patchCord11(playSdWav1, 0, mixerMusicOutput, 2);
// Left channel (music player) plays on the right audio out channel.
AudioConnection patchCordMOR(mixerMusicOutput, 0, audioOut, 1);

void musicPlayerSetup() {
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

void fadeMusic() {
  if (!isFading && playSdWav1.isPlaying()) {
    isFading = true;
    fadeStartTime = millis(); // Record when fading started
    Serial.println("Music fading (ramping down volume)");
  }
}

void resumeMusic() {
  if (isFading && playSdWav1.isPlaying()) {
    // Restore volume
    // TODO: ramp volume back up?
    setMusicVolume(PLAYING_MUSIC_VOLUME);

    isFading = false;
    Serial.println("Music resumed (volume restored)");
  } else {
    Serial.println("Music is not fading or not playing");
  }
}

void stopMusic() {
  if (playSdWav1.isPlaying()) {
    playSdWav1.stop();
  }
}
void queueNextActiveSong() {
  Serial.println("Song finished. Advancing to next active song.");
  currentSongIndex = (currentSongIndex + 1) % NUM_CONTACT_SONGS;
  Serial.print("Next active song will be: ");
  Serial.println(contactSongs[currentSongIndex]);
}

void queueNextIdleSong() {
  Serial.println("Idle song finished. Looping to next idle song.");
  currentIdleSongIndex = (currentIdleSongIndex + 1) % NUM_IDLE_SONGS;
  Serial.print("Next idle song will be: ");
  Serial.println(idleSongs[currentIdleSongIndex]);
}

// Helper function to get the current song to play.
const char *getCurrentSong(bool isLinked) {
  if (isLinked) {
    return contactSongs[currentSongIndex];
  } else {
    return idleSongs[currentIdleSongIndex];
  }
}

// Helper function to determine the current state of music playback
MusicState getMusicState(ContactState state) {
  if (!state.isInitialized) {
    return MUSIC_STATE_NOT_STARTED;
  }

  if (state.isLinked) {
    // Reset idle-out timer when entering active state. Each transition to
    // an unlinked or paused state starts a new idle-out timer.
  }

  if (isFading) {
    // still within the fading window?
    if (millis() - fadeStartTime <= PAUSE_TIMEOUT_MS) {
      // if playback stopped while fading, treat as finished
      if (!playSdWav1.isPlaying()) {
        return MUSIC_STATE_FADE_FINISHED;
      }
      return MUSIC_STATE_FADING;
    }
    // Fading has timed out → start idle-out timer.
    if (!idleOutTimerStarted) {
      idleOutTimerStarted = true;
      idleOutStartTime = millis();
    }
    return MUSIC_STATE_FADE_TIMEOUT;
  }

  // once pause-timeout was set, after 30 s of idle play, enter idle-out
  if (idleOutTimerStarted
      && (millis() - idleOutStartTime >= IDLE_OUT_TIMEOUT_MS)
    ) {
    // Reset the idle out timer, to take action (e.g. queue next song) only once.
    idleOutTimerStarted = false;
    return MUSIC_STATE_RECENT_CONNECTION_IDLE_OUT;
  }

  if (!playSdWav1.isPlaying()) {
    return MUSIC_STATE_FINISHED;
  }
  return MUSIC_STATE_PLAYING;
}

// New helper: updates volume based on fade logic during fade.
void updateFadedVolume(bool isLinked) {
  // TODO: Move this logic into ContactState for sharing with lights?
  // Check if we are fading and not linked. If we're linked, it means
  // we're in the process of resuming a song.
  if (isFading && !isLinked && playSdWav1.isPlaying()) {
    unsigned long elapsed = millis() - fadeStartTime;
    float fraction = elapsed / (float)PAUSE_TIMEOUT_MS;
    if (fraction > 1.0)
      fraction = 1.0;
    float newVolume = FADE_MUSIC_INIT_VOLUME * (1.0 - fraction);
    setMusicVolume(newVolume);

    // Print the volume only if it has changed significantly.
    // This is to avoid flooding the serial output with too many messages.
    static int lastSigVolume = -1;
    int currentSig = (int)(newVolume * 10);
    if (currentSig != lastSigVolume) {
      lastSigVolume = currentSig;
      Serial.print("Fading volume to ");
      Serial.println(newVolume);
    }
  }
}

static void handleFadeComplete() {
  stopMusic();
  queueNextIdleSong();
  // Reset isFading since we're stopping the song.
  isFading = false;
  // Also reset the volume to the default.
  setMusicVolume(PLAYING_MUSIC_VOLUME);
}

/* Play Audio Based On State */
void playMusic(ContactState state) {
  MusicState musicState = getMusicState(state);

  // State transition: Connected -> Disconnected.
  if (state.wasLinked && !state.isLinked) {
    fadeMusic();
  }
  // State transition: Disconnected -> Connected.
  else if (!state.wasLinked && state.isLinked) {
    if (musicState == MUSIC_STATE_FADING) {
      // If we were fading (previous disconnect), resume playback
      Serial.println("Resuming faded music");
      resumeMusic();
    } else if (musicState == MUSIC_STATE_PLAYING) {
      // If we weren't fading, stop any currently playing song.
      // This is expected to be the idle song.
      Serial.println("Stopping current song to play contact song");
      stopMusic();
    }
  }

  // Handle fade timeout and finished states.
  switch (musicState) {
  case MUSIC_STATE_RECENT_CONNECTION_IDLE_OUT:
    Serial.println("Recent connection idled out. Queuing next active song.");
    queueNextActiveSong();
    break;
  case MUSIC_STATE_FADE_TIMEOUT:
    Serial.println("Fade timed out. Switching to dormant music.");
    handleFadeComplete();
    break;
  case MUSIC_STATE_FADE_FINISHED:
    Serial.println("Song finished while fading. Stopping and switching to dormant.");
    handleFadeComplete();
    // Queue the next active song, because the song finished.
    queueNextActiveSong();
    break;
  case MUSIC_STATE_FINISHED:
    if (state.isLinked) {
      queueNextActiveSong();
    } else {
      queueNextIdleSong();
    }
    break;
  case MUSIC_STATE_FADING:
    // Update the faded volume based on the elapsed time.
    updateFadedVolume(state.isLinked);
    break;
  default:
    // No action needed for other states.
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

void setMusicVolume(float volume) {
  // Adjust the gain on the music output mixer channel (channel 2)
  mixerMusicOutput.gain(2, volume);
}
