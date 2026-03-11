from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.competitions.schemas import CompetitionView
from backend.app.competitions.service import CompetitionQueryService

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("/{competition_id}", response_model=CompetitionView)
def get_competition(
    competition_id: str,
    session: Session = Depends(get_session),
) -> CompetitionView:
    competition = CompetitionQueryService(session).get_competition(competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition {competition_id} was not found",
        )
    return CompetitionView.model_validate(competition)
