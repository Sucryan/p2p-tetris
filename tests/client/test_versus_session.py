from __future__ import annotations

from dataclasses import dataclass, field

from p2p_tetris.client import ConnectionState, VersusGameSession
from p2p_tetris.common import MatchId, PlayerId, SessionId
from p2p_tetris.controllers import ScriptedController
from p2p_tetris.game_core import ClearEvent, PieceType, PlayerAction, TSpinType, TopOutEvent
from p2p_tetris.net import (
    AttackReported,
    GarbageAssigned,
    KOReported,
    MatchEnd,
    MatchSnapshot,
    MatchStart,
    OpponentStateSummary,
    ProtocolMessage,
    ReliableAck,
    RespawnAssigned,
)


@dataclass(slots=True)
class FakeNetClient:
    incoming: list[ProtocolMessage] = field(default_factory=list)
    sent: list[ProtocolMessage] = field(default_factory=list)

    def send(self, message: ProtocolMessage) -> None:
        self.sent.append(message)

    def receive(self) -> tuple[ProtocolMessage, ...]:
        messages = tuple(self.incoming)
        self.incoming.clear()
        return messages


LOCAL = PlayerId("p1")
OPPONENT = PlayerId("p2")
SESSION = SessionId("s1")
MATCH = MatchId("m1")


def _match_start() -> MatchStart:
    return MatchStart(
        match_id=MATCH,
        active_players=(LOCAL, OPPONENT),
        match_seconds=120.0,
        ko_target=3,
        seed=42,
        server_time=0.0,
    )


def test_match_start_initializes_engine_and_versus_view_model() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )

    session.handle_server_message(_match_start())

    assert session.view_model.connection.state is ConnectionState.IN_MATCH
    assert session.view_model.versus_hud is not None
    assert session.view_model.versus_hud.opponent_player_id == OPPONENT
    assert session.view_model.versus_hud.ko_counts == {"p1": 0, "p2": 0}


def test_local_clear_reports_attack_to_net_client() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({0: (PlayerAction.HARD_DROP,)}),
        net_client=net,
    )
    session.handle_server_message(_match_start())

    session.handle_local_game_events((ClearEvent(4, TSpinType.NONE, 0, False),))

    attack = next(message for message in net.sent if isinstance(message, AttackReported))
    assert attack.match_id == MATCH
    assert attack.sender_id == LOCAL
    assert attack.target_id == OPPONENT
    assert attack.lines == 4
    assert attack.attack_id == "m1:p1:attack:0"


def test_top_out_reports_ko_to_net_client() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )
    session.handle_server_message(_match_start())

    session.handle_local_game_events((TopOutEvent("spawn blocked"),))

    ko = next(message for message in net.sent if isinstance(message, KOReported))
    assert ko.match_id == MATCH
    assert ko.sender_id == LOCAL
    assert ko.victim_id == LOCAL


def test_garbage_assignment_is_pending_until_next_lock_then_applied() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({0: (PlayerAction.HARD_DROP,)}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    session.handle_server_message(
        GarbageAssigned(SESSION, MATCH, OPPONENT, LOCAL, 10, 2, 3, "g1", "a1"),
    )

    assert session.pending_garbage_lines == 2
    session.tick()

    assert session.pending_garbage_lines == 0
    visible = session.snapshot().visible_board
    assert visible[-1][3] is None
    assert visible[-1][2] is PieceType.Z


def test_duplicate_garbage_assignment_is_acked_but_not_applied_twice() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    assigned = GarbageAssigned(SESSION, MATCH, OPPONENT, LOCAL, 10, 2, 3, "g1", "a1")

    session.handle_server_message(assigned)
    session.handle_server_message(assigned)

    acks = [message for message in net.sent if isinstance(message, ReliableAck)]
    assert len(acks) == 2
    assert acks[0].sender_id == LOCAL
    assert acks[0].acked_sender_id == OPPONENT
    assert acks[0].received_seq == 10
    assert session.pending_garbage_lines == 2
    assert session.view_model.board.pending_garbage_lines == 2


def test_garbage_assignment_can_cancel_existing_pending_lines() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    session.handle_server_message(
        GarbageAssigned(SESSION, MATCH, OPPONENT, LOCAL, 10, 4, 3, "g1", "a1"),
    )

    session.handle_server_message(
        GarbageAssigned(
            SESSION,
            MATCH,
            LOCAL,
            LOCAL,
            11,
            0,
            0,
            "cancel",
            "a2",
            canceled_lines=3,
        ),
    )

    assert session.pending_garbage_lines == 1


def test_duplicate_garbage_cancellation_is_not_applied_twice() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    session.handle_server_message(
        GarbageAssigned(SESSION, MATCH, OPPONENT, LOCAL, 10, 4, 3, "g1", "a1"),
    )
    cancellation = GarbageAssigned(
        SESSION,
        MATCH,
        LOCAL,
        LOCAL,
        11,
        0,
        0,
        "cancel",
        "a2",
        canceled_lines=3,
    )

    session.handle_server_message(cancellation)
    session.handle_server_message(cancellation)

    assert session.pending_garbage_lines == 1


def test_respawn_assignment_resets_local_engine() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({0: (PlayerAction.HARD_DROP,)}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    before = session.snapshot()
    session.tick()
    assert session.snapshot() != before

    session.handle_server_message(RespawnAssigned(SESSION, MATCH, OPPONENT, LOCAL, 11, 3.0))

    assert session.pending_garbage_lines == 0
    assert not session.snapshot().top_out
    assert session.snapshot() != before


def test_snapshot_opponent_summary_and_match_end_update_view_models() -> None:
    net = FakeNetClient()
    session = VersusGameSession(
        session_id=SESSION,
        player_id=LOCAL,
        action_source=ScriptedController({}),
        net_client=net,
    )
    session.handle_server_message(_match_start())
    session.handle_server_message(
        MatchSnapshot(
            MATCH,
            7,
            10.0,
            95.0,
            {"p1": 1, "p2": 2},
            {"p1": 4, "p2": 8},
            {"server": "accepted"},
        ),
    )
    session.handle_server_message(
        OpponentStateSummary(
            SESSION,
            MATCH,
            LOCAL,
            OPPONENT,
            3,
            8,
            2,
            2,
            8,
            True,
            {"well": [4]},
        ),
    )
    session.handle_server_message(
        MatchEnd(MATCH, OPPONENT, "timeout", {"p1": 1, "p2": 2}, {"p1": 4, "p2": 8}, 120.0),
    )

    assert session.last_correction is not None
    assert session.last_correction.correction == {"server": "accepted"}
    assert session.view_model.versus_hud is not None
    assert session.view_model.versus_hud.remaining_seconds == 95.0
    assert session.view_model.opponents[0].player_id == OPPONENT
    assert session.view_model.result is not None
    assert session.view_model.result.winner_id == OPPONENT
    assert session.view_model.connection.state is ConnectionState.ENDED
