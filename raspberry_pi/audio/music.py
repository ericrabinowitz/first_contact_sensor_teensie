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
CLIMAX_MIX_GAIN = 0.5  # Gain factor for mixing all channels in climax mode
MUSIC_GAIN = 1 # Gain factor for playing active audio.

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

        # Climax mode: mix all channels and broadcast to all outputs
        self.climax_mode = False

        # Group devices by device_index to identify shared devices
        self.device_groups = {}
        for device in devices:
            dev_idx = device["device_index"]
            if dev_idx not in self.device_groups:
                self.device_groups[dev_idx] = []
            self.device_groups[dev_idx].append(device)

    def _create_multi_channel_callback(
        self, device_list: list[dict[str, Any]]
    ) -> Callable:
        """Create a callback for multi-channel device handling multiple statues."""

        # Determine number of output channels needed
        max_channel = max(d.get("output_channel", 0) for d in device_list)
        num_channels = max(8, max_channel + 1)  # At least 8 for HiFiBerry

        def callback(outdata, frames, _time_info, status):
            if status:
                print(f"\rMulti-channel stream status: {status}")

            if self.is_paused:
                outdata.fill(0)
                return

            # Calculate remaining frames
            remaining_frames = len(self.audio_data) - self.frame_index
            if remaining_frames <= 0:
                if self.loop:
                    self.frame_index = 0
                    remaining_frames = len(self.audio_data)
                else:
                    outdata.fill(0)
                    self.is_stopped = True
                    return

            frames_to_play = min(frames, remaining_frames)

            # Create multi-channel output
            multi_channel_data = np.zeros((frames, num_channels))

            if self.climax_mode:
                # Climax mode: Mix all 6 channels and broadcast to all outputs
                mixed_signal = np.zeros(frames_to_play)
                num_channels_to_mix = min(6, self.audio_data.shape[1])

                # Sum all channels
                for ch in range(num_channels_to_mix):
                    mixed_signal += self.audio_data[
                        self.frame_index : self.frame_index + frames_to_play,  # noqa: E203
                        ch,
                    ]

                # Apply gain normalization
                mixed_signal *= CLIMAX_MIX_GAIN

                # Broadcast to all output channels (0-5)
                for output_ch in range(min(6, num_channels)):
                    multi_channel_data[:frames_to_play, output_ch] = mixed_signal
            else:
                # Normal mode: Map each input channel to its output channel
                for device in device_list:
                    input_ch = device.get("channel_index", 0)
                    output_ch = device.get("output_channel", input_ch)

                    if (
                        self.channel_enabled[input_ch]
                        and input_ch < self.audio_data.shape[1]
                    ):
                        # Copy audio data to the appropriate output channel
                        channel_data = self.audio_data[
                            self.frame_index : self.frame_index  # noqa: E203
                            + frames_to_play,
                            input_ch,
                        ]
                        # Scale by gain for music.
                        channel_data *= MUSIC_GAIN
                        multi_channel_data[:frames_to_play, output_ch] = channel_data

            outdata[:] = multi_channel_data
            self.frame_index += frames_to_play

        return callback

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
            if self.climax_mode:
                # Climax mode: Mix all 6 channels
                channel_data = np.zeros(frames_to_play)
                num_channels_to_mix = min(6, self.audio_data.shape[1])

                # Sum all channels
                for ch in range(num_channels_to_mix):
                    channel_data += self.audio_data[
                        self.frame_index : self.frame_index + frames_to_play,  # noqa: E203
                        ch,
                    ]

                # Apply gain normalization
                channel_data *= CLIMAX_MIX_GAIN
            elif self.audio_data.ndim == 1 or channel_index >= self.audio_data.shape[1]:
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

        # Create streams for each unique device
        for device_index, device_list in self.device_groups.items():
            if len(device_list) > 1:
                # Multi-channel device (HiFiBerry DAC8x)
                max_channel = max(d.get("output_channel", 0) for d in device_list)
                num_channels = max(8, max_channel + 1)

                stream = sd.OutputStream(
                    device=device_index,
                    channels=num_channels,
                    samplerate=device_list[0]["sample_rate"],
                    callback=self._create_multi_channel_callback(device_list),
                    blocksize=BLOCK_SIZE,
                )
                if self.debug:
                    print(
                        f"Created {num_channels}-channel stream for device {device_index}"
                    )
            else:
                # Single channel device (USB)
                device = device_list[0]
                channel_index = device.get("channel_index", 0)

                stream = sd.OutputStream(
                    device=device_index,
                    channels=2,  # Stereo output
                    samplerate=device["sample_rate"],
                    callback=self._create_callback(channel_index),
                    blocksize=BLOCK_SIZE,
                )
                if self.debug:
                    print(f"Created stereo stream for device {device_index}")

            self.streams.append(stream)

        # Start all streams
        self.is_stopped = False
        for stream in self.streams:
            stream.start()

        print(f"Started {len(self.devices)}-channel playback")

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

    def disable_all_music_channels(self):
        """Disable all music channels."""
        if self.debug:
            print("Disabling all music channels")
        for i in range(len(self.channel_enabled)):
            self.set_music_channel(i, False)

    def switch_to_song(self, audio_data: np.ndarray, enable_all: bool = False):
        """Switch to a different song.

        Args:
            audio_data: New audio data to play
            enable_all: If True, enable all channels (for dormant mode)
        """
        if self.debug:
            print(f"Switching song (enable_all={enable_all})")

        # Update audio data
        self.audio_data = audio_data

        # Reset playback position to start from beginning
        self.frame_index = 0

        # Reset paused state
        self.is_paused = False

        # Configure channels
        if enable_all:
            # Enable all channels for dormant mode
            for i in range(len(self.channel_enabled)):
                self.channel_enabled[i] = True
            self.active_count = len(self.channel_enabled)
        else:
            # Disable all channels (will be selectively enabled for active statues)
            for i in range(len(self.channel_enabled)):
                self.channel_enabled[i] = False
            self.active_count = 0

        if self.debug:
            print(f"Song switched. Active channels: {self.active_count}")

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

    def set_broadcast_mode(self, enabled: bool):
        """Enable or disable broadcast mode.

        In broadcast mode, all 6 audio channels are mixed together and broadcast
        to all output channels simultaneously, creating a fuller, more immersive
        sound experience.

        Args:
            enabled (bool): True to enable broadcast mode, False for normal mode
        """
        if self.debug:
            print(
                f"{'Enabling' if enabled else 'Disabling'} broadcast mode "
                f"(mix all channels to all outputs)"
            )
        self.climax_mode = enabled

    def get_channel_states(self):
        """Return current music channel enabled states."""
        return self.channel_enabled.copy()

    def get_progress(self):
        """Get playback progress as percentage."""
        if len(self.audio_data) == 0:
            return 0
        return min(100, int(self.frame_index / len(self.audio_data) * 100))
