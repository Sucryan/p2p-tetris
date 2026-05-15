# P2P Tetris 詳細設計與最小任務切分

## 1. 文件目的

本文根據 `docs/proposal.md` 與 `docs/high-level-design.md`，將 MVP 模組拆成可執行、可驗收、可獨立測試的最小任務。

本文遵守以下限制：

- 不新增需求文件與概要設計之外的產品意圖。
- 對原文已定版的內容，直接固定為任務約束。
- 對原文標示「待詳細設計」但未給出數值或規則的內容，不擅自選值，改列為「需確認的決策任務」。
- 每個模組必須能以 mock、fixture、fake transport 或 deterministic seed 單獨測試，不依賴 GUI 或真實網路才能驗證核心邏輯。

## 2. 已固定設計輸入

以下內容已由需求與概要設計固定，本文任務不得違反：

- GUI framework：PySide6。
- 遊戲可見盤面：10 x 20。
- 方塊：I、O、T、S、Z、J、L。
- randomizer：MVP 方向採 7-bag。
- 對戰模式：2 名 active players。
- 對戰時間：預設 120 秒，必須可配置。
- KO 目標：任一玩家先達 3 KO 提前獲勝。
- 等待隊列：active players 外預設容量 5，必須可配置。
- MVP garbage：傳統有洞 garbage，不採 bomb garbage。
- UDP：client 與 server 通訊使用 UDP。
- 同步策略：client 本地即時模擬自己的盤面，server 管理 match-level 狀態、可靠事件與輕量校正。
- RL：不屬於 MVP，但必須保留 `PlayerAction`、`ActionSource`、deterministic seed、snapshot 與 controller 抽象。
- 品質檢查：`uv run ruff check .`、`uv run mypy .`、`uv run pytest` 必須通過。

## 3. 決策記錄與待確認項目

本節記錄需求與概要設計中留待確認的項目。已確認項目可以進入對應實作任務；待確認項目在定案前不得寫死到程式碼。

### 3.1 已確認決策

| 決策 ID | 決策 | 實作含義 |
| --- | --- | --- |
| D-CORE-001 | 採完整 guideline-like hidden rows。內部盤面以 10 x 40 為目標：20 行可見區 + 20 行 hidden buffer。 | GUI 只顯示 20 行可見區；spawn、rotation、top-out 與 snapshot 必須清楚區分 visible rows 與 hidden rows。 |
| D-CORE-002 | 採 guideline SRS。 | 實作標準 SRS kick table，I piece、O piece、JLSTZ pieces 分開測試；旋轉行為以 fixture 固定。 |
| D-CORE-003 | 採固定的新手友善手感預設，不做玩家自訂手感 UI。 | `GameConfig` 保留手感參數，方便測試與後續調整；MVP 不提供使用者調整介面。初始建議值：60 ticks/s、lock delay 500 ms、DAS 170 ms、ARR 50 ms、soft drop 約 20 rows/s、初始 gravity 約 1 row/s。 |
| D-CORE-004 | 採完整 T-spin 判定。 | 支援 T-spin、T-spin Mini 與 no-line T-spin 類事件分類；attack table 需能區分這些事件。 |
| D-BATTLE-001 | 採現代 guideline-like attack table。 | 攻擊表 config 化並以 fixture 固定。MVP baseline：single 0、double 1、triple 2、tetris 4、T-spin mini single 1、T-spin single 2、T-spin double 4、T-spin triple 6、back-to-back bonus +1；combo bonus 使用遞增表並由 fixture 固定。 |
| D-BATTLE-002 | 採常見且公平的 garbage queue / cancel 流程。 | incoming garbage 先進 pending queue；本方 outgoing attack 先抵銷 pending incoming garbage，剩餘才送給對手；未被抵銷的 garbage 在本方落鎖與消行處理後套用，避免封包抵達瞬間破壞操作。 |
| D-BATTLE-003 | 採常見對戰垃圾 hole 策略，讓玩家有機會處理。 | 每個 `GarbageEvent` 使用 deterministic seed 產生 hole；同一個多行 garbage event 內 hole 維持一致，下一個 event 可換 hole；測試必須能重播 hole 序列。 |
| D-BATTLE-004 | KO 後短暫 delay 並清空重生，delay 約 1.5 秒。 | 玩家 top-out 後產生 KO；被 KO 玩家停留展示約 1.5 秒後清空盤面並 respawn。match timer、KO count、sent lines 保留；active piece、hold、pending garbage 依 respawn 規則重置。 |
| D-BATTLE-005 | 完全平手允許 draw。 | 時間結束後依 KO 數、sent garbage lines、結束盤面高度判定；若仍完全相同，`MatchResult` 可為 draw，不進入 sudden death。 |
| D-NET-001 | UDP wire encoding 採 UTF-8 JSON。 | dataclass message 透過 typed codec encode/decode 成 JSON bytes；業務邏輯不得直接操作 ad hoc dict。 |
| D-NET-002 | reliable event 與 heartbeat 採 aggressive LAN-friendly 預設。 | 所有 interval 保留在 `NetworkConfig`；MVP 建議 reliable resend 100 ms、heartbeat 500 ms、session timeout 2 s。測試使用 fake clock，不等待真實時間。 |
| D-NET-003 | 採輕量 snapshot 校正，不做 server authoritative rollback。 | server 持有 match-level truth：timer、KO、sent lines、garbage assignment、opponent summary。client 保留本地即時操作手感；snapshot 只校正 match-level 狀態與必要摘要，不回滾本地方塊操作。 |
| D-GUI-001 | 採 `QGraphicsView` + `QGraphicsScene` 作為 MVP game view rendering 架構。 | 盤面、active piece、ghost、hold / next preview、garbage 提示與 KO 視覺狀態由 scene / item 層呈現；GUI 只讀 view model，不承載核心規則。 |
| D-PKG-001 | MVP 先產出 Linux 可玩的打包檔案；Windows 不在 Linux Docker 內 cross-build exe，而是提供 Windows 機器上的 step-by-step 打包與驗證文件。 | packaging 不屬於核心 runtime；保留 Linux automation 模組與 Windows packaging 文件。Windows executable 需在 Windows-capable 環境依文件產出與測試。 |

