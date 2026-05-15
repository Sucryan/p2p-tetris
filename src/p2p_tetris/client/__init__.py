"""Client runtime public API."""

from p2p_tetris.client.events import ClientRuntimeEvent
from p2p_tetris.client.local_session import LocalGameSession
from p2p_tetris.client.network import UdpNetClient
from p2p_tetris.client.network_session import (
    ClientNetworkRuntime,
    ConnectedNetClient,
    NetworkRuntimeUpdate,
    ServerAddress,
)
from p2p_tetris.client.versus_session import (
    NetClientPort,
    SnapshotCorrection,
    VersusGameSession,
)
from p2p_tetris.client.view_models import (
    BoardViewModel,
    ConnectionState,
    ConnectionViewModel,
    GameViewModel,
    MatchResultViewModel,
    OpponentViewModel,
    PiecePreviewViewModel,
    SoloHudViewModel,
    VersusHudViewModel,
    board_height,
)

__all__ = [
    "BoardViewModel",
    "ClientRuntimeEvent",
    "ClientNetworkRuntime",
    "ConnectionState",
    "ConnectionViewModel",
    "ConnectedNetClient",
    "GameViewModel",
    "LocalGameSession",
    "MatchResultViewModel",
    "NetClientPort",
    "NetworkRuntimeUpdate",
    "OpponentViewModel",
    "PiecePreviewViewModel",
    "SnapshotCorrection",
    "ServerAddress",
    "SoloHudViewModel",
    "UdpNetClient",
    "VersusGameSession",
    "VersusHudViewModel",
    "board_height",
]
