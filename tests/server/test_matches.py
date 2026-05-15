from __future__ import annotations

from p2p_tetris.common import MatchConfig, PlayerId, SessionId
from p2p_tetris.net import AttackReported, ClientStateSummary, GarbageAssigned, KOReported, MatchEnd
from p2p_tetris.server.matches import MatchManager


def test_match_start_timer_attack_ko_summary_and_player_left(fake_clock) -> None:
    manager = MatchManager(fake_clock, MatchConfig(match_seconds=120.0, ko_target=3))
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    start = manager.start_if_ready((p1, p2))

    assert start is not None
    assert start.active_players == (p1, p2)

    attack = AttackReported(
        SessionId("s1"),
        start.match_id,
        p1,
        p2,
        1,
        4,
        "a1",
    )
    outputs = manager.handle_reliable_gameplay(attack)
    assert isinstance(outputs[0], GarbageAssigned)
    assert outputs[0].target_id == p2

    summary = ClientStateSummary(SessionId("s1"), start.match_id, p1, 1, 8, 0, 0, 4, True, {})
    relay = manager.relay_summary(summary)
    assert relay is not None
    assert relay.player_id == p2
    assert relay.opponent_id == p1

    for seq in range(2, 5):
        outputs = manager.handle_reliable_gameplay(
            KOReported(SessionId("s1"), start.match_id, p2, p2, seq),
        )

    assert any(isinstance(message, MatchEnd) for message in outputs)
    assert any(
        isinstance(message, MatchEnd) and message.winner_id == p1
        for message in outputs
    )
    assert manager.current_match is None


def test_match_timeout_draw(fake_clock) -> None:
    manager = MatchManager(fake_clock, MatchConfig(match_seconds=1.0))
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    start = manager.start_if_ready((p1, p2))
    assert start is not None

    fake_clock.advance(1.0)
    end = manager.tick()

    assert end is not None
    assert end.reason == "draw"


def test_match_timeout_uses_board_height_tiebreaker_from_client_summary(fake_clock) -> None:
    manager = MatchManager(fake_clock, MatchConfig(match_seconds=1.0))
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    start = manager.start_if_ready((p1, p2))
    assert start is not None

    manager.relay_summary(ClientStateSummary(SessionId("s1"), start.match_id, p1, 1, 4, 0, 0, 0, True, {}))
    manager.relay_summary(ClientStateSummary(SessionId("s2"), start.match_id, p2, 1, 8, 0, 0, 0, True, {}))
    fake_clock.advance(1.0)
    end = manager.tick()

    assert end is not None
    assert end.winner_id == p1
    assert end.reason == "timeout"


def test_match_attack_cancels_pending_incoming_before_assigning_garbage(fake_clock) -> None:
    manager = MatchManager(fake_clock, MatchConfig(match_seconds=120.0, ko_target=3))
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    start = manager.start_if_ready((p1, p2))
    assert start is not None

    first = manager.handle_reliable_gameplay(
        AttackReported(SessionId("s1"), start.match_id, p1, p2, 1, 4, "a1"),
    )
    assert any(isinstance(message, GarbageAssigned) and message.lines == 4 for message in first)

    canceled = manager.handle_reliable_gameplay(
        AttackReported(SessionId("s2"), start.match_id, p2, p1, 2, 3, "a2"),
    )

    cancellation = next(message for message in canceled if isinstance(message, GarbageAssigned))
    assert cancellation.target_id == p2
    assert cancellation.lines == 0
    assert cancellation.canceled_lines == 3
    assert manager.current_match is not None
    assert manager.current_match.sent_lines[p2] == 0
