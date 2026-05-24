from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _BaseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CoefficientEntryView(_BaseView):
    club_id: str
    club_name: str
    region: str
    total_points: int
    recent_season_points: int
    previous_season_points: int
    winner_seasons: tuple[int, ...]
    runner_up_seasons: tuple[int, ...]


class QualifiedClubView(_BaseView):
    club_id: str
    club_name: str
    region: str
    qualification_path: str
    coefficient_points: int
    regional_seed: int
    overall_seed: int


class PlayoffMatchView(_BaseView):
    match_id: str
    stage: str
    home_club: QualifiedClubView
    away_club: QualifiedClubView
    kickoff_at: datetime
    venue: str
    winner: QualifiedClubView | None = None
    decided_by: str | None = None
    home_score: int | None = None
    away_score: int | None = None


class GroupView(_BaseView):
    group_name: str
    clubs: tuple[QualifiedClubView, ...]


class GroupMatchView(_BaseView):
    match_id: str
    group_name: str
    matchday: int
    home_club: QualifiedClubView
    away_club: QualifiedClubView
    kickoff_at: datetime
    venue: str
    home_score: int | None = None
    away_score: int | None = None


class GroupStandingView(_BaseView):
    group_name: str
    position: int
    club: QualifiedClubView
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class GroupTableView(BaseModel):
    group_name: str
    standings: list[GroupStandingView]


class KnockoutMatchView(_BaseView):
    match_id: str
    round_name: str
    home_club: QualifiedClubView
    away_club: QualifiedClubView
    kickoff_at: datetime
    venue: str
    winner: QualifiedClubView | None = None
    decided_by: str | None = None
    home_score: int | None = None
    away_score: int | None = None


class KnockoutRoundView(_BaseView):
    round_name: str
    matches: tuple[KnockoutMatchView, ...]


class PausePolicyView(_BaseView):
    paused_competitions: tuple[str, ...]
    active_competitions: tuple[str, ...]
    cadence_description: str


class WorldSuperCupAuthorityFields(BaseModel):
    source_of_truth: str = "persisted_backend_authority"
    authority: str = "competition_os"
    no_demo_data: bool = True
    tournament_id: str | None = None
    competition_id: str | None = None


class TournamentCountdownView(_BaseView):
    tournament_name: str
    starts_at: datetime
    reference_at: datetime
    minutes_until_start: int
    pause_policy: PausePolicyView
    source_of_truth: str = "persisted_backend_authority"
    authority: str = "competition_os"
    no_demo_data: bool = True
    tournament_id: str | None = None
    competition_id: str | None = None


class WorldSuperCupFixtureView(_BaseView):
    tournament_id: str
    fixture_id: str
    stage: str
    home_club: QualifiedClubView
    away_club: QualifiedClubView
    kickoff_at: datetime
    venue: str
    status: str
    round_name: str | None = None
    group_name: str | None = None
    matchday: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    winner: QualifiedClubView | None = None
    decided_by: str | None = None


class WorldSuperCupFixturesView(WorldSuperCupAuthorityFields):
    fixtures: list[WorldSuperCupFixtureView]


class WorldSuperCupSettlementRequest(BaseModel):
    tournament_id: str | None = None
    competition_id: str | None = None
    match_id: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=1)
    home_score: int
    away_score: int
    winner_club_id: str | None = None
    decided_by: str | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldSuperCupSettlementView(_BaseView):
    tournament_id: str
    fixture_id: str
    idempotency_key: str
    status: str
    home_score: int
    away_score: int
    winner: QualifiedClubView | None = None
    decided_by: str | None = None
    applied_at: datetime
    lifecycle_match_id: str | None = None
    lifecycle_competition_id: str | None = None
    idempotency_source: str = "explicit_key"
    source_of_truth: str = "persisted_backend_authority"
    authority: str = "competition_os"
    no_demo_data: bool = True


class TrophyCeremonyView(_BaseView):
    trophy_name: str
    host_city: str
    presentation_minutes: int
    award_sequence: tuple[str, ...]
    confetti_colors: tuple[str, ...]
    no_extra_time: bool
    penalties_if_tied: bool


class QualificationExplanationView(WorldSuperCupAuthorityFields):
    seasons_considered: tuple[int, int]
    direct_slots: int
    playoff_slots: int
    playoff_winner_slots: int
    coefficient_table: list[CoefficientEntryView]
    direct_qualifiers: list[QualifiedClubView]
    playoff_qualifiers: list[QualifiedClubView]


class PlayoffDrawView(WorldSuperCupAuthorityFields):
    matches: list[PlayoffMatchView]
    winners: list[QualifiedClubView]


class GroupStageTableView(WorldSuperCupAuthorityFields):
    groups: list[GroupView]
    tables: list[GroupTableView]
    matches: list[GroupMatchView]
    advancing_clubs: list[QualifiedClubView]


class KnockoutBracketView(WorldSuperCupAuthorityFields):
    rounds: list[KnockoutRoundView]
    champion: QualifiedClubView
    runner_up: QualifiedClubView
    trophy_ceremony: TrophyCeremonyView
