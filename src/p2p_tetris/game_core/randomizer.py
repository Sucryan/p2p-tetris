"""Deterministic 7-bag randomizer."""

from __future__ import annotations

import random
from collections.abc import Iterator

from p2p_tetris.game_core.pieces import PieceType


class SevenBagRandomizer:
    """Generate tetrominoes by shuffling complete seven-piece bags."""

    def __init__(self, seed: int | str | bytes | bytearray | None = None) -> None:
        self._random = random.Random(seed)
        self._queue: list[PieceType] = []

    def __iter__(self) -> Iterator[PieceType]:
        return self

    def __next__(self) -> PieceType:
        return self.next_piece()

    def next_piece(self) -> PieceType:
        if not self._queue:
            self._queue = list(PieceType)
            self._random.shuffle(self._queue)
        return self._queue.pop(0)

    def take(self, count: int) -> tuple[PieceType, ...]:
        if count < 0:
            msg = "count must be non-negative"
            raise ValueError(msg)
        return tuple(self.next_piece() for _ in range(count))
