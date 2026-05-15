"""Session lifecycle management for the headless server."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import NetworkConfig, PlayerId, SessionId
from p2p_tetris.common.time import MonotonicClock
from p2p_tetris.net.protocol import (
    Address,
    ClientHello,
    DisconnectNotice,
    Heartbeat,
    ServerWelcome,
)
from p2p_tetris.net.reliability import ReliableChannel


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: SessionId
    player_id: PlayerId
    endpoint: Address
    connected_at: float
    last_seen_at: float


class SessionManager:
    def __init__(self, clock: MonotonicClock, config: NetworkConfig | None = None) -> None:
        self._clock = clock
        self._config = config or NetworkConfig()
        self._reliability = ReliableChannel(clock, self._config)
        self._by_session: dict[SessionId, SessionRecord] = {}
        self._by_player: dict[PlayerId, SessionId] = {}
        self._by_endpoint: dict[Address, SessionId] = {}

    def handle_client_hello(
        self,
        hello: ClientHello,
        endpoint: Address,
    ) -> tuple[SessionRecord, ServerWelcome, bool]:
        existing = self.find_by_player(hello.player_id)
        if existing is not None:
            record = self._replace_record(existing, endpoint=endpoint, last_seen_at=self._clock.now())
            return record, self._welcome(record), False

        now = self._clock.now()
        record = SessionRecord(
            session_id=SessionId.new(),
            player_id=hello.player_id,
            endpoint=endpoint,
            connected_at=now,
            last_seen_at=now,
        )
        self._store(record)
        return record, self._welcome(record), True

    def handle_heartbeat(self, heartbeat: Heartbeat, endpoint: Address) -> ServerWelcome | None:
        record = self._by_session.get(heartbeat.session_id)
        if record is None or record.player_id != heartbeat.player_id:
            return None
        updated = self._replace_record(record, endpoint=endpoint, last_seen_at=self._clock.now())
        return self._welcome(updated)

    def disconnect(self, notice: DisconnectNotice) -> SessionRecord | None:
        record = self._by_session.get(notice.session_id)
        if record is None or record.player_id != notice.player_id:
            return None
        self.remove_player(record.player_id)
        return record

    def expire_timed_out(self) -> list[SessionRecord]:
        expired = [
            record
            for record in self._by_session.values()
            if self._reliability.is_session_timed_out(record.last_seen_at)
        ]
        for record in expired:
            self.remove_player(record.player_id)
        return expired

    def find_by_player(self, player_id: PlayerId) -> SessionRecord | None:
        session_id = self._by_player.get(player_id)
        if session_id is None:
            return None
        return self._by_session.get(session_id)

    def find_by_session(self, session_id: SessionId) -> SessionRecord | None:
        return self._by_session.get(session_id)

    def endpoint_for_player(self, player_id: PlayerId) -> Address | None:
        record = self.find_by_player(player_id)
        if record is None:
            return None
        return record.endpoint

    def session_for_player(self, player_id: PlayerId) -> SessionId | None:
        record = self.find_by_player(player_id)
        if record is None:
            return None
        return record.session_id

    def remove_player(self, player_id: PlayerId) -> SessionRecord | None:
        session_id = self._by_player.pop(player_id, None)
        if session_id is None:
            return None
        record = self._by_session.pop(session_id, None)
        if record is not None:
            self._by_endpoint.pop(record.endpoint, None)
        return record

    @property
    def sessions(self) -> tuple[SessionRecord, ...]:
        return tuple(self._by_session.values())

    def _welcome(self, record: SessionRecord) -> ServerWelcome:
        return ServerWelcome(
            session_id=record.session_id,
            player_id=record.player_id,
            heartbeat_seconds=self._config.heartbeat_seconds,
            server_time=self._clock.now(),
        )

    def _store(self, record: SessionRecord) -> None:
        self._by_session[record.session_id] = record
        self._by_player[record.player_id] = record.session_id
        self._by_endpoint[record.endpoint] = record.session_id

    def _replace_record(
        self,
        record: SessionRecord,
        *,
        endpoint: Address,
        last_seen_at: float,
    ) -> SessionRecord:
        self._by_endpoint.pop(record.endpoint, None)
        updated = SessionRecord(
            session_id=record.session_id,
            player_id=record.player_id,
            endpoint=endpoint,
            connected_at=record.connected_at,
            last_seen_at=last_seen_at,
        )
        self._store(updated)
        return updated
