#include <Adafruit_SSD1306.h>
#include <Audio.h>
#include <SD.h>
#include <SPI.h>
#include <SerialFlash.h>
#include <Wire.h>

#include "AudioSense.h"

/* I Added these files to the MicroSd Card */

char file[][40]{
    "Formant Squish2.wav",
    "fire.wav",
    "venus.wav",
    "mars.wav",
    "hold_on.wav",
    "thats_it.wav",
    "connected.wav",
    "disconnected.wav",
    "0.wav",
    "1.wav",
    "2.wav",
    "3.wav",
    "4.wav",
    "5.wav",
    "6.wav",
    "7.wav",
    "8.wav",
    "9.wav",
    "10.wav",
    "comeon.wav",
    "come_here.wav",
    "are_you_from.wav",
    "commander2.wav",
    "standing_by2.wav",
    "Alternating Harmonics2.wav",
    "sample_022.wav",
    "Formant Squish2.wav",
    "Hollow Distorted FM2.wav",
    "wow.wav",
    "feelsreallygood.wav",
    "feelsgood.wav",
    "Missing Link Electra dormant with background.wav",
    "Missing Link Eros dormant.wav",
};
#define MAX_FILES 31

// Audio Files used for Contact and Idle States
//
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
#define NUM_CONTACT_SONGS (sizeof(contactSongs) / sizeof(contactSongs[0]))

// Current song index
unsigned int currentSongIndex = 0;

// Audio Playa Date End

// ------ Audio SD Card Start
//
// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN BUILTIN_SDCARD
#define SDCARD_MOSI_PIN 11 // not actually used
#define SDCARD_SCK_PIN 13  // not actually used

// Music player states

//
// ------ Audio SD Card End

// ------ Audio Contact Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5

//
// Frequencies to Transmit and listen for through hands (f_1 and f_2 are the tx frequencies)
const int f_1 = 20;
const int f_2 = 20;
const int f_3 = 20;
const int f_4 = 20;

// This is the tone dection sensitivity.  Currently set for maximum sensitivity.
// Edit with caution and experimentation.
float thresh = 0.01;

// GUItool: begin automatically generated code
//AudioSynthWaveformSine   sine2;          //xy=190.99998474121094,122.99998474121094
AudioInputI2S audioIn;        //xy=192.99998474121094,369
AudioSynthWaveformSine sine1; //xy=207.99998474121094,60.99998474121094

/*
AudioAnalyzeToneDetect   right_f_4; //xy=466.20001220703125,575.2000122070312
AudioAnalyzeToneDetect   right_f_3;        //xy=467,540
AudioAnalyzeToneDetect   right_f_2;        //xy=471,502
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_4;           //xy=474,384
AudioAnalyzeToneDetect   left_f_3;           //xy=475,348
AudioAnalyzeToneDetect   left_f_2;           //xy=477,313
*/
AudioAnalyzeToneDetect right_f_1; //xy=472,464
AudioAnalyzeToneDetect left_f_1;  //xy=483,276
AudioOutputI2S audioOut;          //xy=711,92.99998474121094
AudioMixer4 mixerRight;
AudioMixer4 mixerLeft;

AudioConnection patchCordM1L(sine1, 0, mixerLeft, 0);
//AudioConnection          patchCordM1R(sine1, 0, mixerRight, 0);

//AudioConnection          patchCordM2L(sine2, 0, mixerLeft, 1);
//AudioConnection          patchCordM2R(sine2, 0, mixerRight, 1);

//
// Audio Player
AudioPlaySdWav playSdWav1;
AudioConnection patchCord11(playSdWav1, 0, mixerLeft, 2);
AudioConnection patchCord12(playSdWav1, 1, mixerRight, 2);
// Audio Player
//

AudioConnection patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection patchCord6(audioIn, 1, right_f_1, 0);
/*
AudioConnection          patchCord3(audioIn, 0, left_f_2, 0);
AudioConnection          patchCord4(audioIn, 0, left_f_3, 0);
AudioConnection          patchCord5(audioIn, 0, left_f_4, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
AudioConnection          patchCord7(audioIn, 1, right_f_2, 0);
AudioConnection          patchCord8(audioIn, 1, right_f_3, 0);
AudioConnection          patchCord9(audioIn, 1, right_f_4, 0);
*/

