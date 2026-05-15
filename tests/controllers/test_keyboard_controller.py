from __future__ import annotations

from p2p_tetris.common import GameConfig
from p2p_tetris.controllers import KeyboardController, KeyboardMapping
from p2p_tetris.game_core import PlayerAction


def test_keyboard_mapping_uses_plain_tokens() -> None:
    mapping = KeyboardMapping()

    assert mapping.move_left == "ArrowLeft"
    assert mapping.hard_drop == "Space"


def test_keyboard_controller_emits_discrete_actions_and_soft_drop_hold() -> None:
    controller = KeyboardController()

    controller.press("ArrowUp", tick=0)
    controller.press("ArrowDown", tick=0)

    assert controller.pull_actions(0).actions == (
        PlayerAction.ROTATE_CW,
        PlayerAction.SOFT_DROP,
    )
    assert controller.pull_actions(1).actions == (PlayerAction.SOFT_DROP,)

    controller.release("ArrowDown", tick=2)
    assert controller.pull_actions(2).actions == ()


def test_keyboard_controller_applies_das_and_arr_for_horizontal_repeat() -> None:
    config = GameConfig(tick_rate_hz=10, das_seconds=0.2, arr_seconds=0.1)
    controller = KeyboardController(config=config)

    controller.press("ArrowLeft", tick=0)

    assert controller.pull_actions(0).actions == (PlayerAction.MOVE_LEFT,)
    assert controller.pull_actions(1).actions == ()
    assert controller.pull_actions(2).actions == (PlayerAction.MOVE_LEFT,)
    assert controller.pull_actions(3).actions == (PlayerAction.MOVE_LEFT,)


def test_keyboard_controller_last_horizontal_pressed_wins_until_release() -> None:
    controller = KeyboardController(config=GameConfig(tick_rate_hz=10, das_seconds=0.1))

    controller.press("ArrowLeft", tick=0)
    controller.press("ArrowRight", tick=0)

    assert controller.pull_actions(0).actions == (
        PlayerAction.MOVE_LEFT,
        PlayerAction.MOVE_RIGHT,
    )
    assert controller.pull_actions(1).actions == (PlayerAction.MOVE_RIGHT,)

    controller.release("ArrowRight", tick=2)
    assert controller.pull_actions(2).actions == (PlayerAction.MOVE_LEFT,)
