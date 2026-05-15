from __future__ import annotations

import time

from p2p_tetris.common import PlayerId
from p2p_tetris.net import ClientHello, NetworkEvent, UdpClient, UdpServer


def test_udp_client_server_datagram_smoke() -> None:
    server = UdpServer(("127.0.0.1", 0))
    client = UdpClient(server.address)
    try:
        client.send(ClientHello(PlayerId("p1"), "Ada"))
        events: list[NetworkEvent] = []
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not events:
            events = server.receive()
        assert len(events) == 1
        assert events[0].message == ClientHello(PlayerId("p1"), "Ada")
    finally:
        client.close()
        server.close()
