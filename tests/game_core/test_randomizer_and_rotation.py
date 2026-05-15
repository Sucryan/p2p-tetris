from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from p2p_tetris.game_core import Board, PieceType, RotationState
from p2p_tetris.game_core.pieces import ActivePiece
from p2p_tetris.game_core.randomizer import SevenBagRandomizer
from p2p_tetris.game_core.rotation import rotate_piece


def test_seven_bag_is_deterministic_and_each_bag_contains_all_pieces() -> None:
    first = SevenBagRandomizer(seed=1234).take(14)
    second = SevenBagRandomizer(seed=1234).take(14)

    assert first == second
    assert set(first[:7]) == set(PieceType)
    assert set(first[7:14]) == set(PieceType)


def test_srs_rotation_fixture_cases() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "game_core" / "srs_cases.json"
    )
    cases: list[dict[str, Any]] = json.loads(fixture_path.read_text())

    for case in cases:
        board = Board()
        for x, y in case["blockers"]:
            board.set_cell(x, y, PieceType.Z)
        piece = ActivePiece(
            PieceType[case["piece"]],
            case["x"],
            case["y"],
            RotationState[case["rotation"]],
        )

        result = rotate_piece(piece, clockwise=case["direction"] == "cw", board=board)

        assert result is not None, case["name"]
        rotated, kick_index = result
        expected = case["expected"]
        assert (rotated.x, rotated.y, rotated.rotation.name, kick_index) == (
            expected["x"],
            expected["y"],
            expected["rotation"],
            expected["kick_index"],
        )
