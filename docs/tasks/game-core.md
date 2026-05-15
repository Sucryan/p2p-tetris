# game-core 模塊任務

## 責任

- 維護單一玩家盤面、方塊、碰撞、旋轉、生成、hold、next queue、ghost piece、gravity、lock、line clear、combo、B2B、top-out。
- 提供 deterministic `GameEngine`，可由 GUI 以外的 controller 驅動。
- 輸出 snapshot 與規則事件，不直接處理 KO、match timer、server 配對或 UDP。

## Public Interface

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

## 最小可執行任務

- [ ] CORE-001: 建立 `game_core` package 與 `PlayerAction` enum
  - 輸出：`actions.py`
  - 驗收：enum 包含 MVP action，系統操作不在 enum 內
  - 依賴：COMMON-001

- [ ] CORE-002: 定義 tetromino 類型與旋轉狀態資料
  - 輸出：`pieces.py`
  - 驗收：每種 piece 有 4 個 orientation fixture
  - 依賴：CORE-001

- [ ] CORE-003: 實作 `Board` 與座標邊界檢查
  - 輸出：`board.py`
  - 驗收：10x20 可見區與 hidden buffer 行為由 fixture 驗證
  - 依賴：CORE-002、D-CORE-001

- [ ] CORE-004: 實作 collision 與 placement 檢查
  - 輸出：`board.py`
  - 驗收：撞牆、撞方塊、hidden row 測試
  - 依賴：CORE-003

- [ ] CORE-005: 實作 7-bag randomizer
  - 輸出：`randomizer.py`
  - 驗收：deterministic seed 產生可重現序列，每 7 顆包含全套 piece
  - 依賴：CORE-002

- [ ] CORE-006: 定義 SRS kick table fixture
  - 輸出：fixture file
  - 驗收：fixture 經使用者確認，不由實作猜測
  - 依賴：D-CORE-002

- [ ] CORE-007: 實作 rotation 與 wall kick
  - 輸出：`rotation.py`
  - 驗收：I、O、JLSTZ 的成功與失敗案例 fixture
  - 依賴：CORE-004、CORE-006

- [ ] CORE-008: 實作 active piece spawn 與 next queue
  - 輸出：`engine.py`
  - 驗收：reset 後 active piece、next queue 長度可測
  - 依賴：CORE-005、D-CORE-001

- [ ] CORE-009: 實作水平移動、soft drop、hard drop
  - 輸出：`engine.py`
  - 驗收：action sequence fixture 驗證 final board
  - 依賴：CORE-008

- [ ] CORE-010: 實作 hold 規則
  - 輸出：`engine.py`
  - 驗收：每顆落鎖前只能 hold 一次、swap 行為可測
  - 依賴：CORE-008

- [ ] CORE-011: 實作 ghost piece 計算
  - 輸出：`snapshots.py`
  - 驗收：ghost 不改變 board，位置符合 hard drop landing
  - 依賴：CORE-009

- [ ] CORE-012: 決策並實作 gravity、lock delay、DAS / ARR 所需 engine hooks
  - 輸出：`engine.py`
  - 驗收：fake clock / tick fixture 驗證 lock timing
  - 依賴：D-CORE-003

- [ ] CORE-013: 實作 line clear
  - 輸出：`board.py`、`engine.py`
  - 驗收：1-4 行消除與 board compact fixture
  - 依賴：CORE-009

- [ ] CORE-014: 實作 combo 與 B2B 狀態追蹤
  - 輸出：`engine.py`
  - 驗收：連續消行、不消行中斷、B2B 延續測試
  - 依賴：CORE-013

- [ ] CORE-015: 決策並實作 T-spin 偵測
  - 輸出：`engine.py`
  - 驗收：T-spin / non T-spin fixture
  - 依賴：D-CORE-004、CORE-007

- [ ] CORE-016: 實作 top-out 判定
  - 輸出：`engine.py`
  - 驗收：spawn blocked、lock above visible area 的 fixture
  - 依賴：CORE-008、D-CORE-001

- [ ] CORE-017: 實作 `GameStateSnapshot`
  - 輸出：`snapshots.py`
  - 驗收：snapshot immutable，包含 GUI/RL 所需欄位，不暴露 seed
  - 依賴：CORE-011、CORE-014、CORE-016

- [ ] CORE-018: 實作 `GameEngine.reset(seed, config)` 與 `step(actions, ticks)`
  - 輸出：`engine.py`
  - 驗收：同 seed 同 action sequence 產生相同 snapshot
  - 依賴：CORE-017

- [ ] CORE-019: 實作 `apply_garbage(GarbageInjection)` 的核心盤面套用入口
  - 輸出：`engine.py`
  - 驗收：傳入 core-local garbage payload 後 board 變化可測
  - 依賴：CORE-013

## 獨立測試

- 所有測試用 deterministic seed 與 action sequence。
- 不 import PySide6、`net`、`server`。
- `apply_garbage()` 測試只使用 `game-core` 自己定義的 `GarbageInjection`，不啟動 match manager。
