# P2P Tetris 需求草案

## 1. 文件目的

本文件定義 `p2p-tetris` 的需求範圍，供專案作者與後續實作 AI 閱讀。文件定位是「需求導向的技術草案」：描述必須達成的使用情境、功能邊界、驗收標準、測試要求與風險；更細的模組設計、協定格式、資料結構與任務切分，將在後續「設計」與「劃分任務」階段處理。

本專案目標是用 Python 實作一個可在桌面環境執行的雙人對戰方塊遊戲，玩法以經典 Tetris 與 Facebook 時代的 Tetris Battle / Tetris Friends Battle 2P 類型對戰為參考。專案不使用官方商標、圖片、音效或受版權保護的素材；需求中的「Tetris」僅作為玩法類型描述。

後續會另開 RL agent 子項目，讓電腦玩家透過 Gymnasium-style 環境與 Stable-Baselines3 訓練後，使用與真人玩家相同的 action space 參與遊戲。RL 子項目不屬於本文件定義的 MVP，需求與初步設計記錄於 `docs/RL_agent.md`。本文件只要求主遊戲在架構上預留必要接口，避免 game-core、GUI、network client 與 controller 邏輯過度耦合。

## 2. 背景與參考行為

使用者希望復刻以前 Facebook 上 Tetris Battle 類型的對戰體驗，並簡化網路架構，使兩名玩家能透過同一台 server 配對並遊玩。

公開資料顯示，Facebook 版 Tetris Battle / Tetris Friends Battle 2P 具有下列特徵，可作為本專案的目標參考：

- 遊戲盤面為 10 x 20 可見格。
- 使用現代 guideline 類規則，包含 SRS 旋轉、hold、hard drop、next queue 等功能。
- Battle 2P 是 2 分鐘制，目標是在時間內盡可能 KO 對手；勝負通常依 KO 數、送出垃圾行數、結束時堆疊高度等條件判定。
- 對戰壓力來自垃圾行。玩家透過消多行、連續消行 combo、T-spin、back-to-back 等行為對對手送出垃圾。
- Facebook 版 Battle 2P 的常見垃圾形式包含 bomb garbage；Arena 類即時模式則更接近傳統有洞垃圾行。

本專案需求階段先採用「目標接近 FB 版 Battle 2P 體感」作為方向，但不在本文件中鎖死所有攻擊數值。攻擊表、垃圾抵銷、bomb 或 hole garbage 的精確規則，應在後續設計階段根據實作成本與測試可行性定版。

參考資料：

- TetrisWiki: Tetris Battle (Facebook): https://tetris.wiki/Tetris_Battle_%28Facebook%29
- TetrisWiki: Combo: https://tetris.wiki/Combo
- TetrisWiki: Line clear / Back-to-Back / Combo: https://tetris.wiki/Line_clear
- Wikipedia: Tetris Friends, Battle 2P 描述: https://en.wikipedia.org/wiki/Tetris_Friends

## 3. 專案目標

### 3.1 主要目標

- 使用 Python 實作桌面 GUI 遊戲。
- 至少支援 Linux 與 Windows。
- 專案使用 uv 管理 Python 工程。
- 專案必須可被打包成使用者友善的可執行檔。
- 第一版 MVP 必須支援單人遊玩。
- MVP 必須支援本機啟動 server 與兩個 client 視窗，並完成雙人對戰測試。
- 網路連線以輸入 server IP 的方式加入，由 server 負責配對。
- 對戰體驗以 FB 版 Tetris Battle / Battle 2P 的垃圾行壓力與 KO 對戰為目標。
- 所有主要 component 必須有測試，並通過 `ruff`、`mypy`、`pytest`。
- 架構必須預留未來 RL agent 控制 client 的接口，使後續能實作人類 vs 電腦與 AI vs AI 測試。

### 3.2 非目標

- MVP 不要求純 P2P。
- MVP 不處理 NAT traversal。
- MVP 不內建 WireGuard、Tailscale 或其他 VPN/overlay network 整合。
- MVP 不要求公開網際網路配對服務。
- MVP 不要求帳號、排名、課金、造型、任務、成就或社交功能。
- MVP 不要求完整重現 FB 版所有 UI、素材、經濟系統或非核心模式。
- MVP 不要求強作弊防護；只需滿足可信任玩家之間的本機或同網段測試。
- MVP 不包含 RL agent 訓練、模型推論或可用的電腦對手。
- MVP 不包含 MARL、多 agent 訓練、自我對戰訓練流程或訓練監控工具。

