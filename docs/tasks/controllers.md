# controllers 模塊任務

## 責任

- 將不同 action source 轉成同一組 `PlayerAction`。
- 支援鍵盤 controller、scripted controller，並預留未來 RL policy controller。
- 不直接修改 game state、GUI 或網路狀態。

## Public Interface

- `ActionSource`
- `ActionBatch`
- `KeyboardController`
- `ScriptedController`

## 最小可執行任務

- [ ] CTRL-001: 定義 `ActionSource` protocol
  - 輸出：`controllers/base.py`
  - 驗收：runtime 可用 mock source 拉取 actions
  - 依賴：CORE-001

- [ ] CTRL-002: 定義 action batch 與 tick 對齊語意
  - 輸出：`controllers/base.py`
  - 驗收：同一 tick 可含多個離散 action 的測試
  - 依賴：CTRL-001

- [ ] CTRL-003: 實作 `ScriptedController`
  - 輸出：`controllers/scripted.py`
  - 驗收：deterministic action script 可驅動 game-core 測試
  - 依賴：CTRL-002

- [ ] CTRL-004: 定義鍵盤映射資料結構
  - 輸出：`controllers/keyboard.py`
  - 驗收：預設 key map 不依賴 PySide6 event 類別
  - 依賴：CTRL-002

- [ ] CTRL-005: 實作鍵盤狀態到 action 的轉換
  - 輸出：`controllers/keyboard.py`
  - 驗收：fake key event stream 驗證 action output
  - 依賴：CTRL-004、D-CORE-003

- [ ] CTRL-006: 預留 future RL controller adapter interface
  - 輸出：`controllers/base.py`
  - 驗收：只定義 protocol，不新增 RL dependency
  - 依賴：CTRL-001

## 獨立測試

- 用 fake key event 或 plain dataclass 表示按鍵。
- 不建立 PySide6 widget。
- scripted controller 可作為 `game-core` 與 `client-runtime` fixture。
