from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol, Sequence

from .matchday_signal import MatchdayValuationSignal, apply_matchday_overlay
from .models import PlayerValueInput, ValueSnapshot
from .scoring import ValueEngine


class ValueSnapshotRepository(Protocol):
    def list_player_ids(self, as_of: datetime) -> Sequence[str]:
        ...

    def load_player_value_input(self, player_id: str, as_of: datetime, lookback_days: int) -> PlayerValueInput:
        ...

    def save_snapshot(self, snapshot: ValueSnapshot) -> None:
        ...


@dataclass(slots=True)
class ValueSnapshotJob:
    engine: ValueEngine = field(default_factory=ValueEngine)
    lookback_days: int = 7
    #: Optional source of the bounded matchday-form overlay. When supplied, each
    #: snapshot is adjusted by the player's persisted GTEX competition form after
    #: the core engine has run. Left unset, behaviour is exactly as before: the
    #: overlay is strictly additive to the existing pipeline, never a replacement.
    matchday_signal_provider: Callable[[str], MatchdayValuationSignal | None] | None = None

    def run(self, repository: ValueSnapshotRepository, as_of: datetime) -> list[ValueSnapshot]:
        snapshots: list[ValueSnapshot] = []
        for player_id in repository.list_player_ids(as_of):
            snapshot_input = repository.load_player_value_input(player_id, as_of, self.lookback_days)
            snapshot = self.engine.build_snapshot(snapshot_input)
            snapshot = self._overlay(snapshot)
            repository.save_snapshot(snapshot)
            snapshots.append(snapshot)
        return sorted(snapshots, key=lambda snapshot: snapshot.player_id)

    def _overlay(self, snapshot: ValueSnapshot) -> ValueSnapshot:
        if self.matchday_signal_provider is None:
            return snapshot
        signal = self.matchday_signal_provider(snapshot.player_id)
        if signal is None:
            return snapshot
        return apply_matchday_overlay(snapshot, signal)


@dataclass(slots=True)
class InMemoryValueSnapshotRepository:
    inputs: dict[str, PlayerValueInput]
    saved_snapshots: list[ValueSnapshot] = field(default_factory=list)

    def list_player_ids(self, as_of: datetime) -> Sequence[str]:
        return sorted(self.inputs.keys())

    def load_player_value_input(self, player_id: str, as_of: datetime, lookback_days: int) -> PlayerValueInput:
        return self.inputs[player_id]

    def save_snapshot(self, snapshot: ValueSnapshot) -> None:
        self.saved_snapshots.append(snapshot)
