"""Deterministic single-player Tetris engine."""

from __future__ import annotations

from collections.abc import Iterable

from p2p_tetris.common import GameConfig
from p2p_tetris.game_core.actions import PlayerAction
from p2p_tetris.game_core.board import Board, GarbageInjection
from p2p_tetris.game_core.events import (
    ClearEvent,
    GameEvent,
    PieceLockedEvent,
    TSpinType,
    TopOutEvent,
)
from p2p_tetris.game_core.pieces import ActivePiece, PieceType, RotationState
from p2p_tetris.game_core.randomizer import SevenBagRandomizer
from p2p_tetris.game_core.rotation import rotate_piece
from p2p_tetris.game_core.snapshots import GameStateSnapshot


class GameEngine:
    """Single-player deterministic engine.

    The board uses top-origin coordinates with hidden rows first. The engine is
    deliberately local-only: it does not know about matches, KO scoring, or
    network state.
    """

    def __init__(
        self,
        seed: int | str | bytes | bytearray | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self.reset(seed=seed, config=config)

    def reset(
        self,
        seed: int | str | bytes | bytearray | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self.config = config or GameConfig()
        self.board = Board(self.config)
        self._randomizer = SevenBagRandomizer(seed)
        self._next_queue: list[PieceType] = []
        self._active: ActivePiece | None = None
        self._hold: PieceType | None = None
        self._hold_used = False
        self._combo = -1
        self._back_to_back = False
        self._score = 0
        self._cleared_lines = 0
        self._top_out = False
        self._top_out_reason: str | None = None
        self._gravity_progress = 0.0
        self._soft_drop_progress = 0.0
        self._lock_ticks_on_ground = 0
        self._last_move_was_rotation = False
        self._last_rotation_kick_index: int | None = None
        self._pending_garbage_lines = 0
        self._fill_next_queue()
        self._spawn_next()

    @property
    def active_piece(self) -> ActivePiece | None:
        return self._active

    @property
    def hold_piece(self) -> PieceType | None:
        return self._hold

    @property
    def next_queue(self) -> tuple[PieceType, ...]:
        return tuple(self._next_queue[: self.config.next_queue_size])

    @property
    def top_out(self) -> bool:
        return self._top_out

    def step(
        self,
        actions: Iterable[PlayerAction] = (),
        ticks: int = 1,
    ) -> tuple[GameEvent, ...]:
        """Advance the engine by fixed ticks and return emitted events."""

        if ticks < 0:
            msg = "ticks must be non-negative"
            raise ValueError(msg)
        if self._top_out:
            return self._top_out_event_if_needed()

        events: list[GameEvent] = []
        action_tuple = tuple(actions)
        for tick_index in range(ticks):
            if self._top_out:
                break
            current_actions = action_tuple if tick_index == 0 else ()
            for action in current_actions:
                events.extend(self._apply_action(action))
                if self._top_out:
                    break
            if not self._top_out:
                events.extend(self._advance_gravity(current_actions))
        return tuple(events)

    def apply_garbage(self, injection: GarbageInjection) -> None:
        """Apply core-local garbage immediately to the board."""

        self.board.apply_garbage(injection)
        if self._active is not None and not self.board.can_place(self._active.cells):
            self._set_top_out("garbage collision")
        if self.board.any_hidden_blocks():
            self._set_top_out("garbage pushed blocks into hidden rows")

    def snapshot(self) -> GameStateSnapshot:
        ghost = self._ghost_piece()
        active_cells = () if self._active is None else self._active.cells
        ghost_cells = () if ghost is None else ghost.cells
        return GameStateSnapshot(
            visible_board=self.board.snapshot_visible(),
            hidden_occupied_count=self.board.hidden_occupied_count(),
            active_piece=self._active,
            active_cells=active_cells,
            ghost_piece=ghost,
            ghost_cells=ghost_cells,
            hold_piece=self._hold,
            next_queue=self.next_queue,
            combo=self._combo,
            back_to_back=self._back_to_back,
            score=self._score,
            cleared_lines=self._cleared_lines,
            top_out=self._top_out,
            pending_garbage_lines=self._pending_garbage_lines,
        )

    def _fill_next_queue(self) -> None:
        while len(self._next_queue) < self.config.next_queue_size + 1:
            self._next_queue.append(self._randomizer.next_piece())

    def _spawn_origin(self, piece: PieceType) -> tuple[int, int]:
        _ = piece
        return (self.config.board_width - 4) // 2, self.config.hidden_rows - 2

    def _spawn_piece(self, piece: PieceType) -> None:
        x, y = self._spawn_origin(piece)
        candidate = ActivePiece(piece, x, y, RotationState.SPAWN)
        self._active = candidate
        self._hold_used = False
        self._gravity_progress = 0.0
        self._soft_drop_progress = 0.0
        self._lock_ticks_on_ground = 0
        self._last_move_was_rotation = False
        self._last_rotation_kick_index = None
        if not self.board.can_place(candidate.cells):
            self._set_top_out("spawn blocked")

    def _spawn_next(self) -> None:
        self._fill_next_queue()
        piece = self._next_queue.pop(0)
        self._fill_next_queue()
        self._spawn_piece(piece)

    def _apply_action(self, action: PlayerAction) -> tuple[GameEvent, ...]:
        if self._active is None or self._top_out or action is PlayerAction.NO_OP:
            return ()
        if action is PlayerAction.MOVE_LEFT:
            self._try_shift(-1, 0)
            return ()
        if action is PlayerAction.MOVE_RIGHT:
            self._try_shift(1, 0)
            return ()
        if action is PlayerAction.SOFT_DROP:
            if self._try_shift(0, 1):
                self._score += 1
            return ()
        if action is PlayerAction.HARD_DROP:
            return self._hard_drop()
        if action is PlayerAction.ROTATE_CW:
            self._try_rotate(clockwise=True)
            return ()
        if action is PlayerAction.ROTATE_CCW:
            self._try_rotate(clockwise=False)
            return ()
        if action is PlayerAction.HOLD:
            return self._hold_current()
        raise AssertionError(f"unknown action: {action}")

    def _try_shift(self, dx: int, dy: int) -> bool:
        if self._active is None:
            return False
        candidate = ActivePiece(
            self._active.type,
            self._active.x + dx,
            self._active.y + dy,
            self._active.rotation,
        )
        if not self.board.can_place(candidate.cells):
            return False
        self._active = candidate
        if dx != 0:
            self._last_move_was_rotation = False
            self._last_rotation_kick_index = None
        if dy == 0:
            self._lock_ticks_on_ground = 0
        return True

    def _try_rotate(self, *, clockwise: bool) -> bool:
        if self._active is None:
            return False
        rotated = rotate_piece(self._active, clockwise, self.board)
        if rotated is None:
            return False
        self._active, kick_index = rotated
        self._last_move_was_rotation = True
        self._last_rotation_kick_index = kick_index
        self._lock_ticks_on_ground = 0
        return True

    def _hard_drop(self) -> tuple[GameEvent, ...]:
        if self._active is None:
            return ()
        distance = 0
        while self._try_shift(0, 1):
            distance += 1
        self._score += distance * 2
        return self._lock_active()

    def _hold_current(self) -> tuple[GameEvent, ...]:
        if self._active is None or self._hold_used:
            return ()
        current = self._active.type
        if self._hold is None:
            self._hold = current
            self._spawn_next()
        else:
            self._hold, swapped = current, self._hold
            self._spawn_piece(swapped)
        self._hold_used = True
        return self._top_out_event_if_needed()

    def _advance_gravity(self, actions: tuple[PlayerAction, ...]) -> tuple[GameEvent, ...]:
        if self._active is None:
            return ()
        if PlayerAction.SOFT_DROP in actions:
            self._soft_drop_progress += (
                self.config.soft_drop_rows_per_second / self.config.tick_rate_hz
            )
            while self._soft_drop_progress >= 1.0 and self._try_shift(0, 1):
                self._soft_drop_progress -= 1.0
                self._score += 1
        else:
            self._soft_drop_progress = 0.0

        self._gravity_progress += self.config.gravity_rows_per_second / self.config.tick_rate_hz
        while self._gravity_progress >= 1.0:
            self._gravity_progress -= 1.0
            if not self._try_shift(0, 1):
                break

        if self._can_fall():
            self._lock_ticks_on_ground = 0
            return ()

        self._lock_ticks_on_ground += 1
        lock_delay_ticks = max(1, round(self.config.lock_delay_seconds * self.config.tick_rate_hz))
        if self._lock_ticks_on_ground >= lock_delay_ticks:
            return self._lock_active()
        return ()

    def _can_fall(self) -> bool:
        if self._active is None:
            return False
        candidate = ActivePiece(
            self._active.type,
            self._active.x,
            self._active.y + 1,
            self._active.rotation,
        )
        return self.board.can_place(candidate.cells)

    def _lock_active(self) -> tuple[GameEvent, ...]:
        if self._active is None:
            return ()
        piece = self._active
        cells = piece.cells
        t_spin = self._classify_t_spin(piece)
        self.board.place(cells, piece.type)
        locked_above_visible = any(y < self.config.hidden_rows for _, y in cells)
        cleared = self.board.clear_full_lines()
        combo = self._update_combo(cleared)
        back_to_back = self._update_back_to_back(cleared, t_spin)
        self._cleared_lines += cleared
        self._score += self._line_clear_score(cleared, t_spin, back_to_back)

        events: list[GameEvent] = [
            PieceLockedEvent(
                piece=piece.type,
                cells=tuple(cells),
                cleared_lines=cleared,
                t_spin=t_spin,
                combo=combo,
                back_to_back=back_to_back,
            ),
        ]
        if cleared:
            events.append(
                ClearEvent(
                    lines_cleared=cleared,
                    t_spin=t_spin,
                    combo=combo,
                    back_to_back=back_to_back,
                ),
            )

        self._active = None
        if locked_above_visible:
            self._set_top_out("piece locked above visible area")
            events.extend(self._top_out_event_if_needed())
            return tuple(events)

        self._spawn_next()
        events.extend(self._top_out_event_if_needed())
        return tuple(events)

    def _update_combo(self, cleared: int) -> int:
        if cleared:
            self._combo = 0 if self._combo < 0 else self._combo + 1
            return self._combo
        self._combo = -1
        return -1

    def _update_back_to_back(self, cleared: int, t_spin: TSpinType) -> bool:
        if not cleared:
            return self._back_to_back
        difficult = cleared == 4 or t_spin is not TSpinType.NONE
        event_back_to_back = difficult and self._back_to_back
        self._back_to_back = difficult
        return event_back_to_back

    def _line_clear_score(
        self,
        cleared: int,
        t_spin: TSpinType,
        back_to_back: bool,
    ) -> int:
        if not cleared:
            return 0
        base = {1: 100, 2: 300, 3: 500, 4: 800}[cleared]
        if t_spin is TSpinType.MINI:
            base += 100
        elif t_spin is TSpinType.FULL:
            base += 400
        if back_to_back:
            base += 200
        if self._combo > 0:
            base += self._combo * 50
        return base

    def _classify_t_spin(self, piece: ActivePiece) -> TSpinType:
        if piece.type is not PieceType.T or not self._last_move_was_rotation:
            return TSpinType.NONE
        corners = (
            (piece.x, piece.y),
            (piece.x + 2, piece.y),
            (piece.x, piece.y + 2),
            (piece.x + 2, piece.y + 2),
        )
        occupied = sum(1 for x, y in corners if self._corner_blocked(x, y))
        if occupied < 3:
            return TSpinType.NONE

        front_corners = self._front_corners(piece)
        front_occupied = sum(1 for x, y in front_corners if self._corner_blocked(x, y))
        if front_occupied == 2 or self._last_rotation_kick_index == 4:
            return TSpinType.FULL
        return TSpinType.MINI

    def _corner_blocked(self, x: int, y: int) -> bool:
        return not self.board.in_bounds(x, y) or self.board.get(x, y) is not None

    def _front_corners(self, piece: ActivePiece) -> tuple[tuple[int, int], tuple[int, int]]:
        if piece.rotation is RotationState.SPAWN:
            return (piece.x, piece.y), (piece.x + 2, piece.y)
        if piece.rotation is RotationState.RIGHT:
            return (piece.x + 2, piece.y), (piece.x + 2, piece.y + 2)
        if piece.rotation is RotationState.REVERSE:
            return (piece.x, piece.y + 2), (piece.x + 2, piece.y + 2)
        return (piece.x, piece.y), (piece.x, piece.y + 2)

    def _ghost_piece(self) -> ActivePiece | None:
        if self._active is None:
            return None
        ghost = self._active
        while True:
            candidate = ActivePiece(ghost.type, ghost.x, ghost.y + 1, ghost.rotation)
            if not self.board.can_place(candidate.cells):
                return ghost
            ghost = candidate

    def _set_top_out(self, reason: str) -> None:
        if self._top_out:
            return
        self._top_out = True
        self._top_out_reason = reason

    def _top_out_event_if_needed(self) -> tuple[TopOutEvent, ...]:
        if self._top_out and self._top_out_reason is not None:
            reason = self._top_out_reason
            self._top_out_reason = None
            return (TopOutEvent(reason=reason),)
        return ()