## 4. 使用情境

### 4.1 單人模式

玩家啟動桌面 client，選擇單人模式後可以立即開始一局傳統方塊遊戲。玩家可以移動、旋轉、soft drop、hard drop、hold 方塊，看到 next queue 與 ghost piece，並在堆疊到頂時結束遊戲。

### 4.2 本機雙人測試

開發者在同一台電腦上啟動一個 server 與兩個 client 視窗。兩個 client 透過 `localhost` 或本機 IP 連到 server。server 將兩名玩家配成一場對戰。兩方可以同時遊玩，彼此送垃圾行，直到回合結束並產生勝負。

### 4.3 區網雙人對戰

玩家 A 在同一區網內啟動 server，玩家 A 與玩家 B 分別啟動 client，輸入 server IP 後加入。server 自動配對前兩名玩家，開始一場即時雙人對戰。

### 4.4 公開 IP 直連

若 server 部署在可連線的公開 IP 上，兩名 client 可以輸入該 public IP 加入。MVP 只要求應用層支援 IP 直連，不負責路由、防火牆、port forwarding 或 NAT traversal 設定。

### 4.5 車輪戰

server 允許額外玩家排隊等待。每一局只有兩名 active players；輸掉的一方離開 active match，等待隊列中的下一名玩家進入下一局。等待隊列容量必須可配置；初始建議值可以是 5，但最終預設值在設計階段確認。

### 4.6 與電腦對打入口

client 主介面需預留 `Play with Computer` 入口。MVP 階段此入口可以顯示為未啟用或 disabled，避免使用者誤以為功能已完成。後續 RL agent 子項目完成後，該入口可啟用並讓玩家與由 agent 控制的 client 對戰。

### 4.7 AI vs AI 預留情境

後續應能透過同一套 client controller 接口啟動兩個由 agent 控制的 client，並連到同一個 server 進行 AI vs AI 測試。主遊戲不需在 MVP 實作 AI vs AI，但 client、server 與 game-core 不應阻礙這種模式。

## 5. 功能需求

### 5.1 遊戲核心

- FR-CORE-001: 遊戲盤面必須支援 10 x 20 可見格，並允許實作隱藏緩衝區供方塊生成與旋轉使用。
- FR-CORE-002: 必須支援 7 種標準 tetromino：I、O、T、S、Z、J、L。
- FR-CORE-003: 必須支援標準方塊生成序列；具體 randomizer 在設計階段確認，優先考慮 7-bag。
- FR-CORE-004: 必須支援方塊左移、右移、旋轉、soft drop、hard drop。
- FR-CORE-005: 必須支援 hold。
- FR-CORE-006: 必須支援 next queue。顯示數量需可配置，目標至少 3 個；若 GUI 空間足夠，優先支援 5 個。
- FR-CORE-007: 必須支援 ghost piece。
- FR-CORE-008: 必須支援 wall kick。旋轉系統目標採用 SRS；完整 kick table 在設計階段定義。
- FR-CORE-009: 必須支援 lock delay 或等效機制，使現代 Tetris 手感可玩。
- FR-CORE-010: 必須支援 line clear、combo、back-to-back 狀態追蹤。
- FR-CORE-011: 必須支援 top-out 判定。
- FR-CORE-012: 單人模式必須有基礎分數、消行數與遊戲結束畫面。
- FR-CORE-013: game-core 必須能被 GUI 以外的 controller 驅動，controller 可來自真人鍵盤、測試程式或未來 RL agent。
- FR-CORE-014: game-core 必須提供足夠的狀態讀取能力，讓後續 RL 環境能建立 observation，但 MVP 不需要實作 Gymnasium 環境。

### 5.2 單人模式

- FR-SOLO-001: 玩家可從 client 啟動單人遊戲，不需要 server。
- FR-SOLO-002: 單人遊戲規則應接近傳統 Tetris：隨時間或等級增加下落壓力，直到玩家 top-out。
- FR-SOLO-003: 單人模式必須可暫停與重新開始。
- FR-SOLO-004: 單人模式必須能作為核心規則測試與除錯入口。

### 5.3 對戰模式

