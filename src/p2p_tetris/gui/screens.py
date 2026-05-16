"""Top-level GUI screens."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from p2p_tetris.client import (
    ConnectionState,
    ConnectionViewModel,
    GameViewModel,
    MatchResultViewModel,
    OpponentViewModel,
)
from p2p_tetris.gui.game_view import GameViewRenderer


class MainMenuScreen(QWidget):
    def __init__(
        self,
        *,
        on_single_player: Callable[[], None],
        on_connect: Callable[[], None],
        on_exit: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.single_player_button = QPushButton("Single Player")
        self.connect_button = QPushButton("Connect")
        self.computer_button = QPushButton("Play with Computer")
        self.exit_button = QPushButton("Exit")
        self.computer_button.setEnabled(False)

        self.single_player_button.clicked.connect(on_single_player)
        self.connect_button.clicked.connect(on_connect)
        self.exit_button.clicked.connect(on_exit)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("P2P Tetris")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        for button in (
            self.single_player_button,
            self.connect_button,
            self.computer_button,
            self.exit_button,
        ):
            button.setMinimumWidth(220)
            layout.addWidget(button)


class ConnectScreen(QWidget):
    def __init__(
        self,
        *,
        on_connect: Callable[[str, int, str], None],
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(7777)
        self.name_input = QLineEdit("Player")
        self.status_label = QLabel("")

        self.connect_button = QPushButton("Connect")
        self.back_button = QPushButton("Back")
        self.connect_button.clicked.connect(self._connect_clicked)
        self.back_button.clicked.connect(on_back)
        self._on_connect = on_connect

        form = QFormLayout()
        form.addRow("Host", self.host_input)
        form.addRow("Port", self.port_input)
        form.addRow("Player name", self.name_input)

        buttons = QHBoxLayout()
        buttons.addWidget(self.back_button)
        buttons.addStretch(1)
        buttons.addWidget(self.connect_button)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def update_connection(self, view_model: ConnectionViewModel) -> None:
        self.status_label.setText(_connection_text(view_model))

    def _connect_clicked(self) -> None:
        name = self.name_input.text().strip() or "Player"
        self._on_connect(self.host_input.text().strip(), int(self.port_input.value()), name)


class WaitingScreen(QWidget):
    def __init__(self, *, on_cancel: Callable[[], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cancel_button = QPushButton("Back")
        self.cancel_button.clicked.connect(on_cancel)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addWidget(self.cancel_button)

    def update_connection(self, view_model: ConnectionViewModel) -> None:
        self.status_label.setText(_connection_text(view_model))


class SoloGameScreen(QWidget):
    def __init__(
        self,
        *,
        on_pause: Callable[[], None],
        on_restart: Callable[[], None],
        on_menu: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.renderer = GameViewRenderer()
        self.score_label = QLabel("Score 0")
        self.lines_label = QLabel("Lines 0")
        self.state_label = QLabel("")
        self.pause_button = QPushButton("Pause")
        self.restart_button = QPushButton("Restart")
        self.menu_button = QPushButton("Menu")

        self.pause_button.clicked.connect(on_pause)
        self.restart_button.clicked.connect(on_restart)
        self.menu_button.clicked.connect(on_menu)

        hud = QVBoxLayout()
        hud.addWidget(self.score_label)
        hud.addWidget(self.lines_label)
        hud.addWidget(self.state_label)
        hud.addSpacing(12)
        hud.addWidget(self.pause_button)
        hud.addWidget(self.restart_button)
        hud.addWidget(self.menu_button)
        hud.addStretch(1)

        layout = QHBoxLayout(self)
        layout.addWidget(self.renderer)
        layout.addLayout(hud)

    def update_view_model(self, view_model: GameViewModel) -> None:
        self.renderer.update_view_model(view_model)
        hud = view_model.solo_hud
        self.score_label.setText(f"Score {hud.score}")
        self.lines_label.setText(f"Lines {hud.cleared_lines}")
        if hud.is_paused:
            state = "Paused"
        elif hud.is_running:
            state = f"Tick {hud.tick}"
        else:
            state = "Stopped"
        self.state_label.setText(state)


class VersusGameScreen(QWidget):
    def __init__(self, *, on_menu: Callable[[], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.renderer = GameViewRenderer()
        self.timer_label = QLabel("Time 0.0")
        self.ko_label = QLabel("KO 0")
        self.sent_label = QLabel("Sent 0")
        self.incoming_label = QLabel("Incoming 0")
        self.opponent_box = QGroupBox("Opponent")
        self.opponent_layout = QGridLayout(self.opponent_box)
        self.menu_button = QPushButton("Menu")
        self.menu_button.clicked.connect(on_menu)

        hud = QVBoxLayout()
        for label in (
            self.timer_label,
            self.ko_label,
            self.sent_label,
            self.incoming_label,
        ):
            hud.addWidget(label)
        hud.addWidget(self.opponent_box)
        hud.addStretch(1)
        hud.addWidget(self.menu_button)

        layout = QHBoxLayout(self)
        layout.addWidget(self.renderer)
        layout.addLayout(hud)

    def update_view_model(self, view_model: GameViewModel) -> None:
        self.renderer.update_view_model(view_model)
        hud = view_model.versus_hud
        if hud is not None:
            local_id = hud.local_player_id.value
            self.timer_label.setText(f"Time {hud.remaining_seconds:.1f}")
            self.ko_label.setText(f"KO {hud.ko_counts.get(local_id, 0)}")
            self.sent_label.setText(f"Sent {hud.sent_lines.get(local_id, 0)}")
            self.incoming_label.setText(f"Incoming {hud.pending_garbage_lines}")
        self._render_opponents(view_model.opponents)

    def _render_opponents(self, opponents: tuple[OpponentViewModel, ...]) -> None:
        while self.opponent_layout.count():
            item = self.opponent_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not opponents:
            self.opponent_layout.addWidget(QLabel("Waiting"), 0, 0)
            return
        for row, opponent in enumerate(opponents):
            text = (
                f"{opponent.player_id.value}  "
                f"height {opponent.board_height}  "
                f"garbage {opponent.pending_garbage}  "
                f"KO {opponent.ko_count}  "
                f"sent {opponent.sent_lines}"
            )
            self.opponent_layout.addWidget(QLabel(text), row, 0)


class MatchResultScreen(QWidget):
    def __init__(
        self,
        *,
        on_next_match: Callable[[], None],
        on_menu: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title_label = QLabel("")
        self.stats_label = QLabel("")
        self.next_status_label = QLabel("Match ended")
        self.next_button = QPushButton("Back to Queue")
        self.menu_button = QPushButton("Menu")
        self.next_button.clicked.connect(on_next_match)
        self.menu_button.clicked.connect(on_menu)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for label in (self.title_label, self.stats_label, self.next_status_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        layout.addWidget(self.next_button)
        layout.addWidget(self.menu_button)

    def update_result(self, result: MatchResultViewModel) -> None:
        if result.is_draw:
            self.title_label.setText("Draw")
        elif result.winner_id is not None:
            self.title_label.setText(f"Winner {result.winner_id.value}")
        else:
            self.title_label.setText("No winner")
        ko_text = ", ".join(f"{player}: {count}" for player, count in result.ko_counts.items())
        sent_text = ", ".join(f"{player}: {count}" for player, count in result.sent_lines.items())
        self.stats_label.setText(f"Reason {result.reason}\nKO {ko_text}\nSent {sent_text}")


def _connection_text(view_model: ConnectionViewModel) -> str:
    if view_model.message:
        return view_model.message
    if view_model.state is ConnectionState.CONNECTING:
        return "Connecting"
    if view_model.state is ConnectionState.QUEUED:
        return "Waiting"
    if view_model.state is ConnectionState.IN_MATCH:
        return "Active"
    if view_model.state is ConnectionState.ENDED:
        return "Ended"
    return "Disconnected"
