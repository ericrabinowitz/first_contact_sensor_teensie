"""Central constants and configuration for Missing Link installation."""

import sys
from enum import IntEnum, auto

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum


class Statue(StrEnum):
    """The Missing Link statues."""

    EROS = auto()
    ELEKTRA = auto()
    ULTIMO = auto()
    SOPHIA = auto()
    ARIEL = auto()


class Board(StrEnum):
    """WLED board identifiers."""

    FIVE_V_1 = auto()
    FIVE_V_2 = auto()
    TWELVE_V_1 = auto()


class Effect(IntEnum):
    """WLED effect identifiers."""

    SOLID = 0
    FIREWORKS = 42
    NOISE = 71
    LIGHTHOUSE = 41  # consider scanner
    HEARTBEAT = 100
    CHASE_RAINBOW = 30
    BREATHE = 2
    # Add some effect for climax and use that.
