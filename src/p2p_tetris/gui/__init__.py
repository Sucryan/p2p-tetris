"""PySide6 desktop GUI for P2P Tetris."""

from p2p_tetris.gui.game_view import GameViewRenderer
from p2p_tetris.gui.main_window import MainWindow, RuntimeEventBridge
from p2p_tetris.gui.screens import (
    ConnectScreen,
    MainMenuScreen,
    MatchResultScreen,
    SoloGameScreen,
    VersusGameScreen,
    WaitingScreen,
)

__all__ = [
    "ConnectScreen",
    "GameViewRenderer",
    "MainMenuScreen",
    "MainWindow",
    "MatchResultScreen",
    "RuntimeEventBridge",
    "SoloGameScreen",
    "VersusGameScreen",
    "WaitingScreen",
]
