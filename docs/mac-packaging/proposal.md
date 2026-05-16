# macOS App Packaging Proposal

## 1. 文件目的

本文件是 `p2p-tetris` 新增 macOS App 打包能力的需求確認文件。它不是最終執行文件，也不直接定案所有選項；後續執行 agent 應先用本文的問題向專案作者確認需求，再撰寫或執行具體 implementation plan。

本文件已基於目前 repo 的 `docs/*` 與 `src/*` 內容整理，特別是：

- 目前專案是 Python 3.13 / `uv` / `src/p2p_tetris` package layout。
- GUI client 使用 PySide6，entrypoint 是 `p2p-tetris-client = p2p_tetris.client.app:main`。
- headless UDP server entrypoint 是 `p2p-tetris-server = p2p_tetris.server.app:main`。
- 現有 packaging 文件以 Linux / Windows 為主，首選 `pyside6-deploy`，PyInstaller 作為 fallback。
- 現有 runtime 已有 `client`、`server`、`net`、`gui`、`packaging` 邊界；macOS 打包不得把 runtime 邏輯塞進 packaging module。

## 2. 目前環境狀態

本輪已在 macOS 環境完成工具部署與 smoke 驗證：

- 已建立分支：`mac-package-proposal`
- 已安裝 `uv`：`0.11.14`
- 已用 `uv sync --dev` 建立 `.venv`
- 已確認 dev tools：
  - `ruff 0.15.13`
  - `mypy 2.1.0`
  - `pytest 9.0.3`
- 已執行並通過：
  - `uv run python -m compileall src`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `QT_QPA_PLATFORM=offscreen uv run pytest`

備註：使用者輸入中的 `ytest` 需要確認是否指 `pytest`。目前 repo 的 `pyproject.toml`、文件與測試套件都是 `pytest`。

## 3. 已知需求

已知需求如下：

- 使用者不希望終端玩家需要自己安裝 `uv`。
- 使用者不希望終端玩家覺得自己需要 compile 或處理 Python 工程。
- macOS 交付物應該是「可以玩的 App」，而不是 source checkout 加指令。
- 目前專案仍應保留 `uv` 作為開發與 build-time 工具；`uv` 不應成為終端玩家執行遊戲的前置條件。
- macOS 打包必須涵蓋 PySide6 GUI client。
- server 是 headless UDP process；依目前需求，macOS GUI App 不內建 server，房主另行啟動 `p2p-tetris-server`。
- 不應新增 RL agent、Gymnasium、SB3、PyTorch 或模型推論依賴。
- 不應破壞目前 Linux / Windows packaging 文件與現有 entrypoints。

## 4. 已回答的核心需求

以下問題已由使用者回答。後續執行 agent 應以本節答案與 4.7 的整理結論為準，不應重新猜測或改變方向。

### 4.1 目標使用者與發佈方式

1. 這個 macOS App 是只給你自己和少數測試者用，還是要給一般使用者下載？ 我希望可以做到給使用者可以下載使用。
2. 你希望交付物是 `.app`、`.dmg`、`.zip`，還是三者都要？我希望交付物是.app
3. 你希望透過 GitHub Releases、網站下載、私下傳檔、還是 Mac App Store 發佈？就github release 就好
4. 是否需要使用者雙擊後完全沒有 Terminal 視窗？ 對。
5. 使用者是否需要能把 App 拖到 `/Applications` 後直接玩？對。

### 4.2 簽章、notarization 與 Gatekeeper

1. 你是否有 Apple Developer Program 帳號？沒有
2. 你是否希望正式交付物用 Developer ID 簽章並 notarize，讓 Gatekeeper 不出現高風險警告？應該沒關係
3. 如果目前沒有 Apple Developer 帳號，是否接受開發階段先產出 unsigned / ad-hoc signed `.app`，並在文件中明確標記 Gatekeeper 限制？可以接受
4. 是否需要 CI 自動簽章與 notarize，還是可以先由本機人工執行 release build？不需要 CI 自動簽章與 notarize；先用本機手動 build unsigned / ad-hoc signed `.app`。
5. 是否有固定 bundle identifier，例如 `com.<your-domain>.p2p-tetris`？使用 `com.ryansuc.p2p-tetris`。

