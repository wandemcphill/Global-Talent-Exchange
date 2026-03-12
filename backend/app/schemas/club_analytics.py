from __future__ import annotations

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema


class ClubLeaderboardEntry(CommonSchema):
    club_id: str
    club_name: str
    score: int
    label: str


class CosmeticRevenueSummary(CommonSchema):
    total_revenue_minor: int
    total_service_fees_minor: int
    currency_code: str
    purchase_count: int


class TrophyIssuanceSummary(CommonSchema):
    trophy_type: str
    count: int


class ThemeUsageStat(CommonSchema):
    theme_name: str
    usage_count: int


class ClubSummaryView(CommonSchema):
    total_clubs: int
    total_branding_assets: int
    total_jerseys: int
    total_trophies: int
    pending_branding_reviews: int


class ClubAnalyticsView(CommonSchema):
    top_reputation_clubs: list[ClubLeaderboardEntry] = Field(default_factory=list)
    top_dynasties: list[ClubLeaderboardEntry] = Field(default_factory=list)
    cosmetic_revenue: CosmeticRevenueSummary
    trophy_issuance: list[TrophyIssuanceSummary] = Field(default_factory=list)
    theme_usage: list[ThemeUsageStat] = Field(default_factory=list)
