"""GUI client entrypoint."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from p2p_tetris.gui import MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the P2P Tetris desktop client.")
    parser.add_argument("--host", default="127.0.0.1", help="Default server host shown on connect screen.")
    parser.add_argument("--port", default=7777, type=int, help="Default server UDP port shown on connect screen.")
    parser.add_argument("--player-name", default="Player", help="Default player name shown on connect screen.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow()
    window.connect_screen.host_input.setText(args.host)
    window.connect_screen.port_input.setValue(args.port)
    window.connect_screen.name_input.setText(args.player_name)
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
