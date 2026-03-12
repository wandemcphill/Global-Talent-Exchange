from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LeagueClubRegistrationRequest(BaseModel):
    club_id: str = Field(min_length=1)
    club_name: str = Field(min_length=1)
    strength_rating: int = Field(default=0, ge=0)


class LeagueRegisterRequest(BaseModel):
    season_id: str | None = Field(default=None, min_length=1)
    buy_in_tier: int
    season_start: date
    clubs: list[LeagueClubRegistrationRequest] = Field(min_length=2, max_length=20)


class LeagueRegistrationView(BaseModel):
    season_id: str
    buy_in_tier: int
    season_start: date
    registered_club_count: int
    group_size_target: int
    group_is_full: bool
    scheduled_matches_per_club: int
    target_matches_per_club: int
    total_fixture_count: int
    total_pool: float
    status: str


class LeagueFixtureResultView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    home_goals: int
    away_goals: int


class LeagueFixtureView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fixture_id: str
    round_number: int
    day_number: int
    window_number: int
    kickoff_at: datetime
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    result: LeagueFixtureResultView | None


class LeagueFixturesView(BaseModel):
    season_id: str
    total_fixtures: int
    day_count: int
    fixtures: list[LeagueFixtureView]


class LeagueStandingRowView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    direct_champions_league: bool
    champions_league_playoff: bool
    next_season_auto_entry: bool
    table_color: str
    auto_entry_color: str | None


class LeagueStandingsView(BaseModel):
    season_id: str
    status: str
    rows: list[LeagueStandingRowView]


class LeagueAutoEntrySlotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slot_number: int
    club_id: str
    club_name: str
    final_position: int
    rolled_over: bool


class LeagueQualificationView(BaseModel):
    season_id: str
    opted_out_club_ids: list[str]
    auto_entry_slots: list[LeagueAutoEntrySlotView]
    rows: list[LeagueStandingRowView]


class LeagueChampionPrizeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    amount: float


class LeagueAwardWinnerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    club_id: str
    stat_value: int
    split_amount: float


class LeagueAwardView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    award: str
    prize_pool: float
    winners: list[LeagueAwardWinnerView]


class LeaguePrizePoolView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_pool: float
    winner_prize: float
    top_scorer_prize: float
    top_assist_prize: float
    champions_league_fund: float


class LeagueSeasonSummaryView(BaseModel):
    season_id: str
    buy_in_tier: int
    season_start: date
    status: str
    registered_club_count: int
    group_size_target: int
    group_is_full: bool
    scheduled_matches_per_club: int
    target_matches_per_club: int
    completed_fixture_count: int
    total_fixture_count: int
    prize_pool: LeaguePrizePoolView
    champion_prize: LeagueChampionPrizeView | None
    top_scorer_award: LeagueAwardView
    top_assist_award: LeagueAwardView
    auto_entry_slots: list[LeagueAutoEntrySlotView]
