# v101 P2P Garbage Debug Proposal

## 1. 文件目的

本文件是「連線對戰時送出 garbage 會導致問題」的第一輪靜態檢視紀錄。這一輪依使用者要求，只用 `grep` 閱讀 `src/*` 下的程式碼，不修改 `src`，先整理目前架構、可能問題點，以及修復前必須向使用者確認的問題。

目前結論是：最可疑的問題不在 `Board.apply_garbage()` 本身，而在 reliable gameplay message 的 client/server 職責沒有對齊。server 會把 `GarbageAssigned` 視為 reliable message 並追蹤重送，但 client 端原本沒有對 server reliable message 做 ack，也沒有去重；因此同一個 garbage assignment 可能被 server 每 0.1 秒重送，client 又每次都把它加入 pending garbage，導致垃圾重複套用或 KO 異常。

使用者後續確認的畫面症狀是：A 對 B 送 garbage 後，B 盤面變成純黑，沒有 active piece，不能移動，但程式沒有 crash。這符合「pending garbage 在畫面上沒有正確顯示，直到下一次 lock 後大量重送 garbage 一次套用，造成 B top-out / `_alive=False`，runtime 停止推進」的路徑。

本輪已完成修復並用測試確認：

- client 對 target 是自己的 `GarbageAssigned` / `RespawnAssigned` 回 `ReliableAck`。
- client 對 duplicate reliable assignment 只 ack，不再次套用。
- versus board view model 會顯示 session-level pending garbage。
- match result 畫面不再被後續 `QueueStatus` 自動切回 waiting。
- 結果畫面文字從 `Next match pending` 改為 `Match ended`，按鈕改為 `Back to Queue`。

## 2. 目前程式碼架構理解

### 2.1 `game_core`

責任：單機 Tetris 規則，不知道 match、網路或對手。

重要檔案：

- `src/p2p_tetris/game_core/engine.py`
- `src/p2p_tetris/game_core/board.py`
- `src/p2p_tetris/game_core/events.py`

相關行為：

- `GameEngine.step()` 推進本地遊戲，產生 `PieceLockedEvent`、`ClearEvent`、`TopOutEvent`。
- `GameEngine.apply_garbage()` 直接呼叫 `Board.apply_garbage()`，把垃圾行推進盤面。
- `Board.apply_garbage()` 會移除頂部 `injection.lines` 行，並在底部加入同數量 garbage row。
- garbage row 目前用 `PieceType.Z` 當填滿格的顯示值，洞的位置由 `GarbageInjection.hole` 決定。
- `GameEngine.snapshot()` 有 `pending_garbage_lines` 欄位，但目前 `GameEngine` 自己的 `_pending_garbage_lines` 沒看到被更新；對戰 pending garbage 主要由 `VersusGameSession` 管。

### 2.2 `battle`

責任：攻擊計算、garbage event 生成、garbage queue 與抵銷規則。

重要檔案：

- `src/p2p_tetris/battle/attack.py`
- `src/p2p_tetris/battle/garbage.py`
- `src/p2p_tetris/battle/match_rules.py`

相關行為：

- `AttackCalculator.calculate()` 把 `ClearEvent` 轉為攻擊行數。
- `GarbageGenerator.generate()` 用 source、target、seq 產生 deterministic hole。
- `GarbageQueue.cancel_with_attack()` 會用自己打出的 attack 抵銷 pending incoming garbage。
- `GarbageQueue.pop_ready_after_lock()` 支援延遲套用，不過 server 目前建立 queue 時沒有傳 garbage delay，等於立即 ready。
- `BattleCoordinator` 看起來是純規則 façade，但目前 server 預設沒有注入 battle coordinator，所以實際路徑多半走 `server/matches.py` 自己的 fallback logic。

### 2.3 `client`

責任：本地對戰 session、網路 runtime 與 GUI 無關的狀態橋接。

重要檔案：

- `src/p2p_tetris/client/network_session.py`
- `src/p2p_tetris/client/versus_session.py`
- `src/p2p_tetris/client/network.py`

相關行為：

