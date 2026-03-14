from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.dispute import DisputeStatus


class DisputeCreateRequest(BaseModel):
    resource_type: str = Field(min_length=2, max_length=64)
    resource_id: str = Field(min_length=1, max_length=64)
    reference: str = Field(min_length=1, max_length=64)
    subject: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=5, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DisputeMessageCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    attachment_id: str | None = None


class DisputeAssignRequest(BaseModel):
    admin_user_id: str | None = None


class DisputeStatusRequest(BaseModel):
    status: DisputeStatus
    note: str | None = Field(default=None, max_length=2000)


class DisputeView(BaseModel):
    id: str
    user_id: str
    admin_user_id: str | None
    resource_type: str
    resource_id: str
    reference: str
    status: DisputeStatus
    subject: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None

    class Config:
        from_attributes = True


class DisputeMessageView(BaseModel):
    id: str
    dispute_id: str
    sender_user_id: str | None
    sender_role: str
    message: str
    attachment_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DisputeDetailResponse(BaseModel):
    dispute: DisputeView
    messages: list[DisputeMessageView]


class DisputeListResponse(BaseModel):
    disputes: list[DisputeView]
    total_open: int
