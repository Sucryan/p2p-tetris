"""Server-owned match lifecycle and battle-event routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from p2p_tetris.battle import (
    AttackEvent,
    GarbageGenerator,
    GarbageQueue,
    PlayerBattleStats,
    WinnerResolver,
)
from p2p_tetris.common import MatchConfig, MatchId, NetworkConfig, PlayerId
from p2p_tetris.common.time import MonotonicClock
from p2p_tetris.net.protocol import (
    AttackReported,
    ClientStateSummary,
    GarbageAssigned,
    KOReported,
    MatchEnd,
    MatchSnapshot,
    MatchStart,
    OpponentStateSummary,
    PlayerLeft,
    ProtocolMessage,
    RespawnAssigned,
)


class BattleCoordinatorPort(Protocol):
    """Duck-typed adapter for the battle module once it is available."""

    def handle_attack(self, event: AttackReported) -> Sequence[GarbageAssigned]: ...

    def handle_ko(self, event: KOReported) -> Sequence[RespawnAssigned]: ...


@dataclass(slots=True)
class MatchRecord:
    match_id: MatchId
    active_players: tuple[PlayerId, ...]
    started_at: float
    ends_at: float
    seed: int
    ko_counts: dict[PlayerId, int] = field(default_factory=dict)
    sent_lines: dict[PlayerId, int] = field(default_factory=dict)
    board_heights: dict[PlayerId, int] = field(default_factory=dict)
    garbage_queues: dict[PlayerId, GarbageQueue] = field(default_factory=dict)
    next_server_seq: int = 1
    snapshot_seq: int = 0


class MatchManager:
    def __init__(
        self,
        clock: MonotonicClock,
        match_config: MatchConfig | None = None,
        network_config: NetworkConfig | None = None,
        battle_coordinator: BattleCoordinatorPort | None = None,
    ) -> None:
        self._clock = clock
        self._match_config = match_config or MatchConfig()
        self._network_config = network_config or NetworkConfig()
        self._battle = battle_coordinator
        self._garbage_generator = GarbageGenerator()
        self._winner_resolver = WinnerResolver()
        self.current_match: MatchRecord | None = None

    def start_if_ready(self, active_players: Sequence[PlayerId]) -> MatchStart | None:
        if self.current_match is not None:
            return None
        if len(active_players) < self._match_config.active_player_count:
            return None
        players = tuple(active_players[: self._match_config.active_player_count])
        now = self._clock.now()
        seed = _stable_match_seed(players, now)
        record = MatchRecord(
            match_id=MatchId.new(),
            active_players=players,
            started_at=now,
            ends_at=now + self._match_config.match_seconds,
            seed=seed,
            ko_counts={player_id: 0 for player_id in players},
            sent_lines={player_id: 0 for player_id in players},
            board_heights={player_id: 0 for player_id in players},
            garbage_queues={player_id: GarbageQueue(self._clock) for player_id in players},
        )
        self.current_match = record
        return MatchStart(
            match_id=record.match_id,
            active_players=record.active_players,
            match_seconds=self._match_config.match_seconds,
            ko_target=self._match_config.ko_target,
            seed=record.seed,
            server_time=now,
        )

    def tick(self) -> MatchEnd | None:
        record = self.current_match
        if record is None or self._clock.now() < record.ends_at:
            return None
        return self.end_current_match("timeout")

    def snapshot(self) -> MatchSnapshot | None:
        record = self.current_match
        if record is None:
            return None
        record.snapshot_seq += 1
        now = self._clock.now()
        return MatchSnapshot(
            match_id=record.match_id,
            sequence=record.snapshot_seq,
            server_time=now,
            remaining_seconds=max(0.0, record.ends_at - now),
            ko_counts=_string_keyed(record.ko_counts),
            sent_lines=_string_keyed(record.sent_lines),
            correction={"active_players": [player.value for player in record.active_players]},
            snapshot_rate_hz=self._network_config.snapshot_rate_hz,
        )

    def handle_reliable_gameplay(
        self,
        message: AttackReported | KOReported,
    ) -> tuple[ProtocolMessage, ...]:
        if isinstance(message, AttackReported):
            return self._handle_attack(message)
        return self._handle_ko(message)

    def relay_summary(self, summary: ClientStateSummary) -> OpponentStateSummary | None:
        record = self.current_match
        if record is None or summary.player_id not in record.active_players:
            return None
        opponent = self.opponent_of(summary.player_id)
        if opponent is None:
            return None
        record.board_heights[summary.player_id] = summary.board_height
        return OpponentStateSummary(
            session_id=summary.session_id,
            match_id=summary.match_id,
            player_id=opponent,
            opponent_id=summary.player_id,
            summary_seq=summary.summary_seq,
            board_height=summary.board_height,
            pending_garbage=summary.pending_garbage,
            ko_count=summary.ko_count,
            sent_lines=summary.sent_lines,
            is_alive=summary.is_alive,
            extra=summary.extra,
        )

    def handle_player_left(self, player_id: PlayerId) -> tuple[ProtocolMessage, ...]:
        record = self.current_match
        if record is None or player_id not in record.active_players:
            return (PlayerLeft(player_id=player_id, reason="left"),)
        winner = self.opponent_of(player_id)
        left = PlayerLeft(
            player_id=player_id,
            reason="left",
            match_id=record.match_id,
        )
        end = self._build_match_end(record, winner, "player_left")
        self.current_match = None
        return (left, end)

    def end_current_match(
        self,
        reason: str = "timeout",
        winner_id: PlayerId | None = None,
    ) -> MatchEnd | None:
        record = self.current_match
        if record is None:
            return None
        if winner_id is None:
            winner_id = self.resolve_winner(record)
        end_reason = "draw" if winner_id is None else reason
        end = self._build_match_end(record, winner_id, end_reason)
        self.current_match = None
        return end

    def opponent_of(self, player_id: PlayerId) -> PlayerId | None:
        record = self.current_match
        if record is None:
            return None
        for candidate in record.active_players:
            if candidate != player_id:
                return candidate
        return None

    def resolve_winner(self, record: MatchRecord) -> PlayerId | None:
        stats = tuple(
            PlayerBattleStats(
                player=player,
                ko_count=record.ko_counts.get(player, 0),
                sent_lines=record.sent_lines.get(player, 0),
                board_height=record.board_heights.get(player, 0),
            )
            for player in record.active_players
        )
        if len(stats) != 2:
            return _winner_by_tiebreakers(record.active_players, record.ko_counts, record.sent_lines)
        return self._winner_resolver.resolve(
            stats=(stats[0], stats[1]),
            reason="timeout",
            seq=record.next_server_seq,
        ).winner

    def _handle_attack(self, attack: AttackReported) -> tuple[ProtocolMessage, ...]:
        record = self.current_match
        if record is None or attack.match_id != record.match_id:
            return ()
        if self._battle is not None:
            assigned = tuple(self._battle.handle_attack(attack))
            if assigned:
                return assigned
        target = attack.target_id or self.opponent_of(attack.sender_id)
        if target is None:
            return ()
        pending_before = record.garbage_queues[attack.sender_id].pending_lines
        outgoing = record.garbage_queues[attack.sender_id].cancel_with_attack(
            AttackEvent(
                source=attack.sender_id,
                seq=attack.event_seq,
                target=target,
                lines=attack.lines,
            ),
        )
        canceled_lines = pending_before - record.garbage_queues[attack.sender_id].pending_lines
        outputs: list[ProtocolMessage] = []
        if canceled_lines > 0:
            outputs.append(
                GarbageAssigned(
                    session_id=attack.session_id,
                    match_id=record.match_id,
                    sender_id=attack.sender_id,
                    target_id=attack.sender_id,
                    event_seq=self._next_server_seq(record),
                    lines=0,
                    hole_column=0,
                    garbage_id=f"{attack.attack_id}:cancel",
                    source_attack_id=attack.attack_id,
                    canceled_lines=canceled_lines,
                ),
            )
        if outgoing is None or outgoing.lines == 0:
            return tuple(outputs)
        record.sent_lines[attack.sender_id] = (
            record.sent_lines.get(attack.sender_id, 0) + outgoing.lines
        )
        server_seq = self._next_server_seq(record)
        garbage = self._garbage_generator.generate(
            source=attack.sender_id,
            target=target,
            lines=outgoing.lines,
            seq=server_seq,
        )
        record.garbage_queues[target].enqueue(garbage)
        outputs.append(
            GarbageAssigned(
                session_id=attack.session_id,
                match_id=record.match_id,
                sender_id=attack.sender_id,
                target_id=target,
                event_seq=server_seq,
                lines=garbage.lines,
                hole_column=garbage.rows[0].hole,
                garbage_id=f"{attack.attack_id}:garbage",
                source_attack_id=attack.attack_id,
            ),
        )
        return tuple(outputs)

    def _handle_ko(self, ko: KOReported) -> tuple[ProtocolMessage, ...]:
        record = self.current_match
        if record is None or ko.match_id != record.match_id:
            return ()
        scorer = self.opponent_of(ko.victim_id)
        if scorer is None:
            return ()
        record.ko_counts[scorer] = record.ko_counts.get(scorer, 0) + 1
        record.garbage_queues[ko.victim_id].reset()
        outputs: list[ProtocolMessage] = []
        if self._battle is not None:
            outputs.extend(self._battle.handle_ko(ko))
        if not any(isinstance(message, RespawnAssigned) for message in outputs):
            outputs.append(
                RespawnAssigned(
                    session_id=ko.session_id,
                    match_id=record.match_id,
                    sender_id=scorer,
                    target_id=ko.victim_id,
                    event_seq=self._next_server_seq(record),
                    respawn_at=self._clock.now() + self._match_config.respawn_delay_seconds,
                ),
            )
        if record.ko_counts[scorer] >= self._match_config.ko_target:
            outputs.append(self._build_match_end(record, scorer, "ko_target"))
            self.current_match = None
        return tuple(outputs)

    def _next_server_seq(self, record: MatchRecord) -> int:
        event_seq = record.next_server_seq
        record.next_server_seq += 1
        return event_seq

    def _build_match_end(
        self,
        record: MatchRecord,
        winner_id: PlayerId | None,
        reason: str,
    ) -> MatchEnd:
        return MatchEnd(
            match_id=record.match_id,
            winner_id=winner_id,
            reason=_match_end_reason(reason, winner_id),
            ko_counts=_string_keyed(record.ko_counts),
            sent_lines=_string_keyed(record.sent_lines),
            server_time=self._clock.now(),
        )


def _match_end_reason(reason: str, winner_id: PlayerId | None) -> Any:
    if winner_id is None:
        return "draw"
    if reason in {"ko_target", "timeout", "player_left"}:
        return reason
    return "timeout"


def _stable_match_seed(players: Sequence[PlayerId], now: float) -> int:
    raw = "|".join(player.value for player in players) + f"|{now:.3f}"
    return sum(ord(char) for char in raw) % (2**31)


def _string_keyed(values: dict[PlayerId, int]) -> dict[str, int]:
    return {player.value: value for player, value in values.items()}


def _winner_by_tiebreakers(
    players: Sequence[PlayerId],
    ko_counts: dict[PlayerId, int],
    sent_lines: dict[PlayerId, int],
) -> PlayerId | None:
    if not players:
        return None
    ordered = list(players)
    for table in (ko_counts, sent_lines):
        best = max(table.get(player, 0) for player in ordered)
        winners = [player for player in ordered if table.get(player, 0) == best]
        if len(winners) == 1:
            return winners[0]
    return None
