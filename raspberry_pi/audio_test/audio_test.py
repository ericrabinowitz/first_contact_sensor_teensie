#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["just-playback"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./audio_test.py

import os
import time

from just_playback import Playback


# ### Reference docs
# https://github.com/cheofusi/just_playback


# Folder for audio files
SONG_DIR = "/run/audio_files"


def play_song(songFile: str):
    path = os.path.join(SONG_DIR, songFile)
    if not songFile.endswith(".wav"):
        raise Exception(f"Error: '{path}' is not a valid .wav file.")
    if not os.path.isfile(path):
        raise Exception(f"Error: '{path}' is not a valid file.")

    # Manages playback of a single audio file
    playback = Playback(path)
    playback.loop_at_end(True)
    playback.set_volume(1.0)
    print(f"Playing {path}...")
    playback.play()

    time.sleep(5)
    playback.pause()
    time.sleep(2)
    playback.resume()
    time.sleep(5)
    playback.stop()
    print("stopped playing")


if __name__ == "__main__":
    play_song("Missing Link unSCruz active 01 Remi Wolf Polo Pan Hello.wav")
