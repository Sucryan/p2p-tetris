# common 模塊任務

## 責任

- 定義共用設定、ID、fake clock-friendly time provider。
- 提供跨模塊共享的 immutable value object。
- 不包含遊戲規則、網路 IO 或 GUI 狀態。

## Public Interface

- `GameConfig`
- `MatchConfig`
- `NetworkConfig`
- `PlayerId`
- `SessionId`
- `MatchId`
- `MonotonicClock` protocol

## 最小可執行任務

- [ ] COMMON-001: 建立 `src/p2p_tetris/common/` package 與 public exports
  - 輸出：package skeleton
  - 驗收：`python -m compileall src`
  - 依賴：無

- [ ] COMMON-002: 定義 strongly typed ID value objects
  - 輸出：`ids.py`
  - 驗收：ID 不可與 raw string / int 隨意混用的型別測試
  - 依賴：COMMON-001

- [ ] COMMON-003: 定義 config dataclass 與已固定預設值
  - 輸出：`config.py`
  - 驗收：config 單元測試覆蓋 10x20、120 秒、3 KO、2 active、5 waiting
  - 依賴：COMMON-001

- [ ] COMMON-004: 為未決設定加入 required field 或明確 TODO gate
  - 輸出：config tests
  - 驗收：未決欄位測試不可默默落入猜測預設
  - 依賴：COMMON-003、對應 `D-*`

- [ ] COMMON-005: 定義 injectable clock protocol 與 fake clock fixture
  - 輸出：`time.py`、test fixture
  - 驗收：fake clock 可手動推進並被 timeout 測試使用
  - 依賴：COMMON-001

## 獨立測試

- 只使用標準函式庫與 pytest。
- 不 import `game_core`、`net`、`server` 或 PySide6。
