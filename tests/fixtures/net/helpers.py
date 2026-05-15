"""Fake transport and deterministic network-loss helpers."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import PlayerId
from p2p_tetris.net import MessageCodec, NetworkEvent, ProtocolMessage
from p2p_tetris.net.protocol import Address


@dataclass(frozen=True, slots=True)
class SentMessage:
    message: ProtocolMessage
    endpoint: Address


class FakeTransport:
    def __init__(self) -> None:
        self.inbound: list[NetworkEvent] = []
        self.sent: list[SentMessage] = []

    def queue_inbound(
        self,
        message: ProtocolMessage,
        endpoint: Address = ("127.0.0.1", 10000),
        received_at: float = 0.0,
    ) -> None:
        self.inbound.append(
            NetworkEvent(message=message, endpoint=endpoint, received_at=received_at),
        )

    def poll(self, max_datagrams: int = 100) -> list[NetworkEvent]:
        events = self.inbound[:max_datagrams]
        del self.inbound[:max_datagrams]
        return events

    def send(self, message: ProtocolMessage, endpoint: Address) -> None:
        self.sent.append(SentMessage(message=message, endpoint=endpoint))

    def messages(self, message_type: type[ProtocolMessage]) -> list[ProtocolMessage]:
        return [sent.message for sent in self.sent if isinstance(sent.message, message_type)]


@dataclass(frozen=True, slots=True)
class MockClient:
    player_id: PlayerId
    endpoint: Address

    def send(self, transport: FakeTransport, message: ProtocolMessage) -> None:
        transport.queue_inbound(message, self.endpoint)

    def received(self, transport: FakeTransport) -> tuple[ProtocolMessage, ...]:
        return tuple(sent.message for sent in transport.sent if sent.endpoint == self.endpoint)


class LossyDatagramLink:
    def __init__(
        self,
        *,
        drop_every: int | None = None,
        duplicate_every: int | None = None,
        codec: MessageCodec | None = None,
    ) -> None:
        self._drop_every = drop_every
        self._duplicate_every = duplicate_every
        self._codec = codec or MessageCodec()
        self._count = 0

    def transmit(self, message: ProtocolMessage) -> list[bytes]:
        self._count += 1
        if self._drop_every is not None and self._count % self._drop_every == 0:
            return []
        datagram = self._codec.encode(message)
        if self._duplicate_every is not None and self._count % self._duplicate_every == 0:
            return [datagram, datagram]
        return [datagram]
