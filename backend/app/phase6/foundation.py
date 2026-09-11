from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlayerMarketLifecycleState(StrEnum):
    """Primary market lifecycle, distinct from player retirement/tradability."""

    SEARCHABLE_ONLY = "searchable_only"
    MARKET_PENDING = "market_pending"
    MARKET_ACTIVE = "market_active"
    TRADE_ONLY = "trade_only"
    MARKET_BLOCKED = "market_blocked"


class RegenCareerStage(StrEnum):
    GENERATED = "generated"
    ACADEMY_PROSPECT = "academy_prospect"
    SENIOR_PLAYER = "senior_player"
    DEVELOPED_STAR = "developed_star"
    CLUB_LEGEND = "club_legend"
    RETIRED_LEGACY = "retired_legacy"


class RegenLegacyStatus(StrEnum):
    NONE = "none"
    ELIGIBLE = "eligible"
    ACTIVE_WINDOW = "active_window"
    COMPLETED = "completed"


class GtexSeasonStatus(StrEnum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StaffSpecialisation(StrEnum):
    COACH = "coach"
    SCOUT = "scout"
    ANALYST = "analyst"
    FITNESS = "fitness"
    MEDICAL = "medical"
    PHYSIOTHERAPY = "physiotherapy"
    NEGOTIATION = "negotiation"


class ClubAppointmentRole(StrEnum):
    FIRST_TEAM_MANAGER = "first_team_manager"
    ASSISTANT_MANAGER = "assistant_manager"
    FIRST_TEAM_COACH = "first_team_coach"
    YOUTH_COACH = "youth_coach"
    SCOUT = "scout"
    PERFORMANCE_ANALYST = "performance_analyst"
    FITNESS_COACH = "fitness_coach"
    MEDICAL_LEAD = "medical_lead"
    MEDICAL_STAFF = "medical_staff"


class StaffQualification(StrEnum):
    FOOTBALL_COACHING = "football_coaching"
    FIRST_TEAM_MANAGEMENT = "first_team_management"
    SCOUTING = "scouting"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    FITNESS = "fitness"
    MEDICAL = "medical"
    PHYSIOTHERAPY = "physiotherapy"
    NEGOTIATION = "negotiation"


class PersonalManagerQualityBand(StrEnum):
    BAND_60_70 = "60_70"
    BAND_71_80 = "71_80"
    BAND_81_90 = "81_90"
    BAND_91_95 = "91_95"
    BAND_96_99 = "96_99"

    @property
    def minimum_gsi(self) -> int:
        return {
            self.BAND_60_70: 60,
            self.BAND_71_80: 71,
            self.BAND_81_90: 81,
            self.BAND_91_95: 91,
            self.BAND_96_99: 96,
        }[self]

    @property
    def maximum_gsi(self) -> int:
        return {
            self.BAND_60_70: 70,
            self.BAND_71_80: 80,
            self.BAND_81_90: 90,
            self.BAND_91_95: 95,
            self.BAND_96_99: 99,
        }[self]


class FacilityTrack(StrEnum):
    ACADEMY = "academy"
    TRAINING_CENTRE = "training_centre"
    MEDICAL_CENTRE = "medical_centre"
    COACHING_STAFF = "coaching_staff"
    YOUTH_RECRUITMENT = "youth_recruitment"
    FACILITIES_EQUIPMENT = "facilities_equipment"
    CLUB_REPUTATION = "club_reputation"
    CLUB_CULTURE = "club_culture"


class FacilityUpgradeStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GtexSeasonRef(BaseModel):
    """Season-clock contract without assuming a wall-clock conversion."""

    model_config = ConfigDict(extra="forbid")

    season_number: int = Field(ge=1)
    status: GtexSeasonStatus
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "GtexSeasonRef":
        if self.starts_on is not None and self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on cannot precede starts_on")
        return self


class RegenCareerState(BaseModel):
    """Structured regen career state; age conversion remains explicitly versioned."""

    model_config = ConfigDict(extra="forbid")

    regen_id: str
    stage: RegenCareerStage
    birth_season_number: int = Field(ge=1)
    current_season_number: int = Field(ge=1)
    active_career_seasons: int = Field(default=0, ge=0)
    retirement_pressure: float | None = Field(default=None, ge=0, le=1)
    retirement_season_number: int | None = Field(default=None, ge=1)
    legacy_status: RegenLegacyStatus = RegenLegacyStatus.NONE
    virtual_date_of_birth: date | None = None
    virtual_age_years: float | None = Field(default=None, ge=0)
    age_calculation_version: str | None = None

    @model_validator(mode="after")
    def validate_clock(self) -> "RegenCareerState":
        if self.current_season_number < self.birth_season_number:
            raise ValueError("current_season_number cannot precede birth_season_number")
        if self.retirement_season_number is not None and self.retirement_season_number < self.birth_season_number:
            raise ValueError("retirement_season_number cannot precede birth_season_number")
        if self.virtual_age_years is not None and not self.age_calculation_version:
            raise ValueError("age_calculation_version is required when virtual_age_years is supplied")
        if self.stage == RegenCareerStage.RETIRED_LEGACY and self.retirement_season_number is None:
            raise ValueError("retired_legacy regens require retirement_season_number")
        return self


class StaffPersonContract(BaseModel):
    """Unique-person contract shared by market and appointment implementations."""

    model_config = ConfigDict(extra="forbid")

    staff_person_id: str
    display_name: str
    specialisations: tuple[StaffSpecialisation, ...] = ()
    qualifications: tuple[StaffQualification, ...] = ()
    unique_share: bool = True


class ClubStaffAppointment(BaseModel):
    """A job held by a staff person at a club."""

    model_config = ConfigDict(extra="forbid")

    staff_person_id: str
    club_id: str
    role: ClubAppointmentRole
    active: bool = True
    salary_coin_unit: str = "FAN"


class PersonalManagerIdentity(BaseModel):
    """One permanent, profile-bound manager identity."""

    model_config = ConfigDict(extra="forbid")

    gt_profile_id: str
    manager_id: str
    quality_band: PersonalManagerQualityBand
    gsi_min: int = Field(ge=60, le=99)
    gsi_max: int = Field(ge=60, le=99)
    transferable: bool = False
    salaried: bool = False
    creation_price_fan_coin: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_band(self) -> "PersonalManagerIdentity":
        if self.gsi_min != self.quality_band.minimum_gsi or self.gsi_max != self.quality_band.maximum_gsi:
            raise ValueError("GSI bounds must match the selected quality band")
        if self.transferable:
            raise ValueError("personal managers are non-transferable")
        if self.salaried:
            raise ValueError("personal managers do not draw club salary")
        return self


class FacilityProgressionBoundary(BaseModel):
    """Foundation contract for Fan Coin-funded facility progression."""

    model_config = ConfigDict(extra="forbid")

    club_id: str
    track: FacilityTrack
    level: int = Field(default=1, ge=1, le=10)
    status: FacilityUpgradeStatus = FacilityUpgradeStatus.NOT_STARTED
    target_level: int | None = Field(default=None, ge=2, le=10)
    fan_coin_investment: int | None = Field(default=None, ge=0)
    completion_season_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_progression(self) -> "FacilityProgressionBoundary":
        if self.target_level is not None and self.target_level <= self.level:
            raise ValueError("target_level must exceed the current level")
        if self.status == FacilityUpgradeStatus.IN_PROGRESS and self.target_level is None:
            raise ValueError("in-progress upgrades require target_level")
        if self.completion_season_number is not None and self.status != FacilityUpgradeStatus.IN_PROGRESS:
            raise ValueError("completion season is only meaningful for in-progress upgrades")
        return self


__all__ = [
    "ClubAppointmentRole",
    "ClubStaffAppointment",
    "FacilityProgressionBoundary",
    "FacilityTrack",
    "FacilityUpgradeStatus",
    "GtexSeasonRef",
    "GtexSeasonStatus",
    "PersonalManagerIdentity",
    "PersonalManagerQualityBand",
    "PlayerMarketLifecycleState",
    "RegenCareerStage",
    "RegenCareerState",
    "RegenLegacyStatus",
    "StaffPersonContract",
    "StaffQualification",
    "StaffSpecialisation",
]
