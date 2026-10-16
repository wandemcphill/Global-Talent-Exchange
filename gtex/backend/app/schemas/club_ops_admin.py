from __future__ import annotations

from pydantic import Field

from app.common.schemas.base import CommonSchema


class TopClubMetricView(CommonSchema):
    club_id: str
    label: str
    value: int


class SponsorModerationQueueItemView(CommonSchema):
    contract_id: str
    club_id: str
    sponsor_name: str
    asset_type: str
    moderation_status: str


class ClubOpsSummaryView(CommonSchema):
    tracked_club_count: int
    active_contract_count: int
    pending_sponsor_moderation_count: int
    academy_enrollment_count: int
    active_scouting_assignment_count: int
    youth_prospect_count: int
    top_academies: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)
    top_scouting_clubs: tuple[TopClubMetricView, ...] = Field(default_factory=tuple)
    sponsor_moderation_queue: tuple[SponsorModerationQueueItemView, ...] = Field(default_factory=tuple)


__all__ = [
    "ClubOpsSummaryView",
    "SponsorModerationQueueItemView",
    "TopClubMetricView",
]
