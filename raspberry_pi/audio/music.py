#!/usr/bin/env python3
"""Multi-channel audio playback system for Missing Link statues.

This module provides synchronized audio playback across multiple USB audio
devices, with support for channel toggling based on statue connection states.

Key Features:
- Synchronized playback across up to 6 audio channels
- Real-time channel muting/unmuting based on link state
- Support for multi-channel WAV files
- Integration with tone generation for contact detection

Architecture:
- MultiChannelPlayback: Base class for synchronized playback
- ToggleableMultiChannelPlayback: Extends base with channel control
- Each statue gets one channel from the source audio file
- Playback callbacks can include tone generators for right channel

Example:
    >>> from audio.music import ToggleableMultiChannelPlayback
    >>> playback = ToggleableMultiChannelPlayback(
    ...     audio_data, sample_rate, devices,
    ...     right_channel_callbacks=tone_generators
    ... )
    >>> playback.start()
    >>> playback.toggle_channel(0)  # Enable first channel
"""

import threading
from typing import Any, Callable

import numpy as np
import sounddevice as sd
import soundfile as sf

from .devices import Statue, dynConfig, get_audio_devices


def play_audio(statue: Statue, audio_file: str) -> None:
    """Play a WAV file on the audio channel for the specified statue.

    This is a simple single-statue playback function, primarily used
    for testing. For production use, see MultiChannelPlayback classes.

    Args:
        statue (Statue): The statue to play audio on
        audio_file (str): Path to WAV file to play

    Note:
        Audio is routed to the left channel (TRS tip) of the statue's
        assigned USB device. The right channel remains silent.
    """
    config = dynConfig[statue.value]["audio"]

    if config["device_index"] == -1:
        print(f"WARNING: No audio device configured for {statue.value}")
        return

    channel_name = "left" if config["channel"] == 0 else "right"
    print(f"Playing audio file for {statue.value} on device {config['device_index']} ({channel_name} channel)")

    try:
        # Load the audio file
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

    def __init__(self, audio_data: np.ndarray, sample_rate: int, devices: list[dict[str, Any]]) -> None:
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.devices = devices
        self.streams = []
        self.is_playing = False
        self.is_paused = False
        self.frame_index = 0
        self.lock = threading.Lock()

    def _create_callback(self, channel_index: int) -> Callable:
        """Create a callback function for a specific channel.

        Each device gets its own callback that reads from the shared
        frame index. Only the first device updates the index to maintain
        synchronization.

        Args:
            channel_index (int): Index of the channel in the audio data

        Returns:
            function: Callback function for sounddevice stream
        """
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


class ToggleableMultiChannelPlayback(MultiChannelPlayback):
    """Extended playback class with per-channel mute control.

    This class extends MultiChannelPlayback with the ability to dynamically
    enable/disable individual channels during playback. This is used to turn
    statue audio on/off based on whether they are linked in the contact
    detection system.

    Additionally supports right channel callbacks for tone generation,
    allowing the same device to output both audio (left) and detection
    tones (right) simultaneously.

    Attributes:
        channel_enabled (list): Boolean flags for each channel
        active_count (int): Number of currently active channels
        right_channel_callbacks (dict): Optional tone generators by statue
    """

    def __init__(self, audio_data, sample_rate, devices, right_channel_callbacks=None):
        """Initialize toggleable playback with optional tone generators.

        Args:
            audio_data (np.ndarray): Multi-channel audio data
            sample_rate (int): Sample rate in Hz
            devices (list): Device configurations
            right_channel_callbacks (dict, optional): Tone generators by statue.
                Maps Statue enum to generator function that returns samples.
        """
        super().__init__(audio_data, sample_rate, devices)
        # Initialize all channels as disabled
        self.channel_enabled = [False] * len(devices)
        self.active_count = 0
        # Optional callbacks for right channel data (e.g., for tone generation)
        self.right_channel_callbacks = right_channel_callbacks or {}

    def _create_callback(self, channel_index):
        """Create a callback function with mute control for a specific channel."""
        def callback(outdata, frames, time_info, status):
            if status:
                print(f"\rStream status for channel {channel_index}: {status}")

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

                # Apply mute if channel is disabled
                if not self.channel_enabled[channel_index]:
                    channel_data = np.zeros_like(channel_data)

                # Create stereo output with audio on left channel
                stereo_data = np.zeros((frames, 2))
                stereo_data[:frames_to_play, 0] = channel_data  # Left channel

                # Right channel: use callback if provided, otherwise silent
                if channel_index in self.right_channel_callbacks:
                    right_data = self.right_channel_callbacks[channel_index](frames)
                    stereo_data[:, 1] = right_data

                outdata[:] = stereo_data

                # Update frame index (only one callback should do this)
                if channel_index == 0:
                    self.frame_index += frames_to_play

        return callback

    def toggle_channel(self, channel_index):
        """Toggle a channel on/off.

        When a statue becomes linked/unlinked, this method is called to
        enable/disable its audio channel. The audio fades in/out smoothly
        to avoid clicks.

        Args:
            channel_index (int): Index of the channel to toggle

        Returns:
            bool: True if toggle successful, False if invalid index
        """
        if 0 <= channel_index < len(self.channel_enabled):
            with self.lock:
                self.channel_enabled[channel_index] = not self.channel_enabled[channel_index]

                # Update active count
                self.active_count = sum(self.channel_enabled)

                # Handle playback state changes
                if self.active_count == 0 and self.is_playing:
                    # Last channel turned off - stop playback
                    self.is_playing = False
                    self.frame_index = 0  # Reset to beginning
                elif self.active_count == 1 and not self.is_playing:
                    # First channel turned on - start playback
                    self.is_playing = True
                    if self.frame_index >= len(self.audio_data):
                        self.frame_index = 0  # Reset if at end

                return True
        return False

    def get_channel_states(self):
        """Return current channel enabled states."""
        return self.channel_enabled.copy()

    def get_progress(self):
        """Get playback progress as percentage."""
        if len(self.audio_data) == 0:
            return 0
        return min(100, int(self.frame_index / len(self.audio_data) * 100))


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
