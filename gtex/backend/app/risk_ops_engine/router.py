from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.risk_ops import RiskSignalType
from app.models.user import User
from app.risk_ops_engine.schemas import (
    AmlCaseCreateRequest,
    AmlCaseResponse,
    AuditLogResponse,
    FraudCaseCreateRequest,
    FraudCaseResponse,
    RiskActionCreateRequest,
    RiskActionReleaseRequest,
    RiskActionResponse,
    RiskCaseResolveRequest,
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    RiskOverviewResponse,
    RiskRestrictionsResponse,
    RiskScanResponse,
    RiskSignalCreateRequest,
    RiskSignalResponse,
    SystemEventCreateRequest,
    SystemEventResponse,
    UserRiskOverviewResponse,
)
from app.risk_ops_engine.service import RiskOpsService
from app.services.device_fingerprint_service import DeviceFingerprintService

router = APIRouter(prefix="/risk-ops", tags=["risk-ops"])
admin_router = APIRouter(prefix="/admin/risk-ops", tags=["risk-ops-admin"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
    if not forwarded:
        return None
    return forwarded.split(",")[0].strip() or None


@router.get("/me/overview", response_model=UserRiskOverviewResponse)
def get_my_risk_overview(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserRiskOverviewResponse.model_validate(RiskOpsService(session).get_user_overview(current_user))


@router.get("/me/restrictions", response_model=RiskRestrictionsResponse)
def get_my_restrictions(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    service = RiskOpsService(session)
    body = service.get_user_restrictions(current_user.id)
    body["active_actions"] = [
        RiskActionResponse.model_validate(item, from_attributes=True) for item in body["active_actions"]
    ]
    return RiskRestrictionsResponse.model_validate(body)


@router.post("/me/signals", response_model=RiskSignalResponse)
def ingest_my_signal(
    payload: RiskSignalCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = RiskOpsService(session)
    data = payload.model_dump()
    data["user_id"] = current_user.id
    metadata = dict(data.get("metadata_json") or {})
    if data["signal_type"] == RiskSignalType.DEVICE_ID and not data.get("device_id") and not data.get("signal_value"):
        fingerprint = DeviceFingerprintService().build(headers=request.headers)
        data["device_id"] = fingerprint.fingerprint
        data["signal_value"] = fingerprint.fingerprint
        metadata["device_signal_sources"] = list(fingerprint.source_signals)
    if data["signal_type"] == RiskSignalType.IP_ADDRESS and not data.get("ip_address") and not data.get("signal_value"):
        ip_address = _client_ip(request)
        data["ip_address"] = ip_address
        data["signal_value"] = ip_address
    data["metadata_json"] = metadata
    signal = service.ingest_signal(actor_user_id=current_user.id, **data)
    session.commit()
    session.refresh(signal)
    return RiskSignalResponse.model_validate(signal, from_attributes=True)


@router.get("/me/aml-cases", response_model=list[AmlCaseResponse])
def get_my_aml_cases(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return [
        AmlCaseResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_aml_cases(user_id=current_user.id)
    ]


@router.get("/me/fraud-cases", response_model=list[FraudCaseResponse])
def get_my_fraud_cases(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return [
        FraudCaseResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_fraud_cases(user_id=current_user.id)
    ]


@admin_router.get("/overview", response_model=RiskOverviewResponse)
def get_risk_overview(_: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return RiskOverviewResponse.model_validate(RiskOpsService(session).get_overview())


@admin_router.get("/signals", response_model=list[RiskSignalResponse])
def list_signals(
    user_id: str | None = None,
    signal_type: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        RiskSignalResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_signals(user_id=user_id, signal_type=signal_type, limit=limit)
    ]


@admin_router.post("/signals", response_model=RiskSignalResponse)
def create_signal(
    payload: RiskSignalCreateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    item = RiskOpsService(session).ingest_signal(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return RiskSignalResponse.model_validate(item, from_attributes=True)


@admin_router.get("/actions", response_model=list[RiskActionResponse])
def list_actions(
    user_id: str | None = None,
    status: str | None = None,
    action_type: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        RiskActionResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_actions(
            user_id=user_id,
            status=status,
            action_type=action_type,
            limit=limit,
        )
    ]


@admin_router.post("/actions", response_model=RiskActionResponse)
def create_action(
    payload: RiskActionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    item, _ = RiskOpsService(session).create_action(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return RiskActionResponse.model_validate(item, from_attributes=True)


@admin_router.post("/actions/{action_id}/release", response_model=RiskActionResponse)
def release_action(
    action_id: str,
    payload: RiskActionReleaseRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    try:
        item = RiskOpsService(session).release_action(
            action_id=action_id,
            admin_user_id=current_admin.id,
            release_note=payload.release_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return RiskActionResponse.model_validate(item, from_attributes=True)


@admin_router.post("/evaluate", response_model=RiskEvaluationResponse)
def evaluate_signals(
    payload: RiskEvaluationRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    result = RiskOpsService(session).evaluate_signals(admin_user_id=current_admin.id, user_id=payload.user_id)
    session.commit()
    return RiskEvaluationResponse.model_validate(result)


@admin_router.get("/aml-cases", response_model=list[AmlCaseResponse])
def list_aml_cases(
    user_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        AmlCaseResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_aml_cases(user_id=user_id, status=status, limit=limit)
    ]


@admin_router.post("/aml-cases", response_model=AmlCaseResponse)
def create_aml_case(
    payload: AmlCaseCreateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    item = RiskOpsService(session).create_aml_case(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return AmlCaseResponse.model_validate(item, from_attributes=True)


@admin_router.get("/fraud-cases", response_model=list[FraudCaseResponse])
def list_fraud_cases(
    user_id: str | None = None,
    status: str | None = None,
    fraud_type: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        FraudCaseResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_fraud_cases(
            user_id=user_id,
            status=status,
            fraud_type=fraud_type,
            limit=limit,
        )
    ]


@admin_router.post("/fraud-cases", response_model=FraudCaseResponse)
def create_fraud_case(
    payload: FraudCaseCreateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    item = RiskOpsService(session).create_fraud_case(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return FraudCaseResponse.model_validate(item, from_attributes=True)


@admin_router.post("/cases/{case_type}/{case_id}/resolve", response_model=dict)
def resolve_case(
    case_type: str,
    case_id: str,
    payload: RiskCaseResolveRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    if case_type not in {"aml", "fraud"}:
        raise HTTPException(status_code=400, detail="case_type must be aml or fraud")
    item = RiskOpsService(session).resolve_case(
        case_type=case_type,
        case_id=case_id,
        admin_user_id=current_admin.id,
        resolution_note=payload.resolution_note,
        dismissed=payload.dismissed,
    )
    session.commit()
    return {"id": item.id, "status": item.status.value if hasattr(item.status, "value") else str(item.status)}


@admin_router.get("/system-events", response_model=list[SystemEventResponse])
def list_system_events(
    severity: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        SystemEventResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_system_events(severity=severity, limit=limit)
    ]


@admin_router.post("/system-events", response_model=SystemEventResponse)
def create_system_event(
    payload: SystemEventCreateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    item = RiskOpsService(session).create_system_event(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return SystemEventResponse.model_validate(item, from_attributes=True)


@admin_router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    action_key: str | None = None,
    limit: int = 100,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    return [
        AuditLogResponse.model_validate(item, from_attributes=True)
        for item in RiskOpsService(session).list_audit_logs(action_key=action_key, limit=limit)
    ]


@admin_router.post("/scan", response_model=RiskScanResponse)
def run_scan(current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    result = RiskOpsService(session).run_automated_scan(admin_user_id=current_admin.id)
    session.commit()
    return RiskScanResponse.model_validate(result)
