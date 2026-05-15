"""Non-blocking UDP client endpoint."""

from __future__ import annotations

import socket

from p2p_tetris.common import SystemClock
from p2p_tetris.common.time import MonotonicClock
from p2p_tetris.net.protocol import Address, MessageCodec, NetworkEvent, ProtocolMessage


class UdpClient:
    def __init__(
        self,
        server_address: Address,
        *,
        bind_address: Address | None = None,
        codec: MessageCodec | None = None,
        clock: MonotonicClock | None = None,
    ) -> None:
        self._server_address = server_address
        self._codec = codec or MessageCodec()
        self._clock = clock or SystemClock()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setblocking(False)
        if bind_address is not None:
            self._socket.bind(bind_address)

    @property
    def local_address(self) -> Address:
        host, port = self._socket.getsockname()
        return (host, port)

    def send(self, message: ProtocolMessage) -> None:
        self._socket.sendto(self._codec.encode(message), self._server_address)

    def receive(self, max_datagrams: int = 100) -> list[NetworkEvent]:
        events: list[NetworkEvent] = []
        for _ in range(max_datagrams):
            try:
                datagram, endpoint = self._socket.recvfrom(65535)
            except BlockingIOError:
                break
            events.append(
                NetworkEvent(
                    message=self._codec.decode(datagram),
                    endpoint=(endpoint[0], endpoint[1]),
                    received_at=self._clock.now(),
                ),
            )
        return events

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> UdpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
