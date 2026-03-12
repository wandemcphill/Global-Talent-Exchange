from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.common.enums.academy_player_status import AcademyPlayerStatus
from backend.app.common.enums.academy_program_type import AcademyProgramType
from backend.app.common.schemas.base import CommonSchema


class AcademyProgramView(CommonSchema):
    id: str
    club_id: str
    name: str
    program_type: AcademyProgramType
    budget_minor: int
    cycle_length_weeks: int
    focus_attributes: tuple[str, ...] = Field(default_factory=tuple)
    is_active: bool = True
    created_at: datetime


class AcademyPlayerView(CommonSchema):
    id: str
    club_id: str
    program_id: str | None = None
    display_name: str
    age: int
    primary_position: str
    secondary_position: str | None = None
    status: AcademyPlayerStatus
    overall_rating: int
    readiness_score: int
    completed_cycles: int
    development_attributes: dict[str, int] = Field(default_factory=dict)
    last_progressed_at: datetime
    pathway_note: str | None = None


class AcademyPlayerProgressView(CommonSchema):
    id: str
    player_id: str
    training_cycle_id: str | None = None
    status_before: AcademyPlayerStatus
    status_after: AcademyPlayerStatus
    delta_overall: int
    metrics: dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class AcademyTrainingCycleView(CommonSchema):
    id: str
    club_id: str
    program_id: str
    cycle_index: int
    focus_attributes: tuple[str, ...] = Field(default_factory=tuple)
    starts_at: datetime
    ends_at: datetime
    player_count: int
    average_delta: int


class AcademyGraduationEventView(CommonSchema):
    id: str
    club_id: str
    player_id: str
    player_name: str
    from_status: AcademyPlayerStatus
    to_status: AcademyPlayerStatus
    reason: str
    created_at: datetime


__all__ = [
    "AcademyGraduationEventView",
    "AcademyPlayerProgressView",
    "AcademyPlayerView",
    "AcademyProgramView",
    "AcademyTrainingCycleView",
]
