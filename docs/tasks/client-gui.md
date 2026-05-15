# client-gui 模塊任務

## 責任

- 建立 PySide6 桌面 GUI。
- 呈現 main menu、connect screen、waiting screen、solo game、versus game、match result。
- 收集鍵盤輸入並交給 controller。
- 顯示 `Play with Computer` disabled。
- 不承載核心規則、不實作 network reliability。

## Public Interface

- `MainWindow`
- `GameViewRenderer`
- screen widgets
- GUI entrypoint callback wiring

## 最小可執行任務

- [ ] GUI-000: 在 `pyproject.toml` 加入 PySide6 dependency
  - 輸出：dependency config
  - 驗收：`uv sync` 後可 `import PySide6`
  - 依賴：無

- [ ] GUI-001: 建立 PySide6 app entrypoint 與 `MainWindow`
  - 輸出：`client/app.py`、`gui/main_window.py`
  - 驗收：可啟動空主視窗
  - 依賴：GUI-000

- [ ] GUI-002: 實作 main menu screen
  - 輸出：`gui/screens.py`
  - 驗收：包含 Single Player、Connect、Play with Computer disabled、Exit
  - 依賴：GUI-001

- [ ] GUI-003: 實作 connect screen
  - 輸出：`gui/screens.py`
  - 驗收：可輸入 host、port、player name，狀態由 view model 驅動
  - 依賴：GUI-002

- [ ] GUI-004: 實作 waiting screen
  - 輸出：`gui/screens.py`
  - 驗收：顯示 active / waiting、room full、rejected 訊息
  - 依賴：GUI-003

- [ ] GUI-005: 決策並實作 game view renderer
  - 輸出：`gui/game_view.py`
  - 驗收：可繪製 board、active piece、ghost、hold、next
  - 依賴：D-GUI-001、CLIENT-RT-001

- [ ] GUI-006: 實作 solo game screen
  - 輸出：`gui/screens.py`
  - 驗收：顯示盤面、hold、next、score、lines、pause、restart
  - 依賴：GUI-005、CLIENT-RT-004

- [ ] GUI-007: 實作 versus game screen
  - 輸出：`gui/screens.py`
  - 驗收：顯示自己盤面、對手摘要、incoming garbage、timer、KO、sent lines
  - 依賴：GUI-005、CLIENT-RT-010

- [ ] GUI-008: 實作 match result screen
  - 輸出：`gui/screens.py`
  - 驗收：顯示 winner、KO、sent lines、下一場狀態
  - 依賴：CLIENT-RT-011

- [ ] GUI-009: 實作 keyboard wiring
  - 輸出：`gui/main_window.py`
  - 驗收：key press/release 只更新 controller，不直接碰 engine
  - 依賴：CTRL-005

- [ ] GUI-010: 實作 GUI 與 runtime 的非阻塞事件橋接
  - 輸出：`gui/main_window.py`
  - 驗收：fake runtime event 不阻塞 GUI loop
  - 依賴：CLIENT-RT-002、CLIENT-RT-006

- [ ] GUI-011: 建立 GUI smoke test
  - 輸出：tests
  - 驗收：headless Qt 環境可建立主要 screen
  - 依賴：GUI-002 至 GUI-008

## 獨立測試

- 使用 fake runtime 與 fake view model。
- 不驗證 core 規則。
- GUI smoke test 只確認 widget 建立、screen 切換與 callback wiring。
