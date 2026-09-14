from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.common.enums.transfer_bid_status import TransferBidStatus
from app.models.user import User, UserRole
from app.schemas.player_lifecycle import RegenContractOfferQuoteRequest, RegenLifecycleView, TransferBidCreateRequest
from app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


def _raise_for_lifecycle_error(exc: Exception) -> None:
    if isinstance(exc, PlayerLifecycleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PlayerLifecycleValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _offer_matches_bid(bid, *, offering_club_id: str, salary: Decimal, contract_years: int) -> bool:
    if bid.buying_club_id != offering_club_id:
        return False
    if bid.status not in {
        TransferBidStatus.SUBMITTED.value,
        TransferBidStatus.ACCEPTED.value,
        TransferBidStatus.COMPLETED.value,
    }:
        return False
    contract_offer = dict((bid.structured_terms_json or {}).get("contract_offer") or {})
    try:
        recorded_salary = Decimal(str(contract_offer.get("offered_salary_fancoin_per_year")))
        recorded_years = int(contract_offer.get("contract_years"))
    except (TypeError, ValueError):
        return False
    return recorded_salary == salary and recorded_years == contract_years


@router.post(
    "/api/players/{player_id}/regen/contract-offers/submit",
    response_model=RegenLifecycleView,
)
def submit_regen_contract_offer(
    player_id: str,
    payload: RegenContractOfferQuoteRequest,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> RegenLifecycleView:
    try:
        club = service._require_club_profile(payload.offering_club_id)
        if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN} and club.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the offering club owner can submit a regen contract offer",
            )

        existing = next(
            (
                bid
                for bid in service.list_player_transfer_bids(player_id)
                if _offer_matches_bid(
                    bid,
                    offering_club_id=payload.offering_club_id,
                    salary=payload.offered_salary_fancoin_per_year,
                    contract_years=payload.contract_years,
                )
            ),
            None,
        )
        if existing is None:
            service.create_bid(
                service.list_transfer_windows(active_on=None)[0].id
                if False
                else next(
                    window.id
                    for window in service.list_transfer_windows(active_on=date.today())
                ),
                TransferBidCreateRequest(
                    player_id=player_id,
                    buying_club_id=payload.offering_club_id,
                    bid_amount=Decimal("0"),
                    wage_offer_amount=payload.offered_salary_fancoin_per_year,
                    contract_years=payload.contract_years,
                ),
            )

        return service.get_regen_summary(player_id, on_date=date.today())
    except HTTPException:
        raise
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_for_lifecycle_error(exc)
