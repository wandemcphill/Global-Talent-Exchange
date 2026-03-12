from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DynastyStatus(StrEnum):
    NONE = "none"
    ACTIVE = "active"
    FALLEN = "fallen"


class EraLabel(StrEnum):
    NONE = "No Active Dynasty"
    EMERGING_POWER = "Emerging Power"
    DOMINANT_ERA = "Dominant Era"
    CONTINENTAL_DYNASTY = "Continental Dynasty"
    GLOBAL_DYNASTY = "Global Dynasty"
    FALLEN_GIANT = "Fallen Giant"


@dataclass(slots=True, frozen=True)
class ClubDynastySeasonSummary:
    club_id: str
    club_name: str
    season_id: str
    season_label: str
    season_index: int
    league_finish: int | None = None
    league_title: bool = False
    champions_league_title: bool = False
    world_super_cup_qualified: bool = False
    world_super_cup_winner: bool = False
    trophy_count: int = 0
    reputation_gain: int = 0

    @property
    def top_four_finish(self) -> bool:
        return self.league_finish is not None and self.league_finish <= 4

    @property
    def elite_finish(self) -> bool:
        return self.league_finish is not None and self.league_finish <= 2


@dataclass(slots=True, frozen=True)
class DynastyWindowMetrics:
    club_id: str
    club_name: str
    season_count: int
    window_start_season_id: str
    window_start_season_label: str
    window_end_season_id: str
    window_end_season_label: str
    seasons: tuple[ClubDynastySeasonSummary, ...]
    league_titles: int
    champions_league_titles: int
    world_super_cup_titles: int
    top_four_finishes: int
    elite_finishes: int
    world_super_cup_qualifications: int
    trophy_density: int
    reputation_gain_total: int
    recent_two_top_four_finishes: int
    recent_two_trophy_density: int
    recent_two_reputation_gain: int
    recent_two_league_titles: int


@dataclass(slots=True, frozen=True)
class DynastyAssessment:
    dynasty_status: DynastyStatus
    era_label: EraLabel
    active_dynasty: bool
    dynasty_score: int
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DynastySnapshot:
    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    era_label: EraLabel
    active_dynasty: bool
    dynasty_score: int
    reasons: tuple[str, ...]
    metrics: DynastyWindowMetrics


@dataclass(slots=True, frozen=True)
class DynastyEra:
    era_label: EraLabel
    dynasty_status: DynastyStatus
    start_season_id: str
    start_season_label: str
    end_season_id: str
    end_season_label: str
    peak_score: int
    active: bool
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DynastyEvent:
    season_id: str
    season_label: str
    event_type: str
    title: str
    detail: str
    score_impact: int


@dataclass(slots=True, frozen=True)
class DynastyStreaks:
    top_four: int
    trophy_seasons: int
    world_super_cup_qualification: int
    positive_reputation: int


@dataclass(slots=True, frozen=True)
class ClubDynastyProfile:
    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    current_era_label: EraLabel
    active_dynasty_flag: bool
    dynasty_score: int
    active_streaks: DynastyStreaks
    last_four_season_summary: tuple[ClubDynastySeasonSummary, ...]
    reasons: tuple[str, ...]
    current_snapshot: DynastySnapshot | None
    dynasty_timeline: tuple[DynastySnapshot, ...]
    eras: tuple[DynastyEra, ...]
    events: tuple[DynastyEvent, ...]


@dataclass(slots=True, frozen=True)
class ClubDynastyHistory:
    club_id: str
    club_name: str
    dynasty_timeline: tuple[DynastySnapshot, ...]
    eras: tuple[DynastyEra, ...]
    events: tuple[DynastyEvent, ...]


@dataclass(slots=True, frozen=True)
class DynastyLeaderboardEntry:
    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    current_era_label: EraLabel
    active_dynasty_flag: bool
    dynasty_score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)
