from __future__ import annotations

from p2p_tetris.controllers import (
    ActionBatch,
    ActionSource,
    RLControllerAdapter,
    RLPolicy,
    ScriptedController,
)
from p2p_tetris.game_core import PlayerAction


def _pull_from_source(source: ActionSource, tick: int) -> ActionBatch:
    return source.pull_actions(tick)


def test_scripted_controller_replays_tick_aligned_multi_action_batches() -> None:
    controller = ScriptedController(
        (
            ActionBatch(2, (PlayerAction.MOVE_LEFT,)),
            ActionBatch(2, (PlayerAction.ROTATE_CW, PlayerAction.HARD_DROP)),
            ActionBatch(4, (PlayerAction.HOLD,)),
        ),
    )

    assert _pull_from_source(controller, 0) == ActionBatch(0, ())
    assert _pull_from_source(controller, 2) == ActionBatch(
        2,
        (PlayerAction.MOVE_LEFT, PlayerAction.ROTATE_CW, PlayerAction.HARD_DROP),
    )
    assert _pull_from_source(controller, 4) == ActionBatch(4, (PlayerAction.HOLD,))


class _DummyPolicy:
    def select_actions(
        self,
        snapshot: object,
        *,
        tick: int,
    ) -> tuple[PlayerAction, ...]:
        _ = snapshot
        _ = tick
        return (PlayerAction.NO_OP,)


class _DummyRLAdapter:
    def __init__(self) -> None:
        self.policy: RLPolicy = _DummyPolicy()
        self._snapshot: object | None = None

    def observe(self, snapshot: object) -> None:
        self._snapshot = snapshot

    def pull_actions(self, tick: int) -> ActionBatch:
        if self._snapshot is None:
            return ActionBatch(tick, ())
        return ActionBatch(tick, self.policy.select_actions(self._snapshot, tick=tick))


def _accept_rl_adapter(adapter: RLControllerAdapter) -> RLControllerAdapter:
    return adapter


def test_rl_controller_adapter_protocol_accepts_plain_structural_adapter() -> None:
    adapter = _accept_rl_adapter(_DummyRLAdapter())

    assert adapter.pull_actions(0) == ActionBatch(0, ())
