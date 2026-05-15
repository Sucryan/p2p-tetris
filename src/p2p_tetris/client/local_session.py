"""GUI-independent local single-player runtime session."""

from __future__ import annotations

from p2p_tetris.common import GameConfig
from p2p_tetris.controllers import ActionSource
from p2p_tetris.game_core import GameEngine, GameEvent, GameStateSnapshot

from p2p_tetris.client.view_models import (
    BoardViewModel,
    ConnectionState,
    ConnectionViewModel,
    GameViewModel,
    PiecePreviewViewModel,
    SoloHudViewModel,
)


class LocalGameSession:
    """Owns a local engine, action source, fixed tick count, and view model."""

    def __init__(
        self,
        action_source: ActionSource,
        *,
        seed: int | str | bytes | bytearray | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self._action_source = action_source
        self._seed = seed
        self._config = config or GameConfig()
        self._engine = GameEngine(seed=self._seed, config=self._config)
        self._tick = 0
        self._running = False
        self._paused = False
        self._view_model = self._build_view_model()

    @property
    def tick_count(self) -> int:
        return self._tick

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def view_model(self) -> GameViewModel:
        return self._view_model

    def reset(self, *, seed: int | str | bytes | bytearray | None = None) -> None:
        if seed is not None:
            self._seed = seed
        self._engine.reset(seed=self._seed, config=self._config)
        self._tick = 0
        self._running = False
        self._paused = False
        self._view_model = self._build_view_model()

    def start(self) -> None:
        self._running = True
        self._paused = False
        self._view_model = self._build_view_model()

    def pause(self) -> None:
        if self._running:
            self._paused = True
            self._view_model = self._build_view_model()

    def resume(self) -> None:
        if self._running:
            self._paused = False
            self._view_model = self._build_view_model()

    def restart(self, *, seed: int | str | bytes | bytearray | None = None) -> None:
        self.reset(seed=seed)
        self.start()

    def tick(self, ticks: int = 1) -> tuple[GameEvent, ...]:
        if ticks < 0:
            msg = "ticks must be non-negative"
            raise ValueError(msg)
        events: list[GameEvent] = []
        for _ in range(ticks):
            if not self._running or self._paused:
                break
            batch = self._action_source.pull_actions(self._tick)
            events.extend(self._engine.step(batch.actions))
            self._tick += 1
            self._view_model = self._build_view_model()
        return tuple(events)

    def run_ticks(self, ticks: int) -> tuple[GameEvent, ...]:
        return self.tick(ticks)

    def snapshot(self) -> GameStateSnapshot:
        return self._engine.snapshot()

    def _build_view_model(self) -> GameViewModel:
        snapshot = self._engine.snapshot()
        return GameViewModel(
            board=BoardViewModel.from_snapshot(
                snapshot,
                hidden_rows=self._config.hidden_rows,
            ),
            preview=PiecePreviewViewModel.from_snapshot(snapshot),
            solo_hud=SoloHudViewModel(
                score=snapshot.score,
                cleared_lines=snapshot.cleared_lines,
                combo=snapshot.combo,
                back_to_back=snapshot.back_to_back,
                tick=self._tick,
                is_running=self._running,
                is_paused=self._paused,
            ),
            connection=ConnectionViewModel(state=ConnectionState.DISCONNECTED),
        )


__all__ = ["LocalGameSession"]
