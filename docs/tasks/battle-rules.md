# battle-rules 模塊任務

## 責任

- 將 `ClearEvent` 轉成 attack pressure。
- 管理 incoming garbage 抵銷、延遲套用、有洞 garbage 生成。
- 管理 KO、respawn、match result 與 winner resolution。
- 不處理方塊碰撞、鍵盤輸入、UDP 封包或 GUI。

## Public Interface

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

## 最小可執行任務

- [ ] BATTLE-001: 建立 battle event dataclass
  - 輸出：`battle/events.py`
  - 驗收：事件可比較、可序列化、含 source player 與 seq 欄位
  - 依賴：COMMON-002

- [ ] BATTLE-002: 定義 attack table fixture
  - 輸出：fixture file
  - 驗收：fixture 經使用者確認，不自行猜測數值
  - 依賴：D-BATTLE-001、D-CORE-004

- [ ] BATTLE-003: 實作 `AttackCalculator`
  - 輸出：`attack.py`
  - 驗收：ClearEvent fixture 對應 AttackEvent lines
  - 依賴：BATTLE-001、BATTLE-002

- [ ] BATTLE-004: 定義有洞 garbage event 與 row model
  - 輸出：`garbage.py`
  - 驗收：資料模型未寫死到 bomb-incompatible
  - 依賴：BATTLE-001

- [ ] BATTLE-005: 決策並實作 garbage hole 策略
  - 輸出：`garbage.py`
  - 驗收：同 seed 產生相同 hole 序列
  - 依賴：D-BATTLE-003、BATTLE-004

- [ ] BATTLE-006: 決策並實作 garbage 抵銷規則
  - 輸出：`garbage.py`
  - 驗收：incoming 先抵銷或其他確認規則的 fixture
  - 依賴：D-BATTLE-002

- [ ] BATTLE-007: 決策並實作 delayed garbage queue
  - 輸出：`garbage.py`
  - 驗收：fake clock / tick 測試延遲與套用順序
  - 依賴：D-BATTLE-002、COMMON-005

- [ ] BATTLE-008: 決策並實作 KO 與 respawn 規則資料
  - 輸出：`match_rules.py`
  - 驗收：top-out 產生 KO，respawn event 符合確認規則
  - 依賴：D-BATTLE-004

- [ ] BATTLE-009: 實作 sent garbage lines 與 KO counter
  - 輸出：`scoring.py`
  - 驗收：match state counter 單元測試
  - 依賴：BATTLE-003、BATTLE-008

- [ ] BATTLE-010: 實作 winner resolver
  - 輸出：`match_rules.py`
  - 驗收：KO 數、sent lines、盤面高度優先順序 fixture
  - 依賴：BATTLE-009

- [ ] BATTLE-011: 決策並實作完全平手處理
  - 輸出：`match_rules.py`
  - 驗收：draw 或額外 tie-breaker fixture
  - 依賴：D-BATTLE-005、BATTLE-010

- [ ] BATTLE-012: 實作 `BattleCoordinator` 純邏輯 facade
  - 輸出：`match_rules.py`
  - 驗收：不啟動 server 即可模擬一場 match-level 事件序列
  - 依賴：BATTLE-003 至 BATTLE-011

## 獨立測試

- 以 `ClearEvent`、`TopOutEvent`、盤面高度摘要作為輸入 fixture。
- 不建立 `GameEngine`。
- 不使用 socket 或 GUI。
