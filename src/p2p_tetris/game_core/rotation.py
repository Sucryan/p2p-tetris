"""Guideline SRS wall kick tables and rotation helper."""

from __future__ import annotations

from p2p_tetris.game_core.board import Board
from p2p_tetris.game_core.pieces import ActivePiece, PieceType, RotationState

Kick = tuple[int, int]

JLSTZ_KICKS: dict[tuple[RotationState, RotationState], tuple[Kick, ...]] = {
    (RotationState.SPAWN, RotationState.RIGHT): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (RotationState.RIGHT, RotationState.SPAWN): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (RotationState.RIGHT, RotationState.REVERSE): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (RotationState.REVERSE, RotationState.RIGHT): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (RotationState.REVERSE, RotationState.LEFT): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (RotationState.LEFT, RotationState.REVERSE): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (RotationState.LEFT, RotationState.SPAWN): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (RotationState.SPAWN, RotationState.LEFT): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
}

I_KICKS: dict[tuple[RotationState, RotationState], tuple[Kick, ...]] = {
    (RotationState.SPAWN, RotationState.RIGHT): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (RotationState.RIGHT, RotationState.SPAWN): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (RotationState.RIGHT, RotationState.REVERSE): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
    (RotationState.REVERSE, RotationState.RIGHT): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (RotationState.REVERSE, RotationState.LEFT): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (RotationState.LEFT, RotationState.REVERSE): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (RotationState.LEFT, RotationState.SPAWN): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (RotationState.SPAWN, RotationState.LEFT): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
}


def kicks_for(
    piece: PieceType,
    from_rotation: RotationState,
    to_rotation: RotationState,
) -> tuple[Kick, ...]:
    """Return the SRS kick sequence for one rotation transition."""

    if piece is PieceType.O:
        return ((0, 0),)
    table = I_KICKS if piece is PieceType.I else JLSTZ_KICKS
    return table[(from_rotation, to_rotation)]


def rotate_piece(piece: ActivePiece, clockwise: bool, board: Board) -> tuple[ActivePiece, int] | None:
    """Try to rotate a piece with SRS kicks.

    Returns the rotated piece and the zero-based kick index, or ``None`` when
    every kick collides.
    """

    target = piece.rotation.rotate_cw() if clockwise else piece.rotation.rotate_ccw()
    for index, (dx, dy) in enumerate(kicks_for(piece.type, piece.rotation, target)):
        candidate = ActivePiece(piece.type, piece.x + dx, piece.y + dy, target)
        if board.can_place(candidate.cells):
            return candidate, index
    return None
