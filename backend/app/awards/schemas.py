from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class AwardCategoryView(CommonSchema):
    award_code: str
    award_name: str
    equivalent_name: str
    category_group: str
    entity_type: str
    shortlist_sizes: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AwardNominationComponentView(CommonSchema):
    performance: float = 0.0
    trophies: float = 0.0
    consistency: float = 0.0
    big_match_impact: float = 0.0
    total: float = 0.0


class AwardNomineeView(CommonSchema):
    entity_id: str
    entity_type: str
    display_name: str
    rank: int
    nomination_score: float
    components: AwardNominationComponentView
    metadata: dict[str, Any] = Field(default_factory=dict)


class AwardShortlistStageView(CommonSchema):
    stage: str
    stage_label: str
    size: int
    nominees: list[AwardNomineeView] = Field(default_factory=list)


class AwardNomineeBucketView(CommonSchema):
    award_code: str
    award_name: str
    equivalent_name: str
    category_group: str
    entity_type: str
    stages: list[AwardShortlistStageView] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)


class AwardWinnerView(CommonSchema):
    award_code: str
    award_name: str
    equivalent_name: str
    entity_type: str
    winners: list[AwardNomineeView] = Field(default_factory=list)
    finalists: list[AwardNomineeView] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AwardsCeremonySegmentView(CommonSchema):
    order: int
    award_code: str
    title: str
    presenter: str
    reveal_style: str
    narration: str
    highlight_reel: list[str] = Field(default_factory=list)
    finalists: list[AwardNomineeView] = Field(default_factory=list)
    winners: list[AwardNomineeView] = Field(default_factory=list)


class AwardsCeremonyView(CommonSchema):
    season_id: str
    season_number: int
    title: str
    broadcast_mode: str = "tv"
    countdown_seconds: int = 0
    presenters: list[str] = Field(default_factory=list)
    debates: list[str] = Field(default_factory=list)
    news_bulletins: list[str] = Field(default_factory=list)
    market_reactions: list[str] = Field(default_factory=list)
    segments: list[AwardsCeremonySegmentView] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


__all__ = [
    "AwardCategoryView",
    "AwardNominationComponentView",
    "AwardNomineeBucketView",
    "AwardNomineeView",
    "AwardShortlistStageView",
    "AwardWinnerView",
    "AwardsCeremonySegmentView",
    "AwardsCeremonyView",
]