### 3.2 仍待確認決策

目前沒有仍待確認的決策項目。若後續發現新需求或平台限制，需先新增決策記錄，再修改任務。

## 4. 模組獨立性規則

### 4.1 依賴方向

允許依賴方向如下。箭頭表示「右側可依賴左側」：

```text
common
  -> game_core
  -> battle
  -> controllers
  -> net

game_core -> battle
game_core -> controllers

game_core + battle + controllers + net -> client_runtime -> gui
common + battle + net -> server
entrypoints -> packaging
```

更精確的 import 規則：

- `common` 不依賴其他專案模組。
- `game_core` 只依賴 `common` 與 Python 標準函式庫，不依賴 `battle`。
- `battle` 可依賴 `common` 與 `game_core` 的事件資料結構，不可依賴 engine internals。
- `controllers` 可依賴 `common` 與 `game_core.actions`，不可依賴 GUI widget。
- `net` 可依賴 `common` 與自己的 protocol dataclass，不可依賴 `game_core` 或 GUI。
- `client-runtime` 可依賴 `common`、`game_core`、`battle`、`controllers`、`net` 與 view model，不可依賴 PySide6 widget 類別。
- `client-gui` 可依賴 `client-runtime` 的 public interface 與 view model，可依賴 PySide6，不可直接修改 `GameEngine` 內部狀態。
- `server` 可依賴 `common`、`battle`、`net`，不可依賴 PySide6 或 client GUI。
- `packaging` 只引用 entrypoint，不承載 runtime 邏輯。

### 4.2 測試隔離規則

- `game-core` 測試不得啟動 GUI 或 socket。
- `battle-rules` 測試不得建立 `GameEngine`，只吃事件 fixture。
- `controllers` 測試不得建立 PySide6 `QApplication`，鍵盤映射可用抽象 key event 測試。
- `net` 測試不得依賴真實時間等待，需以 fake clock 驗證重送與 timeout。
- `server` 測試不得依賴真實 UDP socket；配對、queue、match lifecycle 使用 fake transport。
- `client-runtime` 測試不得建立 PySide6 widget；使用 fake action source 與 fake net client。
- `client-gui` 測試不得驗證核心規則，只驗證畫面狀態與 callback wiring。

## 5. 共用資料契約

### 5.1 `PlayerAction`

`PlayerAction` 是真人、測試腳本與未來 RL agent 共用的遊戲動作 enum。MVP 固定包含：

- `NO_OP`
- `MOVE_LEFT`
- `MOVE_RIGHT`
- `SOFT_DROP`
- `HARD_DROP`
- `ROTATE_CW`
- `ROTATE_CCW`
- `HOLD`

系統操作如 pause、restart、connect、quit 不放入 `PlayerAction`。

### 5.2 設定物件

設定物件使用 typed dataclass 或等效 immutable 結構：

- `GameConfig`：盤面、hidden buffer、next queue 顯示數、gravity、lock delay、DAS / ARR、tick rate。
- `MatchConfig`：match 秒數、KO 目標、active player 數、waiting capacity、respawn 規則。
- `NetworkConfig`：bind host、port、heartbeat、timeout、重送間隔、snapshot 頻率。
- `RenderConfig`：格子尺寸、顏色主題、animation 開關。

已固定值可做預設；未決策項目在實作前必須由對應 `D-*` 決策任務確認。

### 5.3 `GameStateSnapshot`

`GameStateSnapshot` 是 `game-core` 對 GUI、測試、client runtime 與未來 RL observation 的只讀輸出。至少包含：

- 可見盤面狀態。
- 必要 hidden buffer 摘要。
- active piece 類型、座標與旋轉狀態。
- ghost piece 座標。
- hold piece。
- next queue。
- combo 與 back-to-back 狀態。
- score、cleared lines、top-out。
- pending garbage 摘要。

snapshot 不暴露對手 seed 或其他玩家不可得資訊。

### 5.4 規則事件

`game-core` 輸出的規則事件：

- `ClearEvent`
- `TopOutEvent`
- `PieceLockedEvent`

`battle-rules` 輸出的對戰事件：

