"""Runtime view models consumed by GUI layers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from p2p_tetris.common import MatchId, PlayerId
from p2p_tetris.game_core import GameStateSnapshot, PieceType


CellView = PieceType | None


class ConnectionState(Enum):
    """High-level client connection and match state."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    QUEUED = auto()
    IN_MATCH = auto()
    ENDED = auto()


@dataclass(frozen=True, slots=True)
class BoardViewModel:
    width: int
    height: int
    cells: tuple[tuple[CellView, ...], ...]
    active_piece: PieceType | None
    active_cells: tuple[tuple[int, int], ...]
    ghost_cells: tuple[tuple[int, int], ...]
    top_out: bool
    pending_garbage_lines: int

    @classmethod
    def from_snapshot(
        cls,
        snapshot: GameStateSnapshot,
        *,
        hidden_rows: int = 0,
    ) -> BoardViewModel:
        height = len(snapshot.visible_board)
        width = len(snapshot.visible_board[0]) if height else 0
        return cls(
            width=width,
            height=height,
            cells=snapshot.visible_board,
            active_piece=None if snapshot.active_piece is None else snapshot.active_piece.type,
            active_cells=_visible_cells(snapshot.active_cells, hidden_rows, height),
            ghost_cells=_visible_cells(snapshot.ghost_cells, hidden_rows, height),
            top_out=snapshot.top_out,
            pending_garbage_lines=snapshot.pending_garbage_lines,
        )


@dataclass(frozen=True, slots=True)
class PiecePreviewViewModel:
    hold_piece: PieceType | None
    next_queue: tuple[PieceType, ...]

    @classmethod
    def from_snapshot(cls, snapshot: GameStateSnapshot) -> PiecePreviewViewModel:
        return cls(hold_piece=snapshot.hold_piece, next_queue=snapshot.next_queue)


@dataclass(frozen=True, slots=True)
class SoloHudViewModel:
    score: int
    cleared_lines: int
    combo: int
    back_to_back: bool
    tick: int
    is_running: bool
    is_paused: bool


@dataclass(frozen=True, slots=True)
class VersusHudViewModel:
    match_id: MatchId | None
    local_player_id: PlayerId
    opponent_player_id: PlayerId | None
    remaining_seconds: float
    ko_counts: dict[str, int]
    sent_lines: dict[str, int]
    pending_garbage_lines: int
    is_alive: bool


@dataclass(frozen=True, slots=True)
class ConnectionViewModel:
    state: ConnectionState
    message: str = ""


@dataclass(frozen=True, slots=True)
class OpponentViewModel:
    player_id: PlayerId
    summary_seq: int
    board_height: int
    pending_garbage: int
    ko_count: int
    sent_lines: int
    is_alive: bool
    extra: dict[str, object]


@dataclass(frozen=True, slots=True)
class MatchResultViewModel:
    match_id: MatchId
    winner_id: PlayerId | None
    is_draw: bool
    reason: str
    ko_counts: dict[str, int]
    sent_lines: dict[str, int]


@dataclass(frozen=True, slots=True)
class GameViewModel:
    board: BoardViewModel
    preview: PiecePreviewViewModel
    solo_hud: SoloHudViewModel
    connection: ConnectionViewModel
    versus_hud: VersusHudViewModel | None = None
    opponents: tuple[OpponentViewModel, ...] = ()
    result: MatchResultViewModel | None = None


def board_height(snapshot: GameStateSnapshot) -> int:
    """Visible stack height, where lower values mean a cleaner board."""

    for row_index, row in enumerate(snapshot.visible_board):
        if any(cell is not None for cell in row):
            return len(snapshot.visible_board) - row_index
    return 0


def _visible_cells(
    cells: tuple[tuple[int, int], ...],
    hidden_rows: int,
    height: int,
) -> tuple[tuple[int, int], ...]:
    visible: list[tuple[int, int]] = []
    for x, y in cells:
        visible_y = y - hidden_rows
        if 0 <= visible_y < height:
            visible.append((x, visible_y))
    return tuple(visible)


__all__ = [
    "BoardViewModel",
    "CellView",
    "ConnectionState",
    "ConnectionViewModel",
    "GameViewModel",
    "MatchResultViewModel",
    "OpponentViewModel",
    "PiecePreviewViewModel",
    "SoloHudViewModel",
    "VersusHudViewModel",
    "board_height",
]
