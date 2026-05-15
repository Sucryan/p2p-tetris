# packaging 模塊任務

## 責任

- 提供 Linux 可執行檔打包 automation。
- 提供 Windows 機器上的 step-by-step 打包與驗證文件。
- 保留 client GUI entrypoint 與 headless server entrypoint。
- 優先 `pyside6-deploy`，備援 PyInstaller。
- 不承載 runtime 邏輯。

## Public Interface

- client executable entrypoint。
- server executable entrypoint。
- packaging config / spec。
- README 操作步驟。

## 最小可執行任務

- [ ] PKG-001: 定義 Python entrypoints
  - 輸出：`pyproject.toml`
  - 驗收：`uv run p2p-tetris-client`、`uv run p2p-tetris-server --help` 可執行
  - 依賴：GUI-001、SERVER-001

- [ ] PKG-002: 定義 Linux 打包 automation 與 Windows 文件化打包邊界
  - 輸出：packaging note
  - 驗收：明確記錄 Linux 產出可玩檔案；Windows 需在 Windows 機器依文件打包，不做 Linux Docker cross-build exe
  - 依賴：D-PKG-001

- [ ] PKG-003: 建立 Linux `pyside6-deploy` 或等效打包設定
  - 輸出：`src/p2p_tetris/packaging/pyside6_deploy/`
  - 驗收：Linux client 可產出可執行檔
  - 依賴：PKG-001、PKG-002

- [ ] PKG-004: 建立 server 打包流程
  - 輸出：packaging config
  - 驗收：server 可獨立啟動
  - 依賴：SERVER-016

- [ ] PKG-005: 建立 PyInstaller fallback spec
  - 輸出：`src/p2p_tetris/packaging/pyinstaller/`
  - 驗收：fallback spec 能產出 client 或 server
  - 依賴：PKG-001

- [ ] PKG-006: 撰寫本機 server + 2 client 操作文件
  - 輸出：README 或 docs
  - 驗收：文件含 server、client、localhost 測試流程
  - 依賴：SERVER-016、GUI-007

- [ ] PKG-007: 撰寫 Windows step-by-step 打包與驗證文件
  - 輸出：docs
  - 驗收：文件說明在 Windows 上安裝環境、同步依賴、執行打包、啟動 client/server、驗證本機雙 client
  - 依賴：PKG-001、PKG-002

## 獨立測試

- packaging 不測遊戲規則。
- 打包 smoke test 只驗證 executable 啟動與基本 screen / server help。
