from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.regen_living_star import (
    RegenExitPetitionRequest,
    RegenExitPetitionView,
    RegenLivingStarView,
    RegenMatchBehaviorBriefView,
)
from app.services.regen_living_star_service import RegenLivingStarService

router = APIRouter(tags=["regen-living-star"])


def _service(session: Session = Depends(get_session)) -> RegenLivingStarService:
    return RegenLivingStarService(session)


@router.get("/api/players/{player_id}/living-star", response_model=RegenLivingStarView)
def get_regen_living_star(
    player_id: str,
    service: RegenLivingStarService = Depends(_service),
) -> RegenLivingStarView:
    try:
        return service.get_living_star(player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/api/players/{player_id}/behavior-brief",
    response_model=RegenMatchBehaviorBriefView,
)
def get_regen_behavior_brief(
    player_id: str,
    service: RegenLivingStarService = Depends(_service),
) -> RegenMatchBehaviorBriefView:
    try:
        return service.get_behavior_brief(player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/api/players/{player_id}/agency/exit-petition",
    response_model=RegenExitPetitionView,
)
def petition_regen_exit(
    player_id: str,
    payload: RegenExitPetitionRequest,
    current_user: User = Depends(get_current_user),
    service: RegenLivingStarService = Depends(_service),
) -> RegenExitPetitionView:
    del current_user
    try:
        return service.petition_exit(player_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