- FR-VS-001: 對戰模式必須支援一場同時兩名 active players。
- FR-VS-002: 對戰回合目標應接近 FB Battle 2P：限時回合，透過送垃圾與 KO 對手取得勝利。
- FR-VS-003: MVP 回合時間目標為 2 分鐘；實作需允許後續配置。
- FR-VS-004: 玩家 top-out 時視為被 KO。回合是否立即結束，或在同一回合中重生繼續累計 KO，應在設計階段確認；目標行為偏向 FB Battle 2P 的限時多 KO 形式。
- FR-VS-005: 若回合時間結束，勝負判定優先順序目標為：KO 數、送出垃圾行數、結束盤面高度。精確 tie-breaker 在設計階段定義。
- FR-VS-006: 玩家必須能看到自己的盤面、對手盤面摘要、next queue、hold、分數或攻擊狀態、剩餘時間、KO 狀態。
- FR-VS-007: 對戰中必須支援由消多行、combo、T-spin、back-to-back 產生的攻擊壓力。
- FR-VS-008: 垃圾行應支援抵銷或延遲套用機制；精確規則在設計階段定義。
- FR-VS-009: 垃圾型態以 FB 版 Battle 2P 體感為目標。MVP 可先選擇傳統有洞垃圾或 bomb garbage 中較容易測試的方案，但必須在設計文件中明確說明選擇原因。

### 5.4 Server 與配對

- FR-NET-001: 必須提供可獨立啟動的 server component。
- FR-NET-002: client 必須能輸入 server IP 與 port 加入。
- FR-NET-003: server 必須管理連線玩家、等待隊列、active match 與回合狀態。
- FR-NET-004: server 必須自動將等待中的玩家配成兩人對戰。
- FR-NET-005: server 必須支援本機多 client 測試。
- FR-NET-006: server 必須允許等待隊列容量配置；需求目標是可支援至少 5 名非 active 或總連線 buffer，精確定義在設計階段確認。
- FR-NET-007: 一局結束後，server 必須能把輸家移出 active match，並讓等待隊列中的下一名玩家進入下一局。
- FR-NET-008: server 必須能處理玩家中途離線、逾時與重複加入。
- FR-NET-009: server 不需要做長期資料保存。

### 5.5 UDP 網路需求

- FR-UDP-001: client 與 server 通訊使用 UDP。
- FR-UDP-002: UDP 協定必須具備基本 session 識別，避免不同 client 封包混淆。
- FR-UDP-003: 對重要事件必須有可靠性補償設計，例如 ack、重送、序號、快照或狀態校正。具體策略在設計階段定義。
- FR-UDP-004: 遊戲必須能在同機與同區網一般延遲下穩定進行。
- FR-UDP-005: MVP 不要求惡意環境安全性，但必須避免普通封包遺失造成遊戲永久卡死。
- FR-UDP-006: 網路同步策略應優先選擇容易測試與除錯的方案，而不是追求最低延遲。

### 5.6 GUI 與使用者體驗

- FR-GUI-001: client 必須是桌面 GUI，不是純 CLI。
- FR-GUI-002: GUI 必須可在 Linux 與 Windows 運行。
- FR-GUI-003: GUI 必須提供單人開始、連線到 server、`Play with Computer`、重新開始、退出等基本操作。
- FR-GUI-004: GUI 必須支援鍵盤操作，並提供預設按鍵配置。
- FR-GUI-005: GUI 必須避免依賴平台專屬 API。
- FR-GUI-006: GUI 必須能顯示必要的對戰資訊，包含對手狀態與垃圾壓力提示。
- FR-GUI-007: MVP 階段 `Play with Computer` 可以顯示為未啟用或 disabled；啟用條件由 `docs/RL_agent.md` 所定義的子項目決定。
- FR-GUI-008: GUI 細節、框架選擇與美術風格留待設計階段確認。

### 5.7 打包與執行

- FR-PKG-001: 專案必須支援在 Linux 與 Windows 打包成可執行檔。
- FR-PKG-002: 打包方式可使用額外套件；具體工具在設計階段選擇。
- FR-PKG-003: 打包後至少應包含 client 執行入口。
- FR-PKG-004: server 可以是獨立可執行檔，或由同一可執行檔以模式切換啟動；設計階段決定。
- FR-PKG-005: README 或後續操作文件必須說明如何啟動 server、如何啟動 client、如何在本機開兩個 client 測試。

