"""Injectable monotonic clock interfaces."""

from __future__ import annotations

import time as _time
from typing import Protocol


class MonotonicClock(Protocol):
    """Clock interface for code that must be testable without real sleeps."""

    def now(self) -> float:
        """Return monotonic time in seconds."""


class SystemClock:
    """Monotonic clock backed by the Python standard library."""

    def now(self) -> float:
        return _time.monotonic()

