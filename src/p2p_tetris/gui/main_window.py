"""Main PySide6 window and runtime event bridge."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from p2p_tetris.client import (
    ClientNetworkRuntime,
    ConnectionState,
    ConnectionViewModel,
    ConnectedNetClient,
    GameViewModel,
    LocalGameSession,
    MatchResultViewModel,
    ServerAddress,
)
from p2p_tetris.controllers import KeyboardController
from p2p_tetris.gui.screens import (
    ConnectScreen,
    MainMenuScreen,
    MatchResultScreen,
    SoloGameScreen,
    VersusGameScreen,
    WaitingScreen,
)


class RuntimeEventBridge(QObject):
    """Poll a runtime source on the Qt event loop and emit queued events."""

    events_ready = Signal(tuple)

    def __init__(
        self,
        poll: Callable[[], tuple[Any, ...]],
        *,
        interval_ms: int = 16,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._poll = poll
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll_once)

    @property
    def is_active(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll_once(self) -> None:
        events = self._poll()
        if events:
            self.events_ready.emit(events)


class MainWindow(QMainWindow):
    """Own screen navigation and GUI-to-controller wiring."""

    def __init__(
        self,
        *,
        keyboard: KeyboardController | None = None,
        local_session: LocalGameSession | None = None,
        net_client_factory: Callable[[ServerAddress], ConnectedNetClient] | None = None,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("P2P Tetris")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.keyboard = keyboard or KeyboardController()
        self.local_session = local_session or LocalGameSession(self.keyboard)
        self.network_runtime = ClientNetworkRuntime(
            self.keyboard,
            net_client_factory=net_client_factory,
        )
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(16)
        self._runtime_timer.timeout.connect(self._tick_runtime)
        self._network_timer = QTimer(self)
        self._network_timer.setInterval(50)
        self._network_timer.timeout.connect(self._poll_network)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_menu = MainMenuScreen(
            on_single_player=self.start_single_player,
            on_connect=self.show_connect,
            on_exit=self.exit_client,
        )
        self.connect_screen = ConnectScreen(
            on_connect=self.connect_to_server,
            on_back=self.show_main_menu,
        )
        self.waiting_screen = WaitingScreen(on_cancel=self.show_main_menu)
        self.solo_screen = SoloGameScreen(
            on_pause=self.toggle_pause,
            on_restart=self.restart_single_player,
            on_menu=self.show_main_menu,
        )
        self.versus_screen = VersusGameScreen(on_menu=self.show_main_menu)
        self.result_screen = MatchResultScreen(
            on_next_match=lambda: self.show_waiting(),
            on_menu=self.show_main_menu,
        )

        for screen in (
            self.main_menu,
            self.connect_screen,
            self.waiting_screen,
            self.solo_screen,
            self.versus_screen,
            self.result_screen,
        ):
            self.stack.addWidget(screen)

        self.resize(780, 620)
        self.show_main_menu()

    def show_main_menu(self) -> None:
        self._runtime_timer.stop()
        self._network_timer.stop()
        self._disconnect_network()
        self.stack.setCurrentWidget(self.main_menu)
        self.setFocus()

    def exit_client(self) -> None:
        self.close()

    def show_connect(self) -> None:
        self.connect_screen.update_connection(ConnectionViewModel(ConnectionState.DISCONNECTED))
        self.stack.setCurrentWidget(self.connect_screen)

    def show_waiting(self, view_model: ConnectionViewModel | None = None) -> None:
        connection = view_model or ConnectionViewModel(ConnectionState.QUEUED, "Waiting for match")
        self.waiting_screen.update_connection(connection)
        self.stack.setCurrentWidget(self.waiting_screen)

    def start_single_player(self) -> None:
        self._network_timer.stop()
        self._disconnect_network()
        self.local_session.restart()
        self.solo_screen.update_view_model(self.local_session.view_model)
        self.stack.setCurrentWidget(self.solo_screen)
        self._runtime_timer.start()
        self.setFocus()

    def restart_single_player(self) -> None:
        self.local_session.restart()
        self.solo_screen.update_view_model(self.local_session.view_model)
        self.setFocus()

    def toggle_pause(self) -> None:
        if self.local_session.is_paused:
            self.local_session.resume()
            self._runtime_timer.start()
        else:
            self.local_session.pause()
            self._runtime_timer.stop()
        self.solo_screen.update_view_model(self.local_session.view_model)
        self.setFocus()

    def connect_to_server(self, host: str, port: int, player_name: str) -> None:
        self._runtime_timer.stop()
        connection = self.network_runtime.connect(host, port, player_name)
        self._network_timer.start()
        self.connect_screen.update_connection(connection)
        self.show_waiting(connection)

    def show_versus_game(self, view_model: GameViewModel) -> None:
        self.versus_screen.update_view_model(view_model)
        self.stack.setCurrentWidget(self.versus_screen)
        self.setFocus()

    def show_match_result(self, result: MatchResultViewModel) -> None:
        self.result_screen.update_result(result)
        self.stack.setCurrentWidget(self.result_screen)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        token = _qt_key_token(event)
        if token is None or event.isAutoRepeat():
            super().keyPressEvent(event)
            return
        self.keyboard.press(token, tick=self._current_tick())
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        token = _qt_key_token(event)
        if token is None or event.isAutoRepeat():
            super().keyReleaseEvent(event)
            return
        self.keyboard.release(token, tick=self._current_tick())
        event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._runtime_timer.stop()
        self._network_timer.stop()
        self._disconnect_network()
        super().closeEvent(event)

    def _tick_runtime(self) -> None:
        if self.stack.currentWidget() is self.solo_screen:
            self.local_session.tick()
            self.solo_screen.update_view_model(self.local_session.view_model)
            return
        if self.stack.currentWidget() is self.versus_screen:
            view_model = self.network_runtime.tick()
            if view_model is None:
                return
            if view_model.result is not None:
                self.show_match_result(view_model.result)
                self._runtime_timer.stop()
            else:
                self.versus_screen.update_view_model(view_model)

    def _poll_network(self) -> None:
        update = self.network_runtime.poll()
        if update is None:
            return
        if update.view_model is not None:
            if update.view_model.result is not None:
                self.show_match_result(update.view_model.result)
                self._runtime_timer.stop()
                return
            self.show_versus_game(update.view_model)
            self._runtime_timer.start()
            return
        if update.connection.state is ConnectionState.QUEUED:
            self.show_waiting(update.connection)
        elif update.connection.state is ConnectionState.ENDED:
            self.show_waiting(update.connection)

    @property
    def versus_session(self) -> object | None:
        return self.network_runtime.versus_session

    def _disconnect_network(self) -> None:
        self.network_runtime.close()

    def _current_tick(self) -> int:
        versus = self.network_runtime.versus_session
        if versus is not None:
            return versus.tick_count
        return self.local_session.tick_count


def _qt_key_token(event: QKeyEvent) -> str | None:
    key = event.key()
    mapping = {
        int(Qt.Key.Key_Left): "ArrowLeft",
        int(Qt.Key.Key_Right): "ArrowRight",
        int(Qt.Key.Key_Down): "ArrowDown",
        int(Qt.Key.Key_Space): "Space",
        int(Qt.Key.Key_Up): "ArrowUp",
        int(Qt.Key.Key_Z): "KeyZ",
        int(Qt.Key.Key_C): "KeyC",
    }
    return mapping.get(int(key))
