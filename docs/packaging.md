# 打包

MVP 打包目標是在 Linux 產出可玩的 build。Windows build 必須在 Windows 機器上產生；不要使用 Linux Docker cross-build Windows 執行檔。

## 入口點

專案 scripts：

```toml
[project.scripts]
p2p-tetris-client = "p2p_tetris.client.app:main"
p2p-tetris-server = "p2p_tetris.server.app:main"
```

## 使用 pyside6-deploy 打包 Linux client

automation skeleton 位於 `src/p2p_tetris/packaging/pyside6_deploy/`。

先 dry-run 檢查 deploy plan：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.pyside6_deploy.deploy_client --dry-run
```

打包 client：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.pyside6_deploy.deploy_client
```

設定檔為 `src/p2p_tetris/packaging/pyside6_deploy/pysidedeploy.spec`。

## macOS `.app`

macOS GUI App 的執行文件位於 `docs/mac-packaging/execution.md`。

第一版只支援 Apple Silicon `arm64`，只包 GUI client，不內建 server。build-time 依賴透過 `uv sync --dev --group packaging` 安裝；終端玩家不需要安裝 `uv` 或 Python 工程依賴。

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.macos.build_app --dry-run
PYTHONPATH=src uv run python -m p2p_tetris.packaging.macos.build_app
```

輸出：

- `build/pyside6-deploy/macos/P2P Tetris.app`
- `dist/P2P-Tetris-macOS-arm64.zip`

目前沒有 Developer ID signing / notarization；wrapper 會做 ad-hoc signing，Gatekeeper 仍可能要求使用者手動允許。

## PyInstaller fallback

fallback spec 位於 `src/p2p_tetris/packaging/pyinstaller/`。

打包 GUI client：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.pyinstaller.build client
```

打包 headless server：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.pyinstaller.build server
```

若尚未安裝 PyInstaller，請先在目前環境中將它作為 packaging-only tool 加入，再執行上述命令。

## Windows 打包步驟

請在 Windows 機器上執行下列步驟：

1. 安裝 Python 3.13 與 `uv`。
2. Clone repository，並在 repo root 開啟 PowerShell。
3. 執行 `uv sync`。
4. 用 `$env:PYTHONPATH = "src"; uv run python -m p2p_tetris.client.app` 驗證 source client。
5. 用 `$env:PYTHONPATH = "src"; uv run python -m p2p_tetris.packaging.pyinstaller.build client` 打包 client。
6. 用 `$env:PYTHONPATH = "src"; uv run python -m p2p_tetris.packaging.pyinstaller.build server` 打包 server。
7. 在 `127.0.0.1:7777` 啟動打包後的 server。
8. 啟動兩個打包後的 client，並讓兩者連到本機 server。
9. 確認前兩個 client 會成為 active players 或進入等待流程，且 Single Player 可以渲染並接受鍵盤輸入。

## Smoke 驗證

打包前：

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/gui
uv run ruff check src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
uv run mypy src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
```

打包後：

```bash
./dist/p2p-tetris-client/p2p-tetris-client
./dist/p2p-tetris-server --help
```
