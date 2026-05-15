# net 模塊任務

## 責任

- 定義 UDP message schema、codec、session id、match id、sequence、ack、重送、去重。
- 提供 UDP client / server endpoint。
- 不實作配對、Tetris 規則、KO 規則或 GUI。

## Public Interface

- `ProtocolMessage`
- `MessageCodec`
- `ReliableChannel`
- `UdpClient`
- `UdpServer`
- `NetworkEvent`

## Message Groups

- Session：`ClientHello`、`ServerWelcome`、`JoinRejectedRoomFull`、`Heartbeat`、`DisconnectNotice`
- Queue / match：`QueueStatus`、`MatchStart`、`MatchSnapshot`、`MatchEnd`、`PlayerLeft`
- Reliable gameplay：`AttackReported`、`GarbageAssigned`、`KOReported`、`RespawnAssigned`、`ReliableAck`、`ReliableResendRequest`
- State summary：`ClientStateSummary`、`OpponentStateSummary`、`ClockSync`

## 最小可執行任務

- [ ] NET-001: 建立 protocol message dataclass
  - 輸出：`net/protocol.py`
  - 驗收：所有 message group 有 typed schema
  - 依賴：COMMON-002

- [ ] NET-002: 決策 UDP wire encoding
  - 輸出：codec fixture
  - 驗收：格式經使用者確認，不自行猜測
  - 依賴：D-NET-001

- [ ] NET-003: 實作 `MessageCodec`
  - 輸出：`net/protocol.py`
  - 驗收：dataclass encode/decode round-trip
  - 依賴：NET-001、NET-002

- [ ] NET-004: 定義 network event facade
  - 輸出：`net/protocol.py`
  - 驗收：client/server 可用同一事件類型溝通 runtime
  - 依賴：NET-003

- [ ] NET-005: 實作 reliable event envelope
  - 輸出：`net/reliability.py`
  - 驗收：包含 session、match、sender、event_seq、ack、sent_at
  - 依賴：NET-001

- [ ] NET-006: 實作去重與 ack 行為
  - 輸出：`net/reliability.py`
  - 驗收：重複 reliable event 只 ack 不重複套用
  - 依賴：NET-005

- [ ] NET-007: 決策並實作重送與 timeout policy
  - 輸出：`net/reliability.py`
  - 驗收：fake clock 驗證重送間隔與 session timeout
  - 依賴：D-NET-002、COMMON-005

- [ ] NET-008: 實作 non-reliable snapshot / summary channel
  - 輸出：`net/reliability.py`
  - 驗收：新 snapshot 覆蓋舊 snapshot，不要求 ack
  - 依賴：NET-004

- [ ] NET-009: 決策並實作 match snapshot 頻率欄位與 correction payload
  - 輸出：`net/protocol.py`
  - 驗收：payload 可被 client-runtime 消費
  - 依賴：D-NET-003

- [ ] NET-010: 實作 `UdpClient` 非阻塞 endpoint
  - 輸出：`net/udp_client.py`
  - 驗收：socket 測試可連 fake UDP server
  - 依賴：NET-003

- [ ] NET-011: 實作 `UdpServer` 非阻塞 endpoint
  - 輸出：`net/udp_server.py`
  - 驗收：socket 測試可接 fake client datagram
  - 依賴：NET-003

- [ ] NET-012: 建立 UDP loss / duplicate 模擬測試工具
  - 輸出：tests fixture
  - 驗收：reliability 測試可注入掉包與重複封包
  - 依賴：NET-006

## 獨立測試

- protocol 與 reliability 使用 fake transport。
- UDP endpoint 測試只驗證 socket 層收發，不啟動 server match logic。