### 5.8 RL Agent 預留接口

- FR-RL-001: RL agent 子項目不屬於 MVP，需求與初步設計獨立記錄於 `docs/RL_agent.md`。
- FR-RL-002: 主遊戲必須保留 action 抽象，使真人與 RL agent 都能送出同一組遊戲動作。
- FR-RL-003: 不允許為 RL agent 提供高階 placement action；後續 agent 的 action space 應與真人玩家語意一致。
- FR-RL-004: client 應保留 controller 抽象，使鍵盤、測試腳本、RL policy 都能成為 action source。
- FR-RL-005: server 應把 agent-controlled client 視為一般 client，不需為 AI 玩家設計特殊網路協定。
- FR-RL-006: game-core、battle-rules 與 GUI 不應互相硬耦合，以便後續 RL 環境直接使用 game-core 做訓練。

## 6. 非功能需求

- NFR-001: 專案必須維持清楚的 component 邊界，至少區分遊戲核心、對戰規則、controller、GUI、網路、server、測試。
- NFR-002: 遊戲核心邏輯應盡量不依賴 GUI，以便單元測試。
- NFR-003: 網路協定與遊戲規則應可測試、可重播或可用 deterministic fixture 驗證。
- NFR-004: 程式碼必須通過 `ruff`。
- NFR-005: 程式碼必須通過 `mypy`。
- NFR-006: 程式碼必須通過 `pytest`。
- NFR-007: 專案需使用 Python 3.13 或符合 `pyproject.toml` 的 Python 版本。
- NFR-008: 允許加入第三方套件，但必須能在 Linux 與 Windows 安裝與打包。
- NFR-009: 遊戲 loop、網路 loop 與 GUI loop 必須避免互相阻塞。
- NFR-010: 設定值，例如 server port、隊列容量、回合時間、玩家名稱，應避免硬編死在難以修改的位置。
- NFR-011: component 不應透過 GUI 狀態互相傳遞核心遊戲資料；核心狀態應由可測試的資料模型或服務接口承載。
- NFR-012: 後續 RL 子項目可能在獨立 branch 開發，因此主專案接口需穩定、明確且可由測試固定。

## 7. 建議 Component 邊界

此節是需求導向的邊界建議，非最終設計。

- `game-core`: 方塊、盤面、碰撞、旋轉、消行、combo、B2B、top-out、單人規則。
- `battle-rules`: 攻擊計算、垃圾行、KO、回合計時、勝負判定。
- `controller`: 真人鍵盤、測試腳本、未來 RL agent 共用的 action source 抽象。
- `client-gui`: 桌面視覺呈現、輸入處理、單人與連線入口。
- `net-client`: UDP client、session、重送或同步處理。
- `server`: UDP server、玩家管理、配對、等待隊列、active match。
- `rl-env`: 未來子項目；Gymnasium-style 環境、observation wrapper、reward wrapper、SB3 訓練入口。
- `packaging`: Linux / Windows 可執行檔打包設定。
- `tests`: 單元測試、協定測試、server/client 整合測試。

## 8. MVP 範圍

MVP 必須包含：

- 單人 GUI 可執行。
- 主介面可呈現 `Play with Computer` 入口，但此入口可標示未啟用。
- 傳統方塊核心規則可玩。
- hold、next queue、ghost piece、hard drop、soft drop、SRS 或等效 wall kick。
- server 可啟動。
- 兩個 client 可連到本機 server。
- server 可將兩個 client 配對並開始對戰。
- 對戰中雙方可互相送垃圾行。
- 對戰可判定回合結束與勝負。
- 本機同時執行 server + 2 client 的測試流程可被文件化。
- `ruff`、`mypy`、`pytest` 全部通過。

MVP 可延後：

- 完整 FB 版所有攻擊數值精準還原。
- 完整 bomb garbage 邏輯，如果設計階段判定傳統有洞垃圾更適合先行驗證。
- 排名、帳號、房間列表、觀戰、聊天、道具、造型。
- 跨 NAT 自動連線。
- 作弊防護。
- 自動更新。
- RL agent 訓練、模型推論、`Play with Computer` 啟用、AI vs AI。

## 9. 開發里程碑

### M1: 單人核心

