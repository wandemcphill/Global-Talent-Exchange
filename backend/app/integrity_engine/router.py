from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.integrity_engine.schemas import (
    IntegrityIncidentResponse,
    IntegrityResolveRequest,
    IntegrityScanRequest,
    IntegrityScanResponse,
    IntegrityScoreResponse,
)
from backend.app.integrity_engine.service import IntegrityEngineService
from backend.app.models.user import User

router = APIRouter(prefix="/integrity-engine", tags=["integrity-engine"])
admin_router = APIRouter(prefix="/admin/integrity-engine", tags=["integrity-engine-admin"])


@router.get("/me/score", response_model=IntegrityScoreResponse)
def get_my_integrity_score(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    score = IntegrityEngineService(session).get_score_for_user(user=current_user)
    session.commit()
    session.refresh(score)
    return IntegrityScoreResponse.model_validate(score, from_attributes=True)


@router.get("/me/incidents", response_model=list[IntegrityIncidentResponse])
def list_my_integrity_incidents(session: Session = Depends(get_session), current_user: User = Depends(get_current_user), limit: int = 50):
    incidents = IntegrityEngineService(session).list_incidents_for_user(user=current_user, limit=limit)
    return [IntegrityIncidentResponse.model_validate(item, from_attributes=True) for item in incidents]


@admin_router.post("/scan", response_model=IntegrityScanResponse)
def run_integrity_scan(payload: IntegrityScanRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    result = IntegrityEngineService(session).run_scan(
        repeated_gift_threshold=payload.repeated_gift_threshold,
        reward_cluster_threshold=payload.reward_cluster_threshold,
        lookback_limit=payload.lookback_limit,
    )
    session.commit()
    return IntegrityScanResponse(
        created_incidents=[IntegrityIncidentResponse.model_validate(item, from_attributes=True) for item in result["created_incidents"]],
        scanned_gifts=result["scanned_gifts"],
        scanned_rewards=result["scanned_rewards"],
    )


@admin_router.post("/incidents/{incident_id}/resolve", response_model=IntegrityIncidentResponse)
def resolve_incident(incident_id: str, payload: IntegrityResolveRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    try:
        incident = IntegrityEngineService(session).resolve_incident(incident_id=incident_id, actor=current_admin, resolution_note=payload.resolution_note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    session.refresh(incident)
    return IntegrityIncidentResponse.model_validate(incident, from_attributes=True)
