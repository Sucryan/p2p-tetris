"""Pure battle match lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.battle._game_core_events import ClearEventLike, TopOutEventLike
from p2p_tetris.battle.attack import AttackCalculator
from p2p_tetris.battle.events import (
    AttackEvent,
    BattleEventPayload,
    GarbageEvent,
    KOEvent,
    MatchResult,
    RespawnEvent,
)
from p2p_tetris.battle.garbage import GarbageGenerator, GarbageQueue
from p2p_tetris.battle.scoring import BattleScoreboard, PlayerBattleStats
from p2p_tetris.common import MatchConfig, MonotonicClock, PlayerId


@dataclass(frozen=True, slots=True)
class _RespawnTimer:
    player: PlayerId
    due_at: float


class WinnerResolver:
    """Resolve a finished two-player match."""

    def resolve(
        self,
        *,
        stats: tuple[PlayerBattleStats, PlayerBattleStats],
        reason: str,
        seq: int,
    ) -> MatchResult:
        first, second = stats
        winner = self._leader(first, second)
        if winner is None:
            return MatchResult(source=None, seq=seq, winner=None, is_draw=True, reason=reason)
        return MatchResult(source=winner.player, seq=seq, winner=winner.player, is_draw=False, reason=reason)

    def _leader(
        self,
        first: PlayerBattleStats,
        second: PlayerBattleStats,
    ) -> PlayerBattleStats | None:
        comparisons = (
            (first.ko_count, second.ko_count, True),
            (first.sent_lines, second.sent_lines, True),
            (first.board_height, second.board_height, False),
        )
        for first_value, second_value, higher_wins in comparisons:
            if first_value == second_value:
                continue
            first_wins = first_value > second_value if higher_wins else first_value < second_value
            return first if first_wins else second
        return None


class BattleCoordinator:
    """Pure event facade for simulating match-level battle rules."""

    def __init__(
        self,
        *,
        players: tuple[PlayerId, PlayerId],
        clock: MonotonicClock,
        config: MatchConfig | None = None,
        attack_calculator: AttackCalculator | None = None,
        garbage_generator: GarbageGenerator | None = None,
        garbage_delay_seconds: float = 0.0,
    ) -> None:
        if players[0] == players[1]:
            msg = "players must be distinct"
            raise ValueError(msg)
        self._players = players
        self._clock = clock
        self._config = config or MatchConfig()
        self._attack_calculator = attack_calculator or AttackCalculator()
        self._garbage_generator = garbage_generator or GarbageGenerator()
        self._queues = {
            player: GarbageQueue(clock, apply_delay_seconds=garbage_delay_seconds) for player in players
        }
        self._scoreboard = BattleScoreboard(players)
        self._winner_resolver = WinnerResolver()
        self._respawn_timers: dict[PlayerId, _RespawnTimer] = {}
        self._seq = 0

    @property
    def scoreboard(self) -> BattleScoreboard:
        return self._scoreboard

    def handle_clear(
        self,
        player: PlayerId,
        clear_event: ClearEventLike,
        *,
        board_height: int | None = None,
    ) -> tuple[BattleEventPayload, ...]:
        self._require_player(player)
        if board_height is not None:
            self._scoreboard.record_board_height(player, board_height)
        opponent = self._opponent(player)
        attack = self._attack_calculator.calculate(
            clear_event,
            source=player,
            target=opponent,
            seq=self._next_seq(),
        )
        if attack.lines == 0:
            return (attack,)
        outgoing = self._queues[player].cancel_with_attack(attack)
        if outgoing is None:
            return (attack,)
        garbage = self._garbage_generator.generate(
            source=player,
            target=opponent,
            lines=outgoing.lines,
            seq=self._next_seq(),
        )
        self._queues[opponent].enqueue(garbage)
        self._scoreboard.record_sent_lines(player, outgoing.lines)
        if outgoing.lines == attack.lines:
            return (attack, garbage)
        canceled_attack = AttackEvent(
            source=attack.source,
            seq=attack.seq,
            target=attack.target,
            lines=outgoing.lines,
        )
        return (canceled_attack, garbage)

    def handle_lock(self, player: PlayerId, *, board_height: int | None = None) -> tuple[GarbageEvent, ...]:
        self._require_player(player)
        if board_height is not None:
            self._scoreboard.record_board_height(player, board_height)
        return self._queues[player].pop_ready_after_lock()

    def handle_top_out(
        self,
        player: PlayerId,
        top_out_event: TopOutEventLike,
        *,
        board_height: int | None = None,
    ) -> tuple[BattleEventPayload, ...]:
        self._require_player(player)
        if board_height is not None:
            self._scoreboard.record_board_height(player, board_height)
        scorer = self._opponent(player)
        self._scoreboard.record_ko(scorer)
        self._queues[player].reset()
        respawn_at = self._clock.now() + self._config.respawn_delay_seconds
        self._respawn_timers[player] = _RespawnTimer(player=player, due_at=respawn_at)
        ko_event = KOEvent(
            source=scorer,
            seq=self._next_seq(),
            knocked_out=player,
            respawn_at=respawn_at,
            reason=top_out_event.reason,
        )
        if self._scoreboard[scorer].ko_count >= self._config.ko_target:
            result = self._winner_resolver.resolve(
                stats=(self._scoreboard[self._players[0]], self._scoreboard[self._players[1]]),
                reason="ko_target",
                seq=self._next_seq(),
            )
            return (ko_event, result)
        return (ko_event,)

    def tick(self) -> tuple[RespawnEvent, ...]:
        now = self._clock.now()
        due_players = tuple(
            player for player, timer in self._respawn_timers.items() if timer.due_at <= now
        )
        events: list[RespawnEvent] = []
        for player in due_players:
            del self._respawn_timers[player]
            self._queues[player].reset()
            events.append(RespawnEvent(source=player, seq=self._next_seq(), player=player))
        return tuple(events)

    def resolve_timeout(self, *, board_heights: dict[PlayerId, int] | None = None) -> MatchResult:
        if board_heights is not None:
            for player, board_height in board_heights.items():
                self._require_player(player)
                self._scoreboard.record_board_height(player, board_height)
        return self._winner_resolver.resolve(
            stats=(self._scoreboard[self._players[0]], self._scoreboard[self._players[1]]),
            reason="timeout",
            seq=self._next_seq(),
        )

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def _opponent(self, player: PlayerId) -> PlayerId:
        self._require_player(player)
        return self._players[1] if self._players[0] == player else self._players[0]

    def _require_player(self, player: PlayerId) -> None:
        if player not in self._players:
            msg = f"unknown player: {player.value}"
            raise ValueError(msg)


__all__ = ["BattleCoordinator", "WinnerResolver"]
