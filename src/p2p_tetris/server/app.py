"""Headless server application and transport port."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from typing import Protocol

from p2p_tetris.common import MatchConfig, NetworkConfig, PlayerId, SystemClock
from p2p_tetris.common.time import MonotonicClock
from p2p_tetris.net import (
    AttackReported,
    ClientHello,
    ClientStateSummary,
    ClockSync,
    DisconnectNotice,
    GarbageAssigned,
    Heartbeat,
    KOReported,
    MessageCodec,
    NetworkEvent,
    ProtocolMessage,
    ReliableAck,
    RespawnAssigned,
    UdpServer,
)
from p2p_tetris.net.protocol import Address
from p2p_tetris.net.reliability import ReliableChannel, is_reliable_gameplay, target_for_reliable
from p2p_tetris.server.matches import BattleCoordinatorPort, MatchManager
from p2p_tetris.server.queue import QueueManager
from p2p_tetris.server.sessions import SessionManager


class TransportPort(Protocol):
    def send(self, message: ProtocolMessage, endpoint: Address) -> None: ...

    def poll(self, max_datagrams: int = 100) -> list[NetworkEvent]: ...


class UdpServerPort:
    def __init__(self, server: UdpServer) -> None:
        self._server = server

    @property
    def address(self) -> Address:
        return self._server.address

    def send(self, message: ProtocolMessage, endpoint: Address) -> None:
        self._server.send(message, endpoint)

    def poll(self, max_datagrams: int = 100) -> list[NetworkEvent]:
        return self._server.receive(max_datagrams)

    def close(self) -> None:
        self._server.close()


class ServerApp:
    def __init__(
        self,
        *,
        transport: TransportPort | None = None,
        clock: MonotonicClock | None = None,
        match_config: MatchConfig | None = None,
        network_config: NetworkConfig | None = None,
        battle_coordinator: BattleCoordinatorPort | None = None,
    ) -> None:
        self.clock = clock or SystemClock()
        self.match_config = match_config or MatchConfig()
        self.network_config = network_config or NetworkConfig()
        self.transport = transport
        self.sessions = SessionManager(self.clock, self.network_config)
        self.queue = QueueManager(self.match_config)
        self.matches = MatchManager(
            self.clock,
            self.match_config,
            self.network_config,
            battle_coordinator,
        )
        self.reliability = ReliableChannel(self.clock, self.network_config)

    @classmethod
    def with_udp(
        cls,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        clock: MonotonicClock | None = None,
        match_config: MatchConfig | None = None,
        network_config: NetworkConfig | None = None,
    ) -> ServerApp:
        udp = UdpServer((host, port), codec=MessageCodec(), clock=clock)
        return cls(
            transport=UdpServerPort(udp),
            clock=clock,
            match_config=match_config,
            network_config=network_config,
        )

    def poll_once(self, max_datagrams: int = 100) -> None:
        if self.transport is None:
            self._expire_sessions()
            self._tick_match()
            return
        for event in self.transport.poll(max_datagrams):
            self.handle_network_event(event)
        self._expire_sessions()
        self._tick_match()

    def run_once(self, max_datagrams: int = 100) -> None:
        self.poll_once(max_datagrams)

    def handle_network_event(self, event: NetworkEvent) -> None:
        message = event.message
        if isinstance(message, ClientHello):
            self._handle_hello(message, event.endpoint)
        elif isinstance(message, Heartbeat):
            self._handle_heartbeat(message, event.endpoint)
        elif isinstance(message, DisconnectNotice):
            self._handle_disconnect(message)
        elif isinstance(message, ReliableAck):
            self.reliability.mark_acked(message)
        elif is_reliable_gameplay(message):
            self._handle_reliable(message)
        elif isinstance(message, ClientStateSummary):
            self._handle_summary(message)

    def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if callable(close):
            close()

    def _handle_hello(self, hello: ClientHello, endpoint: Address) -> None:
        if not self.queue.would_accept(hello.player_id):
            rejection = self.queue.join(hello.player_id).rejection
            if rejection is not None:
                self._send(rejection, endpoint)
            return
        record, welcome, is_new = self.sessions.handle_client_hello(hello, endpoint)
        if is_new:
            self.queue.join(hello.player_id)
        self._send(welcome, endpoint)
        self._broadcast_queue_status()
        start = self.matches.start_if_ready(self.queue.active_players)
        if start is not None:
            self._send_to_players(start, start.active_players)

    def _handle_heartbeat(self, heartbeat: Heartbeat, endpoint: Address) -> None:
        welcome = self.sessions.handle_heartbeat(heartbeat, endpoint)
        if welcome is not None:
            self._send(
                ClockSync(
                    session_id=heartbeat.session_id,
                    client_time=heartbeat.sent_at,
                    server_time=self.clock.now(),
                ),
                endpoint,
            )

    def _handle_disconnect(self, notice: DisconnectNotice) -> None:
        record = self.sessions.disconnect(notice)
        if record is None:
            return
        self.queue.leave(record.player_id)
        outputs = self.matches.handle_player_left(record.player_id)
        self._broadcast(outputs)
        self._broadcast_queue_status()

    def _handle_reliable(
        self,
        message: AttackReported | GarbageAssigned | KOReported | RespawnAssigned,
    ) -> None:
        decision = self.reliability.mark_received(message)
        self._send_to_player(decision.ack, message.sender_id)
        if not decision.apply:
            return
        if isinstance(message, AttackReported | KOReported):
            outputs = self.matches.handle_reliable_gameplay(message)
            self._broadcast(outputs)
            for output in outputs:
                if isinstance(output, AttackReported | GarbageAssigned | KOReported | RespawnAssigned):
                    self.reliability.track_outgoing(output, target_for_reliable(output))
                if self._is_match_end(output):
                    winner = getattr(output, "winner_id", None)
                    self.queue.rotate_after_match(winner)
                    self._broadcast_queue_status()
                    start = self.matches.start_if_ready(self.queue.active_players)
                    if start is not None:
                        self._send_to_players(start, start.active_players)

    def _handle_summary(self, summary: ClientStateSummary) -> None:
        relay = self.matches.relay_summary(summary)
        if relay is not None:
            self._send_to_player(relay, relay.player_id)

    def _tick_match(self) -> None:
        match_end = self.matches.tick()
        if match_end is None:
            return
        self._broadcast((match_end,))
        self.queue.rotate_after_match(match_end.winner_id)
        self._broadcast_queue_status()
        start = self.matches.start_if_ready(self.queue.active_players)
        if start is not None:
            self._send_to_players(start, start.active_players)

    def _expire_sessions(self) -> None:
        for record in self.sessions.expire_timed_out():
            self.queue.leave(record.player_id)
            self._broadcast(self.matches.handle_player_left(record.player_id))
        if self.transport is not None:
            for resend in self.reliability.due_resends():
                self._send_to_player(resend, target_for_reliable(resend))

    def _broadcast_queue_status(self) -> None:
        for status in self.queue.statuses():
            self._send_to_player(status, status.player_id)

    def _broadcast(self, messages: tuple[ProtocolMessage, ...]) -> None:
        for message in messages:
            self._broadcast_one(message)

    def _broadcast_one(self, message: ProtocolMessage) -> None:
        players = self.queue.players
        current = self.matches.current_match
        if current is not None:
            players = tuple(dict.fromkeys([*players, *current.active_players]))
        self._send_to_players(message, players)

    def _send_to_players(self, message: ProtocolMessage, players: tuple[PlayerId, ...]) -> None:
        for player_id in players:
            self._send_to_player(message, player_id)

    def _send_to_player(self, message: ProtocolMessage, player_id: PlayerId) -> None:
        endpoint = self.sessions.endpoint_for_player(player_id)
        if endpoint is not None:
            self._send(message, endpoint)

    def _send(self, message: ProtocolMessage, endpoint: Address) -> None:
        if self.transport is not None:
            self.transport.send(message, endpoint)

    def _is_match_end(self, message: ProtocolMessage) -> bool:
        return type(message).__name__ == "MatchEnd"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the headless P2P Tetris UDP server.")
    parser.add_argument("--host", default="127.0.0.1", help="UDP bind host.")
    parser.add_argument("--port", default=7777, type=int, help="UDP bind port.")
    parser.add_argument(
        "--poll-interval",
        default=0.01,
        type=float,
        help="Sleep interval between non-blocking polls.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one poll iteration and exit; useful for smoke checks.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.poll_interval < 0:
        raise SystemExit("--poll-interval must be non-negative")
    app = ServerApp.with_udp(host=args.host, port=args.port)
    try:
        if args.once:
            app.poll_once()
            return 0
        while True:
            app.poll_once()
            if args.poll_interval:
                time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
