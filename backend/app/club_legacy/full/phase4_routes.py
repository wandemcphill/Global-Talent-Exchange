"""HTTP routes for Club Legacy phase 4."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy.full import phase4
from app.club_legacy.full.http import run_legacy

router = APIRouter()


class PurchaseBody(BaseModel):
    sku: str
    owner_class: Literal["club", "owner"]
    idempotency_key: str = Field(min_length=2, max_length=128)


class TransferBody(BaseModel):
    asset_id: str
    to_owner_class: Literal["owner", "club", "player", "manager"]
    to_owner_ref: str
    price: Decimal = Decimal("0")
    idempotency_key: str = Field(min_length=2, max_length=128)
    payer_club_id: str | None = None


class GiftBody(BaseModel):
    asset_id: str
    recipient_ref: str


class ListingBody(BaseModel):
    asset_id: str
    price: Decimal
    kind: Literal["fixed", "auction"] = "fixed"


class BuyBody(BaseModel):
    idempotency_key: str = Field(min_length=2, max_length=128)


class BidBody(BaseModel):
    amount: Decimal


@router.post("/{club_id}/market/purchases")
def purchase_asset(
    club_id: str, body: PurchaseBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    def go():
        asset = phase4.purchase_asset(
            session,
            club_id=club_id,
            user_id=user.id,
            sku=body.sku,
            owner_class=body.owner_class,
            idempotency_key=body.idempotency_key,
        )
        return phase4.asset_dict(asset)

    return run_legacy(session, go)


@router.post("/{club_id}/market/transfers")
def transfer_asset(
    club_id: str, body: TransferBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        row = phase4.transfer_asset(
            session,
            asset_id=body.asset_id,
            user_id=user.id,
            to_owner_class=body.to_owner_class,
            to_owner_ref=body.to_owner_ref,
            price=body.price,
            idempotency_key=body.idempotency_key,
            payer_club_id=body.payer_club_id,
        )
        return phase4.provenance_dict(row)

    return run_legacy(session, go)


@router.post("/{club_id}/market/gifts")
def offer_gift(club_id: str, body: GiftBody, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    del club_id

    def go():
        gift = phase4.offer_gift(session, asset_id=body.asset_id, user_id=user.id, recipient_ref=body.recipient_ref)
        return phase4.gift_dict(gift)

    return run_legacy(session, go)


@router.post("/{club_id}/market/gifts/{gift_id}/accept")
def accept_gift(
    club_id: str, gift_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        gift = phase4.resolve_gift(session, gift_id=gift_id, accept=True, actor_user_id=user.id)
        return phase4.gift_dict(gift)

    return run_legacy(session, go)


@router.post("/{club_id}/market/gifts/{gift_id}/decline")
def decline_gift(
    club_id: str, gift_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        gift = phase4.resolve_gift(session, gift_id=gift_id, accept=False, actor_user_id=user.id)
        return phase4.gift_dict(gift)

    return run_legacy(session, go)


@router.post("/{club_id}/market/listings")
def list_asset(
    club_id: str, body: ListingBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict:
    del club_id

    def go():
        listing = phase4.list_asset(
            session, asset_id=body.asset_id, user_id=user.id, price=body.price, kind=body.kind
        )
        return phase4.listing_dict(listing)

    return run_legacy(session, go)


@router.post("/{club_id}/market/listings/{listing_id}/buy")
def buy_listing(
    club_id: str,
    listing_id: str,
    body: BuyBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    def go():
        listing = phase4.buy_listing(
            session,
            listing_id=listing_id,
            buyer_user_id=user.id,
            buyer_club_id=club_id,
            idempotency_key=body.idempotency_key,
        )
        return phase4.listing_dict(listing)

    return run_legacy(session, go)


@router.post("/{club_id}/market/listings/{listing_id}/bids")
def place_bid(
    club_id: str,
    listing_id: str,
    body: BidBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    del club_id

    def go():
        bid = phase4.place_bid(session, listing_id=listing_id, bidder_user_id=user.id, amount=body.amount)
        return {"id": bid.id, "amount": str(bid.amount), "status": bid.status}

    return run_legacy(session, go)
