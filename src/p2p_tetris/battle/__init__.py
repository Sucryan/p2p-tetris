"""Battle rules public interface."""

from p2p_tetris.battle.attack import AttackCalculator, AttackTable
from p2p_tetris.battle.events import (
    AttackEvent,
    GarbageEvent,
    GarbageRow,
    KOEvent,
    MatchResult,
    RespawnEvent,
    event_from_dict,
)
from p2p_tetris.battle.garbage import GarbageGenerator, GarbageQueue
from p2p_tetris.battle.match_rules import BattleCoordinator, WinnerResolver
from p2p_tetris.battle.scoring import BattleScoreboard, PlayerBattleStats

__all__ = [
    "AttackCalculator",
    "AttackEvent",
    "AttackTable",
    "BattleCoordinator",
    "BattleScoreboard",
    "GarbageEvent",
    "GarbageGenerator",
    "GarbageQueue",
    "GarbageRow",
    "KOEvent",
    "MatchResult",
    "PlayerBattleStats",
    "RespawnEvent",
    "WinnerResolver",
    "event_from_dict",
]
