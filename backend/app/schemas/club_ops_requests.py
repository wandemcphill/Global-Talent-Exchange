from __future__ import annotations

from typing import Literal

from pydantic import Field

from backend.app.common.enums.academy_player_status import AcademyPlayerStatus
from backend.app.common.enums.academy_program_type import AcademyProgramType
from backend.app.common.enums.player_pathway_stage import PlayerPathwayStage
from backend.app.common.enums.sponsorship_status import SponsorshipStatus
from backend.app.common.schemas.base import CommonSchema


class CreateSponsorshipContractRequest(CommonSchema):
    package_code: str = Field(min_length=3, max_length=64)
    sponsor_name: str = Field(min_length=2, max_length=120)
    contract_amount_minor: int | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    duration_months: int | None = Field(default=None, ge=1, le=36)
    payout_schedule: Literal["monthly", "quarterly", "upfront"] | None = None
    custom_copy: str | None = Field(default=None, max_length=80)
    custom_logo_url: str | None = Field(default=None, max_length=255)
    performance_bonus_minor: int = Field(default=0, ge=0)
    activate_immediately: bool = True


class UpdateSponsorshipContractRequest(CommonSchema):
    status: SponsorshipStatus | None = None
    custom_copy: str | None = Field(default=None, max_length=80)
    custom_logo_url: str | None = Field(default=None, max_length=255)
    moderation_status: str | None = Field(default=None, max_length=32)
    performance_bonus_minor: int | None = Field(default=None, ge=0)
    settle_due_payouts: bool = True


class CreateAcademyProgramRequest(CommonSchema):
    name: str = Field(min_length=3, max_length=120)
    program_type: AcademyProgramType
    budget_minor: int = Field(ge=0)
    cycle_length_weeks: int = Field(default=6, ge=2, le=26)
    focus_attributes: tuple[str, ...] = Field(default_factory=tuple)


class CreateAcademyPlayerRequest(CommonSchema):
    program_id: str | None = None
    display_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=13, le=21)
    primary_position: str = Field(min_length=1, max_length=40)
    secondary_position: str | None = Field(default=None, max_length=40)
    development_attributes: dict[str, int] = Field(default_factory=dict)


class UpdateAcademyPlayerRequest(CommonSchema):
    status: AcademyPlayerStatus | None = None
    attendance_score: int | None = Field(default=None, ge=0, le=100)
    coach_assessment: int | None = Field(default=None, ge=0, le=100)
    completed_cycles_delta: int = Field(default=0, ge=0, le=6)
    attribute_deltas: dict[str, int] = Field(default_factory=dict)
    pathway_note: str | None = Field(default=None, max_length=240)


class CreateScoutAssignmentRequest(CommonSchema):
    region_code: str = Field(min_length=2, max_length=64)
    focus_area: str = Field(min_length=2, max_length=120)
    budget_minor: int = Field(ge=0)
    scout_count: int = Field(default=2, ge=1, le=6)
    report_confidence_floor_bps: int = Field(default=6500, ge=0, le=10000)
    duration_weeks: int = Field(default=6, ge=1, le=26)


class UpdateYouthProspectRequest(CommonSchema):
    pathway_stage: PlayerPathwayStage | None = None
    follow_priority: int | None = Field(default=None, ge=1, le=10)
    convert_to_academy: bool = False
    academy_program_id: str | None = None
    notes: str | None = Field(default=None, max_length=240)


__all__ = [
    "CreateAcademyPlayerRequest",
    "CreateAcademyProgramRequest",
    "CreateScoutAssignmentRequest",
    "CreateSponsorshipContractRequest",
    "UpdateAcademyPlayerRequest",
    "UpdateSponsorshipContractRequest",
    "UpdateYouthProspectRequest",
]
