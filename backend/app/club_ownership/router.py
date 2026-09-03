from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_ownership.schemas import (
    ClubGovernanceActionView,
    ClubGovernanceProposalRequest,
    ClubGovernanceVoteRequest,
    ClubOwnershipView,
    ClubPortfolioView,
    ClubTokenTradeRequest,
    ClubTokenTradeResultView,
    ClubTreasuryView,
)
from app.club_ownership.service import ClubOwnershipError, ClubOwnershipNotFoundError, ClubOwnershipService
from app.models.user import User

router = APIRouter(tags=["club-ownership"])
legacy_router = APIRouter(prefix="/clubs", tags=["club-ownership"])
api_router = APIRouter(prefix="/api/clubs", tags=["club-ownership"])
portfolio_router = APIRouter(prefix="/api/portfolio", tags=["club-ownership"])


@portfolio_router.get("/clubs", response_model=ClubPortfolioView)
def get_my_club_portfolio(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubPortfolioView:
    """The signed-in user's club-share holdings, valued at the live token price.

    Companion to ``GET /api/portfolio`` (player holdings); the portfolio surface
    renders these as an explicitly-labelled club-ownership section.
    """
    return ClubOwnershipService(session).list_user_club_portfolio(user=user)


@legacy_router.get("/{club_id}/ownership", response_model=ClubOwnershipView)
@api_router.get("/{club_id}/ownership", response_model=ClubOwnershipView)
def get_club_ownership(
    club_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ClubOwnershipView:
    service = ClubOwnershipService(session)
    try:
        return service.get_ownership_view(club_id=club_id, user=user)
    except ClubOwnershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@legacy_router.post("/{club_id}/buy-tokens", response_model=ClubTokenTradeResultView)
@api_router.post("/{club_id}/buy-tokens", response_model=ClubTokenTradeResultView)
def buy_club_tokens(
    club_id: str,
    payload: ClubTokenTradeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubTokenTradeResultView:
    service = ClubOwnershipService(session)
    try:
        result = service.buy_tokens(club_id=club_id, buyer=user, quantity=payload.quantity)
        session.commit()
        return result
    except ClubOwnershipNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@legacy_router.post("/{club_id}/sell-tokens", response_model=ClubTokenTradeResultView)
@api_router.post("/{club_id}/sell-tokens", response_model=ClubTokenTradeResultView)
def sell_club_tokens(
    club_id: str,
    payload: ClubTokenTradeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubTokenTradeResultView:
    service = ClubOwnershipService(session)
    try:
        result = service.sell_tokens(club_id=club_id, seller=user, quantity=payload.quantity)
        session.commit()
        return result
    except ClubOwnershipNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@legacy_router.post("/{club_id}/proposals", response_model=ClubGovernanceActionView)
@api_router.post("/{club_id}/proposals", response_model=ClubGovernanceActionView)
def create_club_proposal(
    club_id: str,
    payload: ClubGovernanceProposalRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubGovernanceActionView:
    service = ClubOwnershipService(session)
    try:
        result = service.create_proposal(club_id=club_id, proposer=user, payload=payload)
        session.commit()
        return result
    except ClubOwnershipNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@legacy_router.post("/{club_id}/vote", response_model=ClubGovernanceActionView)
@api_router.post("/{club_id}/vote", response_model=ClubGovernanceActionView)
def vote_on_club_proposal(
    club_id: str,
    payload: ClubGovernanceVoteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubGovernanceActionView:
    service = ClubOwnershipService(session)
    try:
        result = service.vote_on_proposal(club_id=club_id, voter=user, payload=payload)
        session.commit()
        return result
    except ClubOwnershipNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@legacy_router.get("/{club_id}/treasury", response_model=ClubTreasuryView)
@api_router.get("/{club_id}/treasury", response_model=ClubTreasuryView)
def get_club_treasury(
    club_id: str, _: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ClubTreasuryView:
    service = ClubOwnershipService(session)
    try:
        return service.get_treasury_view(club_id=club_id)
    except ClubOwnershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClubOwnershipError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)
router.include_router(portfolio_router)

__all__ = ["router"]
