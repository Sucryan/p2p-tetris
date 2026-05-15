"""Controller interfaces shared by human, scripted, and future agent inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from p2p_tetris.game_core.actions import PlayerAction


@dataclass(frozen=True, slots=True)
class ActionBatch:
    """Actions to apply on one fixed simulation tick."""

    tick: int
    actions: tuple[PlayerAction, ...] = ()

    def __post_init__(self) -> None:
        if self.tick < 0:
            msg = "tick must be non-negative"
            raise ValueError(msg)


class ActionSource(Protocol):
    """Produces player actions aligned to fixed runtime ticks."""

    def pull_actions(self, tick: int) -> ActionBatch:
        """Return every action that should be applied on ``tick``."""


class RLPolicy(Protocol):
    """Future policy interface for RL agents without importing any RL runtime."""

    def select_actions(
        self,
        snapshot: object,
        *,
        tick: int,
    ) -> tuple[PlayerAction, ...]:
        """Choose actions from an immutable engine observation."""


class RLControllerAdapter(Protocol):
    """ActionSource-compatible wrapper shape for a future RL policy."""

    policy: RLPolicy

    def observe(self, snapshot: object) -> None:
        """Provide the latest observation before the next ``pull_actions`` call."""

    def pull_actions(self, tick: int) -> ActionBatch:
        """Return policy-selected actions for a fixed tick."""


__all__ = ["ActionBatch", "ActionSource", "RLControllerAdapter", "RLPolicy"]
