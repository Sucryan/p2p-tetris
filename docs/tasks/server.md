# server 模塊任務

## 責任

- headless server process。
- 管理 client session、heartbeat、timeout、重複加入。
- 管理 active players、waiting queue、room full。
- 管理 match lifecycle、timer、KO count、sent garbage、winner resolution。
- 轉發 reliable gameplay events 與 opponent summary。
- 不依賴 GUI，不模擬完整本地操作手感。

## Public Interface

- `ServerApp`
- `SessionManager`
- `QueueManager`
- `MatchManager`
- `ReliableEventRouter`
- `BattleCoordinator` adapter

## 最小可執行任務

- [ ] SERVER-001: 建立 server package 與 headless entrypoint
  - 輸出：`server/app.py`
  - 驗收：`uv run ...` 可啟動並立即關閉 smoke command
  - 依賴：COMMON-003

- [ ] SERVER-002: 定義 `TransportPort` protocol
  - 輸出：`server/app.py`
  - 驗收：fake transport 可替代 UDP server
  - 依賴：NET-004

- [ ] SERVER-003: 實作 `SessionManager`
  - 輸出：`server/sessions.py`
  - 驗收：hello、welcome、heartbeat、timeout 測試
  - 依賴：NET-004、NET-007

- [ ] SERVER-004: 實作重複加入處理
  - 輸出：`server/sessions.py`
  - 驗收：同 player / endpoint 重複 hello 行為符合確認規則
  - 依賴：SERVER-003

- [ ] SERVER-005: 實作 `QueueManager` active / waiting 狀態
  - 輸出：`server/queue.py`
  - 驗收：第 1-2 名 active，第 3-7 名 waiting，第 8 名 room full
  - 依賴：COMMON-003

- [ ] SERVER-006: 實作 queue status message 產生
  - 輸出：`server/queue.py`
  - 驗收：狀態變更會產生 QueueStatus
  - 依賴：SERVER-005、NET-001

- [ ] SERVER-007: 實作 `MatchManager` match start
  - 輸出：`server/matches.py`
  - 驗收：active 達 2 人時產生 MatchStart，含 match id 與 config
  - 依賴：SERVER-005

- [ ] SERVER-008: 實作 server-owned match timer
  - 輸出：`server/matches.py`
  - 驗收：fake clock 到 120 秒會觸發 match end 流程
  - 依賴：COMMON-005、SERVER-007

- [ ] SERVER-009: 實作 reliable gameplay event routing
  - 輸出：`server/matches.py`
  - 驗收：AttackReported / KOReported 轉給 BattleCoordinator
  - 依賴：NET-006、BATTLE-012

- [ ] SERVER-010: 實作 GarbageAssigned 下發
  - 輸出：`server/matches.py`
  - 驗收：attack 事件產生 opponent reliable garbage event
  - 依賴：BATTLE-007、SERVER-009

- [ ] SERVER-011: 實作 KO count 與 respawn assignment
  - 輸出：`server/matches.py`
  - 驗收：KOReported 產生 KO count 更新與 RespawnAssigned
  - 依賴：BATTLE-008、SERVER-009

- [ ] SERVER-012: 實作 match end winner resolution
  - 輸出：`server/matches.py`
  - 驗收：3 KO 提前結束與 timeout tie-breaker 測試
  - 依賴：BATTLE-010、SERVER-008

- [ ] SERVER-013: 實作車輪戰下一局流程
  - 輸出：`server/queue.py`、`server/matches.py`
  - 驗收：match 結束後輸家移出 active，waiting 第一名進入下一局
  - 依賴：SERVER-012

- [ ] SERVER-014: 實作 player left / disconnect cleanup
  - 輸出：`server/sessions.py`、`server/matches.py`
  - 驗收：中途離線不使 server 卡死
  - 依賴：SERVER-003、SERVER-007

- [ ] SERVER-015: 實作 opponent summary relay
  - 輸出：`server/matches.py`
  - 驗收：ClientStateSummary 轉為 OpponentStateSummary
  - 依賴：NET-008

- [ ] SERVER-016: 串接真 `UdpServer` 到 `ServerApp`
  - 輸出：`server/app.py`
  - 驗收：本機 fake UDP client 可 hello 並收到 welcome
  - 依賴：NET-011、SERVER-003

## 獨立測試

- 使用 fake transport 與 fake clock 測試 session、queue、match。
- 真 UDP 測試限制在 endpoint 層與一個 smoke integration。
- 不 import PySide6。
