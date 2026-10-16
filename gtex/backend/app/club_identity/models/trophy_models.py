from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TrophyScope = Literal["senior", "academy"]


@dataclass(frozen=True, slots=True)
class TrophyDefinition:
    trophy_type: str
    trophy_name: str
    display_name: str
    competition_region: str
    competition_tier: str
    team_scope: TrophyScope
    is_major_honor: bool = False
    is_elite_honor: bool = False


@dataclass(frozen=True, slots=True)
class ClubTrophyWin:
    trophy_win_id: str
    award_reference: str
    club_id: str
    club_name: str
    trophy_type: str
    trophy_name: str
    season_label: str
    competition_region: str
    competition_tier: str
    final_result_summary: str
    earned_at: datetime
    captain_name: str | None
    top_performer_name: str | None
    team_scope: TrophyScope
    is_major_honor: bool
    is_elite_honor: bool


@dataclass(frozen=True, slots=True)
class TrophyCategoryCount:
    trophy_type: str
    trophy_name: str
    display_name: str
    team_scope: TrophyScope
    count: int
    is_major_honor: bool
    is_elite_honor: bool


@dataclass(frozen=True, slots=True)
class TrophySeasonCount:
    season_label: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int


@dataclass(frozen=True, slots=True)
class SeasonHonorsRecord:
    snapshot_id: str
    club_id: str
    club_name: str
    season_label: str
    team_scope: TrophyScope
    honors: tuple[ClubTrophyWin, ...]
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class ClubHonorsSummary:
    club_id: str
    club_name: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int
    trophies_by_category: tuple[TrophyCategoryCount, ...]
    trophies_by_season: tuple[TrophySeasonCount, ...]
    recent_honors: tuple[ClubTrophyWin, ...]
    historic_honors_timeline: tuple[ClubTrophyWin, ...]
    summary_outputs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HonorsTimeline:
    club_id: str
    club_name: str
    honors: tuple[ClubTrophyWin, ...]


@dataclass(frozen=True, slots=True)
class SeasonHonorsArchive:
    club_id: str
    club_name: str
    season_records: tuple[SeasonHonorsRecord, ...]


@dataclass(frozen=True, slots=True)
class TrophyLeaderboardEntry:
    club_id: str
    club_name: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int
    latest_honor_at: datetime | None
    summary_outputs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrophyLeaderboard:
    entries: tuple[TrophyLeaderboardEntry, ...]


def build_default_trophy_definitions() -> tuple[TrophyDefinition, ...]:
    return (
        TrophyDefinition(
            trophy_type="league_title",
            trophy_name="League Title",
            display_name="African League Champion",
            competition_region="Africa",
            competition_tier="domestic",
            team_scope="senior",
            is_major_honor=True,
        ),
        TrophyDefinition(
            trophy_type="league_runner_up",
            trophy_name="League Runner-up",
            display_name="African League Runner-up",
            competition_region="Africa",
            competition_tier="domestic",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="champions_league",
            trophy_name="Champions League",
            display_name="African Champions League Winner",
            competition_region="Africa",
            competition_tier="continental",
            team_scope="senior",
            is_major_honor=True,
        ),
        TrophyDefinition(
            trophy_type="world_super_cup",
            trophy_name="World Super Cup",
            display_name="GTEX World Super Cup Winner",
            competition_region="Global",
            competition_tier="global",
            team_scope="senior",
            is_major_honor=True,
            is_elite_honor=True,
        ),
        TrophyDefinition(
            trophy_type="fast_cup",
            trophy_name="Fast Cup",
            display_name="Fast Cup Winner",
            competition_region="Africa",
            competition_tier="cup",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="academy_league",
            trophy_name="Academy League",
            display_name="Academy League Champion",
            competition_region="Africa",
            competition_tier="academy_domestic",
            team_scope="academy",
        ),
        TrophyDefinition(
            trophy_type="academy_champions_league",
            trophy_name="Academy Champions League",
            display_name="Academy Champions League Winner",
            competition_region="Africa",
            competition_tier="academy_continental",
            team_scope="academy",
            is_major_honor=True,
        ),
        TrophyDefinition(
            trophy_type="golden_boot",
            trophy_name="Golden Boot",
            display_name="Golden Boot Winner",
            competition_region="Africa",
            competition_tier="individual",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="top_assist",
            trophy_name="Top Assist",
            display_name="Top Assist Winner",
            competition_region="Africa",
            competition_tier="individual",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="fair_play",
            trophy_name="Fair Play",
            display_name="Fair Play Award",
            competition_region="Africa",
            competition_tier="special",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="invincibles",
            trophy_name="Invincibles",
            display_name="Invincibles Season",
            competition_region="Africa",
            competition_tier="special",
            team_scope="senior",
        ),
        TrophyDefinition(
            trophy_type="record_breaker",
            trophy_name="Record Breaker",
            display_name="Record Breaker Award",
            competition_region="Africa",
            competition_tier="special",
            team_scope="senior",
        ),
    )


__all__ = [
    "ClubHonorsSummary",
    "ClubTrophyWin",
    "HonorsTimeline",
    "SeasonHonorsArchive",
    "SeasonHonorsRecord",
    "TrophyCategoryCount",
    "TrophyDefinition",
    "TrophyLeaderboard",
    "TrophyLeaderboardEntry",
    "TrophyScope",
    "TrophySeasonCount",
    "build_default_trophy_definitions",
]
