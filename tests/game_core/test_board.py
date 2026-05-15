from __future__ import annotations

import pytest

from p2p_tetris.common import GameConfig
from p2p_tetris.game_core import Board, GarbageInjection, PieceType


def test_board_uses_hidden_rows_before_visible_rows() -> None:
    board = Board(GameConfig())

    assert board.width == 10
    assert board.total_rows == 40
    assert board.visible_start_y == 20
    assert board.in_bounds(0, 0)
    assert board.in_bounds(9, 39)
    assert not board.in_bounds(10, 39)
    assert not board.in_bounds(0, 40)
    assert not board.is_visible_y(19)
    assert board.is_visible_y(20)


def test_board_collision_and_hidden_snapshot() -> None:
    board = Board()
    cells = ((4, 19), (5, 19), (4, 20), (5, 20))

    assert board.can_place(cells)
    board.place(cells, PieceType.O)

    assert not board.can_place(cells)
    assert board.hidden_occupied_count() == 2
    assert board.snapshot_visible()[0][4] is PieceType.O


def test_clear_full_lines_compacts_from_above() -> None:
    board = Board()
    bottom_y = board.total_rows - 1
    for x in range(board.width):
        board.set_cell(x, bottom_y, PieceType.I)
    board.set_cell(3, bottom_y - 1, PieceType.T)

    assert board.clear_full_lines() == 1
    assert board.get(3, bottom_y) is PieceType.T
    assert all(board.get(x, 0) is None for x in range(board.width))


def test_garbage_injection_adds_bottom_rows_with_shared_hole() -> None:
    board = Board()

    board.apply_garbage(GarbageInjection(lines=2, hole=4))

    for y in (board.total_rows - 2, board.total_rows - 1):
        assert board.get(4, y) is None
        assert all(board.get(x, y) is PieceType.Z for x in range(board.width) if x != 4)


def test_garbage_rejects_invalid_payload() -> None:
    board = Board()

    with pytest.raises(ValueError, match="non-negative"):
        board.apply_garbage(GarbageInjection(lines=-1, hole=0))
    with pytest.raises(ValueError, match="within board width"):
        board.apply_garbage(GarbageInjection(lines=1, hole=99))
