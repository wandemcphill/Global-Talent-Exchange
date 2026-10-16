from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
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
from app.models.access_control import OrganizationRole
from app.models.user import User, UserRole

router = APIRouter(tags=["ai-manager"])
legacy_router = APIRouter(prefix="/ai-manager")
api_router = APIRouter(prefix="/api/ai-manager")


def get_ai_manager_service(request: Request) -> AIManagerService:
    settings = getattr(request.app.state, "settings", None)
    config_root = getattr(settings, "config_root", None)
    if config_root is None:
        return AIManagerService()
    return AIManagerService(storage_path=Path(config_root) / "ai_manager_profiles.json")


def require_ai_manager_profile_write_access(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    if current_user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return current_user
    try:
        AccessControlService(session).require_club_access(
            user=current_user,
            club_id=club_id,
            allowed_roles={OrganizationRole.CLUB, OrganizationRole.ADMIN},
            forbidden_detail="club_ai_manager_access_required",
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return current_user


@legacy_router.put("/profiles/{club_id}", response_model=AIManagerProfileView)
@api_router.put("/profiles/{club_id}", response_model=AIManagerProfileView)
def upsert_ai_manager_profile(
    club_id: str,
    payload: AIManagerProfileInput,
    service: AIManagerService = Depends(get_ai_manager_service),
    _=Depends(require_ai_manager_profile_write_access),
) -> AIManagerProfileView:
    if payload.club_id != club_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path club_id must match payload club_id.")
    return service.upsert_profile(payload)


@legacy_router.get("/profiles/{club_id}", response_model=AIManagerProfileView)
@api_router.get("/profiles/{club_id}", response_model=AIManagerProfileView)
def read_ai_manager_profile(
    club_id: str,
    service: AIManagerService = Depends(get_ai_manager_service),
    _=Depends(get_current_user),
) -> AIManagerProfileView:
    return service.get_profile(club_id)


@legacy_router.post("/autopilot/run", response_model=AutopilotRunResponse)
@api_router.post("/autopilot/run", response_model=AutopilotRunResponse)
def run_club_autopilot(
    payload: AutopilotRunRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
    _=Depends(get_current_user),
) -> AutopilotRunResponse:
    return service.run_autopilot(payload)


@legacy_router.post("/autopilot/live-decision", response_model=LiveDecisionResponse)
@api_router.post("/autopilot/live-decision", response_model=LiveDecisionResponse)
def preview_live_match_decision(
    payload: LiveMatchDecisionRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
    _=Depends(get_current_user),
) -> LiveDecisionResponse:
    return service.evaluate_live_decision(payload)


@legacy_router.post("/economy/reward-preview", response_model=RewardPreviewResponse)
@api_router.post("/economy/reward-preview", response_model=RewardPreviewResponse)
def preview_ai_manager_reward_policy(
    payload: RewardPreviewRequest,
    service: AIManagerService = Depends(get_ai_manager_service),
    _=Depends(get_current_user),
) -> RewardPreviewResponse:
    return service.preview_reward(payload)


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_ai_manager_service", "router"]
