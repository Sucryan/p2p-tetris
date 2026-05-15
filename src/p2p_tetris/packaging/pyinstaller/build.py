"""Run PyInstaller fallback builds for client or server."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SPEC_DIR = Path(__file__).resolve().parent


def build_command(target: str) -> list[str]:
    return ["pyinstaller", "--clean", str(SPEC_DIR / f"{target}.spec")]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build fallback executables with PyInstaller.")
    parser.add_argument("target", choices=("client", "server"))
    args = parser.parse_args(argv)
    return subprocess.call(build_command(args.target), cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
