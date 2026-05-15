from __future__ import annotations

from p2p_tetris.common import NetworkConfig, PlayerId
from p2p_tetris.net import ClientHello, Heartbeat
from p2p_tetris.server.sessions import SessionManager


def test_session_manager_hello_duplicate_heartbeat_and_timeout(fake_clock) -> None:
    manager = SessionManager(fake_clock, NetworkConfig(session_timeout_seconds=2.0))
    player = PlayerId("p1")
    record, welcome, is_new = manager.handle_client_hello(
        ClientHello(player),
        ("127.0.0.1", 10000),
    )

    assert is_new is True
    assert welcome.player_id == player

    duplicate, duplicate_welcome, is_duplicate_new = manager.handle_client_hello(
        ClientHello(player),
        ("127.0.0.1", 10001),
    )
    assert is_duplicate_new is False
    assert duplicate.session_id == record.session_id
    assert duplicate_welcome.session_id == welcome.session_id

    fake_clock.advance(1.0)
    heartbeat_welcome = manager.handle_heartbeat(
        Heartbeat(record.session_id, player, 1.0),
        ("127.0.0.1", 10001),
    )
    assert heartbeat_welcome is not None

    fake_clock.advance(1.9)
    assert manager.expire_timed_out() == []
    fake_clock.advance(0.1)
    assert manager.expire_timed_out()[0].player_id == player
