"""Player actions accepted by the game engine."""

from __future__ import annotations

from enum import Enum, auto


class PlayerAction(Enum):
    """Single-player gameplay actions shared by human, tests, and controllers."""

    NO_OP = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    SOFT_DROP = auto()
    HARD_DROP = auto()
    ROTATE_CW = auto()
    ROTATE_CCW = auto()
    HOLD = auto()
