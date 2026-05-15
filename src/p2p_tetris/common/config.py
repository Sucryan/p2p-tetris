"""Shared configuration value objects."""

from __future__ import annotations

from dataclasses import dataclass


def _require_positive_int(name: str, value: int) -> None:
    if value <= 0:
        msg = f"{name} must be positive"
        raise ValueError(msg)


def _require_non_negative_int(name: str, value: int) -> None:
    if value < 0:
        msg = f"{name} must be non-negative"
        raise ValueError(msg)


def _require_positive_float(name: str, value: float) -> None:
    if value <= 0:
        msg = f"{name} must be positive"
        raise ValueError(msg)


def _require_optional_positive_float(name: str, value: float | None) -> None:
    if value is not None:
        _require_positive_float(name, value)


def _require_optional_port(name: str, value: int | None) -> None:
    if value is not None and not 0 <= value <= 65535:
        msg = f"{name} must be between 0 and 65535"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Single-player board and input timing configuration."""

    board_width: int = 10
    visible_rows: int = 20
    hidden_rows: int = 20
    next_queue_size: int = 5
    tick_rate_hz: int = 60
    lock_delay_seconds: float = 0.5
    das_seconds: float = 0.17
    arr_seconds: float = 0.05
    soft_drop_rows_per_second: float = 20.0
    gravity_rows_per_second: float = 1.0

    def __post_init__(self) -> None:
        _require_positive_int("board_width", self.board_width)
        _require_positive_int("visible_rows", self.visible_rows)
        _require_non_negative_int("hidden_rows", self.hidden_rows)
        _require_positive_int("next_queue_size", self.next_queue_size)
        _require_positive_int("tick_rate_hz", self.tick_rate_hz)
        _require_positive_float("lock_delay_seconds", self.lock_delay_seconds)
        _require_positive_float("das_seconds", self.das_seconds)
        _require_positive_float("arr_seconds", self.arr_seconds)
        _require_positive_float(
            "soft_drop_rows_per_second",
            self.soft_drop_rows_per_second,
        )
        _require_positive_float("gravity_rows_per_second", self.gravity_rows_per_second)

    @property
    def total_rows(self) -> int:
        """Total internal board rows, including hidden buffer rows."""

        return self.visible_rows + self.hidden_rows

    @property
    def visible_columns(self) -> int:
        """Alias for the configured board width."""

        return self.board_width


@dataclass(frozen=True, slots=True)
class MatchConfig:
    """Versus match lifecycle configuration."""

    match_seconds: float = 120.0
    ko_target: int = 3
    active_player_count: int = 2
    waiting_capacity: int = 5
    respawn_delay_seconds: float = 1.5

    def __post_init__(self) -> None:
        _require_positive_float("match_seconds", self.match_seconds)
        _require_positive_int("ko_target", self.ko_target)
        _require_positive_int("active_player_count", self.active_player_count)
        _require_non_negative_int("waiting_capacity", self.waiting_capacity)
        _require_positive_float("respawn_delay_seconds", self.respawn_delay_seconds)


@dataclass(frozen=True, slots=True)
class NetworkConfig:
    """Network timing configuration.

    ``bind_host``, ``port``, and ``snapshot_rate_hz`` intentionally default to
    ``None`` because the current detailed design fixes interval behavior but
    does not fix deployment-specific bind values or snapshot cadence.
    """

    bind_host: str | None = None
    port: int | None = None
    reliable_resend_seconds: float = 0.1
    heartbeat_seconds: float = 0.5
    session_timeout_seconds: float = 2.0
    snapshot_rate_hz: float | None = None

    def __post_init__(self) -> None:
        if self.bind_host == "":
            msg = "bind_host must be non-empty when provided"
            raise ValueError(msg)
        _require_optional_port("port", self.port)
        _require_positive_float(
            "reliable_resend_seconds",
            self.reliable_resend_seconds,
        )
        _require_positive_float("heartbeat_seconds", self.heartbeat_seconds)
        _require_positive_float(
            "session_timeout_seconds",
            self.session_timeout_seconds,
        )
        _require_optional_positive_float("snapshot_rate_hz", self.snapshot_rate_hz)