- `ClientNetworkRuntime.poll()` 從 UDP client 收 server message，遇到 `GarbageAssigned`、`RespawnAssigned` 等 match message 就 forward 給 `VersusGameSession`。
- `VersusGameSession._report_attack()` 在本地清行後送 `AttackReported` 給 server。
- `VersusGameSession._handle_garbage_assigned()` 收到 target 是自己的 `GarbageAssigned` 時，先取消 pending garbage，再把 `message.lines` 加入 `_pending_garbage`。
- `VersusGameSession._handle_local_events()` 在本地 piece lock 後呼叫 `_apply_pending_garbage()`。
- `_apply_pending_garbage()` 會把所有 pending garbage 一次套用到 engine。
- client 目前沒有看到使用 `ReliableChannel`，也沒有看到收到 `GarbageAssigned` 後送 `ReliableAck`。
- client 目前也沒有看到依 `garbage_id`、`sender_id/event_seq` 或其他 key 對 `GarbageAssigned` 去重。

### 2.4 `server`

責任：session、queue、match、轉發 reliable gameplay message。

重要檔案：

- `src/p2p_tetris/server/app.py`
- `src/p2p_tetris/server/matches.py`
- `src/p2p_tetris/net/reliability.py`

相關行為：

- server 收到 client 的 `AttackReported` / `KOReported` 後，會呼叫 `ReliableChannel.mark_received()`，然後送 `ReliableAck` 給 sender。
- `MatchManager._handle_attack()` 會：
  - 用 attacker 自己的 `GarbageQueue` 抵銷 pending incoming garbage。
  - 如果有抵銷，產生 `GarbageAssigned(lines=0, canceled_lines=...)` 給 attacker。
  - 如果還有 outgoing attack，產生 `GarbageAssigned(lines=outgoing.lines, target_id=opponent)` 給對手。
  - 將送出的 lines 加到 `record.sent_lines`。
- `ServerApp._broadcast(outputs)` 會把 output 廣播給 queue/current match players。
- `ServerApp` 對每個 reliable output 呼叫 `self.reliability.track_outgoing(output, target_for_reliable(output))`。
- `ServerApp._expire_sessions()` 會呼叫 `self.reliability.due_resends()`，到期就重送給 `target_for_reliable(resend)`。
- `NetworkConfig.reliable_resend_seconds` 預設是 `0.1` 秒。

### 2.5 `net`

責任：protocol dataclass、JSON codec、reliable channel。

重要檔案：

- `src/p2p_tetris/net/protocol.py`
- `src/p2p_tetris/net/reliability.py`

相關行為：

- `ReliableGameplayMessage = AttackReported | GarbageAssigned | KOReported | RespawnAssigned`。
- `ReliableChannel.mark_received()` 可以對 incoming reliable message 去重並產生 ack。
- `ReliableChannel.track_outgoing()` 會追蹤尚未 ack 的 reliable message。
- `ReliableChannel.due_resends()` 會依 interval 回傳需要重送的 message。
- `target_for_reliable(GarbageAssigned)` 回傳 `message.target_id`。

## 3. 目前推測的 garbage 資料流

1. 玩家 A 清行。
2. A 的 `VersusGameSession._report_attack()` 送 `AttackReported` 到 server。
3. server `ServerApp._handle_reliable()` 對 `AttackReported` 做去重與 ack。
4. server `MatchManager._handle_attack()` 產生 `GarbageAssigned` 給玩家 B。
5. server `_broadcast()` 把 `GarbageAssigned` 送給所有相關玩家；A 會收到但因 target 不是自己而忽略，B 會處理。
6. server `track_outgoing()` 把這個 `GarbageAssigned` 記為等待 B ack 的 reliable message。
7. B 的 client 收到 `GarbageAssigned` 後，加入 `_pending_garbage`。
8. B 下一次 piece lock 後，`_apply_pending_garbage()` 把 garbage 套用到 board。
9. 但 B 沒有送 `ReliableAck`，server 會一直重送同一個 `GarbageAssigned`。
10. B 也沒有去重，所以每次重送都會再加一次 pending garbage。

## 4. 高疑似問題點

### 4.1 client 沒有 ack server reliable gameplay message

