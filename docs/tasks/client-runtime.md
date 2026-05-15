# client-runtime 模塊任務

## 責任

- 管理 client 端單人與對戰 session。
- 維持 fixed tick game loop。
- 將 controller actions 套用到 local game engine。
- 將 snapshot 轉成 view model。
- 對戰模式中橋接 local game、battle local events 與 net-client。
- 不直接依賴 PySide6 widget。

## Public Interface

- `LocalGameSession`
- `VersusGameSession`
- `ClientRuntimeEvent`
- `GameViewModel`
- `ConnectionState`

## 最小可執行任務

- [ ] CLIENT-RT-001: 建立 view model dataclass
  - 輸出：`client/view_models.py`
  - 驗收：可由 snapshot 建立 board、hold、next、HUD view model
  - 依賴：CORE-017

- [ ] CLIENT-RT-002: 實作 `LocalGameSession.reset/start/pause/resume/restart`
  - 輸出：`client/local_session.py`
  - 驗收：不啟動 GUI 即可跑單人 session 狀態機
  - 依賴：CORE-018、CTRL-001

- [ ] CLIENT-RT-003: 實作 local fixed tick 推進
  - 輸出：`client/local_session.py`
  - 驗收：fake clock 推進 N tick，snapshot deterministic
  - 依賴：CLIENT-RT-002、COMMON-005

- [ ] CLIENT-RT-004: 實作單人 view model 更新
  - 輸出：`client/local_session.py`
  - 驗收：action sequence 後 view model 與 snapshot 一致
  - 依賴：CLIENT-RT-001、CLIENT-RT-003

- [ ] CLIENT-RT-005: 定義 `NetClientPort` protocol
  - 輸出：`client/versus_session.py`
  - 驗收：fake net client 可替代真 UDP
  - 依賴：NET-001

- [ ] CLIENT-RT-006: 實作 `VersusGameSession` match start 初始化
  - 輸出：`client/versus_session.py`
  - 驗收：使用 server match config / seed 初始化本地 game
  - 依賴：CLIENT-RT-003、NET-004

- [ ] CLIENT-RT-007: 實作本地 attack / top-out event 上報流程
  - 輸出：`client/versus_session.py`
  - 驗收：fake net client 收到 AttackReported / KOReported
  - 依賴：BATTLE-003、CLIENT-RT-006

- [ ] CLIENT-RT-008: 實作 reliable garbage / KO / respawn 事件套用
  - 輸出：`client/versus_session.py`
  - 驗收：fake server event 會更新 pending garbage，並把 `GarbageEvent` 轉成 `GarbageInjection` 後交給 game-core
  - 依賴：BATTLE-007、BATTLE-008、CORE-019

- [ ] CLIENT-RT-009: 決策並實作 snapshot correction hook
  - 輸出：`client/versus_session.py`
  - 驗收：correction fixture 驗證可執行，不永久卡死
  - 依賴：D-NET-003、NET-009

- [ ] CLIENT-RT-010: 實作 opponent summary view model
  - 輸出：`client/versus_session.py`
  - 驗收：fake opponent summary 更新 GUI 用資料
  - 依賴：NET-004

- [ ] CLIENT-RT-011: 實作 match end 與 result view model
  - 輸出：`client/versus_session.py`
  - 驗收：fake MatchEnd 產生 result screen 所需資料
  - 依賴：BATTLE-010

## 獨立測試

- 使用 `ScriptedController` 與 fake net client。
- 不建立 `QApplication`。
- 對戰 session 測試只驗證資料流與狀態轉移，不測 UDP codec。
