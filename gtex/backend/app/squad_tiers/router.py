from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.squad_tiers.schemas import (
    AcademyIntakeView,
    AssignTierRequest,
    SquadTierMemberView,
    SquadTiersView,
)
from app.squad_tiers.service import SquadTierError, SquadTierService

router = APIRouter(tags=["squad-tiers"])


def _service(session: Session = Depends(get_session)) -> SquadTierService:
    return SquadTierService(session)


def _assert_can_manage(session: Session, club_id: str, user: User) -> None:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found.")
    if club.owner_user_id != user.id and not bool(getattr(user, "is_admin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the club owner can manage squad tiers.",
        )


def _raise(exc: SquadTierError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/clubs/{club_id}/squad/tiers", response_model=SquadTiersView)
def get_squad_tiers(
    club_id: str,
    service: SquadTierService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadTiersView:
    _assert_can_manage(session, club_id, current_user)
    return service.list_squad(club_id)


@router.get("/clubs/{club_id}/academy/intake", response_model=AcademyIntakeView)
def get_academy_intake(
    club_id: str,
    service: SquadTierService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AcademyIntakeView:
    _assert_can_manage(session, club_id, current_user)
    return service.academy_intake(club_id)


@router.post(
    "/clubs/{club_id}/squad/tiers/{player_id}/assign",
    response_model=SquadTierMemberView,
)
def assign_tier(
    club_id: str,
    player_id: str,
    payload: AssignTierRequest,
    service: SquadTierService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadTierMemberView:
    _assert_can_manage(session, club_id, current_user)
    try:
        return service.assign_tier(
            club_id=club_id,
            player_id=player_id,
            tier=payload.tier,
            actor_user_id=current_user.id,
        )
    except SquadTierError as exc:
        _raise(exc)
        raise  # unreachable; satisfies type checker


@router.post(
    "/clubs/{club_id}/academy/intake/{player_id}/sign-up",
    response_model=SquadTierMemberView,
)
def sign_up_to_first_team(
    club_id: str,
    player_id: str,
    service: SquadTierService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadTierMemberView:
    _assert_can_manage(session, club_id, current_user)
    try:
        return service.assign_tier(
            club_id=club_id,
            player_id=player_id,
            tier="first_team",
            actor_user_id=current_user.id,
        )
    except SquadTierError as exc:
        _raise(exc)
        raise
