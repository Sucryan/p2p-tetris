"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if SRC.is_dir():
    src_path = str(SRC)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


class _FakeClock(Protocol):
    def now(self) -> float: ...

    def advance(self, seconds: float) -> None: ...


class FakeClock:
    """Manually advanced monotonic clock for tests."""

    def __init__(self, start: float = 0.0) -> None:
        if start < 0:
            msg = "start must be non-negative"
            raise ValueError(msg)
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            msg = "seconds must be non-negative"
            raise ValueError(msg)
        self._now += seconds


@pytest.fixture
def fake_clock() -> _FakeClock:
    return FakeClock()

