from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _BaseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TrophyWinView(_BaseView):
    trophy_win_id: str
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
    team_scope: str
    is_major_honor: bool
    is_elite_honor: bool


class TrophyCategoryCountView(_BaseView):
    trophy_type: str
    trophy_name: str
    display_name: str
    team_scope: str
    count: int
    is_major_honor: bool
    is_elite_honor: bool


class TrophySeasonCountView(_BaseView):
    season_label: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int


class SeasonHonorsRecordView(_BaseView):
    snapshot_id: str
    club_id: str
    club_name: str
    season_label: str
    team_scope: str
    honors: list[TrophyWinView]
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    recorded_at: datetime


class TrophyCabinetView(BaseModel):
    club_id: str
    club_name: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int
    trophies_by_category: list[TrophyCategoryCountView]
    trophies_by_season: list[TrophySeasonCountView]
    recent_honors: list[TrophyWinView]
    historic_honors_timeline: list[TrophyWinView]
    summary_outputs: list[str]


class HonorsTimelineView(BaseModel):
    club_id: str
    club_name: str
    honors: list[TrophyWinView]


class SeasonHonorsArchiveView(BaseModel):
    club_id: str
    club_name: str
    season_records: list[SeasonHonorsRecordView]


class TrophyLeaderboardEntryView(_BaseView):
    club_id: str
    club_name: str
    total_honors_count: int
    major_honors_count: int
    elite_honors_count: int
    senior_honors_count: int
    academy_honors_count: int
    latest_honor_at: datetime | None
    summary_outputs: list[str]


class TrophyLeaderboardView(BaseModel):
    entries: list[TrophyLeaderboardEntryView]
