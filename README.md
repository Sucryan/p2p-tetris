# P2P Tetris

## 本機操作

啟動 GUI client：

```bash
uv run p2p-tetris-client
```

啟動 headless UDP server：

```bash
uv run p2p-tetris-server --host 127.0.0.1 --port 7777
```

執行 GUI 相關的局部檢查：

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/gui
uv run ruff check src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
uv run mypy src/p2p_tetris/gui src/p2p_tetris/client/app.py src/p2p_tetris/packaging tests/gui
```

本機啟動一個 server 加兩個 client 的流程請見 `docs/local-run.md`；Linux 與 Windows 打包步驟請見 `docs/packaging.md`。
