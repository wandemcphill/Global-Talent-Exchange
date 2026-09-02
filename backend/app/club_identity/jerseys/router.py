from __future__ import annotations

# legacy compatibility route - canonical router provides core identity/jersey endpoints
# this router provides additional legacy endpoints for club identity customization

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from app.access_control.dependencies import require_bound_organization_access
from app.models.access_control import OrganizationRole
from app.club_identity.jerseys.sql_repository import SqlClubIdentityRepository
from app.club_identity.jerseys.schemas import (
    BadgeProfileView,
    ClubIdentityProfilePatch,
    ClubIdentityProfileView,
    JerseySetPatch,
    JerseySetView,
)
from app.club_identity.jerseys.service import ClubIdentityService
from app.auth.dependencies import get_current_user
from app.db import get_session
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole

router = APIRouter(prefix="/api", tags=["club-identity-jerseys"])

# Named module-level dependency (rather than an inline `Depends(require_bound_organization_access(...))`
# per route) so it is a single stable callable both routes share and tests can
# target with `app.dependency_overrides[require_club_identity_write_access] = ...`.
require_club_identity_write_access = require_bound_organization_access(
    OrganizationRole.CLUB, forbidden_detail="club_access_required"
)


def get_identity_service(session=Depends(get_session)) -> ClubIdentityService:
    return ClubIdentityService(SqlClubIdentityRepository(session))


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _require_club_editor(club_id: str, *, session: Session, current_user: User) -> None:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found.")
    if club.owner_user_id != current_user.id and current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this club.")


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
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubIdentityService = Depends(get_identity_service),
    _: User = Depends(require_club_identity_write_access),
) -> ClubIdentityProfileView:
    _require_club_editor(club_id, session=session, current_user=current_user)
    try:
        profile = service.update_identity(club_id, payload.model_dump(exclude_unset=True, mode="python"))
    except ValueError as error:
        raise _bad_request(error) from error
    return ClubIdentityProfileView.model_validate(profile)


# GET /clubs/{club_id}/jerseys is provided by canonical_clubs router
# PATCH /clubs/{club_id}/jerseys/{jersey_id} is provided by canonical_clubs router
# POST /clubs/{club_id}/jerseys is provided by canonical_clubs router
# This router provides legacy/custom jersey set operations and identity endpoints


@router.patch("/clubs/{club_id}/jerseys", response_model=JerseySetView)
def patch_club_jerseys(
    club_id: str,
    payload: JerseySetPatch,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: ClubIdentityService = Depends(get_identity_service),
    _: User = Depends(require_club_identity_write_access),
) -> JerseySetView:
    _require_club_editor(club_id, session=session, current_user=current_user)
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