- `AttackEvent`
- `GarbageEvent`
- `KOEvent`
- `RespawnEvent`
- `MatchResult`

所有事件都必須可序列化、可比較，並能用 deterministic fixture 驗證。

### 5.5 View Model

GUI 只讀取 view model，不直接讀取 engine internals：

- `BoardViewModel`
- `PiecePreviewViewModel`
- `SoloHudViewModel`
- `VersusHudViewModel`
- `ConnectionViewModel`
- `MatchResultViewModel`

View model 由 `client-runtime` 組裝，GUI 只負責呈現與回呼。

## 6. 模組詳細設計與任務

### 6.1 `common`

#### 責任

- 定義共用設定、ID、fake clock-friendly time provider。
- 提供跨模組可共享的 immutable value object。
- 不包含遊戲規則、網路 IO 或 GUI 狀態。

#### Public Interface

- `GameConfig`
- `MatchConfig`
- `NetworkConfig`
- `PlayerId`
- `SessionId`
- `MatchId`
- `MonotonicClock` protocol

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| COMMON-001 | 建立 `src/p2p_tetris/common/` package 與 public exports | package skeleton | `python -m compileall src` | 無 |
| COMMON-002 | 定義 strongly typed ID value objects | `ids.py` | ID 不可與 raw string / int 隨意混用的型別測試 | COMMON-001 |
| COMMON-003 | 定義 config dataclass 與已固定預設值 | `config.py` | config 單元測試覆蓋 10x20、120 秒、3 KO、2 active、5 waiting | COMMON-001 |
| COMMON-004 | 為未決設定加入 required field 或明確 TODO gate | config tests | 未決欄位測試不可默默落入猜測預設 | COMMON-003, 對應 `D-*` |
| COMMON-005 | 定義 injectable clock protocol 與 fake clock fixture | `time.py`, test fixture | fake clock 可手動推進並被 timeout 測試使用 | COMMON-001 |

#### 獨立測試

- 只使用標準函式庫與 pytest。
- 不 import `game_core`、`net`、`server` 或 PySide6。

### 6.2 `game-core`

#### 責任

- 維護單一玩家盤面、方塊、碰撞、旋轉、生成、hold、next queue、ghost piece、gravity、lock、line clear、combo、B2B、top-out。
- 提供 deterministic `GameEngine`，可由 GUI 以外的 controller 驅動。
- 輸出 snapshot 與規則事件，不直接處理 KO、match timer、server 配對或 UDP。

#### Public Interface

- `PlayerAction`
- `GameEngine`
- `Board`
- `GarbageInjection`
- `PieceType`
- `RotationState`
- `GameStateSnapshot`
- `ClearEvent`
- `TopOutEvent`
- `PieceLockedEvent`

#### 內部子單元

- `actions.py`：action enum。
- `pieces.py`：tetromino 定義與 orientation。
- `board.py`：grid、collision、line clear。
- `randomizer.py`：7-bag generator。
- `rotation.py`：SRS wall kick。
- `engine.py`：fixed tick simulation。
- `snapshots.py`：只讀 snapshot。

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| CORE-001 | 建立 `game_core` package 與 `PlayerAction` enum | `actions.py` | enum 包含 MVP action，系統操作不在 enum 內 | COMMON-001 |
| CORE-002 | 定義 tetromino 類型與旋轉狀態資料 | `pieces.py` | 每種 piece 有 4 個 orientation fixture | CORE-001 |
| CORE-003 | 實作 `Board` 與座標邊界檢查 | `board.py` | 10x20 可見區與 hidden buffer 行為由 fixture 驗證 | CORE-002, D-CORE-001 |
| CORE-004 | 實作 collision 與 placement 檢查 | `board.py` | 撞牆、撞方塊、hidden row 測試 | CORE-003 |
| CORE-005 | 實作 7-bag randomizer | `randomizer.py` | deterministic seed 產生可重現序列，每 7 顆包含全套 piece | CORE-002 |
| CORE-006 | 定義 SRS kick table fixture | fixture file | fixture 經使用者確認，不由實作猜測 | D-CORE-002 |
| CORE-007 | 實作 rotation 與 wall kick | `rotation.py` | I、O、JLSTZ 的成功與失敗案例 fixture | CORE-004, CORE-006 |
| CORE-008 | 實作 active piece spawn 與 next queue | `engine.py` | reset 後 active piece、next queue 長度可測 | CORE-005, D-CORE-001 |
| CORE-009 | 實作水平移動、soft drop、hard drop | `engine.py` | action sequence fixture 驗證 final board | CORE-008 |
| CORE-010 | 實作 hold 規則 | `engine.py` | 每顆落鎖前只能 hold 一次、swap 行為可測 | CORE-008 |
| CORE-011 | 實作 ghost piece 計算 | `snapshots.py` | ghost 不改變 board，位置符合 hard drop landing | CORE-009 |
| CORE-012 | 決策並實作 gravity、lock delay、DAS / ARR 所需 engine hooks | `engine.py` | fake clock / tick fixture 驗證 lock timing | D-CORE-003 |
| CORE-013 | 實作 line clear | `board.py`, `engine.py` | 1-4 行消除與 board compact fixture | CORE-009 |
| CORE-014 | 實作 combo 與 B2B 狀態追蹤 | `engine.py` | 連續消行、不消行中斷、B2B 延續測試 | CORE-013 |
| CORE-015 | 決策並實作 T-spin 偵測 | `engine.py` | T-spin / non T-spin fixture | D-CORE-004, CORE-007 |
| CORE-016 | 實作 top-out 判定 | `engine.py` | spawn blocked、lock above visible area 的 fixture | CORE-008, D-CORE-001 |
| CORE-017 | 實作 `GameStateSnapshot` | `snapshots.py` | snapshot immutable，包含 GUI/RL 所需欄位，不暴露 seed | CORE-011, CORE-014, CORE-016 |
| CORE-018 | 實作 `GameEngine.reset(seed, config)` 與 `step(actions, ticks)` | `engine.py` | 同 seed 同 action sequence 產生相同 snapshot | CORE-017 |
| CORE-019 | 實作 `apply_garbage(GarbageInjection)` 的核心盤面套用入口 | `engine.py` | 傳入 core-local garbage payload 後 board 變化可測 | CORE-013 |

