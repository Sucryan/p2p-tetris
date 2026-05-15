"""Battle-facing structural protocols for game-core rule events."""

from __future__ import annotations

from typing import Protocol

from p2p_tetris.game_core.events import ClearEvent, TopOutEvent, TSpinType


class ClearEventLike(Protocol):
    @property
    def lines_cleared(self) -> int: ...

    @property
    def t_spin(self) -> TSpinType: ...

    @property
    def combo(self) -> int: ...

    @property
    def back_to_back(self) -> bool: ...


class TopOutEventLike(Protocol):
    @property
    def reason(self) -> str: ...


__all__ = [
    "ClearEvent",
    "ClearEventLike",
    "TSpinType",
    "TopOutEvent",
    "TopOutEventLike",
]
