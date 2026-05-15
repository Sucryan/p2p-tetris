"""Runtime-level event labels for session state changes."""

from __future__ import annotations

from enum import Enum, auto


class ClientRuntimeEvent(Enum):
    RESET = auto()
    STARTED = auto()
    PAUSED = auto()
    RESUMED = auto()
    TICKED = auto()
    MATCH_STARTED = auto()
    MATCH_ENDED = auto()


__all__ = ["ClientRuntimeEvent"]
