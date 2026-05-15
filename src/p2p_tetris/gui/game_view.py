"""QGraphicsView-based Tetris board and preview renderer."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from p2p_tetris.client import BoardViewModel, GameViewModel, PiecePreviewViewModel


@dataclass(frozen=True, slots=True)
class RenderConfig:
    cell_size: int = 24
    preview_cell_size: int = 14
    board_background: str = "#101418"
    grid_color: str = "#2b333b"
    ghost_color: str = "#8a949e"
    top_out_overlay: str = "#d84a4a"


PIECE_COLORS: dict[str, str] = {
    "I": "#35c9d8",
    "O": "#f1cf46",
    "T": "#a971d1",
    "S": "#67b85a",
    "Z": "#d95757",
    "J": "#4f78d4",
    "L": "#e69a43",
}

PREVIEW_CELLS: dict[str, tuple[tuple[int, int], ...]] = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}


class GameViewRenderer(QWidget):
    """Render board, active piece, ghost piece, hold, and next queue."""

    def __init__(self, *, config: RenderConfig | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config or RenderConfig()
        self._board_scene = QGraphicsScene(self)
        self._hold_scene = QGraphicsScene(self)
        self._next_scene = QGraphicsScene(self)

        self.board_view = QGraphicsView(self._board_scene)
        self.hold_view = QGraphicsView(self._hold_scene)
        self.next_view = QGraphicsView(self._next_scene)

        for view in (self.board_view, self.hold_view, self.next_view):
            view.setRenderHints(view.renderHints())
            view.setFrameShape(QGraphicsView.Shape.NoFrame)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.board_view.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.hold_view.setFixedSize(96, 78)
        self.next_view.setFixedSize(112, 220)

        side_panel = QVBoxLayout()
        side_panel.addWidget(QLabel("Hold"))
        side_panel.addWidget(self.hold_view)
        side_panel.addSpacing(12)
        side_panel.addWidget(QLabel("Next"))
        side_panel.addWidget(self.next_view)
        side_panel.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self.board_view)
        layout.addLayout(side_panel)

    def update_view_model(self, view_model: GameViewModel) -> None:
        self.render_board(view_model.board)
        self.render_preview(view_model.preview)

    def render_board(self, board: BoardViewModel) -> None:
        scene = self._board_scene
        scene.clear()
        cell = self.config.cell_size
        width = board.width * cell
        height = board.height * cell
        scene.setSceneRect(0, 0, width, height)
        self.board_view.setFixedSize(width + 2, height + 2)

        background = QColor(self.config.board_background)
        grid_pen = QPen(QColor(self.config.grid_color))
        grid_pen.setWidth(1)

        for y, row in enumerate(board.cells):
            for x, piece in enumerate(row):
                rect = scene.addRect(x * cell, y * cell, cell, cell, grid_pen, background)
                rect.setZValue(0)
                if piece is not None:
                    self._fill_cell(scene, x, y, piece, cell, z=2)

        ghost_pen = QPen(QColor(self.config.ghost_color))
        ghost_pen.setWidth(2)
        for x, y in board.ghost_cells:
            if 0 <= x < board.width and 0 <= y < board.height:
                item = scene.addRect(x * cell + 3, y * cell + 3, cell - 6, cell - 6, ghost_pen)
                item.setZValue(1)

        if board.active_piece is not None:
            for x, y in board.active_cells:
                if 0 <= x < board.width and 0 <= y < board.height:
                    self._fill_cell(scene, x, y, board.active_piece, cell, z=3)

        if board.pending_garbage_lines > 0:
            garbage_height = min(board.pending_garbage_lines, board.height) * cell
            item = scene.addRect(
                width + 3,
                height - garbage_height,
                6,
                garbage_height,
                QPen(Qt.PenStyle.NoPen),
                QColor("#d87d4a"),
            )
            item.setZValue(4)
            scene.setSceneRect(0, 0, width + 12, height)

        if board.top_out:
            overlay = QColor(self.config.top_out_overlay)
            overlay.setAlpha(92)
            scene.addRect(0, 0, width, height, QPen(Qt.PenStyle.NoPen), overlay).setZValue(5)

    def render_preview(self, preview: PiecePreviewViewModel) -> None:
        self._draw_piece_preview(self._hold_scene, preview.hold_piece, width=96, height=72)
        self._next_scene.clear()
        self._next_scene.setSceneRect(0, 0, 108, 216)
        for index, piece in enumerate(preview.next_queue[:5]):
            self._draw_piece(self._next_scene, piece, offset_x=18, offset_y=8 + index * 40)

    def _fill_cell(
        self,
        scene: QGraphicsScene,
        x: int,
        y: int,
        piece: object,
        cell_size: int,
        *,
        z: int,
    ) -> QGraphicsRectItem:
        color = QColor(PIECE_COLORS[_piece_name(piece)])
        pen = QPen(QColor("#0c1115"))
        pen.setWidth(1)
        item = scene.addRect(x * cell_size + 1, y * cell_size + 1, cell_size - 2, cell_size - 2, pen, color)
        item.setZValue(z)
        return item

    def _draw_piece_preview(
        self,
        scene: QGraphicsScene,
        piece: object | None,
        *,
        width: int,
        height: int,
    ) -> None:
        scene.clear()
        scene.setSceneRect(0, 0, width, height)
        if piece is None:
            return
        self._draw_piece(scene, piece, offset_x=18, offset_y=12)

    def _draw_piece(
        self,
        scene: QGraphicsScene,
        piece: object,
        *,
        offset_x: int,
        offset_y: int,
    ) -> None:
        cell = self.config.preview_cell_size
        piece_name = _piece_name(piece)
        color = QColor(PIECE_COLORS[piece_name])
        pen = QPen(QColor("#0c1115"))
        for x, y in PREVIEW_CELLS[piece_name]:
            scene.addRect(offset_x + x * cell, offset_y + y * cell, cell - 1, cell - 1, pen, color)


def _piece_name(piece: object) -> str:
    value = getattr(piece, "value", piece)
    if not isinstance(value, str) or value not in PIECE_COLORS:
        msg = f"unknown piece for rendering: {piece!r}"
        raise ValueError(msg)
    return value
