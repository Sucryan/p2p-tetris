"""Deterministic action source for tests and reproducible local sessions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from p2p_tetris.controllers.base import ActionBatch
from p2p_tetris.game_core.actions import PlayerAction


class ScriptedController:
    """Replay a finite tick-indexed action script."""

    def __init__(
        self,
        script: Mapping[int, Iterable[PlayerAction]] | Iterable[ActionBatch],
    ) -> None:
        batches = script if not isinstance(script, Mapping) else self._from_mapping(script)
        actions_by_tick: dict[int, tuple[PlayerAction, ...]] = {}
        for batch in batches:
            if batch.tick in actions_by_tick:
                actions_by_tick[batch.tick] = actions_by_tick[batch.tick] + batch.actions
            else:
                actions_by_tick[batch.tick] = batch.actions
        self._actions_by_tick = actions_by_tick

    def pull_actions(self, tick: int) -> ActionBatch:
        if tick < 0:
            msg = "tick must be non-negative"
            raise ValueError(msg)
        return ActionBatch(tick=tick, actions=self._actions_by_tick.get(tick, ()))

    @staticmethod
    def _from_mapping(
        script: Mapping[int, Iterable[PlayerAction]],
    ) -> tuple[ActionBatch, ...]:
        return tuple(
            ActionBatch(tick=tick, actions=tuple(actions))
            for tick, actions in sorted(script.items())
        )


__all__ = ["ScriptedController"]
