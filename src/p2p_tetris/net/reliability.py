"""Reliable gameplay delivery helpers for fake-clock tests and runtime use."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeGuard

from p2p_tetris.common import MatchId, NetworkConfig, PlayerId, SessionId
from p2p_tetris.common.time import MonotonicClock
from p2p_tetris.net.protocol import (
    ClientStateSummary,
    GarbageAssigned,
    MatchSnapshot,
    OpponentStateSummary,
    ProtocolMessage,
    ReliableAck,
    ReliableGameplayMessage,
)


@dataclass(frozen=True, slots=True)
class ReliableEnvelope:
    session_id: SessionId
    match_id: MatchId
    sender_id: PlayerId
    event_seq: int
    message: ReliableGameplayMessage
    sent_at: float


@dataclass(frozen=True, slots=True)
class ReceiveDecision:
    apply: bool
    ack: ReliableAck


@dataclass(slots=True)
class _PendingReliable:
    recipient_id: PlayerId
    envelope: ReliableEnvelope
    last_sent_at: float


class ReliableChannel:
    """Track outgoing reliable messages and deduplicate incoming messages."""

    def __init__(self, clock: MonotonicClock, config: NetworkConfig | None = None) -> None:
        self._clock = clock
        self._config = config or NetworkConfig()
        self._pending: dict[
            tuple[PlayerId, SessionId, MatchId, PlayerId, int],
            _PendingReliable,
        ] = {}
        self._received: set[tuple[SessionId, MatchId, PlayerId, int]] = set()

    def track_outgoing(
        self,
        message: ReliableGameplayMessage,
        recipient_id: PlayerId,
    ) -> ReliableEnvelope:
        envelope = ReliableEnvelope(
            session_id=message.session_id,
            match_id=message.match_id,
            sender_id=message.sender_id,
            event_seq=message.event_seq,
            message=message,
            sent_at=self._clock.now(),
        )
        key = (
            recipient_id,
            message.session_id,
            message.match_id,
            message.sender_id,
            message.event_seq,
        )
        self._pending[key] = _PendingReliable(
            recipient_id=recipient_id,
            envelope=envelope,
            last_sent_at=envelope.sent_at,
        )
        return envelope

    def mark_received(self, message: ReliableGameplayMessage) -> ReceiveDecision:
        key = (
            message.session_id,
            message.match_id,
            message.sender_id,
            message.event_seq,
        )
        should_apply = key not in self._received
        self._received.add(key)
        ack = ReliableAck(
            session_id=message.session_id,
            sender_id=_ack_sender_for(message),
            acked_sender_id=message.sender_id,
            received_seq=message.event_seq,
            match_id=message.match_id,
        )
        return ReceiveDecision(apply=should_apply, ack=ack)

    def mark_acked(self, ack: ReliableAck) -> bool:
        keys = [
            key
            for key in self._pending
            if key[1] == ack.session_id
            and key[2] == ack.match_id
            and key[3] == ack.acked_sender_id
            and key[4] == ack.received_seq
        ]
        for key in keys:
            del self._pending[key]
        return bool(keys)

    def due_resends(self) -> list[ReliableGameplayMessage]:
        now = self._clock.now()
        due: list[ReliableGameplayMessage] = []
        for pending in self._pending.values():
            if now - pending.last_sent_at >= self._config.reliable_resend_seconds:
                pending.last_sent_at = now
                due.append(pending.envelope.message)
        return due

    def is_session_timed_out(self, last_seen_at: float) -> bool:
        return self._clock.now() - last_seen_at >= self._config.session_timeout_seconds

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class LatestStateChannel:
    """Store only the newest non-reliable state for each logical stream."""

    def __init__(self) -> None:
        self._snapshots: dict[MatchId, MatchSnapshot] = {}
        self._client_summaries: dict[tuple[MatchId, PlayerId], ClientStateSummary] = {}
        self._opponent_summaries: dict[
            tuple[MatchId, PlayerId, PlayerId],
            OpponentStateSummary,
        ] = {}

    def apply(self, message: MatchSnapshot | ClientStateSummary | OpponentStateSummary) -> bool:
        if isinstance(message, MatchSnapshot):
            current_snapshot = self._snapshots.get(message.match_id)
            if current_snapshot is not None and current_snapshot.sequence > message.sequence:
                return False
            self._snapshots[message.match_id] = message
            return True
        if isinstance(message, ClientStateSummary):
            client_key = (message.match_id, message.player_id)
            current_client = self._client_summaries.get(client_key)
            if current_client is not None and current_client.summary_seq > message.summary_seq:
                return False
            self._client_summaries[client_key] = message
            return True
        opponent_key = (message.match_id, message.player_id, message.opponent_id)
        current_opponent = self._opponent_summaries.get(opponent_key)
        if current_opponent is not None and current_opponent.summary_seq > message.summary_seq:
            return False
        self._opponent_summaries[opponent_key] = message
        return True

    def latest_snapshot(self, match_id: MatchId) -> MatchSnapshot | None:
        return self._snapshots.get(match_id)

    def latest_client_summary(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> ClientStateSummary | None:
        return self._client_summaries.get((match_id, player_id))


def is_reliable_gameplay(message: ProtocolMessage) -> TypeGuard[ReliableGameplayMessage]:
    return isinstance(message, ReliableGameplayMessage)


def target_for_reliable(message: ReliableGameplayMessage) -> PlayerId:
    if isinstance(message, GarbageAssigned):
        return message.target_id
    target_id = getattr(message, "target_id", None)
    if isinstance(target_id, PlayerId):
        return target_id
    victim_id = getattr(message, "victim_id", None)
    if isinstance(victim_id, PlayerId):
        return victim_id
    return message.sender_id


def _ack_sender_for(message: ReliableGameplayMessage) -> PlayerId:
    target_id = target_for_reliable(message)
    if target_id != message.sender_id:
        return target_id
    return message.sender_id
