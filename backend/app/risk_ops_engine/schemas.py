from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.risk_ops import (
    RiskActionStatus,
    RiskActionType,
    RiskCaseStatus,
    RiskSeverity,
    RiskSignalType,
    SystemEventSeverity,
)


class RiskOverviewResponse(BaseModel):
    open_aml_cases: int
    open_fraud_cases: int
    open_integrity_incidents: int
    open_moderation_reports: int
    critical_system_events: int
    recent_audit_events: int
    users_with_elevated_risk: int
    active_risk_actions: int = 0
    signals_ingested_24h: int = 0
    notes: list[str] = Field(default_factory=list)


class UserRiskOverviewResponse(BaseModel):
    user_id: str
    kyc_status: str
    integrity_score: str
    integrity_risk_level: str
    open_aml_cases: int
    open_fraud_cases: int
    open_integrity_incidents: int
    open_moderation_reports: int
    wallet_frozen: bool = False
    withdrawals_blocked: bool = False
    trading_blocked: bool = False
    manual_review_required: bool = False
    active_actions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AmlCaseCreateRequest(BaseModel):
    user_id: str | None = None
    trigger_source: str = "manual"
    title: str
    description: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    amount_signal: Decimal = Decimal("0.00")
    country_code: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FraudCaseCreateRequest(BaseModel):
    user_id: str | None = None
    fraud_type: str
    title: str
    description: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    confidence_score: Decimal = Decimal("0.00")
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RiskCaseResolveRequest(BaseModel):
    resolution_note: str
    dismissed: bool = False


class SystemEventCreateRequest(BaseModel):
    event_key: str
    event_type: str
    severity: SystemEventSeverity = SystemEventSeverity.INFO
    title: str
    body: str
    subject_type: str | None = None
    subject_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AmlCaseResponse(BaseModel):
    id: str
    user_id: str | None
    case_key: str
    trigger_source: str
    title: str
    description: str
    severity: RiskSeverity
    status: RiskCaseStatus
    amount_signal: Decimal
    country_code: str | None
    metadata_json: dict[str, Any]
    assigned_admin_user_id: str | None
    resolved_by_user_id: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class FraudCaseResponse(BaseModel):
    id: str
    user_id: str | None
    case_key: str
    fraud_type: str
    title: str
    description: str
    severity: RiskSeverity
    status: RiskCaseStatus
    confidence_score: Decimal
    metadata_json: dict[str, Any]
    assigned_admin_user_id: str | None
    resolved_by_user_id: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class SystemEventResponse(BaseModel):
    id: str
    event_key: str
    event_type: str
    severity: SystemEventSeverity
    title: str
    body: str
    subject_type: str | None
    subject_id: str | None
    created_by_user_id: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AuditLogResponse(BaseModel):
    id: str
    actor_user_id: str | None
    action_key: str
    resource_type: str
    resource_id: str | None
    outcome: str
    detail: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RiskScanResponse(BaseModel):
    aml_cases_created: int
    fraud_cases_created: int
    audit_events_created: int
    notes: list[str] = Field(default_factory=list)


class RiskSignalCreateRequest(BaseModel):
    user_id: str | None = None
    signal_type: RiskSignalType
    signal_key: str | None = None
    signal_value: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    source: str = "manual"
    confidence_score: Decimal = Decimal("0.00")
    occurred_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RiskSignalResponse(BaseModel):
    id: str
    user_id: str | None
    signal_type: RiskSignalType
    signal_key: str
    signal_value: str | None
    device_id: str | None
    ip_address: str | None
    source: str
    confidence_score: Decimal
    occurred_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RiskActionCreateRequest(BaseModel):
    user_id: str
    action_type: RiskActionType
    reason: str
    source_rule_key: str = "manual"
    fraud_case_id: str | None = None
    expires_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RiskActionReleaseRequest(BaseModel):
    release_note: str


class RiskActionResponse(BaseModel):
    id: str
    user_id: str
    action_type: RiskActionType
    status: RiskActionStatus
    reason: str
    source_rule_key: str
    created_by_user_id: str | None
    released_by_user_id: str | None
    fraud_case_id: str | None
    release_note: str | None
    released_at: datetime | None
    expires_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RiskRestrictionsResponse(BaseModel):
    user_id: str
    wallet_frozen: bool
    withdrawals_blocked: bool
    trading_blocked: bool
    manual_review_required: bool
    active_actions: list[RiskActionResponse] = Field(default_factory=list)


class RiskEvaluationRequest(BaseModel):
    user_id: str | None = None


class RiskEvaluationResponse(BaseModel):
    signals_reviewed: int
    users_flagged: int
    fraud_cases_created: int
    actions_created: int
    notes: list[str] = Field(default_factory=list)
