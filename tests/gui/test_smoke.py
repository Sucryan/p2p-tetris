"""GUI smoke tests for widget creation, navigation, and callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from p2p_tetris.client import (
    BoardViewModel,
    ConnectionState,
    ConnectionViewModel,
    GameViewModel,
    MatchResultViewModel,
    OpponentViewModel,
    PiecePreviewViewModel,
    ServerAddress,
    SoloHudViewModel,
    VersusHudViewModel,
)
from p2p_tetris.common import MatchId, PlayerId
from p2p_tetris.controllers import KeyboardController
from p2p_tetris.game_core import PieceType, PlayerAction
from p2p_tetris.net import ClientHello, ProtocolMessage
from p2p_tetris.gui import (
    ConnectScreen,
    GameViewRenderer,
    MainMenuScreen,
    MainWindow,
    MatchResultScreen,
    RuntimeEventBridge,
    SoloGameScreen,
    VersusGameScreen,
    WaitingScreen,
)


def test_main_window_switches_between_menu_connect_waiting_and_solo(qt_app: QApplication) -> None:
    fake_clients: list[FakeGuiNetClient] = []

    def factory(_address: ServerAddress) -> FakeGuiNetClient:
        client = FakeGuiNetClient()
        fake_clients.append(client)
        return client

    window = MainWindow(net_client_factory=factory)
    qt_app.processEvents()

    assert window.stack.currentWidget() is window.main_menu
    assert window.main_menu.computer_button.isEnabled() is False

    window.show_connect()
    assert window.stack.currentWidget() is window.connect_screen

    window.connect_to_server("127.0.0.1", 7777, "Alice")
    assert window.stack.currentWidget() is window.waiting_screen
    assert "Alice" in window.waiting_screen.status_label.text()
    assert isinstance(fake_clients[0].sent[0], ClientHello)

    window.start_single_player()
    assert window.stack.currentWidget() is window.solo_screen
    assert window.local_session.is_running is True

    window.show_main_menu()
    assert window.stack.currentWidget() is window.main_menu
    window.close()


def test_main_window_saves_connection_settings(qt_app: QApplication, tmp_path: Path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)

    window = MainWindow(net_client_factory=lambda _address: FakeGuiNetClient(), settings=settings)
    window.connect_to_server("192.168.1.23", 7777, "Ada")

    assert settings.value("connection/host") == "192.168.1.23"
    assert int(settings.value("connection/port")) == 7777
    assert settings.value("connection/player_name") == "Ada"
    window.close()
    qt_app.processEvents()


def test_screens_and_renderer_accept_view_models(qt_app: QApplication) -> None:
    calls: list[Any] = []
    main = MainMenuScreen(
        on_single_player=lambda: calls.append("single"),
        on_connect=lambda: calls.append("connect"),
        on_exit=lambda: calls.append("exit"),
    )
    connect = ConnectScreen(
        on_connect=lambda host, port, name: calls.append((host, port, name)),
        on_back=lambda: calls.append("back"),
    )
    waiting = WaitingScreen(on_cancel=lambda: calls.append("cancel"))
    solo = SoloGameScreen(
        on_pause=lambda: calls.append("pause"),
        on_restart=lambda: calls.append("restart"),
        on_menu=lambda: calls.append("menu"),
    )
    versus = VersusGameScreen(on_menu=lambda: calls.append("versus-menu"))
    result = MatchResultScreen(
        on_next_match=lambda: calls.append("next"),
        on_menu=lambda: calls.append("result-menu"),
    )
    renderer = GameViewRenderer()

    view_model = _game_view_model()
    renderer.update_view_model(view_model)
    solo.update_view_model(view_model)
    versus.update_view_model(_versus_view_model())
    result.update_result(_match_result())
    connect.update_connection(ConnectionViewModel(ConnectionState.CONNECTING, "Connecting"))
    waiting.update_connection(ConnectionViewModel(ConnectionState.QUEUED, "Waiting"))

    main.single_player_button.click()
    connect.connect_button.click()
    assert calls[0] == "single"
    assert calls[1] == ("127.0.0.1", 7777, "Player")
    qt_app.processEvents()


def test_keyboard_events_update_controller_only(qt_app: QApplication) -> None:
    keyboard = KeyboardController()
    window = MainWindow(keyboard=keyboard)

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        int(Qt.Key.Key_Left),
        Qt.KeyboardModifier.NoModifier,
    )
    window.keyPressEvent(event)

    assert keyboard.pull_actions(0).actions == (PlayerAction.MOVE_LEFT,)
    assert event.isAccepted() is True
    window.close()
    qt_app.processEvents()


def test_runtime_event_bridge_emits_polled_events(qt_app: QApplication) -> None:
    emitted: list[tuple[object, ...]] = []
    bridge = RuntimeEventBridge(lambda: ("event",))
    bridge.events_ready.connect(lambda events: emitted.append(events))

    bridge._poll_once()

    assert emitted == [("event",)]
    assert bridge.is_active is False
    qt_app.processEvents()


def _game_view_model() -> GameViewModel:
    cells = tuple(tuple(None for _ in range(10)) for _ in range(20))
    board = BoardViewModel(
        width=10,
        height=20,
        cells=cells,
        active_piece=PieceType.T,
        active_cells=((4, 0), (3, 1), (4, 1), (5, 1)),
        ghost_cells=((4, 17), (3, 18), (4, 18), (5, 18)),
        top_out=False,
        pending_garbage_lines=2,
    )
    preview = PiecePreviewViewModel(
        hold_piece=PieceType.I,
        next_queue=(PieceType.O, PieceType.L, PieceType.J),
    )
    return GameViewModel(
        board=board,
        preview=preview,
        solo_hud=SoloHudViewModel(
            score=1200,
            cleared_lines=8,
            combo=1,
            back_to_back=False,
            tick=30,
            is_running=True,
            is_paused=False,
        ),
        connection=ConnectionViewModel(ConnectionState.DISCONNECTED),
    )


def _versus_view_model() -> GameViewModel:
    local = PlayerId("local")
    opponent = PlayerId("opponent")
    view_model = _game_view_model()
    return GameViewModel(
        board=view_model.board,
        preview=view_model.preview,
        solo_hud=view_model.solo_hud,
        connection=ConnectionViewModel(ConnectionState.IN_MATCH),
        versus_hud=VersusHudViewModel(
            match_id=MatchId("match"),
            local_player_id=local,
            opponent_player_id=opponent,
            remaining_seconds=91.5,
            ko_counts={local.value: 1, opponent.value: 0},
            sent_lines={local.value: 4, opponent.value: 2},
            pending_garbage_lines=3,
            is_alive=True,
        ),
        opponents=(
            OpponentViewModel(
                player_id=opponent,
                summary_seq=3,
                board_height=6,
                pending_garbage=1,
                ko_count=0,
                sent_lines=2,
                is_alive=True,
                extra={},
            ),
        ),
    )


def _match_result() -> MatchResultViewModel:
    return MatchResultViewModel(
        match_id=MatchId("match"),
        winner_id=PlayerId("local"),
        is_draw=False,
        reason="timeout",
        ko_counts={"local": 1, "opponent": 0},
        sent_lines={"local": 4, "opponent": 2},
    )


class FakeGuiNetClient:
    def __init__(self) -> None:
        self.sent: list[ProtocolMessage] = []
        self.inbound: list[ProtocolMessage] = []
        self.closed = False

    def send(self, message: ProtocolMessage) -> None:
        self.sent.append(message)

    def receive(self) -> tuple[ProtocolMessage, ...]:
        messages = tuple(self.inbound)
        self.inbound.clear()
        return messages

    def close(self) -> None:
        self.closed = True
