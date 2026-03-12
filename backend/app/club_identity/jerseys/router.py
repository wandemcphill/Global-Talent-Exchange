from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from backend.app.club_identity.jerseys.schemas import (
    BadgeProfileView,
    ClubIdentityProfilePatch,
    ClubIdentityProfileView,
    JerseySetPatch,
    JerseySetView,
)
from backend.app.club_identity.jerseys.service import ClubIdentityService

router = APIRouter(prefix="/api", tags=["club-identity-jerseys"])

_repository = InMemoryClubIdentityRepository()
_service = ClubIdentityService(_repository)


def get_identity_service() -> ClubIdentityService:
    return _service


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/clubs/{club_id}/identity", response_model=ClubIdentityProfileView)
def get_club_identity(
    club_id: str,
    service: ClubIdentityService = Depends(get_identity_service),
) -> ClubIdentityProfileView:
    return ClubIdentityProfileView.model_validate(service.get_identity(club_id))


@router.patch("/clubs/{club_id}/identity", response_model=ClubIdentityProfileView)
def patch_club_identity(
    club_id: str,
    payload: ClubIdentityProfilePatch,
    service: ClubIdentityService = Depends(get_identity_service),
) -> ClubIdentityProfileView:
    try:
        profile = service.update_identity(club_id, payload.model_dump(exclude_unset=True, mode="python"))
    except ValueError as error:
        raise _bad_request(error) from error
    return ClubIdentityProfileView.model_validate(profile)


@router.get("/clubs/{club_id}/jerseys", response_model=JerseySetView)
def get_club_jerseys(
    club_id: str,
    service: ClubIdentityService = Depends(get_identity_service),
) -> JerseySetView:
    return JerseySetView.model_validate(service.get_jerseys(club_id))


@router.patch("/clubs/{club_id}/jerseys", response_model=JerseySetView)
def patch_club_jerseys(
    club_id: str,
    payload: JerseySetPatch,
    service: ClubIdentityService = Depends(get_identity_service),
) -> JerseySetView:
    try:
        jersey_set = service.update_jerseys(club_id, payload.model_dump(exclude_unset=True, mode="python"))
    except ValueError as error:
        raise _bad_request(error) from error
    return JerseySetView.model_validate(jersey_set)


@router.get("/clubs/{club_id}/badge", response_model=BadgeProfileView)
def get_club_badge(
    club_id: str,
    service: ClubIdentityService = Depends(get_identity_service),
) -> BadgeProfileView:
    return BadgeProfileView.model_validate(service.get_badge(club_id))
