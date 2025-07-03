"""Contact detection module for Missing Link project.

This module provides tone-based contact detection between statues,
including audio playback control and real-time status display.
"""

from .audio_setup import initialize_audio_playback
from .config import AUDIO_JACK, DEFAULT_AUDIO_FILE, TONE_FREQUENCIES
from .display import StatusDisplay
from .link_state import LinkStateTracker
from .tone_detect import create_tone_generator, detect_tone

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
