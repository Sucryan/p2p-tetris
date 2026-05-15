"""Plain-token keyboard controller with DAS/ARR repeat behavior."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import GameConfig
from p2p_tetris.controllers.base import ActionBatch
from p2p_tetris.game_core.actions import PlayerAction


@dataclass(frozen=True, slots=True)
class KeyboardMapping:
    """Default key tokens are strings so GUI layers can adapt any toolkit."""

    move_left: str = "ArrowLeft"
    move_right: str = "ArrowRight"
    soft_drop: str = "ArrowDown"
    hard_drop: str = "Space"
    rotate_cw: str = "ArrowUp"
    rotate_ccw: str = "KeyZ"
    hold: str = "KeyC"


@dataclass(slots=True)
class _KeyState:
    pressed_at_tick: int
    last_repeat_tick: int


class KeyboardController:
    """Convert key press/release tokens into gameplay actions."""

    def __init__(
        self,
        *,
        mapping: KeyboardMapping | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self.mapping = mapping or KeyboardMapping()
        self.config = config or GameConfig()
        self._pressed: dict[str, _KeyState] = {}
        self._queued_discrete: list[PlayerAction] = []
        self._last_horizontal: str | None = None
        self._das_ticks = max(1, round(self.config.das_seconds * self.config.tick_rate_hz))
        self._arr_ticks = max(1, round(self.config.arr_seconds * self.config.tick_rate_hz))

    def press(self, key_token: str, *, tick: int) -> None:
        self._require_tick(tick)
        if key_token in self._pressed:
            return
        self._pressed[key_token] = _KeyState(pressed_at_tick=tick, last_repeat_tick=tick)
        action = self._press_action(key_token)
        if action is not None:
            self._queued_discrete.append(action)
        if key_token in {self.mapping.move_left, self.mapping.move_right}:
            self._last_horizontal = key_token

    def release(self, key_token: str, *, tick: int) -> None:
        self._require_tick(tick)
        self._pressed.pop(key_token, None)
        if key_token == self._last_horizontal:
            self._last_horizontal = self._other_pressed_horizontal(key_token)

    def pull_actions(self, tick: int) -> ActionBatch:
        self._require_tick(tick)
        actions: list[PlayerAction] = []
        actions.extend(self._queued_discrete)
        self._queued_discrete.clear()

        horizontal = self._active_horizontal()
        if horizontal is not None and self._should_repeat(horizontal, tick):
            actions.append(self._horizontal_action(horizontal))

        if self.mapping.soft_drop in self._pressed:
            actions.append(PlayerAction.SOFT_DROP)

        return ActionBatch(tick=tick, actions=tuple(actions))

    def _press_action(self, key_token: str) -> PlayerAction | None:
        if key_token == self.mapping.move_left:
            return PlayerAction.MOVE_LEFT
        if key_token == self.mapping.move_right:
            return PlayerAction.MOVE_RIGHT
        if key_token == self.mapping.hard_drop:
            return PlayerAction.HARD_DROP
        if key_token == self.mapping.rotate_cw:
            return PlayerAction.ROTATE_CW
        if key_token == self.mapping.rotate_ccw:
            return PlayerAction.ROTATE_CCW
        if key_token == self.mapping.hold:
            return PlayerAction.HOLD
        return None

    def _active_horizontal(self) -> str | None:
        if self._last_horizontal in self._pressed:
            return self._last_horizontal
        return self._other_pressed_horizontal("")

    def _other_pressed_horizontal(self, released: str) -> str | None:
        candidates = (self.mapping.move_right, self.mapping.move_left)
        for key_token in candidates:
            if key_token != released and key_token in self._pressed:
                return key_token
        return None

    def _should_repeat(self, key_token: str, tick: int) -> bool:
        state = self._pressed[key_token]
        if tick - state.pressed_at_tick < self._das_ticks:
            return False
        if tick - state.last_repeat_tick < self._arr_ticks:
            return False
        state.last_repeat_tick = tick
        return True

    def _horizontal_action(self, key_token: str) -> PlayerAction:
        if key_token == self.mapping.move_left:
            return PlayerAction.MOVE_LEFT
        return PlayerAction.MOVE_RIGHT

    @staticmethod
    def _require_tick(tick: int) -> None:
        if tick < 0:
            msg = "tick must be non-negative"
            raise ValueError(msg)


__all__ = ["KeyboardController", "KeyboardMapping"]
