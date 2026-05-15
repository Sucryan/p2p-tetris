"""Public game-core event interface consumed by battle/runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeAlias

from p2p_tetris.game_core.pieces import PieceType


class TSpinType(Enum):
    """T-spin classification for locked pieces and line clears."""

    NONE = auto()
    MINI = auto()
    FULL = auto()


@dataclass(frozen=True, slots=True)
class ClearEvent:
    """Emitted when a lock clears at least one line."""

    lines_cleared: int
    t_spin: TSpinType
    combo: int
    back_to_back: bool


@dataclass(frozen=True, slots=True)
class PieceLockedEvent:
    """Emitted whenever a piece locks into the board."""

    piece: PieceType
    cells: tuple[tuple[int, int], ...]
    cleared_lines: int
    t_spin: TSpinType
    combo: int
    back_to_back: bool


@dataclass(frozen=True, slots=True)
class TopOutEvent:
    """Emitted when the local board reaches a top-out condition."""

    reason: str


GameEvent: TypeAlias = ClearEvent | PieceLockedEvent | TopOutEvent
