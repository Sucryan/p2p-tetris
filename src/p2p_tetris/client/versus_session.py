"""GUI-independent versus runtime session and network bridge."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from p2p_tetris.battle import AttackCalculator
from p2p_tetris.common import GameConfig, MatchId, MonotonicClock, PlayerId, SessionId, SystemClock
from p2p_tetris.controllers import ActionSource
from p2p_tetris.game_core import (
    ClearEvent,
    GameEngine,
    GameEvent,
    GameStateSnapshot,
    GarbageInjection,
    PieceLockedEvent,
    TopOutEvent,
)
from p2p_tetris.net import (
    AttackReported,
    ClientStateSummary,
    GarbageAssigned,
    KOReported,
    MatchEnd,
    MatchSnapshot,
    MatchStart,
    OpponentStateSummary,
    ProtocolMessage,
    RespawnAssigned,
)
from p2p_tetris.net.reliability import ReliableChannel, target_for_reliable

from p2p_tetris.client.view_models import (
    BoardViewModel,
    ConnectionState,
    ConnectionViewModel,
    GameViewModel,
    MatchResultViewModel,
    OpponentViewModel,
    PiecePreviewViewModel,
    SoloHudViewModel,
    VersusHudViewModel,
    board_height,
)


class NetClientPort(Protocol):
    """Minimal network client shape used by runtime tests and GUI adapters."""

    def send(self, message: ProtocolMessage) -> None:
        """Send one typed protocol message."""

    def receive(self) -> tuple[ProtocolMessage, ...]:
        """Return currently available typed protocol messages."""


@dataclass(frozen=True, slots=True)
class SnapshotCorrection:
    sequence: int
    correction: dict[str, object]


class VersusGameSession:
    """Own local gameplay and bridge local events to typed network messages."""

    def __init__(
        self,
        *,
        session_id: SessionId,
        player_id: PlayerId,
        action_source: ActionSource,
        net_client: NetClientPort,
        config: GameConfig | None = None,
        attack_calculator: AttackCalculator | None = None,
        clock: MonotonicClock | None = None,
    ) -> None:
        self._session_id = session_id
        self._player_id = player_id
        self._action_source = action_source
        self._net_client = net_client
        self._config = config or GameConfig()
        self._attack_calculator = attack_calculator or AttackCalculator()
        self._incoming_reliability = ReliableChannel(clock or SystemClock())
        self._engine = GameEngine(seed=None, config=self._config)
        self._tick = 0
        self._running = False
        self._paused = False
        self._alive = True
        self._match_id: MatchId | None = None
        self._match_seed: int | None = None
        self._opponent_id: PlayerId | None = None
        self._remaining_seconds = 0.0
        self._ko_counts: dict[str, int] = {}
        self._sent_lines: dict[str, int] = {}
        self._pending_garbage: list[GarbageInjection] = []
        self._opponents: dict[PlayerId, OpponentViewModel] = {}
        self._result: MatchResultViewModel | None = None
        self._last_correction: SnapshotCorrection | None = None
        self._seq = 0
        self._view_model = self._build_view_model(ConnectionState.DISCONNECTED)

    @property
    def tick_count(self) -> int:
        return self._tick

    @property
    def view_model(self) -> GameViewModel:
        return self._view_model

    @property
    def last_correction(self) -> SnapshotCorrection | None:
        return self._last_correction

    @property
    def pending_garbage_lines(self) -> int:
        return sum(injection.lines for injection in self._pending_garbage)

    def start(self) -> None:
        self._running = self._match_id is not None
        self._paused = False
        self._view_model = self._build_view_model(self._connection_state())

    def pause(self) -> None:
        if self._running:
            self._paused = True
            self._view_model = self._build_view_model(self._connection_state())

    def resume(self) -> None:
        if self._running:
            self._paused = False
            self._view_model = self._build_view_model(self._connection_state())

    def handle_server_message(self, message: ProtocolMessage) -> None:
        if isinstance(message, MatchStart):
            self._handle_match_start(message)
        elif isinstance(message, GarbageAssigned):
            if self._mark_incoming_reliable(message):
                self._handle_garbage_assigned(message)
        elif isinstance(message, RespawnAssigned):
            if self._mark_incoming_reliable(message):
                self._handle_respawn_assigned(message)
        elif isinstance(message, MatchSnapshot):
            self._handle_match_snapshot(message)
        elif isinstance(message, OpponentStateSummary):
            self._handle_opponent_summary(message)
        elif isinstance(message, MatchEnd):
            self._handle_match_end(message)
        self._view_model = self._build_view_model(self._connection_state())

    def poll_network(self) -> None:
        for message in self._net_client.receive():
            self.handle_server_message(message)

    def tick(self, ticks: int = 1) -> tuple[GameEvent, ...]:
        if ticks < 0:
            msg = "ticks must be non-negative"
            raise ValueError(msg)
        events: list[GameEvent] = []
        for _ in range(ticks):
            self.poll_network()
            if not self._running or self._paused or not self._alive:
                continue
            batch = self._action_source.pull_actions(self._tick)
            tick_events = self._engine.step(batch.actions)
            events.extend(tick_events)
            self._handle_local_events(tick_events)
            self._tick += 1
            self._view_model = self._build_view_model(self._connection_state())
        return tuple(events)

    def client_state_summary(self) -> ClientStateSummary:
        match_id = self._require_match_id()
        snapshot = self._engine.snapshot()
        return ClientStateSummary(
            session_id=self._session_id,
            match_id=match_id,
            player_id=self._player_id,
            summary_seq=self._next_seq(),
            board_height=board_height(snapshot),
            pending_garbage=self.pending_garbage_lines,
            ko_count=self._ko_counts.get(self._player_id.value, 0),
            sent_lines=self._sent_lines.get(self._player_id.value, 0),
            is_alive=self._alive and not snapshot.top_out,
            extra={"tick": self._tick, "score": snapshot.score},
        )

    def snapshot(self) -> GameStateSnapshot:
        return self._engine.snapshot()

    def handle_local_game_events(self, events: tuple[GameEvent, ...]) -> None:
        """Process game-core events produced by the local engine."""

        self._handle_local_events(events)
        self._view_model = self._build_view_model(self._connection_state())

    def _handle_match_start(self, message: MatchStart) -> None:
        self._match_id = message.match_id
        self._match_seed = message.seed
        self._opponent_id = next(
            (player for player in message.active_players if player != self._player_id),
            None,
        )
        self._remaining_seconds = message.match_seconds
        self._ko_counts = {player.value: 0 for player in message.active_players}
        self._sent_lines = {player.value: 0 for player in message.active_players}
        self._pending_garbage.clear()
        self._result = None
        self._alive = True
        self._running = True
        self._paused = False
        self._tick = 0
        self._engine.reset(seed=message.seed, config=self._config)

    def _mark_incoming_reliable(self, message: GarbageAssigned | RespawnAssigned) -> bool:
        if target_for_reliable(message) != self._player_id:
            return False
        decision = self._incoming_reliability.mark_received(message)
        self._net_client.send(decision.ack)
        return decision.apply

    def _handle_garbage_assigned(self, message: GarbageAssigned) -> None:
        if not self._is_current_match(message.match_id) or message.target_id != self._player_id:
            return
        self._cancel_pending_garbage(message.canceled_lines)
        if message.lines > 0:
            self._pending_garbage.append(
                GarbageInjection(lines=message.lines, hole=message.hole_column),
            )

    def _handle_respawn_assigned(self, message: RespawnAssigned) -> None:
        if not self._is_current_match(message.match_id) or message.target_id != self._player_id:
            return
        seed = self._match_seed if self._match_seed is not None else message.event_seq
        self._engine.reset(seed=f"{seed}:respawn:{message.event_seq}", config=self._config)
        self._pending_garbage.clear()
        self._alive = True
        self._paused = False

    def _handle_match_snapshot(self, message: MatchSnapshot) -> None:
        if not self._is_current_match(message.match_id):
            return
        self._remaining_seconds = message.remaining_seconds
        self._ko_counts = dict(message.ko_counts)
        self._sent_lines = dict(message.sent_lines)
        self._last_correction = SnapshotCorrection(
            sequence=message.sequence,
            correction=dict(message.correction),
        )

    def _handle_opponent_summary(self, message: OpponentStateSummary) -> None:
        if not self._is_current_match(message.match_id) or message.player_id != self._player_id:
            return
        self._opponents[message.opponent_id] = OpponentViewModel(
            player_id=message.opponent_id,
            summary_seq=message.summary_seq,
            board_height=message.board_height,
            pending_garbage=message.pending_garbage,
            ko_count=message.ko_count,
            sent_lines=message.sent_lines,
            is_alive=message.is_alive,
            extra=dict(message.extra),
        )
        self._ko_counts[message.opponent_id.value] = message.ko_count
        self._sent_lines[message.opponent_id.value] = message.sent_lines

    def _handle_match_end(self, message: MatchEnd) -> None:
        if not self._is_current_match(message.match_id):
            return
        is_draw = message.reason == "draw" or message.winner_id is None
        self._result = MatchResultViewModel(
            match_id=message.match_id,
            winner_id=message.winner_id,
            is_draw=is_draw,
            reason=message.reason,
            ko_counts=dict(message.ko_counts),
            sent_lines=dict(message.sent_lines),
        )
        self._ko_counts = dict(message.ko_counts)
        self._sent_lines = dict(message.sent_lines)
        self._running = False

    def _handle_local_events(self, events: tuple[GameEvent, ...]) -> None:
        has_lock = False
        for event in events:
            if isinstance(event, ClearEvent):
                self._report_attack(event)
            elif isinstance(event, PieceLockedEvent):
                has_lock = True
            elif isinstance(event, TopOutEvent):
                self._report_ko(event.reason)
        if has_lock:
            self._apply_pending_garbage()

    def _report_attack(self, event: ClearEvent) -> None:
        match_id = self._match_id
        if match_id is None:
            return
        target = self._opponent_id
        seq = self._next_seq()
        if target is None:
            lines = 0
        else:
            attack = self._attack_calculator.calculate(
                event,
                source=self._player_id,
                target=target,
                seq=seq,
            )
            lines = attack.lines
        self._net_client.send(
            AttackReported(
                session_id=self._session_id,
                match_id=match_id,
                sender_id=self._player_id,
                target_id=target,
                event_seq=seq,
                lines=lines,
                attack_id=self._reliable_id("attack", seq),
                combo=event.combo,
                back_to_back=event.back_to_back,
            ),
        )

    def _report_ko(self, reason: str) -> None:
        match_id = self._match_id
        if match_id is None or not self._alive:
            return
        self._alive = False
        seq = self._next_seq()
        self._net_client.send(
            KOReported(
                session_id=self._session_id,
                match_id=match_id,
                sender_id=self._player_id,
                victim_id=self._player_id,
                event_seq=seq,
            ),
        )
        _ = reason

    def _apply_pending_garbage(self) -> None:
        while self._pending_garbage:
            self._engine.apply_garbage(self._pending_garbage.pop(0))
        if self._engine.snapshot().top_out:
            self._report_ko("garbage collision")

    def _cancel_pending_garbage(self, lines: int) -> None:
        if lines <= 0:
            return
        remaining = lines
        adjusted: list[GarbageInjection] = []
        for injection in self._pending_garbage:
            if remaining <= 0:
                adjusted.append(injection)
                continue
            consumed = min(remaining, injection.lines)
            remaining -= consumed
            kept_lines = injection.lines - consumed
            if kept_lines > 0:
                adjusted.append(GarbageInjection(lines=kept_lines, hole=injection.hole))
        self._pending_garbage = adjusted

    def _build_view_model(self, connection_state: ConnectionState) -> GameViewModel:
        snapshot = self._engine.snapshot()
        board = BoardViewModel.from_snapshot(
            snapshot,
            hidden_rows=self._config.hidden_rows,
        )
        pending_garbage_lines = self.pending_garbage_lines
        versus_hud: VersusHudViewModel | None = None
        if self._match_id is not None:
            board = replace(board, pending_garbage_lines=pending_garbage_lines)
            versus_hud = VersusHudViewModel(
                match_id=self._match_id,
                local_player_id=self._player_id,
                opponent_player_id=self._opponent_id,
                remaining_seconds=self._remaining_seconds,
                ko_counts=dict(self._ko_counts),
                sent_lines=dict(self._sent_lines),
                pending_garbage_lines=pending_garbage_lines,
                is_alive=self._alive and not snapshot.top_out,
            )
        return GameViewModel(
            board=board,
            preview=PiecePreviewViewModel.from_snapshot(snapshot),
            solo_hud=SoloHudViewModel(
                score=snapshot.score,
                cleared_lines=snapshot.cleared_lines,
                combo=snapshot.combo,
                back_to_back=snapshot.back_to_back,
                tick=self._tick,
                is_running=self._running,
                is_paused=self._paused,
            ),
            connection=ConnectionViewModel(state=connection_state),
            versus_hud=versus_hud,
            opponents=tuple(self._opponents.values()),
            result=self._result,
        )

    def _connection_state(self) -> ConnectionState:
        if self._result is not None:
            return ConnectionState.ENDED
        if self._match_id is not None:
            return ConnectionState.IN_MATCH
        return ConnectionState.DISCONNECTED

    def _is_current_match(self, match_id: MatchId) -> bool:
        return self._match_id == match_id

    def _require_match_id(self) -> MatchId:
        if self._match_id is None:
            msg = "session is not in a match"
            raise RuntimeError(msg)
        return self._match_id

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def _reliable_id(self, kind: str, seq: int) -> str:
        match_id = self._match_id.value if self._match_id is not None else "no-match"
        return f"{match_id}:{self._player_id.value}:{kind}:{seq}"


__all__ = ["NetClientPort", "SnapshotCorrection", "VersusGameSession"]
