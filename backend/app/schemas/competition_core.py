from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_start_mode import CompetitionStartMode
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.schemas.competition_financials import CompetitionFinancialsPayload
from backend.app.schemas.competition_rules import CompetitionRuleSetPayload


class CompetitionCorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host_user_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    format: CompetitionFormat
    visibility: CompetitionVisibility = CompetitionVisibility.PUBLIC
    start_mode: CompetitionStartMode = CompetitionStartMode.SCHEDULED
    scheduled_start_at: datetime | None = None
    status: CompetitionStatus = CompetitionStatus.DRAFT

    @model_validator(mode="after")
    def _validate_schedule(self) -> "CompetitionCorePayload":
        if self.start_mode == CompetitionStartMode.SCHEDULED and self.scheduled_start_at is None:
            raise ValueError("scheduled_start_at is required when start_mode is scheduled")
        return self


class CompetitionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core: CompetitionCorePayload
    rules: CompetitionRuleSetPayload
    financials: CompetitionFinancialsPayload

    @model_validator(mode="after")
    def _validate_format_consistency(self) -> "CompetitionCreateRequest":
        if self.core.format != self.rules.format:
            raise ValueError("core.format must match rules.format")
        return self


class CompetitionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    visibility: CompetitionVisibility | None = None
    start_mode: CompetitionStartMode | None = None
    scheduled_start_at: datetime | None = None
    format: CompetitionFormat | None = None
    rules: CompetitionRuleSetPayload | None = None
    financials: CompetitionFinancialsPayload | None = None

    @model_validator(mode="after")
    def _validate_schedule(self) -> "CompetitionUpdateRequest":
        if self.start_mode == CompetitionStartMode.SCHEDULED and self.scheduled_start_at is None:
            raise ValueError("scheduled_start_at is required when start_mode is scheduled")
        return self

    def touches_critical_fields(self) -> bool:
        return self.format is not None or self.rules is not None or self.financials is not None
