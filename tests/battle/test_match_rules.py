from __future__ import annotations

from typing import Protocol

from p2p_tetris.battle import BattleCoordinator, MatchResult, WinnerResolver
from p2p_tetris.battle._game_core_events import ClearEvent, TSpinType, TopOutEvent
from p2p_tetris.battle.scoring import PlayerBattleStats
from p2p_tetris.common import MatchConfig, PlayerId


class AdvancingClock(Protocol):
    def now(self) -> float: ...

    def advance(self, seconds: float) -> None: ...


def test_top_out_creates_ko_then_respawn_after_delay_and_resets_pending_garbage(
    fake_clock: AdvancingClock,
) -> None:
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    coordinator = BattleCoordinator(
        players=(p1, p2),
        clock=fake_clock,
        config=MatchConfig(respawn_delay_seconds=1.5),
    )
    coordinator.handle_clear(p1, ClearEvent(4, TSpinType.NONE, 0, False))
    assert coordinator.handle_lock(p2) != ()

    events = coordinator.handle_top_out(p2, TopOutEvent("spawn_blocked"))

    assert events[0].source == p1
    assert events[0].to_dict()["type"] == "ko"
    assert coordinator.scoreboard[p1].ko_count == 1
    assert coordinator.scoreboard[p1].sent_lines == 4
    assert coordinator.handle_lock(p2) == ()
    fake_clock.advance(1.49)
    assert coordinator.tick() == ()
    fake_clock.advance(0.01)
    respawns = coordinator.tick()
    assert len(respawns) == 1
    assert respawns[0].player == p2


def test_winner_resolver_uses_ko_sent_lines_then_lower_height_and_allows_draw() -> None:
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    resolver = WinnerResolver()

    assert resolver.resolve(
        stats=(
            PlayerBattleStats(player=p1, ko_count=2, sent_lines=0, board_height=20),
            PlayerBattleStats(player=p2, ko_count=1, sent_lines=99, board_height=0),
        ),
        reason="timeout",
        seq=1,
    ).winner == p1
    assert resolver.resolve(
        stats=(
            PlayerBattleStats(player=p1, ko_count=1, sent_lines=10, board_height=20),
            PlayerBattleStats(player=p2, ko_count=1, sent_lines=11, board_height=19),
        ),
        reason="timeout",
        seq=2,
    ).winner == p2
    assert resolver.resolve(
        stats=(
            PlayerBattleStats(player=p1, ko_count=1, sent_lines=10, board_height=4),
            PlayerBattleStats(player=p2, ko_count=1, sent_lines=10, board_height=8),
        ),
        reason="timeout",
        seq=3,
    ).winner == p1
    assert resolver.resolve(
        stats=(
            PlayerBattleStats(player=p1, ko_count=1, sent_lines=10, board_height=4),
            PlayerBattleStats(player=p2, ko_count=1, sent_lines=10, board_height=4),
        ),
        reason="timeout",
        seq=4,
    ) == MatchResult(source=None, seq=4, winner=None, is_draw=True, reason="timeout")


def test_battle_coordinator_can_simulate_match_level_sequence(
    fake_clock: AdvancingClock,
) -> None:
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    coordinator = BattleCoordinator(players=(p1, p2), clock=fake_clock)

    clear_events = coordinator.handle_clear(p1, ClearEvent(4, TSpinType.NONE, 0, True), board_height=3)
    garbage_events = coordinator.handle_lock(p2, board_height=6)
    result = coordinator.resolve_timeout(board_heights={p1: 3, p2: 6})

    assert [event.to_dict()["type"] for event in clear_events] == ["attack", "garbage"]
    assert len(garbage_events) == 1
    assert result.winner == p1
