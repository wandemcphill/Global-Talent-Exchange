from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.club_identity.models.dynasty_models import DynastyStatus, EraLabel


class ClubDynastySeasonSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    season_id: str
    season_label: str
    season_index: int
    league_finish: int | None
    league_title: bool
    champions_league_title: bool
    world_super_cup_qualified: bool
    world_super_cup_winner: bool
    trophy_count: int
    reputation_gain: int
    top_four_finish: bool
    elite_finish: bool


class DynastyWindowMetricsView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    season_count: int
    window_start_season_id: str
    window_start_season_label: str
    window_end_season_id: str
    window_end_season_label: str
    seasons: tuple[ClubDynastySeasonSummaryView, ...]
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


class DynastySnapshotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    era_label: EraLabel
    active_dynasty: bool
    dynasty_score: int
    reasons: tuple[str, ...]
    metrics: DynastyWindowMetricsView


class DynastyEraView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    era_label: EraLabel
    dynasty_status: DynastyStatus
    start_season_id: str
    start_season_label: str
    end_season_id: str
    end_season_label: str
    peak_score: int
    active: bool
    reasons: tuple[str, ...]


class DynastyEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season_id: str
    season_label: str
    event_type: str
    title: str
    detail: str
    score_impact: int


class DynastyStreaksView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    top_four: int
    trophy_seasons: int
    world_super_cup_qualification: int
    positive_reputation: int


class ClubDynastyProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    current_era_label: EraLabel
    active_dynasty_flag: bool
    dynasty_score: int
    active_streaks: DynastyStreaksView
    last_four_season_summary: tuple[ClubDynastySeasonSummaryView, ...]
    reasons: tuple[str, ...]
    current_snapshot: DynastySnapshotView | None
    dynasty_timeline: tuple[DynastySnapshotView, ...]
    eras: tuple[DynastyEraView, ...]
    events: tuple[DynastyEventView, ...]


class ClubDynastyHistoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    dynasty_timeline: tuple[DynastySnapshotView, ...]
    eras: tuple[DynastyEraView, ...]
    events: tuple[DynastyEventView, ...]


class DynastyLeaderboardEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    club_name: str
    dynasty_status: DynastyStatus
    current_era_label: EraLabel
    active_dynasty_flag: bool
    dynasty_score: int
    reasons: tuple[str, ...]
