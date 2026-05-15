from __future__ import annotations

from typing import Protocol

import pytest

from p2p_tetris.common import MonotonicClock, SystemClock


class AdvancingClock(MonotonicClock, Protocol):
    def advance(self, seconds: float) -> None: ...


def elapsed(clock: MonotonicClock, started_at: float) -> float:
    return clock.now() - started_at


def test_system_clock_implements_monotonic_clock() -> None:
    clock: MonotonicClock = SystemClock()

    assert clock.now() <= clock.now()


def test_fake_clock_fixture_can_advance_manually(fake_clock: AdvancingClock) -> None:
    started_at = fake_clock.now()

    fake_clock.advance(0.1)
    fake_clock.advance(1.4)

    assert elapsed(fake_clock, started_at) == pytest.approx(1.5)


def test_fake_clock_rejects_negative_advance(fake_clock: AdvancingClock) -> None:
    with pytest.raises(ValueError):
        fake_clock.advance(-0.1)
