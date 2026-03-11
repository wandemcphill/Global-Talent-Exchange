from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, Sequence

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

    def run(self, repository: ValueSnapshotRepository, as_of: datetime) -> list[ValueSnapshot]:
        snapshots: list[ValueSnapshot] = []
        for player_id in repository.list_player_ids(as_of):
            snapshot_input = repository.load_player_value_input(player_id, as_of, self.lookback_days)
            snapshot = self.engine.build_snapshot(snapshot_input)
            repository.save_snapshot(snapshot)
            snapshots.append(snapshot)
        return sorted(snapshots, key=lambda snapshot: snapshot.player_id)


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
