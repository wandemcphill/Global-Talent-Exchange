from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.risk_ops_engine.schemas import (
    AmlCaseCreateRequest,
    AmlCaseResponse,
    AuditLogResponse,
    FraudCaseCreateRequest,
    FraudCaseResponse,
    RiskCaseResolveRequest,
    RiskOverviewResponse,
    RiskScanResponse,
    SystemEventCreateRequest,
    SystemEventResponse,
    UserRiskOverviewResponse,
)
from app.risk_ops_engine.service import RiskOpsService

router = APIRouter(prefix="/risk-ops", tags=["risk-ops"])
admin_router = APIRouter(prefix="/admin/risk-ops", tags=["risk-ops-admin"])


@router.get("/me/overview", response_model=UserRiskOverviewResponse)
def get_my_risk_overview(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return UserRiskOverviewResponse.model_validate(RiskOpsService(session).get_user_overview(current_user))


@router.get("/me/aml-cases", response_model=list[AmlCaseResponse])
def get_my_aml_cases(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return [AmlCaseResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_aml_cases(user_id=current_user.id)]


@router.get("/me/fraud-cases", response_model=list[FraudCaseResponse])
def get_my_fraud_cases(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return [FraudCaseResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_fraud_cases(user_id=current_user.id)]


@admin_router.get("/overview", response_model=RiskOverviewResponse)
def get_risk_overview(_: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return RiskOverviewResponse.model_validate(RiskOpsService(session).get_overview())


@admin_router.get("/aml-cases", response_model=list[AmlCaseResponse])
def list_aml_cases(user_id: str | None = None, status: str | None = None, limit: int = 100, _: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return [AmlCaseResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_aml_cases(user_id=user_id, status=status, limit=limit)]


@admin_router.post("/aml-cases", response_model=AmlCaseResponse)
def create_aml_case(payload: AmlCaseCreateRequest, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    item = RiskOpsService(session).create_aml_case(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return AmlCaseResponse.model_validate(item, from_attributes=True)


@admin_router.get("/fraud-cases", response_model=list[FraudCaseResponse])
def list_fraud_cases(user_id: str | None = None, status: str | None = None, fraud_type: str | None = None, limit: int = 100, _: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return [FraudCaseResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_fraud_cases(user_id=user_id, status=status, fraud_type=fraud_type, limit=limit)]


@admin_router.post("/fraud-cases", response_model=FraudCaseResponse)
def create_fraud_case(payload: FraudCaseCreateRequest, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    item = RiskOpsService(session).create_fraud_case(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return FraudCaseResponse.model_validate(item, from_attributes=True)


@admin_router.post("/cases/{case_type}/{case_id}/resolve", response_model=dict)
def resolve_case(case_type: str, case_id: str, payload: RiskCaseResolveRequest, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    if case_type not in {"aml", "fraud"}:
        raise HTTPException(status_code=400, detail="case_type must be aml or fraud")
    item = RiskOpsService(session).resolve_case(case_type=case_type, case_id=case_id, admin_user_id=current_admin.id, resolution_note=payload.resolution_note, dismissed=payload.dismissed)
    session.commit()
    return {"id": item.id, "status": item.status.value if hasattr(item.status, 'value') else str(item.status)}


@admin_router.get("/system-events", response_model=list[SystemEventResponse])
def list_system_events(severity: str | None = None, limit: int = 100, _: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return [SystemEventResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_system_events(severity=severity, limit=limit)]


@admin_router.post("/system-events", response_model=SystemEventResponse)
def create_system_event(payload: SystemEventCreateRequest, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    item = RiskOpsService(session).create_system_event(actor_user_id=current_admin.id, **payload.model_dump())
    session.commit()
    session.refresh(item)
    return SystemEventResponse.model_validate(item, from_attributes=True)


@admin_router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(action_key: str | None = None, limit: int = 100, _: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return [AuditLogResponse.model_validate(item, from_attributes=True) for item in RiskOpsService(session).list_audit_logs(action_key=action_key, limit=limit)]


@admin_router.post("/scan", response_model=RiskScanResponse)
def run_scan(current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    result = RiskOpsService(session).run_automated_scan(admin_user_id=current_admin.id)
    session.commit()
    return RiskScanResponse.model_validate(result)
