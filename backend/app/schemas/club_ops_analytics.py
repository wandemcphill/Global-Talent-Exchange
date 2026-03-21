from __future__ import annotations

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.schemas.club_ops_admin import TopClubMetricView


class ClubFinanceAnalyticsView(CommonSchema):
    tracked_club_count: int
    total_operating_balance_minor: int
    total_sponsorship_revenue_minor: int
    total_academy_spend_minor: int
    total_scouting_spend_minor: int
    top_budget_clubs: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)


class ClubSponsorshipAnalyticsView(CommonSchema):
    active_contract_count: int
    total_contract_value_minor: int
    total_settled_revenue_minor: int
    pending_moderation_count: int
    utilization_by_asset_type: dict[str, int] = Field(default_factory=dict)
    top_revenue_clubs: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)


class ClubAcademyAnalyticsView(CommonSchema):
    tracked_club_count: int
    enrollment_count: int
    developing_count: int
    standout_count: int
    promoted_count: int
    released_count: int
    top_academies: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)


class ClubScoutingAnalyticsView(CommonSchema):
    tracked_club_count: int
    active_assignments: int
    prospect_count: int
    academy_signed_count: int
    promoted_count: int
    academy_conversion_rate_bps: int
    pathway_funnel: dict[str, int] = Field(default_factory=dict)
    top_scouting_clubs: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)


__all__ = [
    "ClubAcademyAnalyticsView",
    "ClubFinanceAnalyticsView",
    "ClubScoutingAnalyticsView",
    "ClubSponsorshipAnalyticsView",
]