### 4.3 macOS 版本與 CPU 架構

1. 最低支援 macOS 版本要到哪一版？我現在這版。
2. 是否只支援 Apple Silicon arm64？是
3. 是否需要 Intel x86_64 build？不用
4. 是否需要 universal2 單一 App 同時支援 arm64 與 x86_64？不用
5. 若需要 universal2，是否接受分別在兩種架構環境 build 後合併，或偏好工具自動處理？不需要 universal2，因此本題不適用。

### 4.4 Client / Server 使用體驗

1. macOS App 是否只包含 GUI client？對
2. 是否需要另外交付 `p2p-tetris-server` 給房主啟動？好
3. 是否希望 GUI App 內建「Host Local Server」按鈕，自動在背景啟動 server？不用。
4. 如果 App 內建 server，使用者是否需要看到 server host、port、LAN IP、玩家數、停止 server 等 UI？不用，server一定會由我本人擔任，這個我只是當作我的side project跟與我朋友自娛自樂的玩具。
5. 區網對戰時，macOS App 是否需要處理或提示 firewall / local network permission？需要，不然應該會連不出去吧
6. 目前 server 使用 UDP `7777`；macOS 版是否沿用，或需要可配置 port？沿用就好

### 4.5 App 品牌與視覺資產

1. App 名稱是否固定為 `P2P Tetris`？對
2. 是否需要避免在正式 App 名稱中使用 `Tetris` 這個商標字樣？沒差，反正我也沒有要盈利
3. 是否已有 `.icns` icon？如果沒有，是否需要後續 agent 產生或設計 icon？沒有，你產生一個好看的吧。
4. 是否需要 About dialog、版本號、copyright、license 文字？目前沒有處理license，再看看吧
5. App bundle version 是否沿用 `pyproject.toml` 的 `0.1.0`？這個沒差，就沿用吧

### 4.6 更新與安裝後資料位置

1. 是否需要自動更新？若需要，是 Sparkle、GitHub Releases 手動下載，還是暫不處理？不處理
2. 是否需要保存玩家設定，例如預設 server IP、玩家名稱、鍵位？好
3. 如果保存設定，macOS 版是否應使用 `~/Library/Application Support/P2P Tetris/` 或 Qt settings？是
4. log 應該寫到哪裡？是否需要 GUI 內提供 log 匯出？不需要支援GUI內log匯出，如果有error看通常其他app寫到哪就寫到哪吧

### 4.7 依目前回答整理出的暫定結論

依使用者目前回答，後續執行 agent 應先採用以下方向：

- 發佈對象：可給朋友或 GitHub Releases 使用者下載，不只是本機開發用。
- 交付物：主要目標是 macOS `.app`。但若要讓使用者「拖到 `/Applications` 後直接玩」，後續可以把 `.app` 放進 `.zip` 或 `.dmg` 發佈；真正執行的仍然是 `.app`。
- 發佈管道：GitHub Releases。
- App 啟動方式：Finder 雙擊啟動，不應出現 Terminal 視窗。
- 簽章 / notarization：目前沒有 Apple Developer Program 帳號；第一版接受 unsigned 或 ad-hoc signed `.app`，但文件必須說明 Gatekeeper 可能阻擋，需要使用者手動允許。
- CPU 架構：只支援 Apple Silicon `arm64`，不支援 Intel `x86_64`，不做 universal2。
- macOS 版本：以目前開發機的 macOS 版本為最低支援基準；後續 execution 文件應用實際命令記錄 `sw_vers` 結果。
- client / server：macOS App 只包 GUI client；另外提供 server 啟動方式給房主。server 主要由專案作者本人擔任，不需要 GUI 內建 Host Server。
- port：沿用 UDP `7777`。
- firewall / local network：需要在文件中提示，並在 smoke test 中驗證。
- App 名稱：暫用 `P2P Tetris`。
- icon：需要產生一個 `.icns`。
- version：沿用 `pyproject.toml` 的 `0.1.0`。
- 自動更新：不處理。
- 設定保存：需要保存玩家設定；後續可優先用 Qt settings 或 macOS app support 目錄。
- log：不需要 GUI 匯出；若需要寫 log，使用一般 macOS app 慣例位置，例如 `~/Library/Logs/<App Name>/`。

### 4.8 已補充說明的概念

