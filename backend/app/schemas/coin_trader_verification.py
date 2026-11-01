from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class CoinTraderVerificationInitiateRequest(CommonSchema):
    verification_type: str = Field(default="full_kyc")
    callback_url: str | None = Field(default=None, max_length=512)


class CoinTraderVerificationSessionView(CommonSchema):
    session_id: str
    provider: str
    reference: str
    handoff_url: str | None = None
    verification_type: str
    status: str = "pending"
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoinTraderVerificationStatusView(CommonSchema):
    id: str
    user_id: str
    trader_profile_id: str | None = None
    provider: str
    provider_reference: str | None = None
    verification_type: str
    status: str
    decision: str | None = None
    rejection_reason: str | None = None
    checks_summary: dict[str, Any] = Field(default_factory=dict)
    initiated_at: datetime
    verified_at: datetime | None = None


class AdminTraderVerificationRecordView(CommonSchema):
    id: str
    user_id: str
    user_email: str | None = None
    trader_profile_id: str | None = None
    trader_display_name: str | None = None
    provider: str
    provider_session_id: str | None = None
    provider_reference: str | None = None
    verification_type: str
    status: str
    decision: str | None = None
    rejection_reason: str | None = None
    checks_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_fingerprint: str | None = None
    initiated_at: datetime
    verified_at: datetime | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


IdentityVerificationRecordAdminView = AdminTraderVerificationRecordView


class CoinTraderAdminActionRequest(CommonSchema):
    reason: str | None = None
    note: str | None = None

