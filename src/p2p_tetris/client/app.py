"""GUI client entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from p2p_tetris.gui import MainWindow

APP_NAME = "P2P Tetris"
ORGANIZATION_NAME = "ryansuc"
ORGANIZATION_DOMAIN = "ryansuc.com"
BUNDLE_IDENTIFIER = "com.ryansuc.p2p-tetris"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7777
DEFAULT_PLAYER_NAME = "Player"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the P2P Tetris desktop client.")
    parser.add_argument("--host", default=None, help="Default server host shown on connect screen.")
    parser.add_argument("--port", default=None, type=int, help="Default server UDP port shown on connect screen.")
    parser.add_argument("--player-name", default=None, help="Default player name shown on connect screen.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_application_metadata()
    configure_logging()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    settings = QSettings()
    window = MainWindow(settings=settings)
    host = args.host if args.host is not None else _settings_text(settings, "connection/host", DEFAULT_HOST)
    port = args.port if args.port is not None else _settings_port(settings, "connection/port", DEFAULT_PORT)
    window.connect_screen.host_input.setText(host)
    window.connect_screen.port_input.setValue(port)
    window.connect_screen.name_input.setText(
        args.player_name or _settings_text(settings, "connection/player_name", DEFAULT_PLAYER_NAME)
    )
    window.show()
    logging.info("P2P Tetris client started")
    return int(app.exec())


def configure_application_metadata() -> None:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(_project_version())
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)


def configure_logging() -> None:
    if sys.platform == "darwin":
        log_dir = Path.home() / "Library" / "Logs" / APP_NAME
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_dir / "client.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _project_version() -> str:
    try:
        return version("p2p-tetris")
    except PackageNotFoundError:
        return "0.1.0"


def _settings_text(settings: QSettings, key: str, default: str) -> str:
    value = settings.value(key, default)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _settings_port(settings: QSettings, key: str, default: int) -> int:
    value = settings.value(key, default)
    try:
        port = int(str(value))
    except (TypeError, ValueError):
        return default
    if 1 <= port <= 65535:
        return port
    return default


if __name__ == "__main__":
    raise SystemExit(main())
