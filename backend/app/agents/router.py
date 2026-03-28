from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.agent_manager import (
    AgentManagerSummaryView,
    AgentPerformanceReceiptView,
    AgentPerformanceRequest,
    AgentRunRequest,
    AgentRunResponse,
    AgentRuntimeConfigUpdateRequest,
    AgentRuntimeConfigView,
    CreatorAgentView,
    ensure_creator_agent_manager,
)
from app.auth.dependencies import get_current_admin
from app.models.user import User


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/config", response_model=AgentRuntimeConfigView)
def read_agent_config(
    request: Request,
    _current_user: User = Depends(get_current_admin),
) -> AgentRuntimeConfigView:
    return ensure_creator_agent_manager(request.app).get_config_view()


@router.post("/config", response_model=AgentRuntimeConfigView)
def update_agent_config(
    payload: AgentRuntimeConfigUpdateRequest,
    request: Request,
    _current_user: User = Depends(get_current_admin),
) -> AgentRuntimeConfigView:
    return ensure_creator_agent_manager(request.app).update_config(payload)


@router.get("/summary", response_model=AgentManagerSummaryView)
def read_agent_summary(
    request: Request,
    _current_user: User = Depends(get_current_admin),
) -> AgentManagerSummaryView:
    return ensure_creator_agent_manager(request.app).summary()


@router.get("", response_model=list[CreatorAgentView])
def list_agents(
    request: Request,
    limit: int = 25,
    _current_user: User = Depends(get_current_admin),
) -> list[CreatorAgentView]:
    return ensure_creator_agent_manager(request.app).list_agents(limit=max(limit, 1))


@router.post("/run", response_model=AgentRunResponse)
def run_agent_cycle(
    payload: AgentRunRequest,
    request: Request,
    _current_user: User = Depends(get_current_admin),
) -> AgentRunResponse:
    return ensure_creator_agent_manager(request.app).run_cycle(
        max_agents=payload.max_agents,
        trigger=payload.trigger,
    )


@router.post("/performance", response_model=AgentPerformanceReceiptView)
def submit_agent_performance(
    payload: AgentPerformanceRequest,
    request: Request,
    _current_user: User = Depends(get_current_admin),
) -> AgentPerformanceReceiptView:
    try:
        return ensure_creator_agent_manager(request.app).record_performance(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


__all__ = ["router"]