#### 獨立測試

- 所有測試用 deterministic seed 與 action sequence。
- 不 import PySide6、`net`、`server`。
- `apply_garbage()` 測試只使用 `game-core` 自己定義的 `GarbageInjection`，不啟動 match manager。

### 6.3 `battle-rules`

#### 責任

- 將 `ClearEvent` 轉成 attack pressure。
- 管理 incoming garbage 抵銷、延遲套用、有洞 garbage 生成。
- 管理 KO、respawn、match result 與 winner resolution。
- 不處理方塊碰撞、鍵盤輸入、UDP 封包或 GUI。

#### Public Interface

- `AttackCalculator`
- `GarbageGenerator`
- `GarbageQueue`
- `BattleCoordinator`
- `WinnerResolver`
- `AttackEvent`
- `GarbageEvent`
- `KOEvent`
- `RespawnEvent`
- `MatchResult`

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| BATTLE-001 | 建立 battle event dataclass | `battle/events.py` | 事件可比較、可序列化、含 source player 與 seq 欄位 | COMMON-002 |
| BATTLE-002 | 定義 attack table fixture | fixture file | fixture 經使用者確認，不自行猜測數值 | D-BATTLE-001, D-CORE-004 |
| BATTLE-003 | 實作 `AttackCalculator` | `attack.py` | ClearEvent fixture 對應 AttackEvent lines | BATTLE-001, BATTLE-002 |
| BATTLE-004 | 定義有洞 garbage event 與 row model | `garbage.py` | 資料模型未寫死到 bomb-incompatible | BATTLE-001 |
| BATTLE-005 | 決策並實作 garbage hole 策略 | `garbage.py` | 同 seed 產生相同 hole 序列 | D-BATTLE-003, BATTLE-004 |
| BATTLE-006 | 決策並實作 garbage 抵銷規則 | `garbage.py` | incoming 先抵銷或其他確認規則的 fixture | D-BATTLE-002 |
| BATTLE-007 | 決策並實作 delayed garbage queue | `garbage.py` | fake clock / tick 測試延遲與套用順序 | D-BATTLE-002, COMMON-005 |
| BATTLE-008 | 決策並實作 KO 與 respawn 規則資料 | `match_rules.py` | top-out 產生 KO，respawn event 符合確認規則 | D-BATTLE-004 |
| BATTLE-009 | 實作 sent garbage lines 與 KO counter | `scoring.py` | match state counter 單元測試 | BATTLE-003, BATTLE-008 |
| BATTLE-010 | 實作 winner resolver | `match_rules.py` | KO 數、sent lines、盤面高度優先順序 fixture | BATTLE-009 |
| BATTLE-011 | 決策並實作完全平手處理 | `match_rules.py` | draw 或額外 tie-breaker fixture | D-BATTLE-005, BATTLE-010 |
| BATTLE-012 | 實作 `BattleCoordinator` 純邏輯 facade | `match_rules.py` | 不啟動 server 即可模擬一場 match-level 事件序列 | BATTLE-003 至 BATTLE-011 |

#### 獨立測試

- 以 `ClearEvent`、`TopOutEvent`、盤面高度摘要作為輸入 fixture。
- 不建立 `GameEngine`。
- 不使用 socket 或 GUI。

### 6.4 `controllers`

#### 責任

- 將不同 action source 轉成同一組 `PlayerAction`。
- 支援鍵盤 controller、scripted controller，並預留未來 RL policy controller。
- 不直接修改 game state、GUI 或網路狀態。

#### Public Interface

- `ActionSource`
- `ActionBatch`
- `KeyboardController`
- `ScriptedController`

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| CTRL-001 | 定義 `ActionSource` protocol | `controllers/base.py` | runtime 可用 mock source 拉取 actions | CORE-001 |
| CTRL-002 | 定義 action batch 與 tick 對齊語意 | `controllers/base.py` | 同一 tick 可含多個離散 action 的測試 | CTRL-001 |
| CTRL-003 | 實作 `ScriptedController` | `controllers/scripted.py` | deterministic action script 可驅動 game-core 測試 | CTRL-002 |
| CTRL-004 | 定義鍵盤映射資料結構 | `controllers/keyboard.py` | 預設 key map 不依賴 PySide6 event 類別 | CTRL-002 |
| CTRL-005 | 實作鍵盤狀態到 action 的轉換 | `controllers/keyboard.py` | fake key event stream 驗證 action output | CTRL-004, D-CORE-003 |
| CTRL-006 | 預留 future RL controller adapter interface | `controllers/base.py` | 只定義 protocol，不新增 RL dependency | CTRL-001 |

