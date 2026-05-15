from __future__ import annotations

from p2p_tetris.common import PlayerId
from p2p_tetris.server.queue import QueueManager


def test_queue_manager_active_waiting_room_full_and_rotation() -> None:
    queue = QueueManager()
    players = [PlayerId(f"p{i}") for i in range(1, 9)]
    results = [queue.join(player) for player in players]

    assert [result.accepted for result in results] == [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    assert queue.active_players == (players[0], players[1])
    assert queue.waiting_players == tuple(players[2:7])
    assert results[-1].rejection is not None

    queue.rotate_after_match(players[0])
    assert queue.active_players == (players[0], players[2])
    assert queue.waiting_players == tuple(players[3:7])
