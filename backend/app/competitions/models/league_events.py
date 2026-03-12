from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class LeagueRegisteredClubEventData:
    club_id: str
    club_name: str
    strength_rating: int = 0


@dataclass(frozen=True, slots=True)
class LeagueSeasonRegisteredEvent:
    season_id: str
    buy_in_tier: int
    season_start: date
    registered_at: datetime
    clubs: tuple[LeagueRegisteredClubEventData, ...]


@dataclass(frozen=True, slots=True)
class LeagueFixtureCompletedEvent:
    season_id: str
    fixture_id: str
    home_goals: int
    away_goals: int
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class LeagueClubOptOutEvent:
    season_id: str
    club_id: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class LeaguePlayerStatsRecordedEvent:
    season_id: str
    player_id: str
    player_name: str
    club_id: str
    goals: int
    assists: int
    recorded_at: datetime


LeagueSeasonEvent = (
    LeagueSeasonRegisteredEvent
    | LeagueFixtureCompletedEvent
    | LeagueClubOptOutEvent
    | LeaguePlayerStatsRecordedEvent
)


__all__ = [
    "LeagueClubOptOutEvent",
    "LeagueFixtureCompletedEvent",
    "LeaguePlayerStatsRecordedEvent",
    "LeagueRegisteredClubEventData",
    "LeagueSeasonEvent",
    "LeagueSeasonRegisteredEvent",
]
