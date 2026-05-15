"""Board storage, collision, placement, line clear, and garbage helpers."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import GameConfig
from p2p_tetris.game_core.pieces import Cell, PieceType


CellValue = PieceType | None


@dataclass(frozen=True, slots=True)
class GarbageInjection:
    """Core-local payload for adding garbage rows.

    ``hole`` is the empty column shared by every injected row in this payload.
    """

    lines: int
    hole: int


class Board:
    """Internal board with hidden rows at the top and visible rows at the bottom.

    Coordinates are ``(x, y)`` with ``(0, 0)`` at the top-left hidden cell.
    Visible rows start at ``hidden_rows`` and end at ``total_rows - 1``.
    """

    def __init__(self, config: GameConfig | None = None) -> None:
        self.config = config or GameConfig()
        self.width = self.config.board_width
        self.visible_rows = self.config.visible_rows
        self.hidden_rows = self.config.hidden_rows
        self.total_rows = self.config.total_rows
        self._rows: list[list[CellValue]] = [
            [None for _ in range(self.width)] for _ in range(self.total_rows)
        ]

    @property
    def visible_start_y(self) -> int:
        return self.hidden_rows

    def clone(self) -> Board:
        copied = Board(self.config)
        copied._rows = [row.copy() for row in self._rows]
        return copied

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.total_rows

    def is_visible_y(self, y: int) -> bool:
        return self.hidden_rows <= y < self.total_rows

    def get(self, x: int, y: int) -> CellValue:
        if not self.in_bounds(x, y):
            msg = f"cell out of bounds: {(x, y)}"
            raise IndexError(msg)
        return self._rows[y][x]

    def set_cell(self, x: int, y: int, value: CellValue) -> None:
        if not self.in_bounds(x, y):
            msg = f"cell out of bounds: {(x, y)}"
            raise IndexError(msg)
        self._rows[y][x] = value

    def can_place(self, cells: tuple[Cell, ...]) -> bool:
        return all(self.in_bounds(x, y) and self._rows[y][x] is None for x, y in cells)

    def place(self, cells: tuple[Cell, ...], value: PieceType) -> None:
        if not self.can_place(cells):
            msg = "piece cells collide or are out of bounds"
            raise ValueError(msg)
        for x, y in cells:
            self._rows[y][x] = value

    def clear_full_lines(self) -> int:
        kept_rows = [row for row in self._rows if not all(cell is not None for cell in row)]
        cleared = self.total_rows - len(kept_rows)
        if cleared:
            empty_rows: list[list[CellValue]] = [
                [None for _ in range(self.width)] for _ in range(cleared)
            ]
            self._rows = empty_rows + kept_rows
        return cleared

    def apply_garbage(self, injection: GarbageInjection) -> None:
        if injection.lines < 0:
            msg = "garbage lines must be non-negative"
            raise ValueError(msg)
        if not 0 <= injection.hole < self.width:
            msg = "garbage hole must be within board width"
            raise ValueError(msg)
        if injection.lines == 0:
            return

        garbage_rows: list[list[CellValue]] = []
        for _ in range(injection.lines):
            row: list[CellValue] = [PieceType.Z for _ in range(self.width)]
            row[injection.hole] = None
            garbage_rows.append(row)
        self._rows = self._rows[injection.lines :] + garbage_rows

    def any_hidden_blocks(self) -> bool:
        return any(
            cell is not None
            for row in self._rows[: self.hidden_rows]
            for cell in row
        )

    def snapshot_all(self) -> tuple[tuple[CellValue, ...], ...]:
        return tuple(tuple(row) for row in self._rows)

    def snapshot_visible(self) -> tuple[tuple[CellValue, ...], ...]:
        return tuple(tuple(row) for row in self._rows[self.hidden_rows :])

    def hidden_occupied_count(self) -> int:
        return sum(
            1
            for row in self._rows[: self.hidden_rows]
            for cell in row
            if cell is not None
        )
