# Vibe Coding 起始 Prompt

以下整段作為 Codex / vibe coding 的起始 prompt 使用。

```text
你是本次實作的主 agent，工作目錄是目前這個 `p2p-tetris` repository。你的任務是根據既有文件完整實作 P2P Tetris MVP，並用 pytest、mypy、ruff 驗證通過。

必讀文件：

- `docs/proposal.md`
- `docs/detailed-design.md`
- `docs/tasks/progress.md`
- `docs/tasks/*.md`

目標輸出：

- 可執行的 Python 3.13 / uv 專案，採 `src/p2p_tetris/` package layout。
- PySide6 桌面 client，支援單人與連線入口，`Play with Computer` 在 MVP 顯示為 disabled 或未啟用。
- headless UDP server，支援 2 active players、預設 5 waiting players、車輪戰、timeout 與離線清理。
- game-core、battle-rules、controllers、client-runtime、client-gui、net、server、packaging、tests 全部依任務文件完成。
- 完整 pytest 單元測試與必要整合 / smoke test。
- `uv run ruff check .`、`uv run mypy .`、`uv run pytest` 必須通過。

## 絕對工作規則

1. 你是主 agent，不是唯一實作者。使用者明確要求主 agent 生成 subagent 來實作每個模塊。你必須真的使用 `spawn_agent` 或當前環境提供的等價子 agent 工具，並把具體模塊交給 worker subagents。
2. 不得以單一 agent 獨自完成全部模塊。除非環境完全沒有 subagent 能力，否則不能跳過 subagent。若沒有 subagent 能力，停止並回報「此環境缺少完成本任務所需的 subagent 能力」，不要改成單人實作。
3. 主 agent 的責任是讀文檔、拆分工作、生成 worker、控制依賴順序、整合 worker 變更、review 邊界、修正跨模塊整合問題、執行最終驗證。主 agent 可以做小範圍整合修正，但不得把所有模塊都攬下來自己寫。
4. 每個 worker 都必須被告知：你不是代碼庫中唯一的實作者，不要 revert 其他人的變更，若遇到其他 worker 的變更要協調接口並調整自己的實作。
5. 每個 worker 必須擁有明確且互不重疊的 write scope。若需要改 `pyproject.toml`、entrypoints 或共享 fixture，先在 worker final 中提出，主 agent 統一整合，避免衝突。
6. 整個實作過程不應等待人工參與。任務文件中出現「經使用者確認」、「決策並實作」等文字時，以 `docs/detailed-design.md` 第 3.1 節的已確認決策作為確認來源，不要再向使用者詢問。
7. 若文檔出現無法同時滿足的硬性衝突，優先順序為：`docs/detailed-design.md` 的已確認決策與依賴規則、`docs/proposal.md` 的產品範圍、`docs/tasks/*.md` 的任務列表。仍無法解決且會違反明確需求時，停止並回報 blocker。
8. 不要引入官方 Tetris 商標素材、圖片、音效或受版權保護素材。
9. 不要加入 RL agent 訓練、Gymnasium environment 或模型推論。只保留 `PlayerAction`、`ActionSource`、snapshot、deterministic seed 等未來 RL 接口。

## 已確認規格摘要

以 `docs/detailed-design.md` 為準：

- GUI framework：PySide6。
- 可見盤面：10 x 20，內部目標 10 x 40，含 20 hidden rows。
- pieces：I、O、T、S、Z、J、L。
- randomizer：7-bag，必須支援 deterministic seed。
- rotation：guideline SRS，I、O、JLSTZ 分別測試。
- controls：`PlayerAction` 固定包含 `NO_OP`、`MOVE_LEFT`、`MOVE_RIGHT`、`SOFT_DROP`、`HARD_DROP`、`ROTATE_CW`、`ROTATE_CCW`、`HOLD`。
- 預設手感：60 ticks/s、lock delay 500 ms、DAS 170 ms、ARR 50 ms、soft drop 約 20 rows/s、初始 gravity 約 1 row/s。放在 `GameConfig`，MVP 不做玩家自訂 UI。
- T-spin：完整 T-spin / T-spin Mini / no-line T-spin 類事件分類。
- battle：2 active players，預設 120 秒，先 3 KO 獲勝。
- attack baseline：single 0、double 1、triple 2、tetris 4、T-spin mini single 1、T-spin single 2、T-spin double 4、T-spin triple 6、back-to-back bonus +1，combo bonus 使用遞增表並用 fixture 固定。
- garbage：傳統有洞 garbage。incoming 先進 pending queue，本方 outgoing attack 先抵銷 pending incoming，剩餘才送對手。未抵銷 garbage 在本方落鎖與消行處理後套用。
- garbage hole：每個 `GarbageEvent` 使用 deterministic seed；同一個多行 event hole 維持一致，下一個 event 可換 hole。
- KO：top-out 觸發 KO，被 KO 玩家展示約 1.5 秒後清空盤面並 respawn。match timer、KO count、sent lines 保留，active piece、hold、pending garbage 依 respawn 規則重置。
- winner：timeout 時依 KO 數、sent garbage lines、結束盤面高度判定。仍完全相同則 draw，不做 sudden death。
- UDP wire encoding：UTF-8 JSON，業務邏輯使用 typed dataclass message，不直接操作 ad hoc dict。
- reliability：reliable resend 100 ms、heartbeat 500 ms、session timeout 2 s。測試使用 fake clock，不等待真實時間。
- sync：client 本地即時模擬自己的盤面；server 管理 match-level truth，包括 timer、KO、sent lines、garbage assignment、opponent summary。snapshot 只校正 match-level 狀態與必要摘要，不做 server authoritative rollback。
- GUI rendering：MVP 採 `QGraphicsView` + `QGraphicsScene`。
- packaging：Linux 產出可玩打包檔；Windows 不在 Linux Docker cross-build，提供 Windows 機器上的 step-by-step 文件。

## 模塊邊界

嚴格遵守 `docs/detailed-design.md` 第 4 節依賴方向：

- `common` 不依賴其他專案模塊。
- `game_core` 只依賴 `common` 與標準函式庫，不依賴 `battle`。
- `battle` 可依賴 `common` 與 `game_core` 的事件資料結構，不依賴 engine internals。
- `controllers` 可依賴 `common` 與 `game_core.actions`，不依賴 GUI widget。
- `net` 可依賴 `common` 與自己的 protocol dataclass，不依賴 `game_core` 或 GUI。
- `client-runtime` 可依賴 `common`、`game_core`、`battle`、`controllers`、`net` 與 view model，不依賴 PySide6 widget。
- `client-gui` 可依賴 `client-runtime` public interface 與 PySide6，不直接修改 `GameEngine` internals。
- `server` 可依賴 `common`、`battle`、`net`，不依賴 PySide6 或 client GUI。
- `packaging` 只引用 entrypoint，不承載 runtime 邏輯。

## Subagent 分工要求

先快速讀文件與倉庫現況，建立主 plan，然後依依賴順序 spawn worker。至少要使用下列 worker 分工，可以按實際進度拆得更細，但不能合併成主 agent 自己做。

### Worker A: foundation / common / initial tests

Write scope:

- `src/p2p_tetris/common/`
- `src/p2p_tetris/__init__.py`
- `tests/common/`
- `tests/conftest.py`
- 共享 fake clock fixture

任務：

- COMMON-001 至 COMMON-005
- TEST-001 的 pytest 目錄與基本 fixture
- 提出 pyproject tool config 建議，但除非主 agent 指派，不直接改跨模塊 entrypoints。

### Worker B: game-core

Write scope:

- `src/p2p_tetris/game_core/`
- `tests/game_core/`
- `tests/fixtures/game_core/`

任務：

- CORE-001 至 CORE-019
- TEST-003 SRS fixture
- deterministic engine、snapshot、garbage injection、T-spin、combo、B2B、top-out 全部測試。

### Worker C: battle-rules

Write scope:

- `src/p2p_tetris/battle/`
- `tests/battle/`
- `tests/fixtures/battle/`

任務：

- BATTLE-001 至 BATTLE-012
- TEST-004 battle fixture
- attack、garbage queue / cancel / delay、KO、respawn、winner resolver 全部以純事件 fixture 測試。

### Worker D: controllers / client-runtime

Write scope:

- `src/p2p_tetris/controllers/`
- `src/p2p_tetris/client/`
- `tests/controllers/`
- `tests/client/`

任務：

- CTRL-001 至 CTRL-006
- CLIENT-RT-001 至 CLIENT-RT-011
- scripted controller、keyboard abstraction、local session、versus session、view model、fake net client tests。

### Worker E: net / server

Write scope:

- `src/p2p_tetris/net/`
- `src/p2p_tetris/server/`
- `tests/net/`
- `tests/server/`
- `tests/fixtures/net/`

任務：

- NET-001 至 NET-012
- SERVER-001 至 SERVER-016
- TEST-005、TEST-006
- typed protocol JSON codec、reliability、fake transport、UDP endpoint smoke、session、queue、match lifecycle、車輪戰。

### Worker F: client-gui / packaging / docs

Write scope:

- `src/p2p_tetris/gui/`
- `src/p2p_tetris/client/app.py` 僅 GUI entrypoint 相關，若與 Worker D 衝突由主 agent 整合
- `src/p2p_tetris/packaging/`
- `tests/gui/`
- packaging / local run documentation

任務：

- GUI-000 至 GUI-011
- PKG-001 至 PKG-007
- TEST-007、TEST-008
- PySide6 main window、screens、QGraphicsView renderer、headless GUI smoke tests、client/server entrypoints、Linux packaging automation、Windows step-by-step docs。

### Worker G: verifier / integration QA

Write scope:

- 優先 read-only review。
- 只有主 agent 指派時才改 `tests/` 或小範圍 integration fixes。

任務：

- 在主要 worker 變更整合後，檢查 import 邊界、測試缺口、mypy/ruff 風險。
- 專注找 bug、缺測與文檔驗收缺口，不重做其他 worker 的實作。

## 主 agent 執行流程

1. 讀必讀文件與 `pyproject.toml`，用 `rg --files` 檢查現況。
2. 建立 plan，列出 worker、write scope、依賴和驗收命令。
3. 先 spawn Worker A。A 回來後，整合 common 和測試基礎。
4. 再按可並行性 spawn Worker B、C、E 的早期部分；若某 worker 缺依賴，讓它只做不阻塞的 schema / fixture /純邏輯部分，等待必要接口後再補。
5. Spawn Worker D、F 做 runtime、GUI、packaging。若 GUI 或 entrypoint 需要跨文件修改，主 agent 統一整合 `pyproject.toml`。
6. 每次 worker 完成後，主 agent 檢查 changed paths、任務 ID、測試結果，必要時做小範圍整合修正。
7. 用 Worker G 做 integration QA，不要讓 Worker G 重寫主要模塊。
8. 更新 `docs/tasks/progress.md`，只有在相關測試與品質檢查通過後才勾選完成。
9. 最終執行：
   - `uv sync`
   - `uv run python -m compileall src`
   - `uv run ruff check .`
   - `uv run mypy .`
   - `uv run pytest`
10. 若 GUI smoke test 需要 headless Qt，使用 `QT_QPA_PLATFORM=offscreen uv run pytest` 或在測試中安全設定 offscreen。

## 測試與品質要求

- 必須有完整 pytest 單元測試，覆蓋每個主要 component。
- `game-core` 測試不得啟動 GUI 或 socket。
- `battle-rules` 測試不得建立 `GameEngine`，只吃事件 fixture。
- `controllers` 測試不得建立 PySide6 `QApplication`。
- `net` reliability 測試不得等待真實時間，使用 fake clock。
- `server` queue / match lifecycle 測試不得依賴真 UDP socket，使用 fake transport。
- `client-runtime` 測試不得建立 PySide6 widget。
- `client-gui` smoke test 只驗證 widget 建立、screen 切換與 callback wiring，不驗證核心規則。
- protocol 業務邏輯不得使用 hard-coded ad hoc dict。
- 所有 public dataclass / protocol / enum 需要 type hints，讓 mypy 可檢查。
- 測試不能靠 sleep 等待真時間。
- 不要用 `# type: ignore` 或 `# noqa` 掩蓋實作問題，除非有非常明確、局部且註解說明的理由。

## 最終回報格式

完成後回報：

- 實際 spawned 的 subagents 與各自負責模塊。
- 完成的主要任務與文件變更。
- 最終驗證命令與結果：ruff、mypy、pytest。
- 若有任何未完成項，明確列出原因、影響和下一步。

不要用「已大致完成」代替驗收。只有在測試和品質檢查通過後，才宣稱完成。
```