#### 獨立測試

- 用 fake key event 或 plain dataclass 表示按鍵。
- 不建立 PySide6 widget。
- scripted controller 可作為 `game-core` 與 `client-runtime` fixture。

### 6.5 `client-runtime`

#### 責任

- 管理 client 端單人與對戰 session。
- 維持 fixed tick game loop。
- 將 controller actions 套用到 local game engine。
- 將 snapshot 轉成 view model。
- 對戰模式中橋接 local game、battle local events 與 net-client。
- 不直接依賴 PySide6 widget。

#### Public Interface

- `LocalGameSession`
- `VersusGameSession`
- `ClientRuntimeEvent`
- `GameViewModel`
- `ConnectionState`

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| CLIENT-RT-001 | 建立 view model dataclass | `client/view_models.py` | 可由 snapshot 建立 board、hold、next、HUD view model | CORE-017 |
| CLIENT-RT-002 | 實作 `LocalGameSession.reset/start/pause/resume/restart` | `client/local_session.py` | 不啟動 GUI 即可跑單人 session 狀態機 | CORE-018, CTRL-001 |
| CLIENT-RT-003 | 實作 local fixed tick 推進 | `client/local_session.py` | fake clock 推進 N tick，snapshot deterministic | CLIENT-RT-002, COMMON-005 |
| CLIENT-RT-004 | 實作單人 view model 更新 | `client/local_session.py` | action sequence 後 view model 與 snapshot 一致 | CLIENT-RT-001, CLIENT-RT-003 |
| CLIENT-RT-005 | 定義 `NetClientPort` protocol | `client/versus_session.py` | fake net client 可替代真 UDP | NET-001 |
| CLIENT-RT-006 | 實作 `VersusGameSession` match start 初始化 | `client/versus_session.py` | 使用 server match config / seed 初始化本地 game | CLIENT-RT-003, NET-004 |
| CLIENT-RT-007 | 實作本地 attack / top-out event 上報流程 | `client/versus_session.py` | fake net client 收到 AttackReported / KOReported | BATTLE-003, CLIENT-RT-006 |
| CLIENT-RT-008 | 實作 reliable garbage / KO / respawn 事件套用 | `client/versus_session.py` | fake server event 會更新 pending garbage，並把 `GarbageEvent` 轉成 `GarbageInjection` 後交給 game-core | BATTLE-007, BATTLE-008, CORE-019 |
| CLIENT-RT-009 | 決策並實作 snapshot correction hook | `client/versus_session.py` | correction fixture 驗證可執行，不永久卡死 | D-NET-003, NET-009 |
| CLIENT-RT-010 | 實作 opponent summary view model | `client/versus_session.py` | fake opponent summary 更新 GUI 用資料 | NET-004 |
| CLIENT-RT-011 | 實作 match end 與 result view model | `client/versus_session.py` | fake MatchEnd 產生 result screen 所需資料 | BATTLE-010 |

#### 獨立測試

- 使用 `ScriptedController` 與 fake net client。
- 不建立 `QApplication`。
- 對戰 session 測試只驗證資料流與狀態轉移，不測 UDP codec。

### 6.6 `client-gui`

#### 責任

- 建立 PySide6 桌面 GUI。
- 呈現 main menu、connect screen、waiting screen、solo game、versus game、match result。
- 收集鍵盤輸入並交給 controller。
- 顯示 `Play with Computer` disabled。
- 不承載核心規則、不實作 network reliability。

#### Public Interface

- `MainWindow`
- `GameViewRenderer`
- screen widgets
- GUI entrypoint callback wiring

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| GUI-000 | 在 `pyproject.toml` 加入 PySide6 dependency | dependency config | `uv sync` 後可 `import PySide6` | 無 |
| GUI-001 | 建立 PySide6 app entrypoint 與 `MainWindow` | `client/app.py`, `gui/main_window.py` | 可啟動空主視窗 | GUI-000 |
| GUI-002 | 實作 main menu screen | `gui/screens.py` | 包含 Single Player、Connect、Play with Computer disabled、Exit | GUI-001 |
| GUI-003 | 實作 connect screen | `gui/screens.py` | 可輸入 host、port、player name，狀態由 view model 驅動 | GUI-002 |
| GUI-004 | 實作 waiting screen | `gui/screens.py` | 顯示 active / waiting、room full、rejected 訊息 | GUI-003 |
| GUI-005 | 決策並實作 game view renderer | `gui/game_view.py` | 可繪製 board、active piece、ghost、hold、next | D-GUI-001, CLIENT-RT-001 |
| GUI-006 | 實作 solo game screen | `gui/screens.py` | 顯示盤面、hold、next、score、lines、pause、restart | GUI-005, CLIENT-RT-004 |
| GUI-007 | 實作 versus game screen | `gui/screens.py` | 顯示自己盤面、對手摘要、incoming garbage、timer、KO、sent lines | GUI-005, CLIENT-RT-010 |
| GUI-008 | 實作 match result screen | `gui/screens.py` | 顯示 winner、KO、sent lines、下一場狀態 | CLIENT-RT-011 |
| GUI-009 | 實作 keyboard wiring | `gui/main_window.py` | key press/release 只更新 controller，不直接碰 engine | CTRL-005 |
| GUI-010 | 實作 GUI 與 runtime 的非阻塞事件橋接 | `gui/main_window.py` | fake runtime event 不阻塞 GUI loop | CLIENT-RT-002, CLIENT-RT-006 |
| GUI-011 | 建立 GUI smoke test | tests | headless Qt 環境可建立主要 screen | GUI-002 至 GUI-008 |

