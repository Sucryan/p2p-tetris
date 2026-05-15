"""Thin automation wrapper for Linux pyside6-deploy builds."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ENTRYPOINT = ROOT / "src" / "p2p_tetris" / "client" / "app.py"
CONFIG = Path(__file__).with_name("pysidedeploy.spec")


def build_command(*, dry_run: bool = False) -> list[str]:
    command = ["pyside6-deploy", str(ENTRYPOINT), "--config-file", str(CONFIG)]
    if dry_run:
        command.append("--dry-run")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Linux GUI client with pyside6-deploy.")
    parser.add_argument("--dry-run", action="store_true", help="Print the deployment plan without building.")
    args = parser.parse_args(argv)
    return subprocess.call(build_command(dry_run=args.dry_run), cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