AudioConnection patchCordMOL(mixerLeft, 0, audioOut, 0);
AudioConnection patchCordMOR(mixerRight, 0, audioOut, 1);

AudioControlSGTL5000 audioShield; //xy=709,177.99998474121094

elapsedMillis since_main = 0;
uint16_t main_period_ms = 150;
// ------ Audio Contact Defines - End

// Audio

// Volume
#define PLAYING_AUDIO_VOLUME 0.75
#define PAUSED_AUDIO_VOLUME 0.4

// Define pause timeout duration in milliseconds
#define PAUSE_TIMEOUT_MS 2000 // 2 seconds pause timeout

// Whether audio is 'paused' i.e. low volume.
bool isPaused = false;

// Variable to track when pausing started
unsigned long pauseStartTime = 0;

// Helper function to determine the current state of music playback
MusicState getMusicState(unsigned int init) {
  if (init == 0) {
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

// Contact Sense Start
//
void audioSenseSetup() {
  // NOTE this number is simply a guess.
  // Working: 12 for Sens, 8 for Wav Player + margin.
  AudioMemory(22);

  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  // AudioMemory(12 + 8); // 12 for Sens, 8 for Wav Player

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(PLAYING_AUDIO_VOLUME);

  // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.

  const int sample_time_ms = main_period_ms / 2;

  left_f_1.frequency(f_1, sample_time_ms * f_1 / 1000); //(1209, 36);
  /*
  left_f_2.frequency(f_2,  sample_time_ms*f_2/1000);
  left_f_3.frequency(f_3,  sample_time_ms*f_3/1000);
  left_f_4.frequency(f_4,  sample_time_ms*f_4/1000);
  */
  // Assuming the calcs get optimized out.
  right_f_1.frequency(f_1, sample_time_ms * f_1 / 1000);
  /*
  right_f_2.frequency(f_2, sample_time_ms*f_2/1000);
  right_f_3.frequency(f_3, sample_time_ms*f_3/1000);
  right_f_4.frequency(f_4, sample_time_ms*f_4/1000);
*/
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

// Contact Sense End
//

//
// Music Player Start

void audioMusicSetup() {
  //audioMemory(8); // NOTE:   This memory allocation should be combined with Audio Sense Setup
  //audioShield.enable();
  //audioShield.volume(0.5);

  //
  // Setup the SPI driver for MicroSd Card
  // Our project uses the on board MicroSd, NOT the AudioShield's MicroSd slot
  //
  SPI.setMOSI(SDCARD_MOSI_PIN);
  SPI.setSCK(SDCARD_SCK_PIN);
  if (!(SD.begin(SDCARD_CS_PIN))) {
    while (1) {
      Serial.println("Unable to access the SD card");
      delay(500);
    }
  }
  // delay(1000); XXX 1
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

/* Play Audio Based On State */
void playMusic(bool isInitialized, bool wasLinked, bool isLinked) {
  MusicState musicState = getMusicState(isInitialized);

  // State transition: Connected -> Disconnected.
  if (wasLinked && !isLinked) {
    pauseMusic();
  }

  // State transition: Disconnected -> Connected.
  else if (!wasLinked && isLinked) {
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
    if (isLinked) {
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

  // Nothing is playing - figure out what to play next
  if (!playSdWav1.isPlaying()) {
    // Start the appropriate song.
    Serial.print("Starting song: ");
    const char *songToPlay = getCurrentSong(isLinked);
    Serial.println(songToPlay);

    if (!playSdWav1.play(songToPlay)) {
      Serial.print("Error playing: ");
      Serial.println(songToPlay);
    }
  }
}
// Music Player End
//

/*
  printState() - Print the contact state to the serial console
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void printState(bool isInitialized, bool wasLinked, bool isLinked) {
  if (isInitialized && wasLinked == isLinked) {
    return;
  }

  if (isLinked) {
    Serial.print("CONTACT\n");
  } else {
    Serial.print("--OFF---\n");
  }

  //uncomment these lines to see how much CPU time
  //the tone detectors and audio library are using

  Serial.print("CPU=");
  Serial.print(AudioProcessorUsage());
  Serial.print("%, max=");
  Serial.print(AudioProcessorUsageMax());
  Serial.print("%   ");
  Serial.print("\n");
}