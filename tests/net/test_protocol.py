from __future__ import annotations

from typing import cast

import pytest

from p2p_tetris.common import MatchId, PlayerId, SessionId
from p2p_tetris.net import (
    AttackReported,
    ClientHello,
    ClientStateSummary,
    ClockSync,
    DisconnectNotice,
    GarbageAssigned,
    Heartbeat,
    JoinRejectedRoomFull,
    KOReported,
    MatchEnd,
    MatchSnapshot,
    MatchStart,
    MessageCodec,
    MessageCodecError,
    OpponentStateSummary,
    PlayerLeft,
    ProtocolMessage,
    QueueStatus,
    ReliableAck,
    ReliableResendRequest,
    RespawnAssigned,
    ServerWelcome,
)


def test_codec_round_trips_all_protocol_messages() -> None:
    codec = MessageCodec()
    player = PlayerId("p1")
    opponent = PlayerId("p2")
    session = SessionId("s1")
    match = MatchId("m1")
    messages: list[ProtocolMessage] = [
        ClientHello(player, "Ada"),
        ServerWelcome(session, player, 0.5, 1.0),
        JoinRejectedRoomFull(player, "room_full", 2, 5, 7),
        Heartbeat(session, player, 1.2),
        DisconnectNotice(session, player, "quit"),
        QueueStatus(player, (player, opponent), (), 0, 7),
        MatchStart(match, (player, opponent), 120.0, 3, 42, 2.0),
        MatchSnapshot(match, 1, 2.0, 118.0, {"p1": 0}, {"p1": 4}, {"timer": 118}, 20.0),
        MatchEnd(match, player, "timeout", {"p1": 1}, {"p1": 8}, 120.0),
        PlayerLeft(player, "timeout", match),
        AttackReported(session, match, player, opponent, 1, 4, "a1", 2, True),
        GarbageAssigned(session, match, player, opponent, 2, 4, 3, "g1", "a1"),
        KOReported(session, match, player, opponent, 3),
        RespawnAssigned(session, match, player, opponent, 4, 5.0),
        ReliableAck(session, opponent, player, 1, match),
        ReliableResendRequest(session, opponent, player, 1, match),
        ClientStateSummary(session, match, player, 1, 8, 2, 0, 4, True, {"well": [1, 2]}),
        OpponentStateSummary(session, match, opponent, player, 1, 8, 2, 0, 4, True, {}),
        ClockSync(1.0, 1.1, session),
    ]

    for message in messages:
        assert codec.decode(codec.encode(message)) == message


def test_codec_rejects_dict_leakage_and_unknown_type() -> None:
    codec = MessageCodec()

    with pytest.raises(TypeError):
        codec.encode(cast(ProtocolMessage, {"type": "ClientHello"}))

    with pytest.raises(MessageCodecError):
        codec.decode(b'{"type":"Unknown","payload":{}}')
