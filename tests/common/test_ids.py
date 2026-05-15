from __future__ import annotations

from typing import Any, cast

import pytest

from p2p_tetris.common import MatchId, PlayerId, SessionId


def test_ids_are_value_objects_with_string_representation() -> None:
    player_id = PlayerId("player-1")

    assert player_id.value == "player-1"
    assert str(player_id) == "player-1"
    assert player_id == PlayerId("player-1")
    assert player_id != PlayerId("player-2")


def test_id_types_do_not_compare_equal_across_domains_or_raw_values() -> None:
    player_id = PlayerId("same")

    assert player_id != SessionId("same")
    assert player_id != MatchId("same")
    assert player_id != "same"
    assert player_id != 1


def test_ids_reject_empty_or_non_string_values() -> None:
    with pytest.raises(ValueError):
        PlayerId("")

    with pytest.raises(TypeError):
        PlayerId(cast(Any, 1))


def test_new_ids_are_non_empty_and_typed() -> None:
    player_id = PlayerId.new()
    session_id = SessionId.new()
    match_id = MatchId.new()

    assert isinstance(player_id, PlayerId)
    assert isinstance(session_id, SessionId)
    assert isinstance(match_id, MatchId)
    assert player_id.value
    assert session_id.value
    assert match_id.value