#### 獨立測試

- 使用 fake runtime 與 fake view model。
- 不驗證 core 規則。
- GUI smoke test 只確認 widget 建立、screen 切換與 callback wiring。

### 6.7 `net`

#### 責任

- 定義 UDP message schema、codec、session id、match id、sequence、ack、重送、去重。
- 提供 UDP client / server endpoint。
- 不實作配對、Tetris 規則、KO 規則或 GUI。

#### Public Interface

- `ProtocolMessage`
- `MessageCodec`
- `ReliableChannel`
- `UdpClient`
- `UdpServer`
- `NetworkEvent`

#### Message Groups

- Session：`ClientHello`、`ServerWelcome`、`JoinRejectedRoomFull`、`Heartbeat`、`DisconnectNotice`
- Queue / match：`QueueStatus`、`MatchStart`、`MatchSnapshot`、`MatchEnd`、`PlayerLeft`
- Reliable gameplay：`AttackReported`、`GarbageAssigned`、`KOReported`、`RespawnAssigned`、`ReliableAck`、`ReliableResendRequest`
- State summary：`ClientStateSummary`、`OpponentStateSummary`、`ClockSync`

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| NET-001 | 建立 protocol message dataclass | `net/protocol.py` | 所有 message group 有 typed schema | COMMON-002 |
| NET-002 | 決策 UDP wire encoding | codec fixture | 格式經使用者確認，不自行猜測 | D-NET-001 |
| NET-003 | 實作 `MessageCodec` | `net/protocol.py` | dataclass encode/decode round-trip | NET-001, NET-002 |
| NET-004 | 定義 network event facade | `net/protocol.py` | client/server 可用同一事件類型溝通 runtime | NET-003 |
| NET-005 | 實作 reliable event envelope | `net/reliability.py` | 包含 session、match、sender、event_seq、ack、sent_at | NET-001 |
| NET-006 | 實作去重與 ack 行為 | `net/reliability.py` | 重複 reliable event 只 ack 不重複套用 | NET-005 |
| NET-007 | 決策並實作重送與 timeout policy | `net/reliability.py` | fake clock 驗證重送間隔與 session timeout | D-NET-002, COMMON-005 |
| NET-008 | 實作 non-reliable snapshot / summary channel | `net/reliability.py` | 新 snapshot 覆蓋舊 snapshot，不要求 ack | NET-004 |
| NET-009 | 決策並實作 match snapshot 頻率欄位與 correction payload | `net/protocol.py` | payload 可被 client-runtime 消費 | D-NET-003 |
| NET-010 | 實作 `UdpClient` 非阻塞 endpoint | `net/udp_client.py` | socket 測試可連 fake UDP server | NET-003 |
| NET-011 | 實作 `UdpServer` 非阻塞 endpoint | `net/udp_server.py` | socket 測試可接 fake client datagram | NET-003 |
| NET-012 | 建立 UDP loss / duplicate 模擬測試工具 | tests fixture | reliability 測試可注入掉包與重複封包 | NET-006 |

#### 獨立測試

- protocol 與 reliability 使用 fake transport。
- UDP endpoint 測試只驗證 socket 層收發，不啟動 server match logic。

### 6.8 `server`

#### 責任

- headless server process。
- 管理 client session、heartbeat、timeout、重複加入。
- 管理 active players、waiting queue、room full。
- 管理 match lifecycle、timer、KO count、sent garbage、winner resolution。
- 轉發 reliable gameplay events 與 opponent summary。
- 不依賴 GUI，不模擬完整本地操作手感。

#### Public Interface

