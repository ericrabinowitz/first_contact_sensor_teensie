#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastgoertzel", "numpy", "sounddevice", "soundfile"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./tone_detect_test.py

import os
import threading
import time
import sys

# Add parent directory to path for imports
sys.path.append('../')

import fastgoertzel as G
import numpy as np
import sounddevice as sd

# Import device configuration from audio module
from audio.devices import Statue, dynConfig, configure_devices
from audio.music import play_audio


# TODOs
# How to support multiple detection channels? goertzel is only efficient for a
# limited number of frequencies. The Pi is limited to 4 cores, 1 thread/core.

# ### Reference docs
# https://python-sounddevice.readthedocs.io/en/0.5.1/usage.html
# https://docs.scipy.org/doc/scipy/reference/signal.html
# https://pypi.org/project/fastgoertzel/
# https://arlpy.readthedocs.io/en/latest/signal.html


AUDIO_JACK = "bcm2835 headphones"

# Non-harmonizing frequencies selected to avoid ratios like 2:1, 3:2, 4:3, 5:4
# These are based on prime numbers and spaced 20-35% apart for clear distinction
tones_hz = {
    Statue.EROS: 1789,      # Prime-based
    Statue.ELEKTRA: 2357,   # Prime-based
    Statue.SOPHIA: 3181,    # Prime-based
    Statue.ULTIMO: 4231,    # Avoiding harmonics
    Statue.ARIEL: 7040,     # Prime-based. Skip 5639 which has issues.
}
tone_streams = {}


class LinkStateTracker:
    """Tracks link states between statues and detects changes."""

    def __init__(self):
        # Track which statues are linked to which
        self.links = {}  # {statue: set(linked_statues)}
        # Track link state for each statue (any links at all)
        self.has_links = {}  # {statue: bool}
        # Initialize all statues as unlinked
        for statue in Statue:
            self.links[statue] = set()
            self.has_links[statue] = False

    def update_link(self, detector_statue, source_statue, is_linked):
        """
        Update link state and return True if state changed.
        Links are bidirectional.
        """
        changed = False

        if is_linked:
            # Add link if not already present
            if source_statue not in self.links[detector_statue]:
                self.links[detector_statue].add(source_statue)
                self.links[source_statue].add(detector_statue)
                changed = True
                print(f"🔗 Link established: {detector_statue.value} ↔ {source_statue.value}")
        else:
            # Remove link if present
            if source_statue in self.links[detector_statue]:
                self.links[detector_statue].remove(source_statue)
                self.links[source_statue].remove(detector_statue)
                changed = True
                print(f"🔌 Link broken: {detector_statue.value} ↔ {source_statue.value}")

        # Update has_links status
        old_has_links_detector = self.has_links[detector_statue]
        old_has_links_source = self.has_links[source_statue]

        self.has_links[detector_statue] = len(self.links[detector_statue]) > 0
        self.has_links[source_statue] = len(self.links[source_statue]) > 0

        # Check if overall link status changed
        if old_has_links_detector != self.has_links[detector_statue]:
            status = "linked" if self.has_links[detector_statue] else "unlinked"
            print(f"  → {detector_statue.value} is now {status}")
            changed = True

        if old_has_links_source != self.has_links[source_statue]:
            status = "linked" if self.has_links[source_statue] else "unlinked"
            print(f"  → {source_statue.value} is now {status}")
            changed = True

        return changed

    def get_link_summary(self):
        """Return human-readable link summary."""
        summary = []
        summary.append("=== Current Link Status ===")

        # Show linked statues
        linked = [s for s in Statue if self.has_links[s]]
        unlinked = [s for s in Statue if not self.has_links[s]]

        if linked:
            summary.append("Linked statues:")
            for statue in linked:
                linked_to = ", ".join([s.value for s in self.links[statue]])
                summary.append(f"  {statue.value} ↔ {linked_to}")

        if unlinked:
            summary.append("Unlinked statues:")
            summary.append("  " + ", ".join([s.value for s in unlinked]))

        return "\n".join(summary)


# Global link state tracker
link_tracker = LinkStateTracker()


# Device configuration is now imported from audio.devices module


# def play_tone(statue):
#     config = dynConfig[statue.value]["tone"]
#     freq = dynConfig[statue.value]["tone_freq"]
#     print(f"Playing a {freq} Hz tone for the {statue.value} statue")

#     # Generate a time array and sine wave
#     duration = 60  # seconds
#     t = np.linspace(0, duration, int(config["sample_rate"] * duration), False)
#     tone = np.sin(2 * np.pi * freq * t)
#     tone = tone.astype(np.float32)

#     try:
#         sd.play(
#             device=config["device_id"],
#             data=tone,
#             samplerate=config["sample_rate"],
#             mapping=[config["channel"]],
#             blocking=True,
#             loop=True,
#         )
#     except KeyboardInterrupt:
#         sd.stop()
#         print("Playback stopped")
#     except Exception as e:
#         print(e)


