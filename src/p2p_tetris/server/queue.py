"""Active player and waiting queue management."""

from __future__ import annotations

from dataclasses import dataclass

from p2p_tetris.common import MatchConfig, PlayerId
from p2p_tetris.net.protocol import JoinRejectedRoomFull, QueueStatus


@dataclass(frozen=True, slots=True)
class QueueJoinResult:
    accepted: bool
    player_id: PlayerId
    status: QueueStatus | None = None
    rejection: JoinRejectedRoomFull | None = None


class QueueManager:
    def __init__(self, config: MatchConfig | None = None) -> None:
        self._config = config or MatchConfig()
        self._active: list[PlayerId] = []
        self._waiting: list[PlayerId] = []

    def join(self, player_id: PlayerId) -> QueueJoinResult:
        if player_id in self._active or player_id in self._waiting:
            return QueueJoinResult(
                accepted=True,
                player_id=player_id,
                status=self.status_for(player_id),
            )
        if len(self._active) < self._config.active_player_count:
            self._active.append(player_id)
            return QueueJoinResult(
                accepted=True,
                player_id=player_id,
                status=self.status_for(player_id),
            )
        if len(self._waiting) < self._config.waiting_capacity:
            self._waiting.append(player_id)
            return QueueJoinResult(
                accepted=True,
                player_id=player_id,
                status=self.status_for(player_id),
            )
        return QueueJoinResult(
            accepted=False,
            player_id=player_id,
            rejection=JoinRejectedRoomFull(
                player_id=player_id,
                reason="room_full",
                active_count=len(self._active),
                waiting_count=len(self._waiting),
                capacity=self.capacity,
            ),
        )

    def would_accept(self, player_id: PlayerId) -> bool:
        if player_id in self._active or player_id in self._waiting:
            return True
        return len(self._active) + len(self._waiting) < self.capacity

    def leave(self, player_id: PlayerId) -> None:
        if player_id in self._active:
            self._active.remove(player_id)
            self._promote_waiting()
        elif player_id in self._waiting:
            self._waiting.remove(player_id)

    def rotate_after_match(self, winner_id: PlayerId | None) -> None:
        if winner_id is None or winner_id not in self._active:
            self._active.clear()
        else:
            self._active = [winner_id]
        self._promote_waiting()

    def status_for(self, player_id: PlayerId) -> QueueStatus:
        position: int | None
        if player_id in self._active:
            position = 0
        elif player_id in self._waiting:
            position = self._waiting.index(player_id) + 1
        else:
            position = None
        return QueueStatus(
            player_id=player_id,
            active_players=tuple(self._active),
            waiting_players=tuple(self._waiting),
            position=position,
            room_capacity=self.capacity,
        )

    def statuses(self) -> tuple[QueueStatus, ...]:
        return tuple(self.status_for(player_id) for player_id in self.players)

    @property
    def active_players(self) -> tuple[PlayerId, ...]:
        return tuple(self._active)

    @property
    def waiting_players(self) -> tuple[PlayerId, ...]:
        return tuple(self._waiting)

    @property
    def players(self) -> tuple[PlayerId, ...]:
        return tuple([*self._active, *self._waiting])

    @property
    def capacity(self) -> int:
        return self._config.active_player_count + self._config.waiting_capacity

    def _promote_waiting(self) -> None:
        while len(self._active) < self._config.active_player_count and self._waiting:
            self._active.append(self._waiting.pop(0))
