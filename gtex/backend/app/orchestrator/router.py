from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.db import get_session
from app.models.user import User
from app.orchestrator.orchestrator_service import build_attention_orchestrator_service
from app.orchestrator.schemas import (
    AttentionOrchestratorConfigUpdateRequest,
    AttentionOrchestratorConfigView,
    AttentionOrchestratorMetricsView,
)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/config", response_model=AttentionOrchestratorConfigView)
def read_orchestrator_config(
    request: Request,
    _current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AttentionOrchestratorConfigView:
    return build_attention_orchestrator_service(app=request.app, session=session).get_config_view()


@router.post("/config", response_model=AttentionOrchestratorConfigView)
def update_orchestrator_config(
    payload: AttentionOrchestratorConfigUpdateRequest,
    request: Request,
    _current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AttentionOrchestratorConfigView:
    return build_attention_orchestrator_service(app=request.app, session=session).update_config(payload)


@router.get("/metrics", response_model=AttentionOrchestratorMetricsView)
def read_orchestrator_metrics(
    request: Request,
    sample_limit: int = 10,
    _current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AttentionOrchestratorMetricsView:
    return build_attention_orchestrator_service(app=request.app, session=session).metrics(sample_limit=max(sample_limit, 1))

