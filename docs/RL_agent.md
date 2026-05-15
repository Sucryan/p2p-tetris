# RL Agent 子項目需求與初步設計

## 1. 文件目的

本文件描述 `p2p-tetris` 後續 RL agent 子項目的需求與初步設計。此子項目目標是訓練一個可由 CNN policy 控制的電腦玩家，使它能透過與真人玩家相同的 action space 操作遊戲，並在未來支援 `Play with Computer`。

此子項目不屬於主專案 MVP。主專案 MVP 只需要預留接口，並在 GUI 中顯示未啟用的 `Play with Computer` 入口。實際訓練、模型推論、AI 對戰與相關依賴可以在獨立 branch 或後續任務中完成。

本文件需與 `docs/proposal.md` 一起閱讀。

## 2. 主要目標

- 使用 Gymnasium-style API 建立 RL 環境。
- 使用 Stable-Baselines3 作為訓練框架。
- agent 透過 CNN 觀察遊戲狀態。
- agent 的 action space 必須與真人玩家相同。
- 不允許提供高階 placement action，例如直接指定方塊落點、旋轉狀態或最佳位置。
- 初期訓練從單人無垃圾壓力環境開始。
- 後續可加入隨機 garbage wrapper，讓 agent 在受到壓力的環境中 fine-tune。
- 最終 agent 可作為 client controller，透過一般 client 接口與 server 互動。
- 最終應能支援人類 vs AI。
- 架構需預留 AI vs AI，也就是啟動兩個 agent-controlled client 連到同一個 server 對戰。

## 3. 非目標

- 不納入主專案 MVP。
- 不要求在第一版訓練中達到人類高手程度。
- 不要求 MARL。
- 不要求 agent 觀察對手盤面。
- 不要求 self-play 訓練流程。
- 不要求訓練監控 dashboard。
- 不要求 distributed training。
- 不要求將 SB3、PyTorch、Gymnasium 等 RL 依賴塞進主遊戲的必要安裝路徑。

## 4. AI vs AI 定義

本文件中的 AI vs AI 僅表示「兩個 client 都由 agent controller 送出 action，並連到同一個 server 進行一般對戰」。

AI vs AI 不代表：

- 必須支援 MARL。
- 必須支援自我對戰訓練。
- 必須讓 agent 觀察對方完整狀態。
- 必須為 server 設計 AI 專用協定。

因此主專案要保留的是 client controller 接口，而不是在 server 中加入 AI 特例。

## 5. Observation 需求

### 5.1 觀察範圍

agent 只觀察自己 client 可見的狀態，不觀察對手盤面。此限制是為了避免一開始就把問題變成 MARL 或完整對戰狀態建模。

允許 observation 包含：

- 自己的 board。
- 目前 active piece。
- ghost piece。
- hold piece。
- next queue。
- 自己 pending garbage 或壓力提示。
- 單人或訓練環境中的剩餘時間、步數、分數等自身資訊。

不允許 observation 包含：

- 對手完整 board。
- 對手 hold。
- 對手 next queue。
- 對手內部隨機種子。
- server 或 battle-rules 中真人玩家看不到的隱藏資訊。

### 5.2 CNN-friendly 格式

初步設計使用固定大小 tensor 作為 observation，形式接近：

```text
Box(shape=(channels, height, width), dtype=float32)
```

初始方向：

- `height` 對應遊戲盤面高度，至少包含 20 個可見 rows。
- `width` 對應 10 格 board width。
- `channels` 用來分別表示 locked blocks、active piece、ghost piece、garbage pressure 或其他自己可見資訊。

hold、next queue、計時器等非盤面資訊有兩種可行方案，後續設計階段決定：

- 將它們編碼成額外 channels。
- 將它們作為 dict observation 的額外 vector；若使用 SB3 CNN policy，需確認 policy 架構與 wrapper 支援方式。

MVP 主專案不需要實作 observation tensor，但 game-core 必須保留足夠的狀態讀取接口。

## 6. Action Space 需求

agent action space 必須與真人玩家相同。初步 action set：

- `NO_OP`
- `MOVE_LEFT`
- `MOVE_RIGHT`
- `SOFT_DROP`
- `HARD_DROP`
- `ROTATE_CW`
- `ROTATE_CCW`
- `HOLD`

若主遊戲後續新增其他真人可用 action，例如 pause、restart、rotate 180，需分清楚「遊戲內 action」與「系統控制 action」。RL agent 的 action space 只應包含正式對局中真人可以用來控制方塊的 action。

初步設計使用：

```text
Discrete(n_actions)
```

禁止：

- 直接輸出落點。
- 直接輸出旋轉後最終座標。
- 直接呼叫放置函式。
- 讀取 game-core 內部搜尋結果後跳過正常玩家輸入流程。

## 7. Gymnasium-style 環境

### 7.1 API 形狀

RL 環境應符合 Gymnasium-style：

```python
obs, info = env.reset(seed=seed)
obs, reward, terminated, truncated, info = env.step(action)
```

需求：

- `reset()` 必須支援 seed，讓訓練與測試可重現。
- `step(action)` 必須套用一個與真人玩家同義的 action。
- `NO_OP` 必須能推進遊戲時間或 gravity tick。
- `terminated` 用於 top-out 或明確遊戲結束。
- `truncated` 用於訓練 episode 長度限制或限時模式。
- `info` 可提供 debug 指標，例如消行數、combo、board height、holes、garbage received。

### 7.2 時間與 tick

初步設計採用固定 simulation tick。每次 `step(action)` 執行：

- 套用一次 action。
- 推進固定長度的遊戲 tick。
- 更新 gravity、lock delay、line clear、garbage 等狀態。

