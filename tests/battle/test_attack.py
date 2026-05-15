from __future__ import annotations

import json
from pathlib import Path

from p2p_tetris.battle import AttackCalculator, AttackTable
from p2p_tetris.battle._game_core_events import ClearEvent, TSpinType
from p2p_tetris.common import PlayerId


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "battle" / "attack_table.json"


def test_default_attack_table_matches_fixture() -> None:
    with FIXTURE.open() as handle:
        data = json.load(handle)

    assert AttackTable.default().to_dict() == data


def test_attack_calculator_maps_clear_events_to_lines() -> None:
    calculator = AttackCalculator()
    source = PlayerId("p1")
    target = PlayerId("p2")
    cases = (
        (ClearEvent(1, TSpinType.NONE, 0, False), 0),
        (ClearEvent(2, TSpinType.NONE, 0, False), 1),
        (ClearEvent(3, TSpinType.NONE, 0, False), 2),
        (ClearEvent(4, TSpinType.NONE, 0, False), 4),
        (ClearEvent(1, TSpinType.MINI, 0, False), 1),
        (ClearEvent(1, TSpinType.FULL, 0, False), 2),
        (ClearEvent(2, TSpinType.FULL, 0, False), 4),
        (ClearEvent(3, TSpinType.FULL, 0, False), 6),
        (ClearEvent(4, TSpinType.NONE, 0, True), 5),
        (ClearEvent(4, TSpinType.NONE, 6, True), 8),
    )

    for seq, (clear_event, expected_lines) in enumerate(cases):
        attack = calculator.calculate(clear_event, source=source, target=target, seq=seq)
        assert attack.lines == expected_lines
        assert attack.source == source
        assert attack.target == target
        assert attack.seq == seq
