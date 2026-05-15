from __future__ import annotations

from p2p_tetris.client import ConnectionState, LocalGameSession
from p2p_tetris.controllers import ScriptedController
from p2p_tetris.game_core import PieceLockedEvent, PlayerAction

from tests.client.action_scripts import deterministic_action_script


def test_local_session_lifecycle_and_fixed_ticks_are_deterministic() -> None:
    first = LocalGameSession(ScriptedController(deterministic_action_script()), seed=2026)
    second = LocalGameSession(ScriptedController(deterministic_action_script()), seed=2026)

    first.start()
    second.start()
    first_events = first.tick(6)
    second_events = second.tick(6)

    assert first.tick_count == 6
    assert second.tick_count == 6
    assert first.snapshot() == second.snapshot()
    assert first_events == second_events
    assert any(isinstance(event, PieceLockedEvent) for event in first_events)
    assert first.view_model.connection.state is ConnectionState.DISCONNECTED
    assert first.view_model.solo_hud.tick == 6


def test_local_session_pause_resume_and_restart() -> None:
    session = LocalGameSession(ScriptedController({0: (PlayerAction.HARD_DROP,)}), seed=1)
    session.start()
    session.pause()

    assert session.tick(3) == ()
    assert session.tick_count == 0
    assert session.view_model.solo_hud.is_paused

    session.resume()
    events = session.tick()

    assert any(isinstance(event, PieceLockedEvent) for event in events)
    assert session.tick_count == 1

    session.restart(seed=2)
    assert session.tick_count == 0
    assert session.is_running
    assert not session.is_paused
