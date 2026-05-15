"""Strongly typed identifier value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class _StringId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"{type(self).__name__} value must be a string"
            raise TypeError(msg)
        if self.value == "":
            msg = f"{type(self).__name__} value must be non-empty"
            raise ValueError(msg)

    @classmethod
    def new(cls) -> Self:
        """Create a new random identifier."""

        return cls(uuid4().hex)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PlayerId(_StringId):
    """Identifier for a connected or active player."""


@dataclass(frozen=True, slots=True)
class SessionId(_StringId):
    """Identifier for a network session."""


@dataclass(frozen=True, slots=True)
class MatchId(_StringId):
    """Identifier for a match."""