def play_tone(statue):
    config = dynConfig[statue.value]["tone"]
    freq = dynConfig[statue.value]["tone_freq"]

    if config["device_index"] == -1:
        print(f"WARNING: No output device configured for {statue.value}")
        return

    channel_name = "left" if config["channel"] == 0 else "right"
    print(f"Playing {freq}Hz tone for {statue.value} on device {config['device_index']} ({channel_name} channel)")

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        t = (np.arange(frames) + callback.phase) / config["sample_rate"]
        # Generate sine wave for stereo output with specific channel
        sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)

        # Route to specific channel: 0=left (tip), 1=right (ring)
        if config["channel"] == 0:  # Left channel (TRS tip)
            outdata[:, 0] = sine_wave
            outdata[:, 1] = 0  # Silence right channel
        else:  # Right channel (TRS ring)
            outdata[:, 0] = 0  # Silence left channel
            outdata[:, 1] = sine_wave

        callback.phase = (callback.phase + frames) % config["sample_rate"]

    callback.phase = 0

    # Create and start the output stream
    stream = sd.OutputStream(
        device=config["device_index"],
        channels=2,  # Stereo output (required to route to specific channel)
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
        callback=callback
    )

    tone_streams[statue.value] = stream
    stream.start()
    print(f"✓ Tone stream started for {statue.value} on channel {config['channel']}")



def detect_tone(statue, other_statues):
    config = dynConfig[statue.value]["detect"]  # Use detect config, not tone

    if config["device_index"] == -1:
        print(f"WARNING: No input device configured for {statue.value}")
        return

    freqs = [dynConfig[s.value]["tone_freq"] for s in other_statues]
    print(f"{statue.value} listening for tones {freqs}Hz on device {config['device_index']}")

    stream = sd.InputStream(
        device=config["device_index"],
        channels=1,  # Mono input
        samplerate=config["sample_rate"],
        blocksize=dynConfig["block_size"],
    )

    stream.start()
    print(f"✓ Detection started for {statue.value}")

    # Track current detection state for each statue
    detection_state = {s: False for s in other_statues}

    # Detect tones using the Goertzel algorithm
    while True:
        try:
            audio, overflowed = stream.read(dynConfig["block_size"])
            if overflowed:
                print("Input overflow!")

            # Convert to float64 for Goertzel
            audio_data = audio[:, 0].astype(np.float64)

            # Check for each other statue's tone
            for s in other_statues:
                freq = dynConfig[s.value]["tone_freq"]
                normalized_freq = freq / config["sample_rate"]
                level, _ = G.goertzel(audio_data, normalized_freq)

                # Determine if currently detected
                currently_detected = level > dynConfig["touch_threshold"]

                # Check if state changed
                if currently_detected != detection_state[s]:
                    detection_state[s] = currently_detected
                    # Update link tracker (handles printing)
                    link_tracker.update_link(statue, s, currently_detected)

                    # Future: This is where we would trigger audio changes
                    # based on link_tracker.has_links[statue]

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in detection: {e}")
            break

    stream.stop()
    stream.close()
    print(f"Detection stopped for {statue.value}")


def play_and_detect_tones(devices):
    """
    Start tone generation and detection for all configured statues.
    Each statue plays its unique tone and detects all other statue tones.
    """
    print("\nStarting tone generation and detection...")
    print(f"Configured statues: {[dev['statue'].value for dev in devices]}")

    # Get list of configured statues
    configured_statues = [dev['statue'] for dev in devices]

    # Start tone generation for all configured statues
    print("\nStarting tone generators:")
    for statue in configured_statues:
        if dynConfig[statue.value]["tone"]["device_index"] != -1:
            play_tone(statue)

    # Small delay to ensure all tones are playing
    time.sleep(0.5)

    # Start detection threads for statues with input capability
    print("\nStarting detection threads:")
    detection_threads = []

    for statue in configured_statues:
        if dynConfig[statue.value]["detect"]["device_index"] != -1:
            # Each statue detects all other statues
            other_statues = [s for s in configured_statues if s != statue]
            if other_statues:
                thread = threading.Thread(
                    target=detect_tone,
                    args=(statue, other_statues),
                    daemon=True,
                    name=f"detect_{statue.value}"
                )
                detection_threads.append(thread)
                thread.start()

    print(f"\n{len(detection_threads)} detection thread(s) started")
    print("\nMonitoring for connections... Press Ctrl+C to stop")

    # Print initial status
    time.sleep(1)
    print("\n" + link_tracker.get_link_summary())


if __name__ == "__main__":
    print("=== Missing Link Tone Detection Test ===")
    print("Press Ctrl+C to stop\n")

    devices = configure_devices(max_devices=5)  # Configure up to 5 devices for all statues
    if not devices:
        print("Device configuration failed!")
        exit(1)

    # Set tone frequencies for all configured devices
    for device in devices:
        statue = device['statue']
        if statue in tones_hz:
            dynConfig[statue.value]["tone_freq"] = tones_hz[statue]

    if dynConfig["debug"]:
        print(f"\nTone frequencies configured:")
        for device in devices:
            statue = device['statue']
            freq = dynConfig[statue.value].get('tone_freq', -1)
            if freq > 0:
                print(f"  {statue.value.upper()}: {freq}Hz")

    play_and_detect_tones(devices)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        # Close all tone streams
        for stream in tone_streams.values():
            stream.stop()
            stream.close()
        time.sleep(0.5)
        print("Done")