- 完成 game-core。
- 完成單人 GUI。
- 完成基礎測試。
- 驗收：可在本機啟動並完成一局單人遊戲。

### M2: 對戰規則

- 完成 battle-rules。
- 完成垃圾行、攻擊、KO、勝負判定。
- 驗收：可用測試直接驗證消行、combo、B2B、T-spin 或指定攻擊事件產生正確對戰壓力。

### M3: Server 與 UDP 通訊

- 完成 server。
- 完成 client/server UDP 連線。
- 完成 session、配對、等待隊列。
- 驗收：兩個 client 可在本機連到 server 並進入同一場對戰。

### M4: 雙人可玩版本

- 串接 GUI、game-core、battle-rules、net-client。
- 驗收：本機 server + 2 client 可完整遊玩一局，並產生勝負。

### M5: 跨平台與打包

- 完成 Linux 與 Windows 打包流程。
- 驗收：打包後的 client/server 可在目標平台啟動；至少提供人工或 CI 可重現的打包步驟。

### Post-MVP: RL Agent 子項目

- 參考 `docs/RL_agent.md`。
- 完成 Gymnasium-style 環境、SB3 訓練流程、推論 controller。
- 驗收：agent 可使用與真人相同 action space 控制 client，並與真人或另一個 agent 對戰。

## 10. 測試策略

- 單元測試：
  - tetromino 生成、移動、旋轉、wall kick。
  - collision、lock、line clear、top-out。
  - hold、next queue、ghost piece。
  - combo、B2B、攻擊計算、垃圾抵銷。
  - controller action 抽象不依賴 GUI。

- 整合測試：
  - 單人遊戲 loop 可推進。
  - server 可接受 client 加入。
  - 兩名玩家可被配對。
  - 回合開始、回合結束、勝負判定。
  - 玩家斷線或逾時不使 server 卡死。

- 網路測試：
  - UDP 封包序號或 ack 行為。
  - 封包遺失或重送情境。
  - 重複封包不造成狀態重複套用。

- 品質檢查：
  - `uv run ruff check .`
  - `uv run mypy .`
  - `uv run pytest`

## 11. 驗收標準

專案達成 MVP 時，應滿足：

- 在 Linux 可啟動單人 GUI 遊戲。
- 在 Windows 可啟動單人 GUI 遊戲。
- 主介面可看到 `Play with Computer`，且在 RL 子項目完成前清楚標示未啟用。
- 在本機可啟動 server。
- 在本機可啟動兩個 client 視窗，兩者輸入 server IP 後能配對。
- 雙方能同時遊玩並互相送垃圾行。
- 一局對戰能正常結束並產生勝負。
- server 在對戰結束後能處理下一局或下一名等待玩家。
- 主要規則有自動化測試。
- `ruff`、`mypy`、`pytest` 通過。
- 有打包步驟或打包設定，能產出 Linux / Windows 可執行檔。

## 12. 風險與待設計議題

- UDP 本身不可靠，必須在設計階段定義可靠事件與狀態同步策略。
- GUI framework 會影響跨平台打包難度，需在設計階段評估。
- FB Battle 2P 的精確攻擊數值與垃圾規則需要進一步校準；需求階段只定義目標體感。
- T-spin 偵測與完整 SRS 實作會增加複雜度，需以測試固定行為。
- 同時支援 GUI loop 與 UDP loop 需要避免 blocking。
- Python 3.13 與第三方套件相容性需在選型時確認。
- 若使用公開 IP 連線，防火牆與 port forwarding 是部署問題，不屬於 MVP 應用功能，但需要在使用文件中提醒。
- 若初期設計讓 game-core 依賴 GUI 或網路，後續 RL 子項目會難以接入；設計階段必須優先避免此風險。
- Stable-Baselines3、Gymnasium、PyTorch 與 Python 版本、作業系統、打包流程的相容性需在 RL 子項目設計時確認。

## 13. 需求階段結論

目前需求已足以進入設計階段。下一階段應決定：

- GUI framework。
- 遊戲核心資料模型。
- SRS / randomizer / lock delay 的精確規格。
- FB Battle 2P 風格攻擊表與垃圾行規則。
- UDP 協定與同步模型。
- server queue 與車輪戰狀態機。
- Linux / Windows 打包工具。
- controller 抽象與未來 RL agent 接口。
