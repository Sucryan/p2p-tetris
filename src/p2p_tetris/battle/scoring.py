"""Battle counters for KO and sent garbage lines."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import PlayerId


@dataclass(slots=True)
class PlayerBattleStats:
    player: PlayerId
    ko_count: int = 0
    sent_lines: int = 0
    board_height: int = 0

    def __post_init__(self) -> None:
        self.set_board_height(self.board_height)

    def add_ko(self, amount: int = 1) -> None:
        if amount < 0:
            msg = "amount must be non-negative"
            raise ValueError(msg)
        self.ko_count += amount

    def add_sent_lines(self, lines: int) -> None:
        if lines < 0:
            msg = "lines must be non-negative"
            raise ValueError(msg)
        self.sent_lines += lines

    def set_board_height(self, board_height: int) -> None:
        if board_height < 0:
            msg = "board_height must be non-negative"
            raise ValueError(msg)
        self.board_height = board_height


class BattleScoreboard:
    """Mutable match counters keyed by player id."""

    def __init__(self, players: tuple[PlayerId, ...]) -> None:
        if len(set(players)) != len(players):
            msg = "players must be unique"
            raise ValueError(msg)
        self._stats = {player: PlayerBattleStats(player=player) for player in players}

    def __getitem__(self, player: PlayerId) -> PlayerBattleStats:
        return self._stats[player]

    @property
    def players(self) -> tuple[PlayerId, ...]:
        return tuple(self._stats)

    def record_sent_lines(self, player: PlayerId, lines: int) -> None:
        self[player].add_sent_lines(lines)

    def record_ko(self, player: PlayerId) -> None:
        self[player].add_ko()

    def record_board_height(self, player: PlayerId, board_height: int) -> None:
        self[player].set_board_height(board_height)

    def snapshot(self) -> dict[PlayerId, PlayerBattleStats]:
        return {
            player: PlayerBattleStats(
                player=stats.player,
                ko_count=stats.ko_count,
                sent_lines=stats.sent_lines,
                board_height=stats.board_height,
            )
            for player, stats in self._stats.items()
        }


__all__ = ["BattleScoreboard", "PlayerBattleStats"]
