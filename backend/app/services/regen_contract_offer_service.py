from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.regen import RegenContractOffer
from app.models.transfer_bid import TransferBid
from app.models.user import User
from app.schemas.player_lifecycle import TransferBidAcceptRequest
from app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)


class RegenContractOfferServiceError(PlayerLifecycleValidationError):
    """Raised when a regen contract offer cannot be accepted."""


def accept_regen_contract_offer(
    session: Session,
    *,
    player_id: str,
    offer_id: str,
    actor: User,
    reference_on: date | None = None,
) -> TransferBid:
    effective_date = reference_on or date.today()
    offer = session.get(RegenContractOffer, offer_id)
    if offer is None:
        raise PlayerLifecycleNotFoundError(f"Regen contract offer {offer_id} was not found")
    if offer.transfer_bid_id is None:
        raise RegenContractOfferServiceError("Regen contract offer is missing its transfer bid")

    bid = session.get(TransferBid, offer.transfer_bid_id)
    if bid is None:
        raise PlayerLifecycleNotFoundError(f"Transfer bid {offer.transfer_bid_id} was not found")
    if bid.player_id != player_id:
        raise RegenContractOfferServiceError("Contract offer does not belong to this player")
    if bid.buying_club_id != offer.offering_club_id:
        raise RegenContractOfferServiceError("Contract offer club does not match its transfer bid")

    service = PlayerLifecycleService(session)
    club = service._require_club_profile(offer.offering_club_id)
    if club.owner_user_id != actor.id:
        raise RegenContractOfferServiceError("Only the owning club user can accept this contract offer")

    if offer.status == "accepted":
        accepted_by = str((offer.metadata_json or {}).get("accepted_by_user_id") or "")
        if accepted_by and accepted_by != actor.id:
            raise RegenContractOfferServiceError("Contract offer was already accepted by another actor")
        return bid

    if offer.decision_deadline.date() < effective_date:
        offer.status = "expired"
        session.commit()
        raise RegenContractOfferServiceError("Regen contract offer has expired")
    if offer.status not in {"submitted", "pending"}:
        raise RegenContractOfferServiceError(f"Offer {offer_id} is no longer actionable")

    starts_on = effective_date
    ends_on = starts_on + timedelta(days=365 * offer.contract_years - 1)
    accepted_bid = service.accept_bid(
        bid.window_id,
        bid.id,
        TransferBidAcceptRequest(
            contract_starts_on=starts_on,
            contract_ends_on=ends_on,
            wage_amount=offer.offered_salary_fancoin_per_year,
            signed_on=effective_date,
        ),
        reference_on=effective_date,
    )

    session.refresh(offer)
    offer.status = "accepted"
    metadata = dict(offer.metadata_json or {})
    metadata["accepted_on"] = effective_date.isoformat()
    metadata["accepted_by_user_id"] = actor.id
    metadata["accepted_bid_id"] = accepted_bid.id
    offer.metadata_json = metadata
    session.commit()
    session.refresh(accepted_bid)
    return accepted_bid
