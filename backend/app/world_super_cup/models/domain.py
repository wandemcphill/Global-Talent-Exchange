from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ClubSeasonPerformance:
    club_id: str
    club_name: str
    region: str
    season_year: int
    coefficient_points: int
    continental_finish: str | None = None


@dataclass(frozen=True, slots=True)
class CoefficientEntry:
    club_id: str
    club_name: str
    region: str
    total_points: int
    recent_season_points: int
    previous_season_points: int
    winner_seasons: tuple[int, ...] = ()
    runner_up_seasons: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class QualifiedClub:
    club_id: str
    club_name: str
    region: str
    qualification_path: str
    coefficient_points: int
    regional_seed: int
    overall_seed: int


@dataclass(frozen=True, slots=True)
class PlayoffMatch:
    match_id: str
    stage: str
    home_club: QualifiedClub
    away_club: QualifiedClub
    kickoff_at: datetime
    venue: str
    winner: QualifiedClub | None = None
    decided_by: str | None = None
    home_score: int | None = None
    away_score: int | None = None


@dataclass(frozen=True, slots=True)
class Group:
    group_name: str
    clubs: tuple[QualifiedClub, QualifiedClub, QualifiedClub, QualifiedClub]


@dataclass(frozen=True, slots=True)
class GroupMatch:
    match_id: str
    group_name: str
    matchday: int
    home_club: QualifiedClub
    away_club: QualifiedClub
    kickoff_at: datetime
    venue: str
    home_score: int | None = None
    away_score: int | None = None


@dataclass(frozen=True, slots=True)
class GroupStanding:
    group_name: str
    position: int
    club: QualifiedClub
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


@dataclass(frozen=True, slots=True)
class KnockoutMatch:
    match_id: str
    round_name: str
    home_club: QualifiedClub
    away_club: QualifiedClub
    kickoff_at: datetime
    venue: str
    winner: QualifiedClub | None = None
    decided_by: str | None = None
    home_score: int | None = None
    away_score: int | None = None


@dataclass(frozen=True, slots=True)
class KnockoutRound:
    round_name: str
    matches: tuple[KnockoutMatch, ...]


@dataclass(frozen=True, slots=True)
class PausePolicy:
    paused_competitions: tuple[str, ...]
    active_competitions: tuple[str, ...]
    cadence_description: str


@dataclass(frozen=True, slots=True)
class TournamentCountdown:
    tournament_name: str
    starts_at: datetime
    reference_at: datetime
    minutes_until_start: int
    pause_policy: PausePolicy


@dataclass(frozen=True, slots=True)
class TrophyCeremonyMetadata:
    trophy_name: str
    host_city: str
    presentation_minutes: int
    award_sequence: tuple[str, ...]
    confetti_colors: tuple[str, ...]
    no_extra_time: bool
    penalties_if_tied: bool


@dataclass(frozen=True, slots=True)
class QualificationPlan:
    seasons_considered: tuple[int, int]
    coefficient_table: tuple[CoefficientEntry, ...]
    direct_qualifiers: tuple[QualifiedClub, ...]
    playoff_qualifiers: tuple[QualifiedClub, ...]
    playoff_matches: tuple[PlayoffMatch, ...]
    playoff_winners: tuple[QualifiedClub, ...]
    main_event_clubs: tuple[QualifiedClub, ...]


@dataclass(frozen=True, slots=True)
class GroupStageSnapshot:
    groups: tuple[Group, ...]
    matches: tuple[GroupMatch, ...]
    tables: tuple[GroupStanding, ...]
    advancing_clubs: tuple[QualifiedClub, ...]


@dataclass(frozen=True, slots=True)
class KnockoutBracket:
    rounds: tuple[KnockoutRound, ...]
    champion: QualifiedClub
    runner_up: QualifiedClub
    ceremony: TrophyCeremonyMetadata


@dataclass(frozen=True, slots=True)
class TournamentPlan:
    qualification: QualificationPlan
    group_stage: GroupStageSnapshot
    knockout: KnockoutBracket
    countdown: TournamentCountdown
