"""Typed UDP protocol messages and JSON codec."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from types import UnionType
from typing import Any, Literal, Protocol, Union, get_args, get_origin, get_type_hints

from p2p_tetris.common import MatchId, PlayerId, SessionId

Address = tuple[str, int]
JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ClientHello:
    player_id: PlayerId
    display_name: str = ""
    protocol_version: int = 1


@dataclass(frozen=True, slots=True)
class ServerWelcome:
    session_id: SessionId
    player_id: PlayerId
    heartbeat_seconds: float
    server_time: float


@dataclass(frozen=True, slots=True)
class JoinRejectedRoomFull:
    player_id: PlayerId
    reason: str
    active_count: int
    waiting_count: int
    capacity: int


@dataclass(frozen=True, slots=True)
class Heartbeat:
    session_id: SessionId
    player_id: PlayerId
    sent_at: float


@dataclass(frozen=True, slots=True)
class DisconnectNotice:
    session_id: SessionId
    player_id: PlayerId
    reason: str = "disconnect"


@dataclass(frozen=True, slots=True)
class QueueStatus:
    player_id: PlayerId
    active_players: tuple[PlayerId, ...]
    waiting_players: tuple[PlayerId, ...]
    position: int | None
    room_capacity: int


@dataclass(frozen=True, slots=True)
class MatchStart:
    match_id: MatchId
    active_players: tuple[PlayerId, ...]
    match_seconds: float
    ko_target: int
    seed: int
    server_time: float


@dataclass(frozen=True, slots=True)
class MatchSnapshot:
    match_id: MatchId
    sequence: int
    server_time: float
    remaining_seconds: float
    ko_counts: dict[str, int]
    sent_lines: dict[str, int]
    correction: JsonObject
    snapshot_rate_hz: float | None = None


@dataclass(frozen=True, slots=True)
class MatchEnd:
    match_id: MatchId
    winner_id: PlayerId | None
    reason: Literal["ko_target", "timeout", "player_left", "draw"]
    ko_counts: dict[str, int]
    sent_lines: dict[str, int]
    server_time: float


@dataclass(frozen=True, slots=True)
class PlayerLeft:
    player_id: PlayerId
    reason: str
    match_id: MatchId | None = None


@dataclass(frozen=True, slots=True)
class AttackReported:
    session_id: SessionId
    match_id: MatchId
    sender_id: PlayerId
    target_id: PlayerId | None
    event_seq: int
    lines: int
    attack_id: str
    combo: int = 0
    back_to_back: bool = False


@dataclass(frozen=True, slots=True)
class GarbageAssigned:
    session_id: SessionId
    match_id: MatchId
    sender_id: PlayerId
    target_id: PlayerId
    event_seq: int
    lines: int
    hole_column: int
    garbage_id: str
    source_attack_id: str
    canceled_lines: int = 0


@dataclass(frozen=True, slots=True)
class KOReported:
    session_id: SessionId
    match_id: MatchId
    sender_id: PlayerId
    victim_id: PlayerId
    event_seq: int


@dataclass(frozen=True, slots=True)
class RespawnAssigned:
    session_id: SessionId
    match_id: MatchId
    sender_id: PlayerId
    target_id: PlayerId
    event_seq: int
    respawn_at: float


@dataclass(frozen=True, slots=True)
class ReliableAck:
    session_id: SessionId
    sender_id: PlayerId
    acked_sender_id: PlayerId
    received_seq: int
    match_id: MatchId | None = None


@dataclass(frozen=True, slots=True)
class ReliableResendRequest:
    session_id: SessionId
    sender_id: PlayerId
    requested_sender_id: PlayerId
    requested_seq: int
    match_id: MatchId | None = None


@dataclass(frozen=True, slots=True)
class ClientStateSummary:
    session_id: SessionId
    match_id: MatchId
    player_id: PlayerId
    summary_seq: int
    board_height: int
    pending_garbage: int
    ko_count: int
    sent_lines: int
    is_alive: bool
    extra: JsonObject


@dataclass(frozen=True, slots=True)
class OpponentStateSummary:
    session_id: SessionId
    match_id: MatchId
    player_id: PlayerId
    opponent_id: PlayerId
    summary_seq: int
    board_height: int
    pending_garbage: int
    ko_count: int
    sent_lines: int
    is_alive: bool
    extra: JsonObject


@dataclass(frozen=True, slots=True)
class ClockSync:
    client_time: float
    server_time: float
    session_id: SessionId | None = None


ProtocolMessage = (
    ClientHello
    | ServerWelcome
    | JoinRejectedRoomFull
    | Heartbeat
    | DisconnectNotice
    | QueueStatus
    | MatchStart
    | MatchSnapshot
    | MatchEnd
    | PlayerLeft
    | AttackReported
    | GarbageAssigned
    | KOReported
    | RespawnAssigned
    | ReliableAck
    | ReliableResendRequest
    | ClientStateSummary
    | OpponentStateSummary
    | ClockSync
)

ReliableGameplayMessage = AttackReported | GarbageAssigned | KOReported | RespawnAssigned
StateSummaryMessage = ClientStateSummary | OpponentStateSummary | MatchSnapshot

_MESSAGE_TYPES: dict[str, type[ProtocolMessage]] = {
    cls.__name__: cls
    for cls in (
        ClientHello,
        ServerWelcome,
        JoinRejectedRoomFull,
        Heartbeat,
        DisconnectNotice,
        QueueStatus,
        MatchStart,
        MatchSnapshot,
        MatchEnd,
        PlayerLeft,
        AttackReported,
        GarbageAssigned,
        KOReported,
        RespawnAssigned,
        ReliableAck,
        ReliableResendRequest,
        ClientStateSummary,
        OpponentStateSummary,
        ClockSync,
    )
}


@dataclass(frozen=True, slots=True)
class NetworkEvent:
    message: ProtocolMessage
    endpoint: Address
    received_at: float


class MessageCodecError(ValueError):
    """Raised when a datagram cannot be decoded as a protocol message."""


class MessageCodec:
    """Encode and decode typed protocol dataclasses as UTF-8 JSON datagrams."""

    def encode(self, message: ProtocolMessage) -> bytes:
        if not is_dataclass(message):
            msg = "message must be a protocol dataclass"
            raise TypeError(msg)
        payload: JsonObject = {
            "type": type(message).__name__,
            "payload": {
                field.name: _to_json_value(getattr(message, field.name))
                for field in fields(message)
            },
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def decode(self, datagram: bytes) -> ProtocolMessage:
        try:
            raw = json.loads(datagram.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            msg = "datagram is not valid UTF-8 JSON"
            raise MessageCodecError(msg) from exc
        if not isinstance(raw, dict):
            msg = "protocol datagram must be a JSON object"
            raise MessageCodecError(msg)
        message_type = raw.get("type")
        payload = raw.get("payload")
        if not isinstance(message_type, str) or message_type not in _MESSAGE_TYPES:
            msg = "protocol datagram has unknown message type"
            raise MessageCodecError(msg)
        if not isinstance(payload, dict):
            msg = "protocol datagram payload must be a JSON object"
            raise MessageCodecError(msg)
        return _message_from_payload(_MESSAGE_TYPES[message_type], payload)


class TransportEndpoint(Protocol):
    def send(self, message: ProtocolMessage, endpoint: Address) -> None: ...

    def receive(self, max_datagrams: int = 100) -> list[NetworkEvent]: ...


def _to_json_value(value: Any) -> JsonValue:
    if isinstance(value, PlayerId | SessionId | MatchId):
        return value.value
    if isinstance(value, tuple | list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    msg = f"unsupported protocol value {value!r}"
    raise TypeError(msg)


def _message_from_payload(
    message_type: type[ProtocolMessage],
    payload: dict[str, Any],
) -> ProtocolMessage:
    field_values: dict[str, Any] = {}
    type_hints = get_type_hints(message_type)
    valid_fields = {field.name for field in fields(message_type)}
    extra_fields = set(payload) - valid_fields
    if extra_fields:
        msg = f"unexpected field(s) for {message_type.__name__}: {sorted(extra_fields)}"
        raise MessageCodecError(msg)
    for field in fields(message_type):
        if field.name not in payload:
            msg = f"missing field {field.name!r} for {message_type.__name__}"
            raise MessageCodecError(msg)
        field_values[field.name] = _coerce_field(payload[field.name], type_hints[field.name])
    return message_type(**field_values)


def _coerce_field(value: Any, annotation: Any) -> Any:
    if annotation is PlayerId:
        return _coerce_id(value, PlayerId)
    if annotation is SessionId:
        return _coerce_id(value, SessionId)
    if annotation is MatchId:
        return _coerce_id(value, MatchId)
    if _is_json_value_annotation(annotation):
        return _coerce_json_value(value)
    if annotation in {str, int, float, bool}:
        if not isinstance(value, annotation):
            msg = f"expected {annotation.__name__}, got {type(value).__name__}"
            raise MessageCodecError(msg)
        return value
    if annotation is JsonObject:
        if not isinstance(value, dict):
            msg = "expected JSON object"
            raise MessageCodecError(msg)
        return _coerce_json_object(value)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        if value not in args:
            msg = f"unexpected literal value {value!r}"
            raise MessageCodecError(msg)
        return value
    if origin is tuple:
        if not isinstance(value, list):
            msg = "expected JSON array for tuple field"
            raise MessageCodecError(msg)
        item_type = args[0]
        return tuple(_coerce_field(item, item_type) for item in value)
    if origin is dict:
        if not isinstance(value, dict):
            msg = "expected JSON object for dict field"
            raise MessageCodecError(msg)
        key_type, item_type = args
        if key_type is not str:
            msg = "protocol dict keys must be strings"
            raise MessageCodecError(msg)
        if _is_json_value_annotation(item_type):
            return _coerce_json_object(value)
        return {str(key): _coerce_field(item, item_type) for key, item in value.items()}
    if origin in {Union, UnionType}:
        if value is None and type(None) in args:
            return None
        errors: list[Exception] = []
        for arg in args:
            if arg is type(None):
                continue
            try:
                return _coerce_field(value, arg)
            except MessageCodecError as exc:
                errors.append(exc)
        msg = f"value {value!r} did not match any union type"
        raise MessageCodecError(msg) from errors[-1] if errors else None
    if annotation is Any:
        return value
    msg = f"unsupported protocol annotation {annotation!r}"
    raise MessageCodecError(msg)


def _is_json_value_annotation(annotation: Any) -> bool:
    return annotation is JsonValue or "JsonValue" in repr(annotation)


def _coerce_id(value: Any, id_type: type[PlayerId] | type[SessionId] | type[MatchId]) -> Any:
    if not isinstance(value, str):
        msg = f"expected string for {id_type.__name__}"
        raise MessageCodecError(msg)
    return id_type(value)


def _coerce_json_object(value: dict[str, Any]) -> JsonObject:
    return {str(key): _coerce_json_value(item) for key, item in value.items()}


def _coerce_json_value(value: Any) -> JsonValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_coerce_json_value(item) for item in value]
    if isinstance(value, dict):
        return _coerce_json_object(value)
    msg = f"unsupported JSON value {value!r}"
    raise MessageCodecError(msg)
