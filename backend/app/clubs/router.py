from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.clubs.schemas import ClubView
from app.clubs.service import ClubQueryService

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.get("/{club_id}", response_model=ClubView)
def get_club(
    club_id: str,
    session: Session = Depends(get_session),
) -> ClubView:
    club = ClubQueryService(session).get_club(club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Club {club_id} was not found")
    return ClubView.model_validate(club)
