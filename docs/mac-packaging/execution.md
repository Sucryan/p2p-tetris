# macOS App 打包執行文件

本文件落實 `docs/mac-packaging/proposal.md` 的決策，第一版只產出 Apple Silicon `arm64` 的 GUI client `.app`。server 不內建在 App 裡，房主仍使用 `p2p-tetris-server` 啟動 UDP server。

## 目標

- App 名稱：`P2P Tetris`
- Bundle identifier：`com.ryansuc.p2p-tetris`
- Version：沿用 `pyproject.toml` 的 `0.1.0`
- 最低 macOS：本機 build 環境 `macOS 15.3.1 (24D70)`
- CPU 架構：Apple Silicon `arm64`
- 主要輸出：`build/pyside6-deploy/macos/P2P Tetris.app`
- GitHub Releases artifact：`dist/P2P-Tetris-macOS-arm64.zip`

## 前置條件

```bash
uv sync --dev --group packaging
```

`packaging` dependency group 目前只固定 `Nuitka==4.0`。這是 `pyside6-deploy` 的 build-time dependency，不會成為終端玩家執行 App 的前置條件。

## Build

先確認 deploy plan：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.macos.build_app --dry-run
```

產出 `.app`、ad-hoc sign，並建立 GitHub Releases 用 ZIP：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.macos.build_app
```

若只想產生 `.app`，不要建立 ZIP：

```bash
PYTHONPATH=src uv run python -m p2p_tetris.packaging.macos.build_app --no-zip
```

## 輸出內容

build wrapper 會補齊或覆寫 `.app/Contents/Info.plist` 的 release metadata：

- `CFBundleIdentifier = com.ryansuc.p2p-tetris`
- `CFBundleDisplayName = P2P Tetris`
- `CFBundleShortVersionString = 0.1.0`
- `LSApplicationCategoryType = public.app-category.games`
- `LSMinimumSystemVersion = <build Mac 的 sw_vers -productVersion>`
- `NSLocalNetworkUsageDescription = Connect to a P2P Tetris server on your local network.`

App icon source 位於 `packaging/macos/P2P-Tetris.svg`，實際 `.icns` 位於 `packaging/macos/P2P-Tetris.icns`。

## 啟動與安裝

本機啟動 smoke：

```bash
open "build/pyside6-deploy/macos/P2P Tetris.app"
```

使用者從 GitHub Releases 下載 `P2P-Tetris-macOS-arm64.zip` 後，解壓縮並把 `P2P Tetris.app` 拖到 `/Applications`。

## Gatekeeper

第一版沒有 Apple Developer Program、Developer ID signing 或 notarization。build wrapper 只做 ad-hoc signing，因此第一次從網路下載後啟動時，macOS 可能阻擋。

使用者可在 System Settings 的 Privacy & Security 手動允許，或在 Finder 對 App 使用 Open。正式降低 Gatekeeper 摩擦需要 Developer ID signing、notarization 和 stapling。

## LAN / Firewall

GUI client 會連到房主的 UDP server，預設 port 是 `7777`。App 的 Info.plist 已包含 local network usage description，因為 Apple 要求直接連到 local hosts 的 App 提供 `NSLocalNetworkUsageDescription`。

房主啟動 server：

```bash
uv run p2p-tetris-server --host 0.0.0.0 --port 7777
```

client 端在 Connect screen 輸入房主 LAN IP、port `7777`、player name。若連不上，先檢查房主 Mac firewall、路由器與雙方是否在同一區網。

## 設定與 Log

client 會保存最近使用的 host、port、player name。GUI 透過 Qt settings 使用平台慣例位置保存設定。

macOS log 寫到：

```text
~/Library/Logs/P2P Tetris/client.log
```

## Smoke Test

打包前：

```bash
uv run python -m compileall src
uv run ruff check .
uv run mypy .
QT_QPA_PLATFORM=offscreen uv run pytest
```

打包後：

```bash
open "build/pyside6-deploy/macos/P2P Tetris.app"
plutil -p "build/pyside6-deploy/macos/P2P Tetris.app/Contents/Info.plist"
codesign --verify --deep --strict --verbose=2 "build/pyside6-deploy/macos/P2P Tetris.app"
ditto -x -k "dist/P2P-Tetris-macOS-arm64.zip" /tmp/p2p-tetris-release-check
```

手動驗收：

- Finder 雙擊不出現 Terminal 視窗。
- Single Player 可渲染，鍵盤可移動、旋轉、hard drop。
- 同一台 Mac：開 server + client，client 可進入等待或 match。
- 同一區網：另一台 Mac 的 client 可連到房主 LAN IP。

## Fallback

`src/p2p_tetris/packaging/pyinstaller/client.spec` 已補 macOS `BUNDLE(...)` metadata，可作為 `pyside6-deploy` 遇到 Nuitka / PySide6 / signing 阻塞時的 fallback。第一版 release path 仍以 `pyside6-deploy` 為準。
