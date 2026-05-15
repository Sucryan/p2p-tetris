# PyInstaller fallback spec for the headless server.

from pathlib import Path

ROOT = Path(SPECPATH).parents[3]
ENTRYPOINT = ROOT / "src" / "p2p_tetris" / "server" / "app.py"

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name="p2p-tetris-server",
    console=True,
)
