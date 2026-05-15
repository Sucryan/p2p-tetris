"""GUI-independent network connection orchestration."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from p2p_tetris.client.network import UdpNetClient
from p2p_tetris.client.versus_session import VersusGameSession
from p2p_tetris.client.view_models import ConnectionState, ConnectionViewModel, GameViewModel
from p2p_tetris.common import PlayerId, SessionId
from p2p_tetris.controllers import ActionSource
from p2p_tetris.net import (
    ClientHello,
    DisconnectNotice,
    GarbageAssigned,
    Heartbeat,
    JoinRejectedRoomFull,
    MatchEnd,
    MatchSnapshot,
    MatchStart,
    OpponentStateSummary,
    ProtocolMessage,
    QueueStatus,
    RespawnAssigned,
    ServerWelcome,
)

ServerAddress = tuple[str, int]


class ConnectedNetClient(Protocol):
    def send(self, message: ProtocolMessage) -> None: ...

    def receive(self) -> tuple[ProtocolMessage, ...]: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class NetworkRuntimeUpdate:
    connection: ConnectionViewModel
    view_model: GameViewModel | None = None


class ClientNetworkRuntime:
    """Own UDP connection state and versus runtime wiring outside the GUI."""

    def __init__(
        self,
        action_source: ActionSource,
        *,
        net_client_factory: Callable[[ServerAddress], ConnectedNetClient] | None = None,
    ) -> None:
        self._action_source = action_source
        self._net_client_factory = net_client_factory or UdpNetClient
        self._net_client: ConnectedNetClient | None = None
        self._player_id: PlayerId | None = None
        self._session_id: SessionId | None = None
        self._last_heartbeat_at = 0.0
        self.versus_session: VersusGameSession | None = None
        self.connection = ConnectionViewModel(ConnectionState.DISCONNECTED)

    def connect(self, host: str, port: int, player_name: str) -> ConnectionViewModel:
        self.close()
        self._net_client = self._net_client_factory((host, port))
        self._player_id = PlayerId(f"{_player_slug(player_name)}-{uuid4().hex[:8]}")
        self._session_id = None
        self.versus_session = None
        self._net_client.send(
            ClientHello(
                player_id=self._player_id,
                display_name=player_name,
            ),
        )
        self.connection = ConnectionViewModel(
            ConnectionState.CONNECTING,
            f"Connecting as {player_name} to {host}:{port}",
        )
        return self.connection

    def poll(self) -> NetworkRuntimeUpdate | None:
        client = self._net_client
        if client is None:
            return None
        update: NetworkRuntimeUpdate | None = None
        for message in client.receive():
            update = self._handle_server_message(message)
        self._send_heartbeat_if_due()
        return update

    def tick(self) -> GameViewModel | None:
        session = self.versus_session
        client = self._net_client
        if session is None:
            return None
        session.tick()
        if client is not None and session.tick_count % 15 == 0:
            client.send(session.client_state_summary())
        return session.view_model

    def close(self) -> None:
        client = self._net_client
        if client is None:
            return
        if self._session_id is not None and self._player_id is not None:
            client.send(
                DisconnectNotice(
                    session_id=self._session_id,
                    player_id=self._player_id,
                ),
            )
        client.close()
        self._net_client = None
        self._session_id = None
        self._player_id = None
        self.versus_session = None
        self.connection = ConnectionViewModel(ConnectionState.DISCONNECTED)

    def _handle_server_message(self, message: ProtocolMessage) -> NetworkRuntimeUpdate:
        if isinstance(message, ServerWelcome):
            self._session_id = message.session_id
            self._player_id = message.player_id
            self.connection = ConnectionViewModel(ConnectionState.QUEUED, "Connected; waiting for match")
            return NetworkRuntimeUpdate(self.connection)
        if isinstance(message, JoinRejectedRoomFull):
            self.connection = ConnectionViewModel(ConnectionState.ENDED, "Room full")
            return NetworkRuntimeUpdate(self.connection)
        if isinstance(message, QueueStatus):
            return self._handle_queue_status(message)
        if isinstance(message, MatchStart):
            return self._start_match(message)
        if isinstance(
            message,
            MatchSnapshot | GarbageAssigned | RespawnAssigned | OpponentStateSummary | MatchEnd,
        ):
            return self._forward_match_message(message)
        return NetworkRuntimeUpdate(self.connection)

    def _handle_queue_status(self, message: QueueStatus) -> NetworkRuntimeUpdate:
        if self._player_id is None or message.player_id != self._player_id:
            return NetworkRuntimeUpdate(self.connection)
        if message.position == 0:
            status = "Active slot assigned; waiting for match start"
        elif message.position is None:
            status = "Not queued"
        else:
            status = f"Waiting position {message.position}"
        self.connection = ConnectionViewModel(ConnectionState.QUEUED, status)
        return NetworkRuntimeUpdate(self.connection)

    def _start_match(self, message: MatchStart) -> NetworkRuntimeUpdate:
        if self._net_client is None or self._session_id is None or self._player_id is None:
            return NetworkRuntimeUpdate(self.connection)
        self.versus_session = VersusGameSession(
            session_id=self._session_id,
            player_id=self._player_id,
            action_source=self._action_source,
            net_client=self._net_client,
        )
        self.versus_session.handle_server_message(message)
        self.connection = ConnectionViewModel(ConnectionState.IN_MATCH)
        return NetworkRuntimeUpdate(self.connection, self.versus_session.view_model)

    def _forward_match_message(self, message: ProtocolMessage) -> NetworkRuntimeUpdate:
        if self.versus_session is None:
            return NetworkRuntimeUpdate(self.connection)
        self.versus_session.handle_server_message(message)
        self.connection = self.versus_session.view_model.connection
        return NetworkRuntimeUpdate(self.connection, self.versus_session.view_model)

    def _send_heartbeat_if_due(self) -> None:
        client = self._net_client
        if client is None or self._session_id is None or self._player_id is None:
            return
        now = time.monotonic()
        if now - self._last_heartbeat_at < 0.5:
            return
        self._last_heartbeat_at = now
        client.send(
            Heartbeat(
                session_id=self._session_id,
                player_id=self._player_id,
                sent_at=now,
            ),
        )


def _player_slug(player_name: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in player_name)
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "player"


__all__ = [
    "ClientNetworkRuntime",
    "ConnectedNetClient",
    "NetworkRuntimeUpdate",
    "ServerAddress",
]