- `ServerApp`
- `SessionManager`
- `QueueManager`
- `MatchManager`
- `ReliableEventRouter`
- `BattleCoordinator` adapter

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| SERVER-001 | 建立 server package 與 headless entrypoint | `server/app.py` | `uv run ...` 可啟動並立即關閉 smoke command | COMMON-003 |
| SERVER-002 | 定義 `TransportPort` protocol | `server/app.py` | fake transport 可替代 UDP server | NET-004 |
| SERVER-003 | 實作 `SessionManager` | `server/sessions.py` | hello、welcome、heartbeat、timeout 測試 | NET-004, NET-007 |
| SERVER-004 | 實作重複加入處理 | `server/sessions.py` | 同 player / endpoint 重複 hello 行為符合確認規則 | SERVER-003 |
| SERVER-005 | 實作 `QueueManager` active / waiting 狀態 | `server/queue.py` | 第 1-2 名 active，第 3-7 名 waiting，第 8 名 room full | COMMON-003 |
| SERVER-006 | 實作 queue status message 產生 | `server/queue.py` | 狀態變更會產生 QueueStatus | SERVER-005, NET-001 |
| SERVER-007 | 實作 `MatchManager` match start | `server/matches.py` | active 達 2 人時產生 MatchStart，含 match id 與 config | SERVER-005 |
| SERVER-008 | 實作 server-owned match timer | `server/matches.py` | fake clock 到 120 秒會觸發 match end 流程 | COMMON-005, SERVER-007 |
| SERVER-009 | 實作 reliable gameplay event routing | `server/matches.py` | AttackReported / KOReported 轉給 BattleCoordinator | NET-006, BATTLE-012 |
| SERVER-010 | 實作 GarbageAssigned 下發 | `server/matches.py` | attack 事件產生 opponent reliable garbage event | BATTLE-007, SERVER-009 |
| SERVER-011 | 實作 KO count 與 respawn assignment | `server/matches.py` | KOReported 產生 KO count 更新與 RespawnAssigned | BATTLE-008, SERVER-009 |
| SERVER-012 | 實作 match end winner resolution | `server/matches.py` | 3 KO 提前結束與 timeout tie-breaker 測試 | BATTLE-010, SERVER-008 |
| SERVER-013 | 實作車輪戰下一局流程 | `server/queue.py`, `server/matches.py` | match 結束後輸家移出 active，waiting 第一名進入下一局 | SERVER-012 |
| SERVER-014 | 實作 player left / disconnect cleanup | `server/sessions.py`, `server/matches.py` | 中途離線不使 server 卡死 | SERVER-003, SERVER-007 |
| SERVER-015 | 實作 opponent summary relay | `server/matches.py` | ClientStateSummary 轉為 OpponentStateSummary | NET-008 |
| SERVER-016 | 串接真 `UdpServer` 到 `ServerApp` | `server/app.py` | 本機 fake UDP client 可 hello 並收到 welcome | NET-011, SERVER-003 |

#### 獨立測試

- 使用 fake transport 與 fake clock 測試 session、queue、match。
- 真 UDP 測試限制在 endpoint 層與一個 smoke integration。
- 不 import PySide6。

### 6.9 `packaging`

#### 責任

- 提供 Linux 可執行檔打包 automation。
- 提供 Windows 機器上的 step-by-step 打包與驗證文件。
- 保留 client GUI entrypoint 與 headless server entrypoint。
- 優先 `pyside6-deploy`，備援 PyInstaller。
- 不承載 runtime 邏輯。

#### Public Interface

- client executable entrypoint。
- server executable entrypoint。
- packaging config / spec。
- README 操作步驟。

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| PKG-001 | 定義 Python entrypoints | `pyproject.toml` | `uv run p2p-tetris-client`、`uv run p2p-tetris-server --help` 可執行 | GUI-001, SERVER-001 |
| PKG-002 | 定義 Linux 打包 automation 與 Windows 文件化打包邊界 | packaging note | 明確記錄：Linux 產出可玩檔案；Windows 需在 Windows 機器依文件打包，不做 Linux Docker cross-build exe | D-PKG-001 |
| PKG-003 | 建立 Linux `pyside6-deploy` 或等效打包設定 | `src/p2p_tetris/packaging/pyside6_deploy/` | Linux client 可產出可執行檔 | PKG-001, PKG-002 |
| PKG-004 | 建立 server 打包流程 | packaging config | server 可獨立啟動 | SERVER-016 |
| PKG-005 | 建立 PyInstaller fallback spec | `src/p2p_tetris/packaging/pyinstaller/` | fallback spec 能產出 client 或 server | PKG-001 |
| PKG-006 | 撰寫本機 server + 2 client 操作文件 | README 或 docs | 文件含 server、client、localhost 測試流程 | SERVER-016, GUI-007 |
| PKG-007 | 撰寫 Windows step-by-step 打包與驗證文件 | docs | 文件說明在 Windows 上安裝環境、同步依賴、執行打包、啟動 client/server、驗證本機雙 client | PKG-001, PKG-002 |

#### 獨立測試

- packaging 不測遊戲規則。
- 打包 smoke test 只驗證 executable 啟動與基本 screen / server help。

### 6.10 `tests`

#### 責任

- 提供跨模組 fixture、fake clock、fake transport、deterministic seed、action script。
- 覆蓋單元、整合、協定、server/client 測試。
- 執行品質檢查。

#### 最小任務

