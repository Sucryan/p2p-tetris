"""Build and prepare the macOS GUI app bundle."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from importlib.util import find_spec
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ENTRYPOINT = ROOT / "src" / "p2p_tetris" / "client" / "app.py"
CONFIG = ROOT / "packaging" / "macos" / "pysidedeploy.spec"
GENERATED_CONFIG = ROOT / "build" / "pyside6-deploy" / "macos-pysidedeploy.spec"
APP_NAME = "P2P Tetris"
BUNDLE_IDENTIFIER = "com.ryansuc.p2p-tetris"
OUTPUT_DIR = ROOT / "build" / "pyside6-deploy" / "macos"
APP_PATH = OUTPUT_DIR / f"{APP_NAME}.app"
DIST_DIR = ROOT / "dist"
ZIP_PATH = DIST_DIR / "P2P-Tetris-macOS-arm64.zip"
LOCAL_NETWORK_USAGE = "Connect to a P2P Tetris server on your local network."
EXTRA_IGNORE_DIRS = (
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "docs",
    "tests",
)


def build_command(*, config: Path = CONFIG, dry_run: bool = False) -> list[str]:
    command = [
        "pyside6-deploy",
        str(ENTRYPOINT),
        "--config-file",
        str(config),
        "--name",
        APP_NAME,
        "--force",
        "--extra-ignore-dirs",
        ",".join(EXTRA_IGNORE_DIRS),
    ]
    if dry_run:
        command.append("--dry-run")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the macOS P2P Tetris.app bundle.")
    parser.add_argument("--dry-run", action="store_true", help="Print the deployment plan without building.")
    parser.add_argument("--skip-codesign", action="store_true", help="Skip ad-hoc signing after metadata updates.")
    parser.add_argument("--no-zip", action="store_true", help="Do not create the GitHub Releases ZIP artifact.")
    args = parser.parse_args(argv)

    if not args.dry_run and find_spec("nuitka") is None:
        print("Nuitka is not installed. Run: uv sync --group packaging", file=sys.stderr)
        return 2

    config = CONFIG if args.dry_run else _write_generated_config()
    command = build_command(config=config, dry_run=args.dry_run)
    completed = subprocess.run(command, cwd=ROOT, env=_build_env(), check=False)
    if completed.returncode != 0 or args.dry_run:
        return completed.returncode

    if not APP_PATH.exists():
        print(f"Expected app bundle was not created: {APP_PATH}", file=sys.stderr)
        return 1

    _write_info_plist(APP_PATH)
    if not args.skip_codesign:
        _codesign(APP_PATH)
    if not args.no_zip:
        _write_zip(APP_PATH, ZIP_PATH)
    print(f"macOS app bundle: {APP_PATH}")
    if not args.no_zip:
        print(f"release ZIP: {ZIP_PATH}")
    return 0


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not current else os.pathsep.join((src, current))
    return env


def _write_generated_config() -> Path:
    GENERATED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    content = CONFIG.read_text(encoding="utf-8")
    replacements = {
        "project_dir = ../..": f"project_dir = {ROOT}",
        "input_file = src/p2p_tetris/client/app.py": f"input_file = {ENTRYPOINT}",
        "icon = packaging/macos/P2P-Tetris.icns": f"icon = {ROOT / 'packaging' / 'macos' / 'P2P-Tetris.icns'}",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    GENERATED_CONFIG.write_text(content, encoding="utf-8")
    return GENERATED_CONFIG


def _project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _minimum_system_version() -> str | None:
    try:
        completed = subprocess.run(
            ["sw_vers", "-productVersion"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    version = completed.stdout.strip()
    return version or None


def _write_info_plist(app_path: Path) -> None:
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as file:
        plist = plistlib.load(file)

    version = _project_version()
    plist.update(
        {
            "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": BUNDLE_IDENTIFIER,
            "CFBundleName": APP_NAME,
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "LSApplicationCategoryType": "public.app-category.games",
            "NSLocalNetworkUsageDescription": LOCAL_NETWORK_USAGE,
        }
    )
    minimum_system_version = _minimum_system_version()
    if minimum_system_version is not None:
        plist["LSMinimumSystemVersion"] = minimum_system_version

    with plist_path.open("wb") as file:
        plistlib.dump(plist, file, sort_keys=True)


def _codesign(app_path: Path) -> None:
    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
        check=True,
    )


def _write_zip(app_path: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    subprocess.run(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(app_path),
            str(zip_path),
        ],
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
