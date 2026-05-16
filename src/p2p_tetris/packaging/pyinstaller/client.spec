# PyInstaller fallback spec for the GUI client.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parents[3]
ENTRYPOINT = ROOT / "src" / "p2p_tetris" / "client" / "app.py"
MAC_ICON = ROOT / "packaging" / "macos" / "P2P-Tetris.icns"

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="p2p-tetris-client",
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="p2p-tetris-client",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="P2P Tetris.app",
        icon=str(MAC_ICON),
        bundle_identifier="com.ryansuc.p2p-tetris",
        info_plist={
            "CFBundleDisplayName": "P2P Tetris",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "LSApplicationCategoryType": "public.app-category.games",
            "NSLocalNetworkUsageDescription": "Connect to a P2P Tetris server on your local network.",
        },
    )
