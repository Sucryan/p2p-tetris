"""Concrete network adapters for the GUI-independent client runtime."""

from __future__ import annotations

from p2p_tetris.client.versus_session import NetClientPort
from p2p_tetris.net import ProtocolMessage, UdpClient
from p2p_tetris.net.protocol import Address


class UdpNetClient(NetClientPort):
    """Adapt the UDP endpoint to the runtime's typed message port."""

    def __init__(self, server_address: Address) -> None:
        self._endpoint = UdpClient(server_address)

    @property
    def local_address(self) -> Address:
        return self._endpoint.local_address

    def send(self, message: ProtocolMessage) -> None:
        self._endpoint.send(message)

    def receive(self) -> tuple[ProtocolMessage, ...]:
        return tuple(event.message for event in self._endpoint.receive())

    def close(self) -> None:
        self._endpoint.close()

    def __enter__(self) -> UdpNetClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["UdpNetClient"]