#### CI 自動簽章與 notarize 是什麼？

CI 是 GitHub Actions 這種「雲端自動幫你跑打包流程」的東西。自動簽章與 notarize 的意思是：

1. 你 push tag，例如 `v0.1.0`。
2. GitHub Actions 自動在 macOS runner 上 build `.app`。
3. 它用 Apple Developer 憑證幫 `.app` 簽章。
4. 它把 `.app` 上傳給 Apple 做 notarization。
5. Apple 通過後，CI 產出 release artifact，放到 GitHub Releases。

這需要 Apple Developer Program、Developer ID 憑證、notarytool credentials，還要把敏感資料放進 GitHub secrets。你目前沒有 Apple Developer Program，所以第一版不做這件事。

目前結論：不需要 CI 自動簽章與 notarize；先用本機手動 build unsigned / ad-hoc signed `.app`。

#### bundle identifier 是什麼？

bundle identifier 是 macOS 用來辨識 App 的唯一 ID，不是使用者看到的 App 名稱。格式通常像：

```text
com.ryansuc.p2p-tetris
```

它的用途包括：

- macOS 用它分辨「這是哪一個 App」。
- 設定檔、權限、簽章、notarization 都會用到它。
- 之後如果你改 bundle identifier，macOS 會把它當成另一個 App。

你現在不需要懂很深，只需要選一個不容易跟別人撞名、未來不要常改的字串。

目前結論：先用 `com.ryansuc.p2p-tetris`。如果你有自己的 domain，正式 release 前可改成 `com.<your-domain>.p2p-tetris`。

#### universal2 是什麼？為什麼你不需要？

Mac 現在有兩種 CPU：

- Apple Silicon：M1、M2、M3、M4，架構叫 `arm64`。
- Intel Mac：舊款 Mac，架構叫 `x86_64`。

universal2 是「同一個 App 同時包 arm64 和 x86_64」，所以兩種 Mac 都能跑。缺點是 build 更麻煩、檔案更大、驗證矩陣更多。

你已經回答只支援 Apple Silicon，所以後續不需要 universal2，也不需要回答「分別 build 後合併」這題。

目前結論：不需要 universal2；只 build Apple Silicon arm64。

#### `.app` 和「拖到 `/Applications`」的關係

`.app` 本身就是 App，但使用者從 GitHub Releases 下載時，通常不會直接下載一個裸 `.app` 目錄，因為 `.app` 其實是一個資料夾 bundle。常見發佈方式是：

- `.zip`：把 `.app` 壓縮起來，使用者解壓後拖到 `/Applications`。
- `.dmg`：打開後看到 App icon 和 Applications 捷徑，使用者拖過去。

你說交付物希望是 `.app`，可以理解成「最後使用者拿到的是一個可以雙擊的 App」。實際 GitHub Releases artifact 建議可以是 `P2P-Tetris-macOS-arm64.zip`，裡面放 `P2P Tetris.app`。

目前結論：正式 artifact 用 `.zip` 包住 `.app`；不急著做 `.dmg`。

#### 沒有 Developer Account 會發生什麼？

沒有 Apple Developer Program 也可以做 `.app`，但一般使用者第一次開啟時可能看到 macOS 警告，甚至需要到 System Settings 手動允許。

這不影響你和朋友測試，但如果你希望陌生使用者下載後無摩擦執行，就需要 Developer ID signing + notarization。

目前結論：第一版接受 Gatekeeper 摩擦；文件要明確告知。

#### firewall / local network 要怎麼理解？

你的 client 需要連到 server 的 UDP `7777`。如果 server 是你本人開，朋友的 App 主要是 outbound 連線，通常問題較少。但 macOS firewall、路由器、防火牆或區網權限仍可能造成連不上。

後續 smoke test 應至少做：

- 同一台 Mac 開 server + client。
- 同一區網另一台 Mac 開 client 連到 server。
- 第一次啟動時確認 macOS 是否跳出網路權限提示。

目前結論：App 不需要內建複雜 firewall 修復功能，但文件要提示，測試要覆蓋。

## 5. 打包工具候選方案

### 5.1 方案 A：`pyside6-deploy` 作為 macOS 首選

理由：

