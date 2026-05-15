from __future__ import annotations

from typing import Protocol

from p2p_tetris.battle import AttackEvent, GarbageGenerator, GarbageQueue
from p2p_tetris.common import PlayerId


class AdvancingClock(Protocol):
    def now(self) -> float: ...

    def advance(self, seconds: float) -> None: ...


def test_garbage_generator_uses_deterministic_event_seed_and_one_hole_per_event() -> None:
    generator = GarbageGenerator(board_width=10)
    source = PlayerId("p1")
    target = PlayerId("p2")

    first = generator.generate(source=source, target=target, lines=4, seq=1, seed=12345)
    replay = generator.generate(source=source, target=target, lines=4, seq=1, seed=12345)
    second = generator.generate(source=source, target=target, lines=4, seq=2, seed=12346)

    assert replay == first
    assert len({row.hole for row in first.rows}) == 1
    assert first.seed == 12345
    assert first.rows != second.rows


def test_garbage_queue_cancels_pending_incoming_before_sending(fake_clock: AdvancingClock) -> None:
    source = PlayerId("p1")
    target = PlayerId("p2")
    generator = GarbageGenerator(board_width=10)
    queue = GarbageQueue(fake_clock)
    queue.enqueue(generator.generate(source=target, target=source, lines=3, seq=1, seed=11))

    outgoing = queue.cancel_with_attack(AttackEvent(source=source, seq=2, target=target, lines=5))

    assert queue.pending_lines == 0
    assert outgoing == AttackEvent(source=source, seq=2, target=target, lines=2)


def test_garbage_queue_applies_ready_events_after_lock_in_fifo_order(
    fake_clock: AdvancingClock,
) -> None:
    source = PlayerId("p1")
    target = PlayerId("p2")
    generator = GarbageGenerator(board_width=10)
    queue = GarbageQueue(fake_clock, apply_delay_seconds=1.0)
    first = generator.generate(source=source, target=target, lines=2, seq=1, seed=21)
    second = generator.generate(source=source, target=target, lines=1, seq=2, seed=22)
    queue.enqueue(first)
    fake_clock.advance(0.5)
    queue.enqueue(second)

    fake_clock.advance(0.49)
    assert queue.pop_ready_after_lock() == ()
    fake_clock.advance(0.01)
    assert queue.pop_ready_after_lock() == (first,)
    fake_clock.advance(0.5)
    assert queue.pop_ready_after_lock() == (second,)
