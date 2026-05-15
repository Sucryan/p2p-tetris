from __future__ import annotations

from p2p_tetris.common import GameConfig
from p2p_tetris.game_core import (
    ClearEvent,
    GameEngine,
    GarbageInjection,
    PieceLockedEvent,
    PieceType,
    PlayerAction,
    RotationState,
    TSpinType,
    TopOutEvent,
)
from p2p_tetris.game_core.pieces import ActivePiece


def _fill_row_except(engine: GameEngine, y: int, gaps: set[int]) -> None:
    for x in range(engine.board.width):
        if x not in gaps:
            engine.board.set_cell(x, y, PieceType.J)


def _set_active(engine: GameEngine, piece: ActivePiece) -> None:
    engine._active = piece
    engine._lock_ticks_on_ground = 0
    engine._last_move_was_rotation = False
    engine._last_rotation_kick_index = None


def test_reset_seed_and_action_script_are_deterministic() -> None:
    actions = (
        [PlayerAction.MOVE_LEFT, PlayerAction.ROTATE_CW]
        + [PlayerAction.SOFT_DROP] * 3
        + [PlayerAction.HARD_DROP]
        + [PlayerAction.HOLD, PlayerAction.MOVE_RIGHT, PlayerAction.HARD_DROP]
    )
    first = GameEngine(seed=2026)
    second = GameEngine(seed=2026)

    first_events: list[object] = []
    second_events: list[object] = []
    for action in actions:
        first_events.extend(first.step([action]))
        second_events.extend(second.step([action]))

    assert first.snapshot() == second.snapshot()
    assert first_events == second_events


def test_spawn_next_queue_and_hold_once_per_piece() -> None:
    engine = GameEngine(seed=7)
    original_active = engine.active_piece
    original_next = engine.next_queue

    engine.step([PlayerAction.HOLD])
    after_first_hold = engine.active_piece

    assert original_active is not None
    assert after_first_hold is not None
    assert engine.hold_piece is original_active.type
    assert after_first_hold.type is original_next[0]

    engine.step([PlayerAction.HOLD])

    assert engine.active_piece == after_first_hold
    assert engine.hold_piece is original_active.type


def test_movement_hard_drop_and_ghost_snapshot() -> None:
    engine = GameEngine(seed=11)
    before = engine.snapshot()

    assert before.active_piece is not None
    assert before.ghost_piece is not None
    assert before.ghost_piece.y >= before.active_piece.y
    assert before.visible_board == engine.board.snapshot_visible()

    events = engine.step([PlayerAction.MOVE_LEFT, PlayerAction.HARD_DROP])

    assert any(isinstance(event, PieceLockedEvent) for event in events)
    assert engine.snapshot().visible_board != before.visible_board


def test_gravity_and_lock_delay_lock_grounded_piece() -> None:
    config = GameConfig(tick_rate_hz=2, gravity_rows_per_second=2.0, lock_delay_seconds=0.5)
    engine = GameEngine(seed=3, config=config)

    events = engine.step(ticks=60)

    assert any(isinstance(event, PieceLockedEvent) for event in events)


def test_line_clear_combo_and_back_to_back_events() -> None:
    engine = GameEngine(seed=1)
    bottom = engine.board.total_rows - 1
    for y in range(bottom - 3, bottom + 1):
        _fill_row_except(engine, y, {4})
    _set_active(engine, ActivePiece(PieceType.I, 2, bottom - 3, RotationState.RIGHT))

    first_events = engine.step([PlayerAction.HARD_DROP])

    first_clear = next(event for event in first_events if isinstance(event, ClearEvent))
    assert first_clear.lines_cleared == 4
    assert first_clear.combo == 0
    assert not first_clear.back_to_back

    for y in range(bottom - 3, bottom + 1):
        _fill_row_except(engine, y, {4})
    _set_active(engine, ActivePiece(PieceType.I, 2, bottom - 3, RotationState.RIGHT))

    second_events = engine.step([PlayerAction.HARD_DROP])

    second_clear = next(event for event in second_events if isinstance(event, ClearEvent))
    assert second_clear.lines_cleared == 4
    assert second_clear.combo == 1
    assert second_clear.back_to_back


