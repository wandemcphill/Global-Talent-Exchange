from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class TournamentCountdownView(_BaseView):
    tournament_name: str
    starts_at: datetime
    reference_at: datetime
    minutes_until_start: int
    pause_policy: PausePolicyView


class TrophyCeremonyView(_BaseView):
    trophy_name: str
    host_city: str
    presentation_minutes: int
    award_sequence: tuple[str, ...]
    confetti_colors: tuple[str, ...]
    no_extra_time: bool
    penalties_if_tied: bool


class QualificationExplanationView(BaseModel):
    seasons_considered: tuple[int, int]
    direct_slots: int
    playoff_slots: int
    playoff_winner_slots: int
    coefficient_table: list[CoefficientEntryView]
    direct_qualifiers: list[QualifiedClubView]
    playoff_qualifiers: list[QualifiedClubView]


class PlayoffDrawView(BaseModel):
    matches: list[PlayoffMatchView]
    winners: list[QualifiedClubView]


class GroupStageTableView(BaseModel):
    groups: list[GroupView]
    tables: list[GroupTableView]
    matches: list[GroupMatchView]
    advancing_clubs: list[QualifiedClubView]


class KnockoutBracketView(BaseModel):
    rounds: list[KnockoutRoundView]
    champion: QualifiedClubView
    runner_up: QualifiedClubView
    trophy_ceremony: TrophyCeremonyView
