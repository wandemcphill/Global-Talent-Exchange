from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai_manager.schemas import (
    AIManagerProfileInput,
    AIManagerProfileView,
    AutopilotRunRequest,
    AutopilotRunResponse,
    LiveDecisionResponse,
    LiveMatchDecisionRequest,
    RewardPreviewRequest,
    RewardPreviewResponse,
)
from app.ai_manager.service import AIManagerService

router = APIRouter(tags=["ai-manager"])
legacy_router = APIRouter(prefix="/ai-manager")
api_router = APIRouter(prefix="/api/ai-manager")


def get_ai_manager_service(request: Request) -> AIManagerService:
    service = getattr(request.app.state, "ai_manager_service", None)
    if service is None:
        service = AIManagerService()
        request.app.state.ai_manager_service = service
    return service


@legacy_router.put("/profiles/{club_id}", response_model=AIManagerProfileView)
@api_router.put("/profiles/{club_id}", response_model=AIManagerProfileView)
def upsert_ai_manager_profile(
    club_id: str,
    payload: AIManagerProfileInput,
    service: AIManagerService = Depends(get_ai_manager_service),
) -> AIManagerProfileView:
    if payload.club_id != club_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path club_id must match payload club_id.")
    return service.upsert_profile(payload)


@legacy_router.get("/profiles/{club_id}", response_model=AIManagerProfileView)
@api_router.get("/profiles/{club_id}", response_model=AIManagerProfileView)
def read_ai_manager_profile(
    club_id: str,
    service: AIManagerService = Depends(get_ai_manager_service),
) -> AIManagerProfileView:
    return service.get_profile(club_id)


@legacy_router.post("/autopilot/run", response_model=AutopilotRunResponse)
@api_router.post("/autopilot/run", response_model=AutopilotRunResponse)
def run_club_autopilot(
    payload: AutopilotRunRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
) -> AutopilotRunResponse:
    return service.run_autopilot(payload)


@legacy_router.post("/autopilot/live-decision", response_model=LiveDecisionResponse)
@api_router.post("/autopilot/live-decision", response_model=LiveDecisionResponse)
def preview_live_match_decision(
    payload: LiveMatchDecisionRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
) -> LiveDecisionResponse:
    return service.evaluate_live_decision(payload)


@legacy_router.post("/economy/reward-preview", response_model=RewardPreviewResponse)
@api_router.post("/economy/reward-preview", response_model=RewardPreviewResponse)
def preview_ai_manager_reward_policy(
    payload: RewardPreviewRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
) -> RewardPreviewResponse:
    return service.preview_reward(payload)


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_ai_manager_service", "router"]
