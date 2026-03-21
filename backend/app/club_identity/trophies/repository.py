from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Protocol

from app.club_identity.models.trophy_models import (
    ClubTrophyWin,
    SeasonHonorsRecord,
    TrophyDefinition,
    build_default_trophy_definitions,
)


class TrophyRepository(Protocol):
    def list_definitions(self) -> tuple[TrophyDefinition, ...]: ...

    def get_definition(self, trophy_type: str) -> TrophyDefinition | None: ...

    def list_trophy_wins(self, *, club_id: str | None = None) -> tuple[ClubTrophyWin, ...]: ...

    def append_trophy_win(self, trophy_win: ClubTrophyWin) -> None: ...

    def list_season_snapshots(
        self,
        *,
        club_id: str | None = None,
        season_label: str | None = None,
    ) -> tuple[SeasonHonorsRecord, ...]: ...

    def append_season_snapshot(self, snapshot: SeasonHonorsRecord) -> None: ...


class InMemoryTrophyRepository:
    def __init__(self, definitions: tuple[TrophyDefinition, ...] | None = None) -> None:
        self._definitions = {
            definition.trophy_type: definition
            for definition in (definitions or build_default_trophy_definitions())
        }
        self._trophy_wins: list[ClubTrophyWin] = []
        self._season_snapshots: dict[tuple[str, str, str], list[SeasonHonorsRecord]] = defaultdict(list)
        self._lock = RLock()

    def list_definitions(self) -> tuple[TrophyDefinition, ...]:
        with self._lock:
            return tuple(self._definitions.values())

    def get_definition(self, trophy_type: str) -> TrophyDefinition | None:
        with self._lock:
            return self._definitions.get(trophy_type)

    def list_trophy_wins(self, *, club_id: str | None = None) -> tuple[ClubTrophyWin, ...]:
        with self._lock:
            if club_id is None:
                return tuple(self._trophy_wins)
            return tuple(trophy_win for trophy_win in self._trophy_wins if trophy_win.club_id == club_id)

    def append_trophy_win(self, trophy_win: ClubTrophyWin) -> None:
        with self._lock:
            self._trophy_wins.append(trophy_win)

    def list_season_snapshots(
        self,
        *,
        club_id: str | None = None,
        season_label: str | None = None,
    ) -> tuple[SeasonHonorsRecord, ...]:
        with self._lock:
            snapshots = [snapshot for records in self._season_snapshots.values() for snapshot in records]
            if club_id is not None:
                snapshots = [snapshot for snapshot in snapshots if snapshot.club_id == club_id]
            if season_label is not None:
                snapshots = [snapshot for snapshot in snapshots if snapshot.season_label == season_label]
            return tuple(snapshots)

    def append_season_snapshot(self, snapshot: SeasonHonorsRecord) -> None:
        key = (snapshot.club_id, snapshot.season_label, snapshot.team_scope)
        with self._lock:
            self._season_snapshots[key].append(snapshot)

    def clear(self) -> None:
        with self._lock:
            self._trophy_wins.clear()
            self._season_snapshots.clear()


_trophy_repository = InMemoryTrophyRepository()


def get_trophy_repository() -> TrophyRepository:
    return _trophy_repository


__all__ = [
    "InMemoryTrophyRepository",
    "TrophyRepository",
    "get_trophy_repository",
]
