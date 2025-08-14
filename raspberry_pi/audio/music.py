#!/usr/bin/env python3
"""Multi-channel audio playback system for Missing Link statues.

This module provides synchronized audio playback across multiple USB audio
devices, with support for channel toggling based on statue connection states.

Key Features:
- Synchronized playback across up to 6 audio channels
- Real-time channel muting/un-muting based on link state
- Support for multi-channel WAV files

Architecture:
- ToggleableMultiChannelPlayback: Class for synchronized playback with channel control
- Each statue gets one channel from the source audio file

Example:
    >>> from audio.music import ToggleableMultiChannelPlayback
    >>> playback = ToggleableMultiChannelPlayback(
    ...     audio_data, sample_rate, devices)
    >>> playback.start()
    >>> playback.toggle_music_channel(0)  # Enable first channel
"""

# import threading
from typing import Any, Callable

import numpy as np
import sounddevice as sd


BLOCK_SIZE = 1024  # Default block size for audio processing


class ToggleableMultiChannelPlayback:
    """Manages synchronized multi-channel audio playback across multiple devices.

    Has the ability to dynamically enable/disable music channels independently
    during playback. Music channels control statue audio playback.

    Channel Architecture:
    - Left channel (TRS tip): Music audio controlled by channel_enabled
    - Right channel (TRS ring): Muted

    Attributes:
        channel_enabled (list): Boolean flags for music channels (left)
        active_count (int): Number of currently active music channels
        lock (threading.RLock): Reentrant lock for thread-safe state changes
    """

    def __init__(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        devices: list[dict[str, Any]],
        loop: bool = True,
        debug: bool = False,
    ):
        """Initialize toggleable playback.

        Args:
            audio_data (np.ndarray): Multi-channel audio data
            sample_rate (int): Sample rate in Hz
            devices (list): Device configurations
            loop (bool, optional): Whether to loop audio playback. Defaults to True.
        """
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.devices = devices
        self.streams = []
        self.is_stopped = True
        self.is_paused = False
        self.frame_index = 0
        # Use reentrant lock to allow toggle->set method calls
        # self.lock = threading.Lock()

        # Initialize all music channels as disabled
        self.channel_enabled = [False] * len(devices)
        self.active_count = 0

        # Whether to loop audio playback
        self.loop = loop
        self.debug = debug

    def _create_callback(self, channel_index: int) -> Callable:
        """Create a callback function with mute control for a specific channel."""

        def callback(outdata, frames, _time_info, status):
            if status:
                print(f"\rStream status for channel {channel_index}: {status}")

            # with self.lock:
            if self.is_paused:
                outdata.fill(0)
                return

            # Calculate remaining frames
            remaining_frames = len(self.audio_data) - self.frame_index
            if remaining_frames <= 0:
                if self.loop:
                    # Reset frame index to loop
                    self.frame_index = 0
                    remaining_frames = len(self.audio_data)
                else:
                    outdata.fill(0)
                    self.is_stopped = True
                    return

            # Get frames to play
            frames_to_play = min(frames, remaining_frames)

            # Extract channel data
            if self.audio_data.ndim == 1 or channel_index >= self.audio_data.shape[1]:
                # Mono or channel doesn't exist - use silence
                channel_data = np.zeros(frames_to_play)
            elif not self.channel_enabled[channel_index]:
                # Apply mute if channel is disabled
                channel_data = np.zeros(frames_to_play)
            else:
                # Get specific channel
                channel_data = self.audio_data[
                    self.frame_index : self.frame_index + frames_to_play,  # noqa: E203
                    channel_index,
                ]

            # Create stereo output with audio on left channel
            stereo_data = np.zeros((frames, 2))
            stereo_data[:frames_to_play, 0] = channel_data  # Left channel

            # Leave the right channel muted

            outdata[:] = stereo_data

            # Update frame index (only one callback should do this)
            if channel_index == 0:
                self.frame_index += frames_to_play

        return callback

    def start(self):
        """Start synchronized playback on all devices."""
        if not self.is_stopped:
            return

        # Create output streams for each device
        for i, device in enumerate(self.devices):
            channel_index = i  # Map device index to audio channel

            stream = sd.OutputStream(
                device=device["device_index"],
                channels=2,  # Stereo output
                samplerate=self.sample_rate,
                callback=self._create_callback(channel_index),
                blocksize=BLOCK_SIZE,
            )
            self.streams.append(stream)

        # Start all streams
        self.is_stopped = False
        for stream in self.streams:
            stream.start()

        print(f"Started {len(self.streams)}-channel playback")

    def pause(self):
        """Pause playback."""
        if self.debug:
            print("Pausing playback")
        # with self.lock:
        self.is_paused = True

    def resume(self):
        """Resume playback."""
        if self.debug:
            print("Resuming playback")
        # with self.lock:
        self.is_paused = False

    def stop(self):
        """Stop playback and clean up resources."""
        if self.debug:
            print("Stopping playback")
        self.is_stopped = True

        # Stop and close all streams
        for stream in self.streams:
            stream.stop()
            stream.close()

        self.streams = []
        print("Playback stopped")

    def is_active(self):
        """Check if playback is still active."""
        return (not self.is_stopped) and self.frame_index < len(self.audio_data)

    def toggle_music_channel(self, channel_index: int) -> bool:
        """Toggle a music channel on/off.

        When a statue becomes linked/unlinked, this method is called to
        enable/disable its music audio channel (left channel). The audio
        fades in/out smoothly to avoid clicks.

        Args:
            channel_index (int): Index of the music channel to toggle

        Returns:
            bool: True if toggle successful, False if invalid index
        """
        if channel_index < 0 or channel_index >= len(self.channel_enabled):
            return False
        # with self.lock:
        current_state = self.channel_enabled[channel_index]
        return self.set_music_channel(channel_index, not current_state)

    def enable_all_music_channels(self):
        """Enable all music channels."""
        if self.debug:
            print("Enabling all music channels")
        # with self.lock:
        for i in range(len(self.channel_enabled)):
            self.set_music_channel(i, True)

    def set_music_channel(self, channel_index: int, enabled: bool) -> bool:
        """Set music channel state explicitly.

        Args:
            channel_index (int): Index of the music channel
            enabled (bool): True to enable music, False to disable

        Returns:
            bool: True if set successful, False if invalid index
        """
        if channel_index < 0 or channel_index >= len(self.channel_enabled):
            return False
        if self.debug:
            print(
                f"Setting channel {channel_index} to {'enabled' if enabled else 'disabled'}"
            )

        # with self.lock:
        self.channel_enabled[channel_index] = enabled

        # Update active count
        self.active_count = sum(self.channel_enabled)

        # Handle playback state changes
        if self.active_count == 0 and not self.is_stopped:
            # Last channel turned off - stop playback
            self.is_stopped = True
            self.frame_index = 0  # Reset to beginning
        elif self.active_count == 1 and self.is_stopped and enabled:
            # First channel turned on - start playback
            self.is_stopped = False
            if self.frame_index >= len(self.audio_data):
                self.frame_index = 0  # Reset if at end
        return True

    def get_channel_states(self):
        """Return current music channel enabled states."""
        return self.channel_enabled.copy()

    def get_progress(self):
        """Get playback progress as percentage."""
        if len(self.audio_data) == 0:
            return 0
        return min(100, int(self.frame_index / len(self.audio_data) * 100))