- 目前 repo 已有 `src/p2p_tetris/packaging/pyside6_deploy/` skeleton。
- Qt for Python 官方文件說明 `pyside6-deploy` 可部署 PySide6 app，底層包裝 Nuitka；macOS 產物是 `.app`。
- 與既有 `docs/packaging.md` 的「首選 pyside6-deploy」一致。

疑問：

- 目前 spec 以 Linux 文件為主，需實測 macOS `.app` 產出位置、Qt plugin 收集、Nuitka 相容性與 codesign 後行為。那就產出這個
- `pyside6-deploy` 會在 build 環境安裝 deployment 依賴；需要確認是否接受 build-time 額外依賴。可以
- 需要確認產出的 `.app` 是否容易接續 Developer ID signing、notarization、DMG 製作。剛剛上面有回答過了

建議定位：

- 第一階段 smoke build 優先使用。
- 若 macOS 簽章或 notarization 流程不順，再轉 PyInstaller fallback。

### 5.2 方案 B：PyInstaller macOS `.app` fallback

理由：

- 目前 repo 已有 `src/p2p_tetris/packaging/pyinstaller/` fallback skeleton。
- PyInstaller 官方文件支援 macOS windowed `.app` bundle，並可在 spec 中定義 icon、bundle identifier、Info.plist。
- 對於「一個 GUI `.app` + 一個 headless server executable」的交付模型，PyInstaller spec 會比較直觀。

疑問：

- 現有 `client.spec` 目前是 generic COLLECT，尚未加入 macOS `BUNDLE(...)` block。
- 需要另外處理 Qt / PySide6 hooks、codesign、notarization、DMG packaging。
- PyInstaller 官方文件不建議用 onefile + windowed 做 macOS App bundle release；應優先 one-dir bundle。

建議定位：

- 作為正式 fallback。
- 如果 `pyside6-deploy` 對 PySide6 6.11 / Python 3.13 / macOS signing 有阻塞，改以 PyInstaller macOS spec 推進。

### 5.3 方案 C：Briefcase 作為 release packaging layer

理由：

- Briefcase 官方文件以 native app packaging 為核心，macOS 支援 `.app`、DMG、ZIP、PKG，並描述簽章與 notarization 流程。
- 如果目標是「一般使用者下載 DMG，拖到 Applications」，Briefcase 的發佈語意比較接近終端產品。

疑問：

- 這會引入新的 packaging framework 與 `tool.briefcase` 設定，和目前既有 packaging skeleton 不完全一致。
- 需要確認 PySide6 project 是否適合用 Briefcase 包裝，尤其是 Qt plugin 與 PySide6 binary dependency。
- 對目前 MVP 來說可能比必要範圍更大。

建議定位：

- 不是第一階段首選。
- 若目標明確是 signed / notarized DMG 或未來 Mac App Store，再評估是否值得導入。

## 6. 建議決策路線

依目前回答，建議採用以下低風險路線：

1. 第一輪只做 Apple Silicon `arm64`，不做 Intel `x86_64`，不做 universal2。
2. 第一輪只包 GUI client `.app`；server 另以既有 `p2p-tetris-server` 流程提供給房主，不做 GUI 內建 Host Server。
3. 第一輪以 `pyside6-deploy` 產出 macOS `.app` smoke build。
4. GitHub Releases 的實際 artifact 建議用 `.zip` 包住 `.app`，因為 `.app` 在檔案系統上是 bundle 目錄。
5. 同輪保留 PyInstaller macOS fallback spec，但只有在 `pyside6-deploy` 卡住時啟用。
6. 第一版不做 Developer ID signing / notarization / CI release automation；文件需明確說明 Gatekeeper 限制。
7. 後續若要降低一般下載者的 Gatekeeper 摩擦，再加入 Apple Developer Program、Developer ID signing、notarization、stapling 與 CI release gate。

## 7. 建議後續執行文件範圍

後續可以新增 `docs/mac-package-execution.md`，但必須在本文問題回答後再寫。該文件應包含：

- 最終選定 packaging tool。
- macOS build prerequisites。
- `uv sync --dev` 與 packaging-only dependency 安裝方式。
- client `.app` build command。
- server executable 啟動或打包方式；目前不做 Server.app。
- icon / Info.plist / bundle identifier 設定。
- ad-hoc signing 或 unsigned 開發版的處理方式。
- 未 notarize App 的 Gatekeeper 使用說明。
- ZIP 製作 command；DMG 暫列後續可選項。
- smoke test matrix。
- release artifact 命名規則。
- rollback / fallback 流程。

