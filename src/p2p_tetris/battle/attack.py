"""Attack line calculation from game-core clear events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from p2p_tetris.battle._game_core_events import ClearEventLike, TSpinType
from p2p_tetris.battle.events import AttackEvent
from p2p_tetris.common import PlayerId


@dataclass(frozen=True, slots=True)
class AttackTable:
    """Configurable guideline-like attack table."""

    single: int
    double: int
    triple: int
    tetris: int
    t_spin_mini_single: int
    t_spin_single: int
    t_spin_double: int
    t_spin_triple: int
    back_to_back_bonus: int
    combo_bonus: tuple[int, ...]

    @classmethod
    def default(cls) -> AttackTable:
        return cls(
            single=0,
            double=1,
            triple=2,
            tetris=4,
            t_spin_mini_single=1,
            t_spin_single=2,
            t_spin_double=4,
            t_spin_triple=6,
            back_to_back_bonus=1,
            combo_bonus=(0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5),
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        combo_bonus = data.get("combo_bonus")
        if not isinstance(combo_bonus, list):
            msg = "combo_bonus must be a list"
            raise TypeError(msg)

        def require_int(key: str) -> int:
            value = data.get(key)
            if not isinstance(value, int):
                msg = f"{key} must be an integer"
                raise TypeError(msg)
            return value

        if not all(isinstance(value, int) for value in combo_bonus):
            msg = "combo_bonus entries must be integers"
            raise TypeError(msg)
        return cls(
            single=require_int("single"),
            double=require_int("double"),
            triple=require_int("triple"),
            tetris=require_int("tetris"),
            t_spin_mini_single=require_int("t_spin_mini_single"),
            t_spin_single=require_int("t_spin_single"),
            t_spin_double=require_int("t_spin_double"),
            t_spin_triple=require_int("t_spin_triple"),
            back_to_back_bonus=require_int("back_to_back_bonus"),
            combo_bonus=tuple(combo_bonus),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "single": self.single,
            "double": self.double,
            "triple": self.triple,
            "tetris": self.tetris,
            "t_spin_mini_single": self.t_spin_mini_single,
            "t_spin_single": self.t_spin_single,
            "t_spin_double": self.t_spin_double,
            "t_spin_triple": self.t_spin_triple,
            "back_to_back_bonus": self.back_to_back_bonus,
            "combo_bonus": list(self.combo_bonus),
        }

    def combo_lines(self, combo: int) -> int:
        if combo < 0:
            return 0
        if combo >= len(self.combo_bonus):
            return self.combo_bonus[-1]
        return self.combo_bonus[combo]


class AttackCalculator:
    """Translate line clear events into attack events."""

    def __init__(self, table: AttackTable | None = None) -> None:
        self._table = table or AttackTable.default()

    @property
    def table(self) -> AttackTable:
        return self._table

    def calculate(
        self,
        clear_event: ClearEventLike,
        *,
        source: PlayerId,
        target: PlayerId,
        seq: int,
    ) -> AttackEvent:
        if clear_event.lines_cleared < 0:
            msg = "lines_cleared must be non-negative"
            raise ValueError(msg)
        base_lines = self._base_lines(clear_event)
        b2b_bonus = self._table.back_to_back_bonus if clear_event.back_to_back and base_lines > 0 else 0
        combo_bonus = self._table.combo_lines(clear_event.combo) if clear_event.lines_cleared > 0 else 0
        return AttackEvent(
            source=source,
            seq=seq,
            target=target,
            lines=base_lines + b2b_bonus + combo_bonus,
        )

    def _base_lines(self, clear_event: ClearEventLike) -> int:
        lines = clear_event.lines_cleared
        if clear_event.t_spin == TSpinType.MINI:
            return self._table.t_spin_mini_single if lines == 1 else 0
        if clear_event.t_spin == TSpinType.FULL:
            if lines == 1:
                return self._table.t_spin_single
            if lines == 2:
                return self._table.t_spin_double
            if lines == 3:
                return self._table.t_spin_triple
            return 0
        if lines == 1:
            return self._table.single
        if lines == 2:
            return self._table.double
        if lines == 3:
            return self._table.triple
        if lines == 4:
            return self._table.tetris
        return 0


__all__ = ["AttackCalculator", "AttackTable"]
