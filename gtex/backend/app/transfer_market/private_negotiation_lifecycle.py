from __future__ import annotations

from typing import Any

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models.transfer_market import TransferHubOffer, TransferListing, TransferNegotiation


_TERMINAL_NEGOTIATION_STATUSES = frozenset({"completed"})


def _hub_terms(offer: TransferHubOffer) -> dict[str, Any]:
    return {
        "source": "transfer_hub_private_negotiation",
        "hub_offer_id": offer.id,
        "offer_type": offer.offer_type,
        "cash_amount": str(offer.cash_amount),
        "offered_player_ids": list(offer.offered_player_ids_json or []),
        "loan_terms": dict(offer.loan_terms_json or {}),
        "swap_terms": dict(offer.swap_terms_json or {}),
        "conditional_terms": dict(offer.conditional_terms_json or {}),
        "sell_on_percentage": (
            str(offer.sell_on_percentage) if offer.sell_on_percentage is not None else None
        ),
    }


def _accepted_hub_offer(session: Session, listing: TransferListing) -> TransferHubOffer | None:
    for candidate in session.dirty:
        if (
            isinstance(candidate, TransferHubOffer)
            and candidate.listing_id == listing.id
            and candidate.status == "accepted"
        ):
            return candidate
    return session.scalar(
        select(TransferHubOffer)
        .where(
            TransferHubOffer.listing_id == listing.id,
            TransferHubOffer.status == "accepted",
        )
        .order_by(TransferHubOffer.resolved_at.desc(), TransferHubOffer.created_at.desc())
    )


def _ensure_private_negotiation(session: Session, listing: TransferListing) -> None:
    if listing.listing_type != "private_negotiation" or listing.status != "accepted":
        return

    offer = _accepted_hub_offer(session, listing)
    if offer is None:
        return

    negotiation = session.scalar(
        select(TransferNegotiation).where(TransferNegotiation.listing_id == listing.id)
    )
    if negotiation is not None and negotiation.status in _TERMINAL_NEGOTIATION_STATUSES:
        return

    hub_terms = _hub_terms(offer)
    if negotiation is None:
        session.add(
            TransferNegotiation(
                listing_id=listing.id,
                winning_bid_id=None,
                player_id=listing.player_id,
                selling_club_id=offer.seller_club_id,
                bidder_club_id=offer.bidder_club_id,
                status="awaiting_contract_offer",
                clauses_json=hub_terms,
                metadata_json=hub_terms,
            )
        )
        return

    negotiation.winning_bid_id = None
    negotiation.player_id = listing.player_id
    negotiation.selling_club_id = offer.seller_club_id
    negotiation.bidder_club_id = offer.bidder_club_id
    negotiation.status = "awaiting_contract_offer"
    negotiation.resolved_at = None
    negotiation.decision_due_at = None
    negotiation.clauses_json = {**dict(negotiation.clauses_json or {}), **hub_terms}
    negotiation.metadata_json = {**dict(negotiation.metadata_json or {}), **hub_terms}


@event.listens_for(Session, "before_flush")
def _materialize_private_negotiation_on_accept(
    session: Session,
    _flush_context: Any,
    _instances: Any,
) -> None:
    accepted_listings = [
        listing
        for listing in session.dirty
        if isinstance(listing, TransferListing)
        and listing.status == "accepted"
        and listing.listing_type == "private_negotiation"
    ]
    for listing in accepted_listings:
        _ensure_private_negotiation(session, listing)
