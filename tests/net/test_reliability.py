from __future__ import annotations

from p2p_tetris.common import MatchId, NetworkConfig, PlayerId, SessionId
from p2p_tetris.net import AttackReported, ClientStateSummary, MatchSnapshot
from p2p_tetris.net.reliability import LatestStateChannel, ReliableChannel


def _attack(seq: int = 1, *, match_id: MatchId | None = None) -> AttackReported:
    return AttackReported(
        session_id=SessionId("s1"),
        match_id=match_id or MatchId("m1"),
        sender_id=PlayerId("p1"),
        target_id=PlayerId("p2"),
        event_seq=seq,
        lines=4,
        attack_id=f"a{seq}",
    )


def test_duplicate_reliable_event_only_acks_once_in_application(fake_clock) -> None:
    channel = ReliableChannel(fake_clock)

    first = channel.mark_received(_attack(1))
    duplicate = channel.mark_received(_attack(1))

    assert first.apply is True
    assert duplicate.apply is False
    assert first.ack.received_seq == 1
    assert duplicate.ack.received_seq == 1


def test_reliable_dedupe_is_scoped_by_session_and_match(fake_clock) -> None:
    channel = ReliableChannel(fake_clock)

    first = channel.mark_received(_attack(1, match_id=MatchId("m1")))
    next_match_same_seq = channel.mark_received(_attack(1, match_id=MatchId("m2")))

    assert first.apply is True
    assert next_match_same_seq.apply is True


def test_reliable_resend_and_ack_use_fake_clock(fake_clock) -> None:
    channel = ReliableChannel(fake_clock, NetworkConfig(reliable_resend_seconds=0.1))
    channel.track_outgoing(_attack(1), PlayerId("p2"))

    fake_clock.advance(0.099)
    assert channel.due_resends() == []

    fake_clock.advance(0.001)
    due = channel.due_resends()
    assert due == [_attack(1)]

    decision = channel.mark_received(_attack(1))
    assert channel.mark_acked(decision.ack)
    assert channel.pending_count == 0


def test_session_timeout_uses_fake_clock(fake_clock) -> None:
    channel = ReliableChannel(fake_clock, NetworkConfig(session_timeout_seconds=2.0))

    assert channel.is_session_timed_out(0.0) is False
    fake_clock.advance(2.0)
    assert channel.is_session_timed_out(0.0) is True


def test_latest_state_channel_keeps_newest_snapshot_and_summary() -> None:
    channel = LatestStateChannel()
    match = MatchId("m1")
    player = PlayerId("p1")
    session = SessionId("s1")
    old = MatchSnapshot(match, 1, 0.0, 100.0, {}, {}, {"old": True})
    new = MatchSnapshot(match, 2, 0.1, 99.9, {}, {}, {"new": True})

    assert channel.apply(new)
    assert not channel.apply(old)
    assert channel.latest_snapshot(match) == new

    summary = ClientStateSummary(session, match, player, 4, 10, 1, 0, 0, True, {})
    assert channel.apply(summary)
    assert channel.latest_client_summary(match, player) == summary
