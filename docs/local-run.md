# 本機執行

本專案使用 `uv` 與 Python 3.13。

## 品質檢查命令

執行 GUI 相關的局部檢查：

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/gui
python -m compileall src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
uv run ruff check src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
uv run mypy src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
```

執行完整專案檢查：

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```

## GUI client

從專案 script 啟動 client：

```bash
uv run p2p-tetris-client
```

## 本機 server 加兩個 client

在終端機 1 啟動 server：

```bash
uv run p2p-tetris-server --host 127.0.0.1 --port 7777
```

在終端機 2 啟動 client A：

```bash
uv run p2p-tetris-client --host 127.0.0.1 --port 7777 --player-name Alice
```

在終端機 3 啟動 client B：

```bash
uv run p2p-tetris-client --host 127.0.0.1 --port 7777 --player-name Bob
```

預期 MVP 流程：

1. 兩個 client 都開啟 Connect 畫面。
2. 使用 `127.0.0.1` 與 port `7777`。
3. client 會透過 UDP 送出 `ClientHello`，並顯示排隊狀態。
4. server 接受兩名 active players，並送出 `MatchStart`。
5. 額外的 client 會進入等待隊列，直到容量上限。
6. 若只要驗證本機渲染與鍵盤輸入，可使用 Single Player。
