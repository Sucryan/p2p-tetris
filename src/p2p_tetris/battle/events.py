"""Serializable battle-level events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from p2p_tetris.common import PlayerId


def _player_to_wire(player_id: PlayerId | None) -> str | None:
    return None if player_id is None else player_id.value


def _player_from_wire(value: object) -> PlayerId | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "player id must be encoded as a string or null"
        raise TypeError(msg)
    return PlayerId(value)


def _require_int(name: str, value: object) -> int:
    if not isinstance(value, int):
        msg = f"{name} must be an integer"
        raise TypeError(msg)
    return value


def _require_str(name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{name} must be a string"
        raise TypeError(msg)
    return value


def _require_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        msg = f"{name} must be a bool"
        raise TypeError(msg)
    return value


def _payload(data: dict[str, Any], event_type: str) -> dict[str, Any]:
    if data.get("type") != event_type:
        msg = f"expected {event_type} payload"
        raise ValueError(msg)
    return data


@dataclass(frozen=True, slots=True)
class BattleEvent:
    """Base shape shared by all battle events."""

    source: PlayerId | None
    seq: int

    event_type: ClassVar[str] = "battle"

    def __post_init__(self) -> None:
        if not isinstance(self.seq, int):
            msg = "seq must be an integer"
            raise TypeError(msg)
        if self.seq < 0:
            msg = "seq must be non-negative"
            raise ValueError(msg)

    def _base_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type,
            "source": _player_to_wire(self.source),
            "seq": self.seq,
        }


@dataclass(frozen=True, slots=True)
class AttackEvent(BattleEvent):
    target: PlayerId
    lines: int

    event_type: ClassVar[str] = "attack"

    def __post_init__(self) -> None:
        BattleEvent.__post_init__(self)
        if self.lines < 0:
            msg = "lines must be non-negative"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        data = self._base_dict()
        data.update({"target": self.target.value, "lines": self.lines})
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttackEvent:
        payload = _payload(data, cls.event_type)
        source = _player_from_wire(payload.get("source"))
        return cls(
            source=source,
            seq=_require_int("seq", payload.get("seq")),
            target=PlayerId(_require_str("target", payload.get("target"))),
            lines=_require_int("lines", payload.get("lines")),
        )


@dataclass(frozen=True, slots=True)
class GarbageRow:
    """One garbage row with a hole and an extensible filled-cell kind."""

    width: int
    hole: int
    filled_cell: str = "garbage"

    def __post_init__(self) -> None:
        if self.width <= 0:
            msg = "width must be positive"
            raise ValueError(msg)
        if not 0 <= self.hole < self.width:
            msg = "hole must be within row width"
            raise ValueError(msg)
        if self.filled_cell == "":
            msg = "filled_cell must be non-empty"
            raise ValueError(msg)

    def cells(self) -> tuple[str | None, ...]:
        return tuple(None if column == self.hole else self.filled_cell for column in range(self.width))

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "hole": self.hole,
            "filled_cell": self.filled_cell,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GarbageRow:
        return cls(
            width=_require_int("width", data.get("width")),
            hole=_require_int("hole", data.get("hole")),
            filled_cell=_require_str("filled_cell", data.get("filled_cell")),
        )


@dataclass(frozen=True, slots=True)
class GarbageEvent(BattleEvent):
    target: PlayerId
    seed: int
    rows: tuple[GarbageRow, ...]

    event_type: ClassVar[str] = "garbage"

    def __post_init__(self) -> None:
        BattleEvent.__post_init__(self)
        if self.seed < 0:
            msg = "seed must be non-negative"
            raise ValueError(msg)
        if len(self.rows) == 0:
            msg = "rows must be non-empty"
            raise ValueError(msg)

    @property
    def lines(self) -> int:
        return len(self.rows)

    def with_line_count(self, lines: int) -> GarbageEvent:
        if lines <= 0 or lines > self.lines:
            msg = "lines must be within the existing garbage event size"
            raise ValueError(msg)
        return GarbageEvent(
            source=self.source,
            seq=self.seq,
            target=self.target,
            seed=self.seed,
            rows=self.rows[:lines],
        )

    def to_dict(self) -> dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "target": self.target.value,
                "seed": self.seed,
                "rows": [row.to_dict() for row in self.rows],
            },
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GarbageEvent:
        payload = _payload(data, cls.event_type)
        rows_payload = payload.get("rows")
        if not isinstance(rows_payload, list):
            msg = "rows must be a list"
            raise TypeError(msg)
        return cls(
            source=_player_from_wire(payload.get("source")),
            seq=_require_int("seq", payload.get("seq")),
            target=PlayerId(_require_str("target", payload.get("target"))),
            seed=_require_int("seed", payload.get("seed")),
            rows=tuple(GarbageRow.from_dict(row) for row in rows_payload),
        )


@dataclass(frozen=True, slots=True)
class KOEvent(BattleEvent):
    knocked_out: PlayerId
    respawn_at: float
    reason: str

    event_type: ClassVar[str] = "ko"

    def to_dict(self) -> dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "knocked_out": self.knocked_out.value,
                "respawn_at": self.respawn_at,
                "reason": self.reason,
            },
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KOEvent:
        payload = _payload(data, cls.event_type)
        respawn_at = payload.get("respawn_at")
        if not isinstance(respawn_at, int | float):
            msg = "respawn_at must be a number"
            raise TypeError(msg)
        return cls(
            source=_player_from_wire(payload.get("source")),
            seq=_require_int("seq", payload.get("seq")),
            knocked_out=PlayerId(_require_str("knocked_out", payload.get("knocked_out"))),
            respawn_at=float(respawn_at),
            reason=_require_str("reason", payload.get("reason")),
        )


@dataclass(frozen=True, slots=True)
class RespawnEvent(BattleEvent):
    player: PlayerId

    event_type: ClassVar[str] = "respawn"

    def to_dict(self) -> dict[str, Any]:
        data = self._base_dict()
        data.update({"player": self.player.value})
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RespawnEvent:
        payload = _payload(data, cls.event_type)
        return cls(
            source=_player_from_wire(payload.get("source")),
            seq=_require_int("seq", payload.get("seq")),
            player=PlayerId(_require_str("player", payload.get("player"))),
        )


@dataclass(frozen=True, slots=True)
class MatchResult(BattleEvent):
    winner: PlayerId | None
    is_draw: bool
    reason: str

    event_type: ClassVar[str] = "match_result"

    def __post_init__(self) -> None:
        BattleEvent.__post_init__(self)
        if self.is_draw and self.winner is not None:
            msg = "draw results cannot have a winner"
            raise ValueError(msg)
        if not self.is_draw and self.winner is None:
            msg = "non-draw results must have a winner"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "winner": _player_to_wire(self.winner),
                "is_draw": self.is_draw,
                "reason": self.reason,
            },
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatchResult:
        payload = _payload(data, cls.event_type)
        return cls(
            source=_player_from_wire(payload.get("source")),
            seq=_require_int("seq", payload.get("seq")),
            winner=_player_from_wire(payload.get("winner")),
            is_draw=_require_bool("is_draw", payload.get("is_draw")),
            reason=_require_str("reason", payload.get("reason")),
        )


BattleEventPayload = AttackEvent | GarbageEvent | KOEvent | RespawnEvent | MatchResult


def event_from_dict(data: dict[str, Any]) -> BattleEventPayload:
    event_type = data.get("type")
    if event_type == AttackEvent.event_type:
        return AttackEvent.from_dict(data)
    if event_type == GarbageEvent.event_type:
        return GarbageEvent.from_dict(data)
    if event_type == KOEvent.event_type:
        return KOEvent.from_dict(data)
    if event_type == RespawnEvent.event_type:
        return RespawnEvent.from_dict(data)
    if event_type == MatchResult.event_type:
        return MatchResult.from_dict(data)
    msg = f"unknown battle event type: {event_type!r}"
    raise ValueError(msg)


__all__ = [
    "AttackEvent",
    "BattleEvent",
    "BattleEventPayload",
    "GarbageEvent",
    "GarbageRow",
    "KOEvent",
    "MatchResult",
    "RespawnEvent",
    "event_from_dict",
]
