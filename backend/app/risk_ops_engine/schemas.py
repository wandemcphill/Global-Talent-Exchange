from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.risk_ops import RiskCaseStatus, RiskSeverity, SystemEventSeverity


class RiskOverviewResponse(BaseModel):
    open_aml_cases: int
    open_fraud_cases: int
    open_integrity_incidents: int
    open_moderation_reports: int
    critical_system_events: int
    recent_audit_events: int
    users_with_elevated_risk: int
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
