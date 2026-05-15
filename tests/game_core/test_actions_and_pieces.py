from __future__ import annotations

from p2p_tetris.game_core import PieceType, PlayerAction, RotationState
from p2p_tetris.game_core.pieces import cells_for


def test_player_action_enum_is_fixed_to_gameplay_actions() -> None:
    assert [action.name for action in PlayerAction] == [
        "NO_OP",
        "MOVE_LEFT",
        "MOVE_RIGHT",
        "SOFT_DROP",
        "HARD_DROP",
        "ROTATE_CW",
        "ROTATE_CCW",
        "HOLD",
    ]
    assert "PAUSE" not in PlayerAction.__members__
    assert "RESTART" not in PlayerAction.__members__


def test_every_piece_has_four_orientations_with_four_cells() -> None:
    for piece in PieceType:
        orientations = [cells_for(piece, rotation) for rotation in RotationState]
        assert len(orientations) == 4
        assert all(len(cells) == 4 for cells in orientations)
