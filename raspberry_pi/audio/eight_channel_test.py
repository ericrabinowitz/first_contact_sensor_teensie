#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["numpy", "sounddevice", "soundfile", "scipy"]
# ///

"""
8-Channel Audio Test for HiFiBerry DAC8x

This script provides comprehensive testing for 8-channel audio output,
specifically designed for the HiFiBerry DAC8x but compatible with any
8+ channel audio device.

Features:
- Generate 8-channel test WAV files
- Real-time channel toggling
- Visual VU meters
- Channel identification test
- Diagnostic output
"""

import os
import sys
import time
import select
import termios
import tty
from typing import Optional, List, Dict, Any
import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal


# Channel names for display
CHANNEL_NAMES = [
    "EROS",      # Channel 0
    "ELEKTRA",   # Channel 1
    "SOPHIA",    # Channel 2
    "ULTIMO",    # Channel 3
    "ARIEL",     # Channel 4
    "TEST_6",    # Channel 5
    "TEST_7",    # Channel 6
    "TEST_8",    # Channel 7
]

# Test tone frequencies for each channel (Hz)
TONE_FREQUENCIES = [
    440.0,   # A4
    523.25,  # C5
    659.25,  # E5
    783.99,  # G5
    220.0,   # A3
    330.0,   # E4
    392.0,   # G4
    493.88,  # B4
]


