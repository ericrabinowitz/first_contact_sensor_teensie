#!/usr/bin/env python3
"""
Audio playback module for Missing Link project.
Handles WAV file playback with channel routing for statue audio output.
"""

import threading
import time
import numpy as np
import sounddevice as sd
from .devices import dynConfig, get_audio_devices


def play_audio(statue, audio_file):
    """Play a WAV file on the audio channel for the specified statue."""
    config = dynConfig[statue.value]["audio"]

    if config["device_index"] == -1:
        print(f"WARNING: No audio device configured for {statue.value}")
        return

    channel_name = "left" if config["channel"] == 0 else "right"
    print(f"Playing audio file for {statue.value} on device {config['device_index']} ({channel_name} channel)")

    try:
        # Load the audio file
        import soundfile as sf
        data, samplerate = sf.read(audio_file)

        # Handle multi-channel files - extract first channel if needed
        if len(data.shape) > 1:
            data = data[:, 0]  # Use first channel

        # Convert to stereo and route to specific channel
        if config["channel"] == 0:  # Left channel (TRS tip)
            stereo_data = np.column_stack([data, np.zeros_like(data)])
        else:  # Right channel (TRS ring)
            stereo_data = np.column_stack([np.zeros_like(data), data])

        # Play with specific channel routing
        sd.play(
            stereo_data,
            samplerate=samplerate,
            device=config["device_index"]
        )
        print(f"✓ Audio playback started for {statue.value} on channel {config['channel']}")

    except ImportError:
        print("WARNING: soundfile library not available, falling back to simple method")
        # Fallback: use sd.play without soundfile (limited format support)
        try:
            # This is a simple fallback - won't work with all file formats
            print("Please install soundfile: pip install soundfile")
        except Exception as e:
            print(f"Error playing audio: {e}")
    except Exception as e:
        print(f"Error playing audio file {audio_file}: {e}")


class MultiChannelPlayback:
    """Manages synchronized multi-channel audio playback across multiple devices."""

    def __init__(self, audio_data, sample_rate, devices):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.devices = devices
        self.streams = []
        self.is_playing = False
        self.is_paused = False
        self.frame_index = 0
        self.lock = threading.Lock()

    def _create_callback(self, channel_index):
        """Create a callback function for a specific channel."""
        def callback(outdata, frames, time_info, status):
            if status:
                print(f"Stream status for channel {channel_index}: {status}")

            with self.lock:
                if self.is_paused:
                    outdata.fill(0)
                    return

                # Calculate remaining frames
                remaining_frames = len(self.audio_data) - self.frame_index
                if remaining_frames <= 0:
                    outdata.fill(0)
                    self.is_playing = False
                    return

                # Get frames to play
                frames_to_play = min(frames, remaining_frames)

                # Extract channel data
                if self.audio_data.ndim == 1 or channel_index >= self.audio_data.shape[1]:
                    # Mono or channel doesn't exist - use silence
                    channel_data = np.zeros(frames_to_play)
                else:
                    # Get specific channel
                    channel_data = self.audio_data[self.frame_index:self.frame_index + frames_to_play, channel_index]

                # Create stereo output with audio on left channel only
                stereo_data = np.zeros((frames, 2))
                stereo_data[:frames_to_play, 0] = channel_data  # Left channel
                # Right channel stays silent (reserved for tone)

                outdata[:] = stereo_data

                # Update frame index (only one callback should do this)
                if channel_index == 0:
                    self.frame_index += frames_to_play

        return callback

    def start(self):
        """Start synchronized playback on all devices."""
        if self.is_playing:
            return

        # Create output streams for each device
        for i, device in enumerate(self.devices):
            channel_index = i  # Map device index to audio channel

            stream = sd.OutputStream(
                device=device["device_index"],
                channels=2,  # Stereo output
                samplerate=self.sample_rate,
                callback=self._create_callback(channel_index),
                blocksize=dynConfig.get("block_size", 1024)
            )
            self.streams.append(stream)

        # Start all streams
        self.is_playing = True
        for stream in self.streams:
            stream.start()

        print(f"Started {len(self.streams)}-channel playback")

    def pause(self):
        """Pause playback."""
        with self.lock:
            self.is_paused = True

    def resume(self):
        """Resume playback."""
        with self.lock:
            self.is_paused = False

    def stop(self):
        """Stop playback and clean up resources."""
        self.is_playing = False

        # Stop and close all streams
        for stream in self.streams:
            stream.stop()
            stream.close()

        self.streams = []
        print("Playback stopped")

    def is_active(self):
        """Check if playback is still active."""
        return self.is_playing and self.frame_index < len(self.audio_data)


def play_multichannel_audio(audio_file, devices=None):
    """
    Play a multi-channel audio file across multiple devices.

    Args:
        audio_file: Path to the multi-channel WAV file
        devices: List of device configurations. If None, uses all configured audio devices.

    Returns:
        MultiChannelPlayback instance for control, or None on error
    """
    try:
        # Load the audio file
        import soundfile as sf
        audio_data, sample_rate = sf.read(audio_file)

        # Ensure audio_data is 2D (samples x channels)
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        print(f"Loaded audio file: {audio_file}")
        print(f"  Sample rate: {sample_rate} Hz")
        print(f"  Duration: {len(audio_data) / sample_rate:.2f} seconds")
        print(f"  Channels: {audio_data.shape[1]}")

        # Get devices if not provided
        if devices is None:
            devices = get_audio_devices()

        if not devices:
            print("ERROR: No audio devices configured")
            return None

        # Limit to available channels
        num_channels = min(len(devices), audio_data.shape[1])
        devices = devices[:num_channels]

        print(f"\nMapping {num_channels} audio channels to devices:")
        for i, device in enumerate(devices):
            statue_name = device['statue'].value if hasattr(device['statue'], 'value') else str(device['statue'])
            print(f"  Channel {i} → {statue_name} (device {device['device_index']})")

        # Create and start playback
        playback = MultiChannelPlayback(audio_data, sample_rate, devices)
        playback.start()

        return playback

    except ImportError:
        print("ERROR: soundfile library not available")
        print("Install with: pip install soundfile")
        return None
    except Exception as e:
        print(f"Error loading audio file {audio_file}: {e}")
        return None