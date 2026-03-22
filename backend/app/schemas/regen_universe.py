from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas.base import CommonSchema


class RegenSeasonCreateRequest(CommonSchema):
    season_number: int = Field(ge=1)
    start_date: date
    end_date: date
    is_active: bool = True
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenSeasonCloseRequest(CommonSchema):
    close_date: date | None = None
    start_next_season: bool = True


class RegenSeasonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    season_number: int
    start_date: date
    end_date: date
    is_active: bool
    closed_at: datetime | None = None
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenAwardDefinitionView(CommonSchema):
    id: str
    code: str
    name: str
    description: str
    category: str
    ranking_category: str | None = None
    eligibility_rules_json: dict[str, object] = Field(default_factory=dict)
    is_regen_only: bool = True


class RegenAwardWinnerView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    ranking_score: float
    rank: int | None = None
    awarded_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenAwardResultView(CommonSchema):
    award: RegenAwardDefinitionView
    season: RegenSeasonView
    winners: list[RegenAwardWinnerView] = Field(default_factory=list)


class RegenRankingEntryView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    category: str
    score: float
    rank: int
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenRankingLeaderboardView(CommonSchema):
    season: RegenSeasonView | None = None
    category: str
    entries: list[RegenRankingEntryView] = Field(default_factory=list)


class RegenHallOfFameEntryView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    total_awards: int
    peak_rank: int | None = None
    seasons_active: int
    legacy_score: float
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenHallOfFameView(CommonSchema):
    entries: list[RegenHallOfFameEntryView] = Field(default_factory=list)


class RegenUniverseCloseResultView(CommonSchema):
    season_id: str
    season_number: int
    performance_records_created: int
    ranking_snapshots_created: int
    award_winners_created: int
    hall_of_fame_entries_tracked: int
    next_season_id: str | None = None
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenSeasonRankingReferenceView(CommonSchema):
    season_number: int
    rank: int
    score: float


class RegenRecentAwardView(CommonSchema):
    award_code: str
    award_name: str
    season_number: int
    rank: int | None = None
    ranking_score: float


class RegenPlayerPrestigeSummaryView(CommonSchema):
    player_id: str
    total_awards: int
    peak_rank: int | None = None
    seasons_active: int
    legacy_score: float
    current_overall_ranking: RegenSeasonRankingReferenceView | None = None
    latest_overall_ranking: RegenSeasonRankingReferenceView | None = None
    recent_awards: list[RegenRecentAwardView] = Field(default_factory=list)
