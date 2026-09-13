from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.common.enums.transfer_window_status import TransferWindowStatus
from app.models.regen import RegenContractOffer
from app.models.transfer_bid import TransferBid
from app.models.user import User
from app.schemas.player_lifecycle import (
    RegenContractOfferQuoteRequest,
    TransferBidCreateRequest,
    TransferBidView,
)
from app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)
from app.services.regen_contract_offer_service import accept_regen_contract_offer

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> PlayerLifecycleService:
    return PlayerLifecycleService(session)


def _raise_lifecycle_error(exc: Exception) -> None:
    if isinstance(exc, PlayerLifecycleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/api/players/{player_id}/regen/contract-offers",
    response_model=TransferBidView,
    status_code=status.HTTP_201_CREATED,
)
def submit_regen_contract_offer_endpoint(
    player_id: str,
    payload: RegenContractOfferQuoteRequest,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    """Submit a free-agent regen offer through the canonical transfer engine."""
    try:
        club = service._require_club_profile(payload.offering_club_id)
        if club.owner_user_id != current_user.id:
            raise PlayerLifecycleValidationError("Only the owning club user can submit this contract offer")

        effective_date = date.today()
        regen = service._require_regen_profile(player_id)
        existing = service.session.scalar(
            select(RegenContractOffer)
            .where(
                RegenContractOffer.regen_id == regen.id,
                RegenContractOffer.offering_club_id == payload.offering_club_id,
                RegenContractOffer.offered_salary_fancoin_per_year == payload.offered_salary_fancoin_per_year,
                RegenContractOffer.contract_years == payload.contract_years,
                RegenContractOffer.status.in_(("submitted", "pending")),
                RegenContractOffer.decision_deadline >= datetime.combine(effective_date, time.min),
            )
            .order_by(RegenContractOffer.created_at.desc())
        )
        if existing is not None and existing.transfer_bid_id is not None:
            bid = service.session.get(TransferBid, existing.transfer_bid_id)
            if bid is not None:
                return service.to_transfer_bid_view(bid)

        windows = service.list_transfer_windows(active_on=effective_date)
        window = next(
            (
                candidate
                for candidate in windows
                if str(getattr(candidate.status, "value", candidate.status)).lower()
                == TransferWindowStatus.OPEN.value
            ),
            None,
        )
        if window is None:
            raise PlayerLifecycleValidationError(
                "No open GTEX transfer window is available for regen contract offers"
            )

        bid = service.create_bid(
            window.id,
            TransferBidCreateRequest(
                player_id=player_id,
                selling_club_id=None,
                buying_club_id=payload.offering_club_id,
                bid_amount=Decimal("0"),
                wage_offer_amount=payload.offered_salary_fancoin_per_year,
                contract_years=payload.contract_years,
                notes="regen_contract_offer",
            ),
            submitted_on=effective_date,
        )
        return service.to_transfer_bid_view(bid)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_lifecycle_error(exc)


@router.post(
    "/api/players/{player_id}/regen/contract-offers/{offer_id}/accept",
    response_model=TransferBidView,
)
def accept_regen_contract_offer_endpoint(
    player_id: str,
    offer_id: str,
    service: PlayerLifecycleService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> TransferBidView:
    try:
        accepted_bid = accept_regen_contract_offer(
            service.session,
            player_id=player_id,
            offer_id=offer_id,
            actor=current_user,
        )
        return service.to_transfer_bid_view(accepted_bid)
    except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
        _raise_lifecycle_error(exc)
