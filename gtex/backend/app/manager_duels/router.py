from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import get_current_user
from app.manager_duels.schemas import ManagerDuelCreateRequest, ManagerDuelLeaderboardEntryView, ManagerDuelView
from app.manager_duels.service import ManagerDuelError, ensure_manager_duel_service
from app.models.user import User

router = APIRouter(tags=["manager-duels"])
legacy_router = APIRouter(prefix="/manager-duels", tags=["manager-duels"])
api_router = APIRouter(prefix="/api/manager-duels", tags=["manager-duels"])


@legacy_router.get("/leaderboard", response_model=list[ManagerDuelLeaderboardEntryView])
@api_router.get("/leaderboard", response_model=list[ManagerDuelLeaderboardEntryView])
def read_leaderboard(request: Request, limit: int = Query(default=25, ge=1, le=100)) -> list[ManagerDuelLeaderboardEntryView]:
    return ensure_manager_duel_service(request.app).get_leaderboard(limit=limit)


@legacy_router.post("", response_model=ManagerDuelView, status_code=status.HTTP_201_CREATED)
@api_router.post("", response_model=ManagerDuelView, status_code=status.HTTP_201_CREATED)
def create_manager_duel(
    payload: ManagerDuelCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ManagerDuelView:
    try:
        return ensure_manager_duel_service(request.app).create_and_start_duel(actor=current_user, payload=payload)
    except ManagerDuelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@legacy_router.get("/{duel_id}", response_model=ManagerDuelView)
@api_router.get("/{duel_id}", response_model=ManagerDuelView)
def read_duel(duel_id: str, request: Request) -> ManagerDuelView:
    try:
        return ensure_manager_duel_service(request.app).get_duel(duel_id)
    except ManagerDuelError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)

__all__ = ["router"]
