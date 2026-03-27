from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.predictions.schemas import (
    PredictionCreateRequest,
    PredictionLeaderboardEntryView,
    PredictionLeaderboardView,
    PredictionView,
)
from app.predictions.service import PredictionError, PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _to_prediction_view(prediction) -> PredictionView:
    return PredictionView.model_validate(prediction, from_attributes=True)


@router.get("", response_model=list[PredictionView])
def list_predictions(
    match_id: str | None = Query(default=None),
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[PredictionView]:
    service = PredictionService(session)
    return [_to_prediction_view(item) for item in service.list_predictions(actor=actor, match_id=match_id)]


@router.post("", response_model=PredictionView, status_code=status.HTTP_201_CREATED)
def submit_prediction(
    payload: PredictionCreateRequest,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PredictionView:
    service = PredictionService(session)
    try:
        prediction = service.submit_prediction(
            actor=actor,
            match_id=payload.match_id,
            predicted_outcome=payload.predicted_outcome,
            confidence_level=payload.confidence_level,
        )
        session.commit()
        session.refresh(prediction)
        return _to_prediction_view(prediction)
    except PredictionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/leaderboard", response_model=PredictionLeaderboardView)
def get_prediction_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    _actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PredictionLeaderboardView:
    service = PredictionService(session)
    return PredictionLeaderboardView(
        entries=[PredictionLeaderboardEntryView.model_validate(item) for item in service.leaderboard(limit=limit)]
    )


__all__ = ["router"]
