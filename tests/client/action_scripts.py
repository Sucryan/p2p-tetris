"""Deterministic action scripts for controller and runtime tests."""

from __future__ import annotations

from p2p_tetris.controllers import ActionBatch
from p2p_tetris.game_core import PlayerAction


def deterministic_action_script() -> tuple[ActionBatch, ...]:
    return (
        ActionBatch(0, (PlayerAction.MOVE_LEFT, PlayerAction.ROTATE_CW)),
        ActionBatch(1, (PlayerAction.SOFT_DROP,)),
        ActionBatch(2, (PlayerAction.SOFT_DROP,)),
        ActionBatch(3, (PlayerAction.HARD_DROP,)),
        ActionBatch(4, (PlayerAction.HOLD, PlayerAction.MOVE_RIGHT)),
        ActionBatch(5, (PlayerAction.HARD_DROP,)),
    )


__all__ = ["deterministic_action_script"]