| 任務 ID | 任務 | 輸出 | 驗收方式 | 依賴 |
| --- | --- | --- | --- | --- |
| TEST-001 | 建立 pytest 目錄與 fixture 分層 | `tests/` | pytest 可收集空測試 | COMMON-001 |
| TEST-002 | 建立 deterministic action script fixture | `tests/fixtures/` | 可供 game-core 與 runtime 共用 | CTRL-003 |
| TEST-003 | 建立 SRS fixture 測試集 | fixture file | 覆蓋 I、O、JLSTZ 旋轉案例 | D-CORE-002 |
| TEST-004 | 建立 battle fixture 測試集 | fixture file | attack、garbage、KO、winner 規則可重播 | D-BATTLE-001 至 D-BATTLE-005 |
| TEST-005 | 建立 fake transport 與 network loss fixture | test helpers | 掉包、重複、重送測試可重現 | NET-012 |
| TEST-006 | 建立 server/client integration fixture | test helpers | 兩個 mock client 可進入 match | SERVER-016 |
| TEST-007 | 建立 GUI smoke test 設定 | test config | headless 環境可測 screen 建立 | GUI-011 |
| TEST-008 | 建立品質檢查命令文件化 | README 或 docs | `ruff`、`mypy`、`pytest` 命令清楚可執行 | pyproject |

## 7. 里程碑與任務順序

### M1：單人核心

目標：可用測試驅動單人 game-core，並具備最小 GUI 單人入口。

必要任務：

- COMMON-001 至 COMMON-005
- CORE-001 至 CORE-018
- CTRL-001 至 CTRL-005
- CLIENT-RT-001 至 CLIENT-RT-004
- GUI-000、GUI-001、GUI-002、GUI-005、GUI-006、GUI-009、GUI-010
- TEST-001 至 TEST-003

阻塞決策：無，D-CORE-001 至 D-CORE-004 與 D-GUI-001 已確認。

驗收：

- scripted controller 可完成 deterministic 單人回放。
- GUI 可啟動單人遊戲並顯示 board、hold、next、ghost、score、lines。
- `game-core` 測試不依賴 GUI。

### M2：對戰規則

目標：可用純事件 fixture 驗證 attack、garbage、KO、winner。

必要任務：

- BATTLE-001 至 BATTLE-012
- CORE-019
- TEST-004

阻塞決策：無，D-BATTLE-001 至 D-BATTLE-005 已確認。

驗收：

- ClearEvent fixture 可產生正確 attack。
- garbage 抵銷與延遲套用可重播。
- 3 KO、120 秒 timeout、tie-breaker 可測。

### M3：Server 與 UDP

目標：server 可接受 client、配對、可靠轉發事件。

必要任務：

- NET-001 至 NET-012
- SERVER-001 至 SERVER-016
- TEST-005、TEST-006

阻塞決策：無，D-NET-001 至 D-NET-003 已確認。

驗收：

- 2 active + 5 waiting 後第 8 名被拒絕。
- 兩個 mock client 可進入同一 match。
- reliable garbage event 在掉包後可重送，重複封包不重複套用。

### M4：雙人可玩版本

目標：串接 GUI、runtime、game-core、battle、net、server。

必要任務：

- CLIENT-RT-005 至 CLIENT-RT-011
- GUI-003、GUI-004、GUI-007、GUI-008
- SERVER-010 至 SERVER-016 的整合修正
- PKG-006 的本機操作流程草稿

驗收：

- 本機啟動 server + 2 client。
- 兩個 client 可輸入 localhost / IP 加入。
- 雙方可同時遊玩、互送 garbage、KO、respawn。
- 一局能結束並顯示勝負。

### M5：跨平台與打包

目標：Linux 可產出可玩的打包檔案；Windows 提供可在 Windows 機器重現的 step-by-step 打包文件。

必要任務：

- PKG-001 至 PKG-007
- TEST-008

阻塞決策：無，D-PKG-001 已確認。

驗收：

- Linux client executable 可啟動並可玩。
- Linux server executable 可啟動。
- 文件說明本機 server + 2 client 測試流程。
- Windows step-by-step 文件可指導使用者在 Windows 機器上打包並驗證 client/server。

## 8. 不可合併的完成條件

任何任務若符合以下情況，不視為完成：

- 需要 GUI 才能驗證 `game-core` 或 `battle-rules`。
- 需要真 UDP 才能驗證 server queue 或 match lifecycle。
- 以 hard-coded ad hoc dict 在業務邏輯中傳 protocol message。
- 對未決策規格填入未確認數值。
- controller 直接修改 engine internals。
- GUI 直接承載核心規則判定。
- server 需要知道玩家是人類、測試腳本或未來 RL agent。
- `ruff`、`mypy`、`pytest` 任一失敗且未標明原因。

## 9. MVP 完成檢查表

- 單人 GUI 可啟動並完成一局。
- `Play with Computer` 顯示為 disabled 或未啟用。
- game-core 支援 hold、next queue、ghost piece、hard drop、soft drop、SRS 或已確認等效 wall kick。
- server 可獨立啟動。
- 兩個 client 可連到本機 server 並配對。
- 對戰中雙方可互送傳統有洞 garbage。
- KO、respawn、match end、winner resolution 可正常運作。
- server 可處理等待隊列與車輪戰。
- 玩家離線或 timeout 不使 server 永久卡死。
- `PlayerAction`、`ActionSource`、snapshot、deterministic seed 可支援未來 RL 子項目。
- Linux 打包流程具備 automation；Windows 打包流程具備 step-by-step 文件。
- `uv run ruff check .` 通過。
- `uv run mypy .` 通過。
- `uv run pytest` 通過。