## 8. 建議驗收標準

macOS packaging 任務完成時，至少應滿足：

- 使用者不需要安裝 `uv` 就能啟動遊戲。
- 使用者不需要 compile source。
- GUI client 可從 Finder 雙擊啟動。
- Single Player 可正常渲染並接受鍵盤輸入。
- server 由房主使用既有 server entrypoint 或另行打包的 server executable 啟動；GUI client 不內建 host flow。
- 如果 macOS 支援 LAN 對戰，兩個 App instance 可連到 server 並進入 match。
- 打包後仍可通過基本 smoke test。
- release 文件清楚說明 `.app` / `.zip` 的用途與安裝方式。
- 因目前沒有 Apple Developer Program，第一版 artifact 可以不 notarize，但必須清楚說明 Gatekeeper 可能阻擋與手動允許方式。

## 9. 初步任務切分

### Phase 0：需求確認

- 固定 bundle identifier，暫定 `com.ryansuc.p2p-tetris`，正式 release 前可再改。
- 用 `sw_vers` 記錄目前開發機 macOS 版本，作為第一版最低支援基準。
- 確認 GitHub Releases artifact 命名，例如 `P2P-Tetris-macOS-arm64.zip`。
- 確認 App 顯示名稱暫用 `P2P Tetris`。

### Phase 1：macOS `.app` smoke build

- 新增 macOS-specific packaging wrapper，避免污染 Linux / Windows docs。
- 以 `pyside6-deploy` 嘗試產出 client `.app`。
- 記錄實際輸出路徑、bundle structure、啟動方式。
- 用 Finder / `open` 啟動 `.app`。
- 驗證 Single Player smoke。

### Phase 2：server 交付模型

依目前回答，server 不內建進 GUI client：

- client `.app` 只負責遊戲 GUI。
- 房主使用 `p2p-tetris-server` 啟動 UDP server。
- 文件說明 server host、port `7777`、LAN IP 與 firewall 注意事項。
- 不做 Server.app。
- 不做 embedded host mode。

### Phase 3：release packaging

- 補 `.icns` icon。
- 補 `Info.plist` / bundle identifier / version。
- 補 ad-hoc signing 或 unsigned build 說明。
- 補 ZIP packaging。
- 不做 notarization；DMG 暫列後續可選項。
- 補 release smoke test。

### Phase 4：CI / release docs

- 第一版不做 CI 自動簽章與 notarization。
- 可選：後續再評估 GitHub Actions macOS runner 產出 unsigned / ad-hoc signed ZIP。
- 更新 `docs/packaging.md` 或新增 `docs/mac-packaging.md`。
- 保留 Linux / Windows 現有流程。

## 10. 風險

- PySide6 / Qt plugin 收集在 macOS bundle 中可能需要額外 hook 或 config。
- Python 3.13、PySide6、Nuitka、PyInstaller 的相容性必須以實際 macOS build 驗證。
- Developer ID signing 與 notarization 需要 Apple Developer Program、certificate、notarytool credentials；沒有這些就不能宣稱一般使用者可無 Gatekeeper 摩擦地執行。
- 若要支援 Intel + Apple Silicon，可能需要兩份 build 或 universal2 策略。
- UDP LAN 對戰可能觸發 macOS local network / firewall prompts；需要在 App metadata、文件與 QA 中驗證。
- 若 GUI 內建 server，會新增 lifecycle、port conflict、crash cleanup、UI 狀態與測試範圍。

## 11. 參考資料

- Qt for Python `pyside6-deploy`: https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html
- PyInstaller macOS bundles: https://pyinstaller.org/en/stable/usage.html#building-macos-app-bundles
- PyInstaller spec files and `BUNDLE`: https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle
- Briefcase macOS packaging: https://briefcase.beeware.org/en/stable/reference/platforms/macOS/index.html
- Apple notarization overview: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- Apple distribution signing: https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac
- Apple packaging Mac software: https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution
- uv installation: https://docs.astral.sh/uv/getting-started/installation/
