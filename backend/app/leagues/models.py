from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

LeagueTableColor = Literal["blue", "yellow", "green", "grey"]
LeagueSeasonStatus = Literal["scheduled", "in_progress", "completed"]


@dataclass(frozen=True, slots=True)
class LeagueClub:
    club_id: str
    club_name: str
    strength_rating: int = 0


@dataclass(frozen=True, slots=True)
class LeagueMatchResult:
    home_goals: int
    away_goals: int


@dataclass(frozen=True, slots=True)
class LeagueFixture:
    fixture_id: str
    round_number: int
    day_number: int
    window_number: int
    kickoff_at: datetime
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    result: LeagueMatchResult | None = None


@dataclass(frozen=True, slots=True)
class LeagueStandingRow:
    position: int
    club_id: str
    club_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    direct_champions_league: bool = False
    champions_league_playoff: bool = False
    next_season_auto_entry: bool = False
    table_color: LeagueTableColor = "grey"
    auto_entry_color: LeagueTableColor | None = None


@dataclass(frozen=True, slots=True)
class LeaguePlayerContribution:
    player_id: str
    player_name: str
    club_id: str
    goals: int = 0
    assists: int = 0


@dataclass(frozen=True, slots=True)
class LeagueAwardWinner:
    player_id: str
    player_name: str
    club_id: str
    stat_value: int
    split_amount: float


@dataclass(frozen=True, slots=True)
class LeagueAwardResult:
    award: str
    prize_pool: float
    winners: tuple[LeagueAwardWinner, ...]


@dataclass(frozen=True, slots=True)
class LeagueChampionPrize:
    club_id: str
    club_name: str
    amount: float


@dataclass(frozen=True, slots=True)
class LeaguePrizePoolBreakdown:
    total_pool: float
    winner_prize: float
    top_scorer_prize: float
    top_assist_prize: float
    champions_league_fund: float


@dataclass(frozen=True, slots=True)
class LeagueAutoEntrySlot:
    slot_number: int
    club_id: str
    club_name: str
    final_position: int
    rolled_over: bool


@dataclass(frozen=True, slots=True)
class LeagueSeasonState:
    season_id: str
    buy_in_tier: int
    season_start: date
    registered_at: datetime
    clubs: tuple[LeagueClub, ...]
    fixtures: tuple[LeagueFixture, ...]
    standings: tuple[LeagueStandingRow, ...]
    auto_entry_slots: tuple[LeagueAutoEntrySlot, ...]
    opted_out_club_ids: tuple[str, ...]
    prize_pool: LeaguePrizePoolBreakdown
    champion_prize: LeagueChampionPrize | None
    top_scorer_award: LeagueAwardResult
    top_assist_award: LeagueAwardResult
    status: LeagueSeasonStatus
    completed_fixture_count: int
    total_fixture_count: int
    scheduled_matches_per_club: int
    target_matches_per_club: int
    group_size_target: int
    group_is_full: bool
