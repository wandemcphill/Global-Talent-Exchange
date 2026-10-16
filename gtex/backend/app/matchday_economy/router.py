from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_optional_current_user, get_session
from app.models.user import User

from .schemas import (
    CardListingSettlementRequest,
    FederationSanctionResolutionRequest,
    MatchdayEconomyActionView,
    MatchdayEconomyOverviewView,
    PredictionRewardSettlementRequest,
    TicketCheckInRequest,
)
from .service import MatchdayEconomyActionError, MatchdayEconomyService

router = APIRouter(tags=["matchday-economy"])


def _service(session: Session = Depends(get_session)) -> MatchdayEconomyService:
    return MatchdayEconomyService(session)


@router.get("/matchday-economy/overview", response_model=MatchdayEconomyOverviewView)
def read_matchday_economy_overview(
    current_user: User | None = Depends(get_optional_current_user),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyOverviewView:
    return service.overview(user=current_user, admin=False)


@router.get("/admin/matchday-economy/overview", response_model=MatchdayEconomyOverviewView)
def read_admin_matchday_economy_overview(
    current_admin: User = Depends(get_current_admin),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyOverviewView:
    return service.overview(user=current_admin, admin=True)


@router.post("/admin/matchday-economy/federation-sanctions/{sanction_id}/resolve", response_model=MatchdayEconomyActionView)
def resolve_federation_sanction(
    sanction_id: str,
    payload: FederationSanctionResolutionRequest,
    current_admin: User = Depends(get_current_admin),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyActionView:
    try:
        return service.resolve_federation_sanction(sanction_id, payload, actor=current_admin)
    except MatchdayEconomyActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/matchday-economy/predictions/{fixture_id}/settle-rewards", response_model=MatchdayEconomyActionView)
def settle_prediction_rewards(
    fixture_id: str,
    payload: PredictionRewardSettlementRequest,
    current_admin: User = Depends(get_current_admin),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyActionView:
    try:
        return service.settle_prediction_rewards(fixture_id, payload, actor=current_admin)
    except MatchdayEconomyActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/matchday-economy/tickets/{ticket_id}/check-in", response_model=MatchdayEconomyActionView)
def check_in_ticket(
    ticket_id: str,
    payload: TicketCheckInRequest,
    current_admin: User = Depends(get_current_admin),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyActionView:
    try:
        return service.check_in_ticket(ticket_id, payload, actor=current_admin)
    except MatchdayEconomyActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/matchday-economy/card-listings/{listing_id}/settle", response_model=MatchdayEconomyActionView)
def settle_card_listing(
    listing_id: str,
    payload: CardListingSettlementRequest,
    current_admin: User = Depends(get_current_admin),
    service: MatchdayEconomyService = Depends(_service),
) -> MatchdayEconomyActionView:
    try:
        return service.settle_card_listing(listing_id, payload, actor=current_admin)
    except MatchdayEconomyActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
