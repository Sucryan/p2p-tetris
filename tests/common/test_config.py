from __future__ import annotations

from typing import Any

import pytest

from p2p_tetris.common import GameConfig, MatchConfig, NetworkConfig


def test_game_config_defaults_match_detailed_design() -> None:
    config = GameConfig()

    assert config.board_width == 10
    assert config.visible_columns == 10
    assert config.visible_rows == 20
    assert config.hidden_rows == 20
    assert config.total_rows == 40
    assert config.next_queue_size == 5
    assert config.tick_rate_hz == 60
    assert config.lock_delay_seconds == pytest.approx(0.5)
    assert config.das_seconds == pytest.approx(0.17)
    assert config.arr_seconds == pytest.approx(0.05)
    assert config.soft_drop_rows_per_second == pytest.approx(20.0)
    assert config.gravity_rows_per_second == pytest.approx(1.0)


def test_match_config_defaults_match_detailed_design() -> None:
    config = MatchConfig()

    assert config.match_seconds == pytest.approx(120.0)
    assert config.ko_target == 3
    assert config.active_player_count == 2
    assert config.waiting_capacity == 5
    assert config.respawn_delay_seconds == pytest.approx(1.5)


def test_network_config_defaults_match_detailed_design_intervals() -> None:
    config = NetworkConfig()

    assert config.reliable_resend_seconds == pytest.approx(0.1)
    assert config.heartbeat_seconds == pytest.approx(0.5)
    assert config.session_timeout_seconds == pytest.approx(2.0)


def test_network_config_keeps_unfixed_values_explicit() -> None:
    config = NetworkConfig()

    assert config.bind_host is None
    assert config.port is None
    assert config.snapshot_rate_hz is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("board_width", 0),
        ("visible_rows", 0),
        ("hidden_rows", -1),
        ("next_queue_size", 0),
        ("tick_rate_hz", 0),
        ("lock_delay_seconds", 0.0),
        ("das_seconds", 0.0),
        ("arr_seconds", 0.0),
        ("soft_drop_rows_per_second", 0.0),
        ("gravity_rows_per_second", 0.0),
    ],
)
def test_game_config_rejects_invalid_values(field_name: str, value: int | float) -> None:
    kwargs: dict[str, Any] = {field_name: value}

    with pytest.raises(ValueError):
        GameConfig(**kwargs)


def test_network_config_rejects_invalid_optional_values() -> None:
    with pytest.raises(ValueError):
        NetworkConfig(bind_host="")
    with pytest.raises(ValueError):
        NetworkConfig(port=-1)
    with pytest.raises(ValueError):
        NetworkConfig(port=65536)
    with pytest.raises(ValueError):
        NetworkConfig(snapshot_rate_hz=0.0)
