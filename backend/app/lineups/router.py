from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.lineups.schemas import ClubMatchPlanView, SaveMatchPlanRequest
from app.lineups.service import ClubMatchPlanError, ClubMatchPlanService
from app.models.club_profile import ClubProfile
from app.models.user import User

router = APIRouter(tags=["club-lineup"])


def _service(session: Session = Depends(get_session)) -> ClubMatchPlanService:
    return ClubMatchPlanService(session)


def _assert_can_manage(session: Session, club_id: str, user: User) -> None:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found.")
    if club.owner_user_id != user.id and not bool(getattr(user, "is_admin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the club owner can manage the lineup.",
        )


@router.get("/clubs/{club_id}/lineup", response_model=ClubMatchPlanView)
def get_lineup(
    club_id: str,
    service: ClubMatchPlanService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubMatchPlanView:
    _assert_can_manage(session, club_id, current_user)
    return service.get_plan(club_id)


@router.put("/clubs/{club_id}/lineup", response_model=ClubMatchPlanView)
def save_lineup(
    club_id: str,
    payload: SaveMatchPlanRequest,
    service: ClubMatchPlanService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubMatchPlanView:
    _assert_can_manage(session, club_id, current_user)
    try:
        return service.save_plan(
            club_id=club_id,
            formation=payload.formation,
            starter_player_ids=payload.starter_player_ids,
            bench_player_ids=payload.bench_player_ids,
            actor_user_id=current_user.id,
        )
    except ClubMatchPlanError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
