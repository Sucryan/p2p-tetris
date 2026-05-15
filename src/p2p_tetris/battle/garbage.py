"""Garbage generation, cancellation, and delayed application."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from random import Random
from typing import Deque

from p2p_tetris.battle.events import AttackEvent, GarbageEvent, GarbageRow
from p2p_tetris.common import MonotonicClock, PlayerId


@dataclass(frozen=True, slots=True)
class _PendingGarbage:
    event: GarbageEvent
    remaining_lines: int
    ready_at: float

    def consume(self, lines: int) -> tuple[_PendingGarbage | None, int]:
        consumed = min(lines, self.remaining_lines)
        remaining = self.remaining_lines - consumed
        if remaining == 0:
            return None, consumed
        return (
            _PendingGarbage(
                event=self.event.with_line_count(remaining),
                remaining_lines=remaining,
                ready_at=self.ready_at,
            ),
            consumed,
        )


class GarbageGenerator:
    """Create deterministic holed garbage events."""

    def __init__(self, *, board_width: int = 10, base_seed: int = 0) -> None:
        if board_width <= 0:
            msg = "board_width must be positive"
            raise ValueError(msg)
        if base_seed < 0:
            msg = "base_seed must be non-negative"
            raise ValueError(msg)
        self._board_width = board_width
        self._base_seed = base_seed

    @property
    def board_width(self) -> int:
        return self._board_width

    def generate(
        self,
        *,
        source: PlayerId,
        target: PlayerId,
        lines: int,
        seq: int,
        seed: int | None = None,
    ) -> GarbageEvent:
        if lines <= 0:
            msg = "lines must be positive"
            raise ValueError(msg)
        event_seed = self._derive_seed(source=source, target=target, seq=seq) if seed is None else seed
        hole = Random(event_seed).randrange(self._board_width)
        rows = tuple(GarbageRow(width=self._board_width, hole=hole) for _ in range(lines))
        return GarbageEvent(source=source, seq=seq, target=target, seed=event_seed, rows=rows)

    def _derive_seed(self, *, source: PlayerId, target: PlayerId, seq: int) -> int:
        material = f"{self._base_seed}:{source.value}:{target.value}:{seq}".encode()
        return int.from_bytes(sha256(material).digest()[:8], "big")


class GarbageQueue:
    """Pending incoming garbage with attack cancellation and delayed apply."""

    def __init__(self, clock: MonotonicClock, *, apply_delay_seconds: float = 0.0) -> None:
        if apply_delay_seconds < 0:
            msg = "apply_delay_seconds must be non-negative"
            raise ValueError(msg)
        self._clock = clock
        self._apply_delay_seconds = apply_delay_seconds
        self._pending: Deque[_PendingGarbage] = deque()

    @property
    def pending_lines(self) -> int:
        return sum(item.remaining_lines for item in self._pending)

    def enqueue(self, event: GarbageEvent) -> None:
        self._pending.append(
            _PendingGarbage(
                event=event,
                remaining_lines=event.lines,
                ready_at=self._clock.now() + self._apply_delay_seconds,
            ),
        )

    def cancel_with_attack(self, attack: AttackEvent) -> AttackEvent | None:
        lines_to_cancel = attack.lines
        while lines_to_cancel > 0 and self._pending:
            current = self._pending.popleft()
            replacement, consumed = current.consume(lines_to_cancel)
            lines_to_cancel -= consumed
            if replacement is not None:
                self._pending.appendleft(replacement)
        if lines_to_cancel == 0:
            return None
        return AttackEvent(
            source=attack.source,
            seq=attack.seq,
            target=attack.target,
            lines=lines_to_cancel,
        )

    def pop_ready_after_lock(self) -> tuple[GarbageEvent, ...]:
        ready: list[GarbageEvent] = []
        now = self._clock.now()
        while self._pending and self._pending[0].ready_at <= now:
            current = self._pending.popleft()
            ready.append(current.event.with_line_count(current.remaining_lines))
        return tuple(ready)

    def reset(self) -> None:
        self._pending.clear()


__all__ = ["GarbageGenerator", "GarbageQueue", "GarbageRow"]