依 `net/reliability.py` 的設計，`GarbageAssigned`、`RespawnAssigned` 都屬於 reliable gameplay message。server 有 outgoing tracking 和 resend，但 client runtime 沒有對這些 server-to-client reliable message 回 ack。

可能症狀：

- 對手收到一波 garbage 後，短時間內 pending garbage 不斷增加。
- 只送 1 或 2 行 garbage，對方卻被塞多次。
- 一段時間後對手突然被大量 garbage KO。
- server 持續 resend，網路訊息越來越吵。

### 4.2 client 沒有去重 server reliable gameplay message

即使 ack 可能丟失，client 仍應避免同一個 reliable message 被套用多次。現在 `VersusGameSession._handle_garbage_assigned()` 每次看到同 match 且 target 是自己，就直接 `_cancel_pending_garbage()` 和 append 新 garbage，沒有檢查 `garbage_id` 或 `(sender_id, event_seq)` 是否已處理。

這會讓 UDP duplicate 或 server resend 直接變成遊戲狀態重複套用。

### 4.3 `GarbageAssigned` 被 broadcast 給所有玩家，但可靠追蹤只追 target

`ServerApp._broadcast()` 會把同一個 `GarbageAssigned` 傳給所有 queue/current match players；但 `track_outgoing()` 只以 `target_for_reliable(output)` 的 target 作為 recipient。非 target client 會忽略 message，通常不會造成盤面問題。

這不是最高疑似 bug，但會讓 wire traffic 比必要更多，也可能干擾未來 ack 設計：非 target 是否應 ack？目前看起來不應該，因為 reliable recipient 是 target。

### 4.4 server 對 outgoing reliable 的 sender/session 語意可能需要確認

`GarbageAssigned.session_id` 目前沿用原始 attacker 的 `attack.session_id`，`sender_id` 也是 attacker。server 是實際分派者，但 message 上看起來像 attacker 直接傳給 target。

這可能可以接受，因為 attack/gargabe 的 logical sender 是 attacker；但如果 client 端要產生 ack，需要確認 `ReliableAck.session_id` 應該填誰的 session。現有 `_ack_sender_for()` 會用 target 當 ack sender，但 `ReliableAck.session_id` 取自 message.session_id。若 `GarbageAssigned.session_id` 是 attacker session，B 回 ack 時會帶 A 的 session_id，server `mark_acked()` 目前正好用這個 key 找 pending message。

這個設計能工作，但語意不直覺，修復時要用測試固定，不要半途改成 target session 而破壞 pending key。

### 4.5 cancellation message 也可能被重複套用

server 抵銷 pending garbage 時會送 `GarbageAssigned(lines=0, canceled_lines=N)` 給 attacker。若這個 cancellation message 被重送，而 client 沒有去重，`_cancel_pending_garbage(N)` 會重複執行。

可能症狀：

- 玩家用清行抵銷 incoming garbage 後，pending garbage 被取消過頭。
- HUD 上 pending garbage 和實際套用不一致。

### 4.6 `GameEngine.snapshot().pending_garbage_lines` 目前不是對戰 pending 來源

`GameEngine` 裡有 `_pending_garbage_lines`，snapshot 也回傳它，但對戰 pending garbage 是 `VersusGameSession._pending_garbage` 自己管理。GUI 的 board renderer 會看 `BoardViewModel.pending_garbage_lines`，而 view model 是否用 session pending 還要後續追 `view_models.py` 確認。

這不一定是造成 garbage 套用錯誤的主因，但可能導致顯示與實際 pending 狀態不一致。

## 5. 需要向使用者確認的問題

修復前，我需要先確認你看到的「問題」是哪一類，避免修錯方向：

1. 你實際看到的症狀是什麼？例如：對手收到過多 garbage、自己被 garbage、遊戲 crash、兩邊不同步、pending 指示錯、KO 判定錯、還是其他現象？
2. 問題是否會在送出第一波 garbage 後約 0.1 秒開始變嚴重，或呈現每隔一小段時間重複增加的感覺？
3. 你測試時是同一台電腦開 server + 兩個 client，還是兩台電腦區網連線？
4. 問題是否只在「有 line clear 產生 attack」後發生？若只移動/落下但不清行，是否正常？
5. 你希望對戰 garbage 的套用規則是「收到後下一次 lock 全部套用」，還是希望有延遲、分批、或像 Tetris Battle 那樣有更明確的倒數/抵銷窗口？
6. 你希望 reliable gameplay 的最終模型是：server-to-client 的 `GarbageAssigned` / `RespawnAssigned` 必須可靠送達且 client ack，還是先接受不可靠但用 snapshot 校正？