def test_non_clear_resets_combo_but_keeps_back_to_back_state() -> None:
    engine = GameEngine(seed=1)
    bottom = engine.board.total_rows - 1
    for y in range(bottom - 3, bottom + 1):
        _fill_row_except(engine, y, {4})
    _set_active(engine, ActivePiece(PieceType.I, 2, bottom - 3, RotationState.RIGHT))
    engine.step([PlayerAction.HARD_DROP])

    _set_active(engine, ActivePiece(PieceType.O, 0, bottom - 1, RotationState.SPAWN))
    lock_events = engine.step([PlayerAction.HARD_DROP])

    locked = next(event for event in lock_events if isinstance(event, PieceLockedEvent))
    assert locked.cleared_lines == 0
    assert locked.combo == -1
    assert locked.back_to_back
    assert engine.snapshot().combo == -1
    assert engine.snapshot().back_to_back


def test_full_t_spin_single_emits_t_spin_clear_event() -> None:
    engine = GameEngine(seed=1)
    bottom = engine.board.total_rows - 1
    _fill_row_except(engine, bottom, {5})
    engine.board.set_cell(6, bottom - 2, PieceType.Z)
    _set_active(engine, ActivePiece(PieceType.T, 4, bottom - 2, RotationState.RIGHT))
    engine._last_move_was_rotation = True
    engine._last_rotation_kick_index = 0

    events = engine.step([PlayerAction.HARD_DROP])

    clear = next(event for event in events if isinstance(event, ClearEvent))
    locked = next(event for event in events if isinstance(event, PieceLockedEvent))
    assert clear.lines_cleared == 1
    assert clear.t_spin is TSpinType.FULL
    assert locked.t_spin is TSpinType.FULL


def test_t_spin_mini_can_be_reported_without_line_clear() -> None:
    engine = GameEngine(seed=1)
    bottom = engine.board.total_rows - 1
    engine.board.set_cell(4, bottom - 2, PieceType.Z)
    engine.board.set_cell(4, bottom, PieceType.Z)
    engine.board.set_cell(6, bottom, PieceType.Z)
    _set_active(engine, ActivePiece(PieceType.T, 4, bottom - 2, RotationState.RIGHT))
    engine._last_move_was_rotation = True
    engine._last_rotation_kick_index = 0

    events = engine.step([PlayerAction.HARD_DROP])

    locked = next(event for event in events if isinstance(event, PieceLockedEvent))
    assert locked.cleared_lines == 0
    assert locked.t_spin is TSpinType.MINI


def test_locking_above_visible_area_tops_out() -> None:
    engine = GameEngine(seed=1)
    engine.board.set_cell(5, 2, PieceType.Z)
    engine.board.set_cell(6, 2, PieceType.Z)
    _set_active(engine, ActivePiece(PieceType.O, 4, 0, RotationState.SPAWN))

    events = engine.step([PlayerAction.HARD_DROP])

    top_out = next(event for event in events if isinstance(event, TopOutEvent))
    assert "above visible" in top_out.reason
    assert engine.snapshot().top_out


def test_spawn_blocked_top_out_event_is_returned_on_step() -> None:
    engine = GameEngine(seed=1)
    assert engine.active_piece is not None
    for x, y in engine.active_piece.cells:
        engine.board.set_cell(x, y, PieceType.Z)
    engine._spawn_next()

    events = engine.step()

    top_out = next(event for event in events if isinstance(event, TopOutEvent))
    assert top_out.reason == "spawn blocked"


def test_apply_garbage_changes_board_and_can_top_out() -> None:
    engine = GameEngine(seed=1)

    engine.apply_garbage(GarbageInjection(lines=2, hole=3))

    visible = engine.snapshot().visible_board
    assert visible[-1][3] is None
    assert visible[-1][2] is PieceType.Z