class TestWaveGenerator:
    """Generate various test waveforms for 8-channel testing."""

    @staticmethod
    def generate_sine(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
        """Generate a sine wave."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        return 0.5 * np.sin(2 * np.pi * frequency * t)

    @staticmethod
    def generate_square(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
        """Generate a square wave."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        return 0.5 * signal.square(2 * np.pi * frequency * t)

    @staticmethod
    def generate_sawtooth(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
        """Generate a sawtooth wave."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        return 0.5 * signal.sawtooth(2 * np.pi * frequency * t)

    @staticmethod
    def generate_white_noise(duration: float, sample_rate: int) -> np.ndarray:
        """Generate white noise."""
        samples = int(sample_rate * duration)
        return 0.3 * np.random.randn(samples)

    @staticmethod
    def generate_pink_noise(duration: float, sample_rate: int) -> np.ndarray:
        """Generate pink noise (1/f noise)."""
        samples = int(sample_rate * duration)
        white = np.random.randn(samples)
        # Simple pink noise approximation using filtering
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        pink = signal.lfilter(b, a, white)
        return 0.3 * pink / np.max(np.abs(pink))

    @classmethod
    def create_8ch_test_tones(cls, duration: float = 10.0, sample_rate: int = 48000) -> np.ndarray:
        """Create an 8-channel test file with different tones on each channel."""
        samples = int(sample_rate * duration)
        audio_data = np.zeros((samples, 8))

        print("Generating 8-channel test tones...")
        for ch in range(8):
            freq = TONE_FREQUENCIES[ch]
            print(f"  Channel {ch+1} ({CHANNEL_NAMES[ch]}): {freq:.2f} Hz sine wave")
            audio_data[:, ch] = cls.generate_sine(freq, duration, sample_rate)

        return audio_data

    @classmethod
    def create_8ch_sweep(cls, duration: float = 16.0, sample_rate: int = 48000) -> np.ndarray:
        """Create an 8-channel sweep test (2 seconds per channel)."""
        samples = int(sample_rate * duration)
        audio_data = np.zeros((samples, 8))

        samples_per_channel = samples // 8

        print("Generating 8-channel sweep test...")
        for ch in range(8):
            start = ch * samples_per_channel
            end = min((ch + 1) * samples_per_channel, samples)
            freq = TONE_FREQUENCIES[ch]

            # Generate tone with fade in/out
            tone = cls.generate_sine(freq, (end - start) / sample_rate, sample_rate)

            # Apply fade in/out (100ms)
            fade_samples = int(0.1 * sample_rate)
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)

            tone[:fade_samples] *= fade_in
            tone[-fade_samples:] *= fade_out

            audio_data[start:end, ch] = tone
            print(f"  Channel {ch+1} ({CHANNEL_NAMES[ch]}): {start/sample_rate:.1f}s - {end/sample_rate:.1f}s")

        return audio_data

    @classmethod
    def create_8ch_mixed(cls, duration: float = 10.0, sample_rate: int = 48000) -> np.ndarray:
        """Create an 8-channel test with different waveform types."""
        samples = int(sample_rate * duration)
        audio_data = np.zeros((samples, 8))

        print("Generating 8-channel mixed waveforms...")
        # Channels 0-3: Different frequency sines
        for ch in range(4):
            freq = TONE_FREQUENCIES[ch]
            audio_data[:, ch] = cls.generate_sine(freq, duration, sample_rate)
            print(f"  Channel {ch+1} ({CHANNEL_NAMES[ch]}): {freq:.2f} Hz sine")

        # Channel 4: Square wave
        audio_data[:, 4] = cls.generate_square(220.0, duration, sample_rate)
        print(f"  Channel 5 ({CHANNEL_NAMES[4]}): 220 Hz square wave")

        # Channel 5: Sawtooth
        audio_data[:, 5] = cls.generate_sawtooth(330.0, duration, sample_rate)
        print(f"  Channel 6 ({CHANNEL_NAMES[5]}): 330 Hz sawtooth")

        # Channel 6: White noise
        audio_data[:, 6] = cls.generate_white_noise(duration, sample_rate)
        print(f"  Channel 7 ({CHANNEL_NAMES[6]}): White noise")

        # Channel 7: Pink noise
        audio_data[:, 7] = cls.generate_pink_noise(duration, sample_rate)
        print(f"  Channel 8 ({CHANNEL_NAMES[7]}): Pink noise")

        return audio_data


class EightChannelPlayer:
    """8-channel audio player with individual channel control."""

    def __init__(self, audio_data: np.ndarray, sample_rate: int, device_index: Optional[int] = None):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.device_index = device_index

        # Ensure we have 8 channels
        if audio_data.shape[1] < 8:
            # Pad with zeros if needed
            padding = np.zeros((audio_data.shape[0], 8 - audio_data.shape[1]))
            self.audio_data = np.hstack([audio_data, padding])

        self.channels_enabled = [True] * 8
        self.frame_index = 0
        self.is_playing = False
        self.stream = None

        # For VU meter
        self.channel_levels = [0.0] * 8
        self.peak_levels = [0.0] * 8

    def callback(self, outdata, frames, time_info, status):
        """Audio callback for real-time playback."""
        if status:
            print(f"Stream status: {status}")

        # Calculate remaining frames
        remaining = len(self.audio_data) - self.frame_index
        if remaining <= 0:
            # Loop back to start
            self.frame_index = 0
            remaining = len(self.audio_data)

        frames_to_play = min(frames, remaining)

        # Get audio data for this chunk
        chunk = self.audio_data[self.frame_index:self.frame_index + frames_to_play]

        # Apply channel enables
        output = np.zeros((frames, 8))
        for ch in range(8):
            if self.channels_enabled[ch]:
                output[:frames_to_play, ch] = chunk[:, ch]

                # Calculate RMS level for VU meter
                if frames_to_play > 0:
                    rms = np.sqrt(np.mean(chunk[:, ch] ** 2))
                    self.channel_levels[ch] = rms
                    self.peak_levels[ch] = max(self.peak_levels[ch] * 0.95, np.max(np.abs(chunk[:, ch])))
            else:
                self.channel_levels[ch] = 0
                self.peak_levels[ch] *= 0.95

        outdata[:] = output
        self.frame_index += frames_to_play

    def start(self):
        """Start playback."""
        if self.stream is not None:
            self.stop()

        self.stream = sd.OutputStream(
            device=self.device_index,
            channels=8,
            samplerate=self.sample_rate,
            callback=self.callback,
            blocksize=512
        )
        self.stream.start()
        self.is_playing = True
        print("Playback started")

    def stop(self):
        """Stop playback."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_playing = False
        print("Playback stopped")

    def toggle_channel(self, channel: int):
        """Toggle a channel on/off."""
        if 0 <= channel < 8:
            self.channels_enabled[channel] = not self.channels_enabled[channel]
            return self.channels_enabled[channel]
        return None

    def set_all_channels(self, enabled: bool):
        """Enable or disable all channels."""
        self.channels_enabled = [enabled] * 8

    def get_progress(self) -> float:
        """Get playback progress as percentage."""
        if len(self.audio_data) == 0:
            return 0
        return (self.frame_index / len(self.audio_data)) * 100


class InteractiveInterface:
    """Terminal-based interface for 8-channel control."""

    def __init__(self, player: EightChannelPlayer):
        self.player = player
        self.running = True
        self.old_settings = None

    def setup_terminal(self):
        """Set terminal to raw mode."""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    def restore_terminal(self):
        """Restore terminal settings."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def clear_screen(self):
        """Clear terminal screen."""
        print("\033[2J\033[H", end='')

    def draw_vu_meter(self, level: float, peak: float, width: int = 20) -> str:
        """Draw a VU meter bar."""
        level_bars = int(level * width * 2)  # Scale to 0-width
        peak_pos = int(peak * width)

        meter = ""
        for i in range(width):
            if i < level_bars:
                if i < width * 0.5:
                    meter += "▓"  # Green zone
                elif i < width * 0.75:
                    meter += "▒"  # Yellow zone
                else:
                    meter += "░"  # Red zone
            elif i == peak_pos:
                meter += "|"  # Peak indicator
            else:
                meter += " "

        return meter

    def draw_interface(self):
        """Draw the main interface."""
        self.clear_screen()

        print("=== 8-Channel HiFiBerry DAC8x Test ===\r\n")
        print("Channel Status:                    Level              Peak\r")
        print("-" * 70 + "\r")

        for i in range(8):
            enabled = self.player.channels_enabled[i]
            status = "[ON ] " if enabled else "[OFF] "
            level = self.player.channel_levels[i]
            peak = self.player.peak_levels[i]

            vu_meter = self.draw_vu_meter(level, peak)

            print(f"[{i+1}] {CHANNEL_NAMES[i]:8s} {status} {vu_meter} {level*100:3.0f}% | {peak*100:3.0f}%\r")

        active = sum(self.player.channels_enabled)
        progress = self.player.get_progress()

        print(f"\r\nActive: {active}/8 | Progress: {progress:.1f}%\r")
        print("\r\nControls:\r")
        print("1-8: Toggle channel | A: All on | N: All off | T: Test sweep\r")
        print("S: Save WAV | Q: Quit\r")

    def run(self):
        """Run the interactive interface."""
        self.setup_terminal()

        try:
            self.player.start()

            while self.running:
                self.draw_interface()

                # Non-blocking key input
                if sys.stdin in select.select([sys.stdin], [], [], 0.05)[0]:
                    key = sys.stdin.read(1)

                    if key == 'q' or key == 'Q':
                        self.running = False
                    elif key.isdigit():
                        channel = int(key) - 1
                        if 0 <= channel < 8:
                            self.player.toggle_channel(channel)
                    elif key == 'a' or key == 'A':
                        self.player.set_all_channels(True)
                    elif key == 'n' or key == 'N':
                        self.player.set_all_channels(False)
                    elif key == 't' or key == 'T':
                        # Quick test: enable each channel for 0.5s
                        for ch in range(8):
                            self.player.set_all_channels(False)
                            self.player.channels_enabled[ch] = True
                            time.sleep(0.5)
                        self.player.set_all_channels(True)

                time.sleep(0.05)  # Update rate

        finally:
            self.player.stop()
            self.restore_terminal()
            self.clear_screen()
            print("Test ended.")


def find_hifiberry_device() -> Optional[int]:
    """Find the HiFiBerry DAC8x device."""
    devices = sd.query_devices()
    for device in devices:
        if "hifiberry" in device["name"].lower() and device["max_output_channels"] >= 8:
            print(f"Found HiFiBerry DAC8x: {device['name']} (device {device['index']})")
            return device["index"]
    return None


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="8-Channel Audio Test")
    parser.add_argument("--generate", choices=["tones", "sweep", "mixed"],
                       help="Generate test WAV file")
    parser.add_argument("--output", default="test_8ch.wav",
                       help="Output filename for generated WAV")
    parser.add_argument("--input", help="Input WAV file to play")
    parser.add_argument("--device", type=int, help="Audio device index")
    parser.add_argument("--duration", type=float, default=10.0,
                       help="Duration for generated test (seconds)")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices")

    args = parser.parse_args()

    if args.list_devices:
        print("Available audio devices:")
        for device in sd.query_devices():
            if device["max_output_channels"] >= 8:
                print(f"  {device['index']}: {device['name']} "
                     f"({device['max_output_channels']} outputs)")
        return

    # Generate test file if requested
    if args.generate:
        generator = TestWaveGenerator()
        if args.generate == "tones":
            audio_data = generator.create_8ch_test_tones(args.duration)
        elif args.generate == "sweep":
            audio_data = generator.create_8ch_sweep(args.duration * 8 / 10)  # Adjust for sweep
        elif args.generate == "mixed":
            audio_data = generator.create_8ch_mixed(args.duration)

        sf.write(args.output, audio_data, 48000)
        print(f"Generated {args.output}")
        return

    # Load audio file
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}")
            return
        audio_data, sample_rate = sf.read(args.input)
        print(f"Loaded: {args.input}")
    else:
        # Generate default test tones
        print("No input file specified, generating test tones...")
        generator = TestWaveGenerator()
        audio_data = generator.create_8ch_test_tones(30.0)
        sample_rate = 48000

    print(f"Audio: {audio_data.shape[0]} samples, {audio_data.shape[1]} channels, {sample_rate} Hz")

    # Find device
    device_index = args.device
    if device_index is None:
        device_index = find_hifiberry_device()
        if device_index is None:
            print("Warning: HiFiBerry DAC8x not found, using default device")

    # Create player and interface
    player = EightChannelPlayer(audio_data, sample_rate, device_index)
    interface = InteractiveInterface(player)

    try:
        interface.run()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()