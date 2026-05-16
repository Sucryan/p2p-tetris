from __future__ import annotations

import time

from p2p_tetris.common import MatchConfig, PlayerId
from p2p_tetris.net import (
    AttackReported,
    ClientHello,
    GarbageAssigned,
    MatchStart,
    ReliableAck,
    ServerWelcome,
    UdpClient,
)
from p2p_tetris.net.protocol import NetworkEvent
from p2p_tetris.server import ServerApp, UdpServerPort
from tests.fixtures.net.helpers import FakeTransport


def test_server_app_two_mock_clients_enter_match(fake_clock) -> None:
    transport = FakeTransport()
    app = ServerApp(transport=transport, clock=fake_clock)
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")

    transport.queue_inbound(ClientHello(p1), ("127.0.0.1", 10001))
    transport.queue_inbound(ClientHello(p2), ("127.0.0.1", 10002))
    app.poll_once()

    assert len([sent for sent in transport.sent if isinstance(sent.message, ServerWelcome)]) == 2
    starts = [sent.message for sent in transport.sent if isinstance(sent.message, MatchStart)]
    assert len(starts) == 2
    assert starts[0].active_players == (p1, p2)


def test_server_app_reliable_attack_routes_ack_and_garbage(fake_clock) -> None:
    transport = FakeTransport()
    app = ServerApp(transport=transport, clock=fake_clock)
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    transport.queue_inbound(ClientHello(p1), ("127.0.0.1", 10001))
    transport.queue_inbound(ClientHello(p2), ("127.0.0.1", 10002))
    app.poll_once()
    start = next(sent.message for sent in transport.sent if isinstance(sent.message, MatchStart))
    session = app.sessions.session_for_player(p1)
    assert session is not None
    transport.sent.clear()

    transport.queue_inbound(
        AttackReported(session, start.match_id, p1, p2, 1, 4, "a1"),
        ("127.0.0.1", 10001),
    )
    app.poll_once()

    assert any(isinstance(sent.message, ReliableAck) for sent in transport.sent)
    assert any(isinstance(sent.message, GarbageAssigned) for sent in transport.sent)


def test_server_app_garbage_assignment_ack_clears_resend_tracking(fake_clock) -> None:
    transport = FakeTransport()
    app = ServerApp(transport=transport, clock=fake_clock)
    p1 = PlayerId("p1")
    p2 = PlayerId("p2")
    transport.queue_inbound(ClientHello(p1), ("127.0.0.1", 10001))
    transport.queue_inbound(ClientHello(p2), ("127.0.0.1", 10002))
    app.poll_once()
    start = next(sent.message for sent in transport.sent if isinstance(sent.message, MatchStart))
    session = app.sessions.session_for_player(p1)
    assert session is not None
    transport.sent.clear()

    transport.queue_inbound(
        AttackReported(session, start.match_id, p1, p2, 1, 4, "a1"),
        ("127.0.0.1", 10001),
    )
    app.poll_once()
    garbage = next(sent.message for sent in transport.sent if isinstance(sent.message, GarbageAssigned))
    assert app.reliability.pending_count == 1

    transport.queue_inbound(
        ReliableAck(
            session_id=garbage.session_id,
            sender_id=garbage.target_id,
            acked_sender_id=garbage.sender_id,
            received_seq=garbage.event_seq,
            match_id=garbage.match_id,
        ),
        ("127.0.0.1", 10002),
    )
    app.poll_once()

    assert app.reliability.pending_count == 0


def test_server_app_udp_smoke_hello_welcome() -> None:
    app = ServerApp.with_udp(host="127.0.0.1", port=0, match_config=MatchConfig())
    transport = app.transport
    assert isinstance(transport, UdpServerPort)
    address = transport.address
    client = UdpClient(address)
    try:
        client.send(ClientHello(PlayerId("p1")))
        events: list[NetworkEvent] = []
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not events:
            app.poll_once()
            events = client.receive()
        assert any(isinstance(event.message, ServerWelcome) for event in events)
    finally:
        client.close()
        app.close()
