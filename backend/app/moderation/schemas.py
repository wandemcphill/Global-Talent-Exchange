from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ModerationReportCreateRequest(BaseModel):
    target_type: str = Field(min_length=2, max_length=32)
    target_id: str = Field(min_length=1, max_length=64)
    subject_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    reason_code: str = Field(min_length=2, max_length=48)
    description: str = Field(min_length=8, max_length=2000)
    evidence_url: str | None = Field(default=None, max_length=500)


class ModerationAssignmentRequest(BaseModel):
    admin_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    priority: str | None = Field(default=None, max_length=16)


class ModerationResolveRequest(BaseModel):
    resolution_action: str = Field(min_length=2, max_length=32)
    resolution_note: str = Field(min_length=3, max_length=2000)
    dismiss: bool = False


class ModerationReportView(BaseModel):
    id: str
    reporter_user_id: str
    subject_user_id: str | None = None
    target_type: str
    target_id: str
    reason_code: str
    description: str
    evidence_url: str | None = None
    status: str
    priority: str
    assigned_admin_user_id: str | None = None
    resolution_action: str
    resolution_note: str | None = None
    resolved_by_user_id: str | None = None
    report_count_for_target: int
    created_at: datetime
    updated_at: datetime


class ModerationSummaryView(BaseModel):
    open_count: int
    in_review_count: int
    actioned_count: int
    dismissed_count: int
    critical_count: int
    high_priority_count: int
    recent_reports: list[ModerationReportView]
