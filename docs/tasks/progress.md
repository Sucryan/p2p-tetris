# P2P Tetris 任務總進度

## 模塊完成狀態

- [x] `common`：共用設定、ID 與時間接口完成，獨立測試通過。
- [x] `game-core`：單人核心規則完成，snapshot 與 deterministic engine 可測。
- [x] `battle-rules`：attack、garbage、KO、respawn、winner resolution 純邏輯完成。
- [x] `controllers`：keyboard、scripted 與 future RL action source 抽象完成。
- [x] `client-runtime`：單人與對戰 session orchestration、view model 與 fake net 串接完成。
- [x] `client-gui`：PySide6 GUI、screen flow、game renderer 與 runtime wiring 完成。
- [x] `net`：UDP protocol、codec、reliability、endpoint 與 loss/duplicate fixture 完成。
- [x] `server`：session、queue、match lifecycle、車輪戰與 UDP 串接完成。
- [x] `packaging`：entrypoints、Linux 打包 automation、Windows 打包文件與本機操作文件完成。
- [x] `tests`：共用 fixture、整合測試、GUI smoke test 與品質檢查命令完成。

## 里程碑進度

- [x] M1：單人核心
  - 必要模塊：`common`、`game-core`、`controllers`、`client-runtime`、`client-gui`、`tests`
  - 完成條件：scripted controller 可 deterministic 回放；GUI 可啟動單人遊戲並顯示 board、hold、next、ghost、score、lines。

- [x] M2：對戰規則
  - 必要模塊：`battle-rules`、`game-core`、`tests`
  - 完成條件：ClearEvent 可產生 attack；garbage 抵銷與延遲套用可重播；3 KO、120 秒 timeout、tie-breaker 可測。

- [x] M3：Server 與 UDP
  - 必要模塊：`net`、`server`、`tests`
  - 完成條件：2 active + 5 waiting 後第 8 名被拒絕；兩個 mock client 可進入同一 match；可靠事件在掉包後可重送且重複封包不重複套用。

- [x] M4：雙人可玩版本
  - 必要模塊：`client-runtime`、`client-gui`、`server`、`packaging`
  - 完成條件：本機啟動 server + 2 client；兩個 client 可加入、互送 garbage、KO、respawn，並顯示勝負。

- [x] M5：跨平台與打包
  - 必要模塊：`packaging`、`tests`
  - 完成條件：Linux client/server executable 可啟動；Windows step-by-step 文件可指導使用者在 Windows 上打包並驗證。

## 任務文件索引

- [common.md](common.md)
- [game-core.md](game-core.md)
- [battle-rules.md](battle-rules.md)
- [controllers.md](controllers.md)
- [client-runtime.md](client-runtime.md)
- [client-gui.md](client-gui.md)
- [net.md](net.md)
- [server.md](server.md)
- [packaging.md](packaging.md)
- [tests.md](tests.md)

## 不可標記完成的情況

- 需要 GUI 才能驗證 `game-core` 或 `battle-rules`。
- 需要真 UDP 才能驗證 server queue 或 match lifecycle。
- 以 hard-coded ad hoc dict 在業務邏輯中傳 protocol message。
- 對未決策規格填入未確認數值。
- controller 直接修改 engine internals。
- GUI 直接承載核心規則判定。
- server 需要知道玩家是人類、測試腳本或未來 RL agent。
- `ruff`、`mypy`、`pytest` 任一失敗且未標明原因。

## MVP 完成檢查表

- [x] 單人 GUI 可啟動並完成一局。
- [x] `Play with Computer` 顯示為 disabled 或未啟用。
- [x] game-core 支援 hold、next queue、ghost piece、hard drop、soft drop、SRS 或已確認等效 wall kick。
- [x] server 可獨立啟動。
- [x] 兩個 client 可連到本機 server 並配對。
- [x] 對戰中雙方可互送傳統有洞 garbage。
- [x] KO、respawn、match end、winner resolution 可正常運作。
- [x] server 可處理等待隊列與車輪戰。
- [x] 玩家離線或 timeout 不使 server 永久卡死。
- [x] `PlayerAction`、`ActionSource`、snapshot、deterministic seed 可支援未來 RL 子項目。
- [x] Linux 打包流程具備 automation；Windows 打包流程具備 step-by-step 文件。
- [x] `uv run ruff check .` 通過。
- [x] `uv run mypy .` 通過。
- [x] `uv run pytest` 通過。
