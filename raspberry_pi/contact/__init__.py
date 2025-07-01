"""Contact detection module for Missing Link project.

This module provides tone-based contact detection between statues,
including audio playback control and real-time status display.
"""

from .config import TONE_FREQUENCIES, AUDIO_JACK, DEFAULT_AUDIO_FILE
from .link_state import LinkStateTracker
from .display import StatusDisplay
from .tone_generation import create_tone_generator
from .detection import detect_tone
from .audio_setup import initialize_audio_playback

__all__ = [
    'TONE_FREQUENCIES',
    'AUDIO_JACK',
    'DEFAULT_AUDIO_FILE',
    'LinkStateTracker',
    'StatusDisplay',
    'create_tone_generator',
    'detect_tone',
    'initialize_audio_playback'
]

__version__ = '1.0.0'