# tests 模塊任務

## 責任

- 提供跨模塊 fixture、fake clock、fake transport、deterministic seed、action script。
- 覆蓋單元、整合、協定、server/client 測試。
- 執行品質檢查。

## 最小可執行任務

- [ ] TEST-001: 建立 pytest 目錄與 fixture 分層
  - 輸出：`tests/`
  - 驗收：pytest 可收集空測試
  - 依賴：COMMON-001

- [ ] TEST-002: 建立 deterministic action script fixture
  - 輸出：`tests/fixtures/`
  - 驗收：可供 game-core 與 runtime 共用
  - 依賴：CTRL-003

- [ ] TEST-003: 建立 SRS fixture 測試集
  - 輸出：fixture file
  - 驗收：覆蓋 I、O、JLSTZ 旋轉案例
  - 依賴：D-CORE-002

- [ ] TEST-004: 建立 battle fixture 測試集
  - 輸出：fixture file
  - 驗收：attack、garbage、KO、winner 規則可重播
  - 依賴：D-BATTLE-001 至 D-BATTLE-005

- [ ] TEST-005: 建立 fake transport 與 network loss fixture
  - 輸出：test helpers
  - 驗收：掉包、重複、重送測試可重現
  - 依賴：NET-012

- [ ] TEST-006: 建立 server/client integration fixture
  - 輸出：test helpers
  - 驗收：兩個 mock client 可進入 match
  - 依賴：SERVER-016

- [ ] TEST-007: 建立 GUI smoke test 設定
  - 輸出：test config
  - 驗收：headless 環境可測 screen 建立
  - 依賴：GUI-011

- [ ] TEST-008: 建立品質檢查命令文件化
  - 輸出：README 或 docs
  - 驗收：`ruff`、`mypy`、`pytest` 命令清楚可執行
  - 依賴：pyproject

## 品質檢查

- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
