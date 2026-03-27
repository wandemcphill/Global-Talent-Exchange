from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User

from .schemas import (
    ManagerCardView,
    ManagerHireRequest,
    ManagerHireResponse,
    ManagerLeaderboardEntryView,
    ManagerProfileView,
    ManagerReleaseResponse,
)
from .service import ManagerMarketplaceError, ManagerMarketplaceService

router = APIRouter(prefix="/managers", tags=["manager-marketplace"])


def get_service(session: Session = Depends(get_session)) -> ManagerMarketplaceService:
    return ManagerMarketplaceService(session)


@router.get("", response_model=list[ManagerCardView])
def list_managers(service: ManagerMarketplaceService = Depends(get_service)) -> list[ManagerCardView]:
    return service.list_managers()


@router.get("/leaderboard", response_model=list[ManagerLeaderboardEntryView])
def get_manager_leaderboard(service: ManagerMarketplaceService = Depends(get_service)) -> list[ManagerLeaderboardEntryView]:
    return service.leaderboard()


@router.get("/{manager_id}", response_model=ManagerProfileView)
def get_manager(manager_id: str, service: ManagerMarketplaceService = Depends(get_service)) -> ManagerProfileView:
    try:
        return service.get_manager(manager_id)
    except ManagerMarketplaceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{manager_id}/hire", response_model=ManagerHireResponse, status_code=status.HTTP_201_CREATED)
def hire_manager(
    manager_id: str,
    payload: ManagerHireRequest,
    current_user: User = Depends(get_current_user),
    service: ManagerMarketplaceService = Depends(get_service),
) -> ManagerHireResponse:
    try:
        result = service.hire_manager(current_user, manager_id, end_date=payload.end_date)
        service.session.commit()
        return result
    except ManagerMarketplaceError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{manager_id}/release", response_model=ManagerReleaseResponse)
def release_manager(
    manager_id: str,
    current_user: User = Depends(get_current_user),
    service: ManagerMarketplaceService = Depends(get_service),
) -> ManagerReleaseResponse:
    try:
        result = service.release_manager(current_user, manager_id)
        service.session.commit()
        return result
    except ManagerMarketplaceError as exc:
        service.session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
