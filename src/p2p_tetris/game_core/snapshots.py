"""Immutable game state snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.game_core.board import CellValue
from p2p_tetris.game_core.pieces import ActivePiece, PieceType


@dataclass(frozen=True, slots=True)
class GameStateSnapshot:
    """Read-only state exposed to GUI, runtime, tests, and future RL agents."""

    visible_board: tuple[tuple[CellValue, ...], ...]
    hidden_occupied_count: int
    active_piece: ActivePiece | None
    active_cells: tuple[tuple[int, int], ...]
    ghost_piece: ActivePiece | None
    ghost_cells: tuple[tuple[int, int], ...]
    hold_piece: PieceType | None
    next_queue: tuple[PieceType, ...]
    combo: int
    back_to_back: bool
    score: int
    cleared_lines: int
    top_out: bool
    pending_garbage_lines: int
