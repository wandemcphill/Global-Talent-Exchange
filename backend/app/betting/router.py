from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_wallet_user, get_session
from app.betting.schemas import (
    BetHistoryResponse,
    BetOddsResponse,
    BetPlaceRequest,
    BetPlaceResponse,
    BetPreferenceRequest,
    BettingProfileView,
)
from app.betting.service import BettingError, BettingService
from app.models.user import User

router = APIRouter(tags=["betting"])


def _service(session: Session = Depends(get_session)) -> BettingService:
    return BettingService(session=session)


def _raise(exc: BettingError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/bets/preferences", response_model=BettingProfileView)
def update_betting_preferences(
    payload: BetPreferenceRequest,
    actor: User = Depends(get_current_wallet_user),
    service: BettingService = Depends(_service),
) -> BettingProfileView:
    try:
        result = service.update_preferences(actor=actor, payload=payload)
    except BettingError as exc:
        _raise(exc)
    service.session.commit()
    return result


@router.get("/bets/odds/{match_id}", response_model=BetOddsResponse)
def get_match_odds(
    match_id: str,
    region_code: str | None = Query(default=None),
    actor: User = Depends(get_current_wallet_user),
    service: BettingService = Depends(_service),
) -> BetOddsResponse:
    try:
        return service.get_odds(actor=actor, match_id=match_id, region_code=region_code)
    except BettingError as exc:
        _raise(exc)
    raise AssertionError("unreachable")


@router.post("/bets/place", response_model=BetPlaceResponse, status_code=status.HTTP_201_CREATED)
def place_bet(
    payload: BetPlaceRequest,
    actor: User = Depends(get_current_wallet_user),
    service: BettingService = Depends(_service),
) -> BetPlaceResponse:
    try:
        result = service.place_bet(actor=actor, payload=payload)
    except BettingError as exc:
        _raise(exc)
    service.session.commit()
    return result


@router.get("/bets/history", response_model=BetHistoryResponse)
def get_bet_history(
    actor: User = Depends(get_current_wallet_user),
    service: BettingService = Depends(_service),
) -> BetHistoryResponse:
    try:
        result = service.history(actor=actor)
    except BettingError as exc:
        _raise(exc)
    service.session.commit()
    return result