若後續訓練效率不足，可在 wrapper 中加入 frame skip 或 action repeat，但不應改變底層 game-core 的規則正確性。

## 8. 訓練階段

### Phase 1: 單人無垃圾壓力

目標是讓 agent 學會基本存活、消行與避免 top-out。

環境特性：

- 不加入對手。
- 不加入垃圾行。
- 使用標準方塊生成與單人規則。
- episode 結束條件為 top-out 或達到最大步數。

### Phase 2: 隨機垃圾壓力 fine-tune

目標是讓 agent 適應對戰中的堆高壓力，但仍避免進入 MARL。

環境特性：

- 使用 wrapper 隨機產生 garbage。
- garbage 強度、頻率、洞位置策略可配置。
- agent 仍只觀察自己的狀態。
- 不需要真實對手 client。

### Phase 3: 推論整合

目標是讓訓練後的 policy 控制 client。

需求：

- agent controller 讀取 client view 或 game-core observation。
- agent controller 輸出與真人相同的 action。
- server 將 agent-controlled client 視為一般 client。
- 可以進行人類 vs AI。
- 可以啟動兩個 agent-controlled client 進行 AI vs AI 測試。

## 9. Reward 初步方向

Reward 會大幅影響訓練結果，最終數值需在設計與實驗階段調整。初始方向：

- 存活小獎勵。
- 消行獎勵。
- 多行消除給更高獎勵。
- combo 或 back-to-back 可給額外獎勵。
- top-out 給大懲罰。
- 過高堆疊、holes、surface bumpiness 可作為 shaping 懲罰。
- 在 garbage wrapper 中，成功清除壓力或避免 top-out 可給額外獎勵。

不應在 reward 中加入 agent 無法透過 observation 合理推斷的隱藏資訊。

## 10. 主專案需預留的接口

主專案 MVP 不需要實作 RL 訓練，但需要避免阻礙後續開發。主專案需預留：

- `PlayerAction` 或等效 action enum。
- 不依賴 GUI 的 game-core step/reset 能力。
- 可由測試或 agent 讀取的 game state snapshot。
- 可重現的 random seed 控制。
- controller 抽象，讓鍵盤與 agent 都能成為 action source。
- client 不應假設 action 一定來自鍵盤事件。
- server 不應假設玩家一定是人類。
- battle-rules 不應依賴 GUI render 狀態。

後續可新增的 component：

- `rl-env`: Gymnasium-style 環境。
- `rl-wrappers`: observation、reward、random garbage、time limit 等 wrappers。
- `rl-train`: SB3 訓練入口。
- `rl-eval`: 評估與 smoke test。
- `agent-controller`: 載入訓練後 model，輸出 player action。

## 11. 依賴與封裝

RL 子項目預期使用：

- Gymnasium-style API。
- Stable-Baselines3。
- CNN policy。

RL 相關依賴應盡量獨立於主遊戲執行依賴。建議後續在設計階段評估：

- 是否使用 uv dependency group，例如 `rl`。
- 是否讓主遊戲可在未安裝 RL 依賴時正常執行。
- 是否將 `Play with Computer` 啟用條件綁定為「有可用模型且已安裝推論依賴」。
- SB3、Gymnasium、PyTorch 與 Python 3.13、Linux、Windows 的相容性。

## 12. 測試需求

RL 子項目至少需要：

- environment reset/step API 測試。
- observation shape 與 dtype 測試。
- action mapping 測試，確認 agent action 與真人 action 語意一致。
- deterministic seed 測試。
- top-out、line clear、garbage wrapper 測試。
- reward wrapper 測試。
- agent controller smoke test。
- 低步數 SB3 訓練 smoke test，可作為非必跑或慢速測試。

主專案需要：

- controller 抽象測試。
- game-core 不依賴 GUI 的測試。
- client 可接受非鍵盤 action source 的測試。

## 13. 驗收標準

此子項目完成時，應滿足：

- 可以建立 Gymnasium-style Tetris 環境。
- 可以用 SB3 啟動訓練流程。
- observation 由 CNN-friendly tensor 或明確 wrapper 提供。
- action space 與真人遊戲 action 一致。
- agent 不使用高階 placement action。
- 訓練後 policy 可以被 agent controller 載入。
- agent controller 可以控制 client。
- 人類可以透過 `Play with Computer` 與 agent 對打。
- 可以啟動兩個 agent-controlled client 連到 server 做 AI vs AI 測試。

## 14. 風險與待確認事項

- SB3、Gymnasium、PyTorch 與 Python 3.13 的相容性需實測。
- CNN observation 若只含 board，可能不足以學好 hold、next queue 與長期規劃；是否加入自己可見的 next/hold 編碼需實驗確認。
- action space 與真人一致會使學習比 high-level placement action 困難，但這是本子項目的明確需求。
- reward shaping 可能導致 agent 學到非預期策略，需透過評估場景檢查。
- 若 game-core 未提供 deterministic reset/step，訓練與測試會很難穩定。
- 若 GUI、network、game-core 過度耦合，agent controller 會難以接入。
- 即時對戰推論需要控制 action rate，避免 policy 輸出頻率與遊戲 tick 不一致。

## 15. 待設計決策

- observation 最終 channel 定義。
- hold 與 next queue 的編碼方式。
- 初始 reward 權重。
- SB3 演算法選擇。
- frame skip 或 action repeat 是否啟用。
- random garbage wrapper 的壓力分佈。
- model 儲存格式與載入路徑。
- `Play with Computer` 啟用後是否自動啟動本機 server，或沿用一般 server/client 流程。
