from __future__ import annotations

from p2p_tetris.battle import (
    AttackEvent,
    GarbageEvent,
    GarbageRow,
    KOEvent,
    MatchResult,
    RespawnEvent,
    event_from_dict,
)
from p2p_tetris.common import PlayerId


def test_battle_events_are_comparable_and_serializable() -> None:
    player_1 = PlayerId("p1")
    player_2 = PlayerId("p2")
    events = (
        AttackEvent(source=player_1, seq=1, target=player_2, lines=4),
        GarbageEvent(
            source=player_1,
            seq=2,
            target=player_2,
            seed=99,
            rows=(GarbageRow(width=10, hole=3), GarbageRow(width=10, hole=3)),
        ),
        KOEvent(source=player_1, seq=3, knocked_out=player_2, respawn_at=1.5, reason="top_out"),
        RespawnEvent(source=player_2, seq=4, player=player_2),
        MatchResult(source=player_1, seq=5, winner=player_1, is_draw=False, reason="timeout"),
        MatchResult(source=None, seq=6, winner=None, is_draw=True, reason="timeout"),
    )

    for event in events:
        assert event_from_dict(event.to_dict()) == event


def test_garbage_row_represents_holed_model_without_fixed_payload_kind() -> None:
    row = GarbageRow(width=5, hole=2, filled_cell="heavy_garbage")

    assert row.cells() == ("heavy_garbage", "heavy_garbage", None, "heavy_garbage", "heavy_garbage")
