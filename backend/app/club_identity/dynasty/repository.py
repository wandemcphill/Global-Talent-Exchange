from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.club_identity.models.dynasty_models import ClubDynastySeasonSummary
from backend.app.club_identity.models.reputation import ReputationEventLog, ReputationSnapshot


class DynastyReadRepository(Protocol):
    def get_club_season_summaries(self, club_id: str) -> Sequence[ClubDynastySeasonSummary]:
        ...

    def list_club_ids(self) -> Sequence[str]:
        ...


@dataclass(slots=True)
class DatabaseDynastyReadRepository:
    session_factory: sessionmaker[Session]

    def get_club_season_summaries(self, club_id: str) -> Sequence[ClubDynastySeasonSummary]:
        with self.session_factory() as session:
            snapshots = session.scalars(
                select(ReputationSnapshot)
                .where(ReputationSnapshot.club_id == club_id)
                .order_by(ReputationSnapshot.season.asc())
            ).all()
            if not snapshots:
                return ()
            events = session.scalars(
                select(ReputationEventLog)
                .where(ReputationEventLog.club_id == club_id)
                .order_by(ReputationEventLog.season.asc(), ReputationEventLog.created_at.asc())
            ).all()
        events_by_season: dict[int, list[ReputationEventLog]] = {}
        for event in events:
            if event.season is None:
                continue
            events_by_season.setdefault(event.season, []).append(event)
        return tuple(_snapshot_to_summary(club_id=club_id, snapshot=snapshot, season_events=events_by_season.get(snapshot.season, [])) for snapshot in snapshots)

    def list_club_ids(self) -> Sequence[str]:
        with self.session_factory() as session:
            club_ids = session.scalars(
                select(ReputationSnapshot.club_id).distinct().order_by(ReputationSnapshot.club_id.asc())
            ).all()
        return tuple(club_ids)


class InMemoryDynastyReadRepository:
    def __init__(self, season_map: Mapping[str, Sequence[ClubDynastySeasonSummary]]) -> None:
        self._season_map = {
            club_id: tuple(sorted(seasons, key=lambda season: season.season_index))
            for club_id, seasons in season_map.items()
        }

    def get_club_season_summaries(self, club_id: str) -> Sequence[ClubDynastySeasonSummary]:
        return self._season_map.get(club_id, ())

    def list_club_ids(self) -> Sequence[str]:
        return tuple(sorted(self._season_map))


def _snapshot_to_summary(
    *,
    club_id: str,
    snapshot: ReputationSnapshot,
    season_events: Sequence[ReputationEventLog],
) -> ClubDynastySeasonSummary:
    league_finish = None
    world_super_cup_qualified = False
    for event in season_events:
        if event.source == "league_finish":
            payload_finish = event.payload.get("league_finish")
            if isinstance(payload_finish, int):
                league_finish = payload_finish
        if event.source == "world_super_cup_qualification":
            world_super_cup_qualified = True

    league_title = league_finish == 1
    champions_league_title = any(event.badge_code == "continental_champion" for event in season_events)
    world_super_cup_winner = any(event.badge_code == "world_super_cup_champion" for event in season_events)
    major_honors = int(league_title) + int(champions_league_title) + int(world_super_cup_winner)

    return ClubDynastySeasonSummary(
        club_id=club_id,
        club_name=club_id,
        season_id=f"season-{snapshot.season}",
        season_label=f"Season {snapshot.season}",
        season_index=snapshot.season,
        league_finish=league_finish,
        league_title=league_title,
        champions_league_title=champions_league_title,
        world_super_cup_qualified=world_super_cup_qualified,
        world_super_cup_winner=world_super_cup_winner,
        trophy_count=max(major_honors, len(snapshot.badges)),
        reputation_gain=snapshot.season_delta,
    )
