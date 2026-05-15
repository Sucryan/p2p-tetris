"""Tetromino definitions and orientation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PieceType(Enum):
    """Guideline tetromino piece types."""

    I = "I"  # noqa: E741 - public Tetris piece name.
    O = "O"  # noqa: E741 - public Tetris piece name.
    T = "T"
    S = "S"
    Z = "Z"
    J = "J"
    L = "L"


class RotationState(Enum):
    """SRS rotation states."""

    SPAWN = 0
    RIGHT = 1
    REVERSE = 2
    LEFT = 3

    def rotate_cw(self) -> RotationState:
        return RotationState((self.value + 1) % 4)

    def rotate_ccw(self) -> RotationState:
        return RotationState((self.value - 1) % 4)


Cell = tuple[int, int]


@dataclass(frozen=True, slots=True)
class ActivePiece:
    """A piece in board coordinates, anchored by the 4x4 SRS bounding box."""

    type: PieceType
    x: int
    y: int
    rotation: RotationState = RotationState.SPAWN

    @property
    def cells(self) -> tuple[Cell, ...]:
        return absolute_cells(self.type, self.rotation, self.x, self.y)


PIECE_CELLS: dict[PieceType, dict[RotationState, tuple[Cell, ...]]] = {
    PieceType.I: {
        RotationState.SPAWN: ((0, 1), (1, 1), (2, 1), (3, 1)),
        RotationState.RIGHT: ((2, 0), (2, 1), (2, 2), (2, 3)),
        RotationState.REVERSE: ((0, 2), (1, 2), (2, 2), (3, 2)),
        RotationState.LEFT: ((1, 0), (1, 1), (1, 2), (1, 3)),
    },
    PieceType.O: {
        RotationState.SPAWN: ((1, 0), (2, 0), (1, 1), (2, 1)),
        RotationState.RIGHT: ((1, 0), (2, 0), (1, 1), (2, 1)),
        RotationState.REVERSE: ((1, 0), (2, 0), (1, 1), (2, 1)),
        RotationState.LEFT: ((1, 0), (2, 0), (1, 1), (2, 1)),
    },
    PieceType.T: {
        RotationState.SPAWN: ((1, 0), (0, 1), (1, 1), (2, 1)),
        RotationState.RIGHT: ((1, 0), (1, 1), (2, 1), (1, 2)),
        RotationState.REVERSE: ((0, 1), (1, 1), (2, 1), (1, 2)),
        RotationState.LEFT: ((1, 0), (0, 1), (1, 1), (1, 2)),
    },
    PieceType.S: {
        RotationState.SPAWN: ((1, 0), (2, 0), (0, 1), (1, 1)),
        RotationState.RIGHT: ((1, 0), (1, 1), (2, 1), (2, 2)),
        RotationState.REVERSE: ((1, 1), (2, 1), (0, 2), (1, 2)),
        RotationState.LEFT: ((0, 0), (0, 1), (1, 1), (1, 2)),
    },
    PieceType.Z: {
        RotationState.SPAWN: ((0, 0), (1, 0), (1, 1), (2, 1)),
        RotationState.RIGHT: ((2, 0), (1, 1), (2, 1), (1, 2)),
        RotationState.REVERSE: ((0, 1), (1, 1), (1, 2), (2, 2)),
        RotationState.LEFT: ((1, 0), (0, 1), (1, 1), (0, 2)),
    },
    PieceType.J: {
        RotationState.SPAWN: ((0, 0), (0, 1), (1, 1), (2, 1)),
        RotationState.RIGHT: ((1, 0), (2, 0), (1, 1), (1, 2)),
        RotationState.REVERSE: ((0, 1), (1, 1), (2, 1), (2, 2)),
        RotationState.LEFT: ((1, 0), (1, 1), (0, 2), (1, 2)),
    },
    PieceType.L: {
        RotationState.SPAWN: ((2, 0), (0, 1), (1, 1), (2, 1)),
        RotationState.RIGHT: ((1, 0), (1, 1), (1, 2), (2, 2)),
        RotationState.REVERSE: ((0, 1), (1, 1), (2, 1), (0, 2)),
        RotationState.LEFT: ((0, 0), (1, 0), (1, 1), (1, 2)),
    },
}


def cells_for(piece: PieceType, rotation: RotationState) -> tuple[Cell, ...]:
    """Return local 4x4-grid cells for a piece orientation."""

    return PIECE_CELLS[piece][rotation]


def absolute_cells(
    piece: PieceType,
    rotation: RotationState,
    x: int,
    y: int,
) -> tuple[Cell, ...]:
    """Return board cells for an anchored piece."""

    return tuple((x + local_x, y + local_y) for local_x, local_y in cells_for(piece, rotation))
