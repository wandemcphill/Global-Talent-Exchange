from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.common.enums.scout_assignment_status import ScoutAssignmentStatus
from app.common.enums.scouting_region_type import ScoutingRegionType
from app.common.enums.youth_prospect_rating_band import YouthProspectRatingBand
from app.common.schemas.base import CommonSchema


class ScoutingRegionView(CommonSchema):
    id: str
    code: str
    name: str
    region_type: ScoutingRegionType
    territory_codes: tuple[str, ...] = Field(default_factory=tuple)
    is_active: bool = True


class ScoutAssignmentView(CommonSchema):
    id: str
    club_id: str
    region_code: str
    region_name: str
    region_type: ScoutingRegionType
    focus_area: str
    budget_minor: int
    scout_count: int
    status: ScoutAssignmentStatus
    report_confidence_floor_bps: int
    starts_at: datetime
    ends_at: datetime
    generated_prospect_ids: tuple[str, ...] = Field(default_factory=tuple)


class YouthProspectReportView(CommonSchema):
    id: str
    prospect_id: str
    assignment_id: str
    confidence_bps: int
    summary_text: str
    strengths: tuple[str, ...] = Field(default_factory=tuple)
    development_flags: tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime


class YouthProspectView(CommonSchema):
    id: str
    club_id: str
    assignment_id: str
    display_name: str
    age: int
    nationality_code: str
    region_label: str
    primary_position: str
    secondary_position: str | None = None
    rating_band: YouthProspectRatingBand
    development_traits: tuple[str, ...] = Field(default_factory=tuple)
    pathway_stage: PlayerPathwayStage
    discovered_at: datetime
    scouting_source: str
    follow_priority: int
    academy_player_id: str | None = None
    reports: tuple[YouthProspectReportView, ...] = Field(default_factory=tuple)


class YouthPipelineSnapshotView(CommonSchema):
    club_id: str
    captured_at: datetime
    funnel: dict[str, int] = Field(default_factory=dict)
    academy_conversion_rate_bps: int
    promotion_rate_bps: int


__all__ = [
    "ScoutAssignmentView",
    "ScoutingRegionView",
    "YouthPipelineSnapshotView",
    "YouthProspectReportView",
    "YouthProspectView",
]