## 6. 建議後續修復方向

若你確認症狀符合重送/重複套用，下一步建議修復方向如下：

1. 在 client 端新增 incoming reliable handling：
   - 對 `GarbageAssigned`、`RespawnAssigned` 這類 server-to-client reliable message 呼叫 `ReliableChannel.mark_received()` 或等價的小型去重/ack 邏輯。
   - 對 duplicate message 只送 ack，不再次 forward 給 `VersusGameSession` 套用。
2. 讓 client 對 server 發回 `ReliableAck`：
   - ack 的 key 必須能讓 server `ReliableChannel.mark_acked()` 移除 pending outgoing message。
   - 需要用測試固定 `session_id`、`sender_id`、`acked_sender_id`、`received_seq` 的預期。
3. 補測試：
   - server 送同一個 `GarbageAssigned` 兩次，client 只增加一次 pending garbage。
   - client 收到 `GarbageAssigned` 後會送 `ReliableAck`。
   - server 收到 ack 後 pending reliable count 歸零，不再 due resend。
   - cancellation `GarbageAssigned(lines=0, canceled_lines=N)` 重複送達時只取消一次。
4. 再檢查是否要把 `ServerApp._broadcast(outputs)` 改成針對 reliable gameplay 只送 target，避免非 target 收到不需要處理的 reliable message。

## 7. 暫不建議優先修改的地方

以下區域目前不像第一優先問題：

- `Board.apply_garbage()`：目前邏輯符合「底部加 garbage、上方被推高」的基本模型。
- `AttackCalculator`：攻擊行數表可能需要玩法校準，但不像會造成重複 garbage。
- `GarbageGenerator`：hole 生成 deterministic，且 server 傳給 client 的只有 `hole_column`；若問題是重複行數，生成器不是主因。
- `GameEngine.apply_garbage()`：top-out 判定可能需要玩法微調，但不解釋同一波 garbage 被多次套用。

## 8. 下一步

本輪已先修復最可疑的 reliable resend / duplicate apply 路徑。下一步建議用實際 GUI 流程重測：同機啟動 server + 兩個 client，讓 A 對 B 送 garbage，確認 B 不再黑畫面卡死，incoming garbage 指示會正常顯示，match end 後 result screen 不會自動跳回 waiting。

## 9. 本輪實作紀錄

已修改：

- `src/p2p_tetris/client/versus_session.py`
  - 新增 incoming reliable dedupe / ack。
  - 對非 target 的 `GarbageAssigned` / `RespawnAssigned` 不 ack、不套用，避免非 target broadcast 讓 server 誤以為 target 已收到。
  - duplicate reliable message 會回 ack，但不再 forward 到 garbage / respawn handler。
  - versus mode 的 `BoardViewModel.pending_garbage_lines` 改用 session-level `_pending_garbage`。
- `src/p2p_tetris/gui/main_window.py`
  - result screen 開啟時，忽略沒有 `view_model` 的 queue / ended connection update，避免結果畫面被 queue status 蓋掉。
- `src/p2p_tetris/gui/screens.py`
  - 結果畫面文案改成不預設暗示下一局等待。
- `tests/client/test_versus_session.py`
  - 補 duplicate garbage assignment 只套用一次、但仍 ack duplicate 的測試。
  - 補 duplicate cancellation 不會重複取消 pending garbage 的測試。
- `tests/gui/test_smoke.py`
  - 補 result screen 不會被 queue status 取代的測試。
- `tests/server/test_app.py`
  - 補 `GarbageAssigned` ack 會清掉 server resend tracking 的測試。

已驗證：

- `.venv/bin/python -m pytest`
- `.venv/bin/ruff check .`
- `.venv/bin/mypy .`

備註：目前 shell 找不到 `uv`，所以本輪使用既有 `.venv` 執行測試與靜態檢查。
