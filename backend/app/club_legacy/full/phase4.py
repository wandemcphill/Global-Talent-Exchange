"""Phase 4 market: purchase, transfer, gift, caps, listings, and fees.

Documented defaults, used when ``club_legacy_market_settings`` has no row:

* transfer fee rate ``0.05`` (5 percent of a priced transfer or resale)
* club jet cap ``5``
* club coach cap ``10``

Primary-market purchases debit the buying club's treasury exactly once.
The fee on a resale or priced transfer is its own ledger line.
Gift acceptance writes a relationship event. That event does not set loyalty
or morale to 100, and it does not write those fields onto a player record.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError, require_owner
from app.club_legacy.full.support import money, remember_refusal
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyBid,
    ClubLegacyCatalogueItem,
    ClubLegacyGift,
    ClubLegacyListing,
    ClubLegacyMarketSettings,
    ClubLegacyProvenance,
    ClubLegacyRelationshipEvent,
)
from app.models.club_profile import ClubProfile
from app.owner_console import ledger

OWNER_CLASSES = ("owner", "club", "player", "manager")
PURCHASE_CLASSES = ("owner", "club")
SETTINGS_KEY = "club_legacy_market"
# Used only when the admin settings row is absent. See the module docstring.
DEFAULT_TRANSFER_FEE_RATE = Decimal("0.0500")
DEFAULT_JET_CAP = 5
DEFAULT_COACH_CAP = 10
# Relationship events are a social note, not a player attribute, and stay well below 100.
RELATIONSHIP_LOYALTY = 12
RELATIONSHIP_MORALE = 9


def market_limits(session: Session) -> tuple[Decimal, int, int]:
    row = session.scalar(select(ClubLegacyMarketSettings).where(ClubLegacyMarketSettings.settings_key == SETTINGS_KEY))
    if row is None:
        return DEFAULT_TRANSFER_FEE_RATE, DEFAULT_JET_CAP, DEFAULT_COACH_CAP
    return Decimal(row.transfer_fee_rate), int(row.jet_cap), int(row.coach_cap)


def purchase_asset(
    session: Session, *, club_id: str, user_id: str, sku: str, owner_class: str, idempotency_key: str
) -> ClubLegacyAsset:
    require_owner(session, club_id, user_id)
    if owner_class not in PURCHASE_CLASSES:
        raise LegacyError("invalid_owner_class")
    existing = session.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    from app.club_legacy.operations import seed_catalogue

    seed_catalogue(session)
    item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == sku))
    if item is None:
        raise LegacyError("unknown_item", 404)
    edition = _mint_one(session, item)
    try:
        _enforce_club_cap(session, club_id, item.category)
    except LegacyError:
        _unmint(session, item)
        raise
    owner_ref = club_id if owner_class == "club" else user_id
    asset = ClubLegacyAsset(
        catalogue_id=item.id,
        edition_number=edition,
        owner_class=owner_class,
        owner_ref=owner_ref,
        club_id=club_id,
        status="owned",
        idempotency_key=idempotency_key,
    )
    try:
        with session.begin_nested():
            session.add(asset)
            session.flush()
    except IntegrityError:
        _unmint(session, item)
        existing = session.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
        raise LegacyError("sold_out", 409) from None
    source = ledger.wallet_account(session, ledger.club_account(club_id), ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.PLATFORM_FEES, ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"asset:{idempotency_key}",
        source=source,
        destination=destination,
        amount=Decimal(item.price),
        description=f"Buy {item.name}",
    )
    session.flush()
    return asset


def _mint_one(session: Session, item: ClubLegacyCatalogueItem) -> int:
    """Increment minted_count only while the row is still under its supply cap."""
    minted = session.execute(
        update(ClubLegacyCatalogueItem)
        .where(ClubLegacyCatalogueItem.id == item.id)
        .where(
            or_(
                ClubLegacyCatalogueItem.supply_cap.is_(None),
                ClubLegacyCatalogueItem.minted_count < ClubLegacyCatalogueItem.supply_cap,
            )
        )
        .values(minted_count=ClubLegacyCatalogueItem.minted_count + 1)
        .returning(ClubLegacyCatalogueItem.minted_count)
    ).scalar_one_or_none()
    if minted is None:
        raise LegacyError("sold_out", 409)
    session.expire(item)
    return int(minted)


def _unmint(session: Session, item: ClubLegacyCatalogueItem) -> None:
    session.execute(
        update(ClubLegacyCatalogueItem)
        .where(ClubLegacyCatalogueItem.id == item.id)
        .where(ClubLegacyCatalogueItem.minted_count > 0)
        .values(minted_count=ClubLegacyCatalogueItem.minted_count - 1)
    )
    session.expire(item)


def _enforce_club_cap(session: Session, club_id: str, category: str) -> None:
    from app.club_legacy.full.phase1 import inventory_cap

    _, jet_cap, coach_cap = market_limits(session)
    cap = {"jet": jet_cap, "coach": coach_cap}.get(category)
    configured = inventory_cap(session, category)
    if configured is not None:
        cap = configured if cap is None else min(cap, configured)
    if cap is None:
        return
    owned = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyAsset)
            .join(ClubLegacyCatalogueItem, ClubLegacyCatalogueItem.id == ClubLegacyAsset.catalogue_id)
            .where(
                ClubLegacyAsset.club_id == club_id,
                ClubLegacyAsset.owner_class == "club",
                ClubLegacyCatalogueItem.category == category,
                ClubLegacyAsset.status == "owned",
            )
        )
        or 0
    )
    if int(owned) >= cap:
        raise LegacyError("inventory_cap", 409, f"Club already holds {cap} {category} assets.")


def transfer_asset(
    session: Session,
    *,
    asset_id: str,
    user_id: str,
    to_owner_class: str,
    to_owner_ref: str,
    price,
    idempotency_key: str,
    payer_club_id: str | None = None,
) -> ClubLegacyProvenance:
    """Move an asset between owner, club, player, and manager.

    The provenance row and any ledger lines commit or roll back together.
    A priced move debits the paying club and posts the transfer fee on its own line.
    """
    if to_owner_class not in OWNER_CLASSES:
        raise LegacyError("invalid_owner_class")
    existing = session.scalar(
        select(ClubLegacyProvenance).where(ClubLegacyProvenance.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    asset = session.get(ClubLegacyAsset, asset_id)
    if asset is None or asset.status != "owned":
        raise LegacyError("asset_unavailable", 409)
    _require_holder(session, asset, user_id)
    gross = money(price)
    if gross < 0:
        raise LegacyError("amount_must_be_positive")
    fee_rate, _, _ = market_limits(session)
    fee = money(gross * fee_rate) if gross > 0 else Decimal("0.00")
    provenance = ClubLegacyProvenance(
        asset_id=asset.id,
        from_owner_class=asset.owner_class,
        from_owner_ref=asset.owner_ref,
        to_owner_class=to_owner_class,
        to_owner_ref=to_owner_ref,
        price=gross,
        actor_user_id=user_id,
        idempotency_key=idempotency_key,
    )
    savepoint = session.begin_nested()
    try:
        session.add(provenance)
        if gross > 0:
            paying_club = payer_club_id or (to_owner_ref if to_owner_class == "club" else asset.club_id)
            receiving_club = asset.club_id or paying_club
            if paying_club is None or receiving_club is None:
                raise LegacyError("transfer_account_missing", 409)
            source = ledger.wallet_account(session, ledger.club_account(paying_club), ledger.GTEX)
            destination = ledger.wallet_account(session, ledger.club_account(receiving_club), ledger.GTEX)
            post_club_legacy_transfer(
                session,
                idempotency_key=f"transfer:{idempotency_key}",
                source=source,
                destination=destination,
                amount=gross,
                actor=None,
                description="Club Legacy asset transfer",
            )
            if fee > 0:
                fee_source = ledger.wallet_account(session, ledger.club_account(paying_club), ledger.GTEX)
                fee_destination = ledger.wallet_account(session, ledger.PLATFORM_FEES, ledger.GTEX)
                post_club_legacy_transfer(
                    session,
                    idempotency_key=f"transfer-fee:{idempotency_key}",
                    source=fee_source,
                    destination=fee_destination,
                    amount=fee,
                    description="Club Legacy transfer fee",
                )
        asset.owner_class = to_owner_class
        asset.owner_ref = to_owner_ref
        if to_owner_class == "club":
            asset.club_id = to_owner_ref
        session.flush()
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise
    return provenance


def _require_holder(session: Session, asset: ClubLegacyAsset, user_id: str) -> None:
    if asset.owner_class == "club":
        require_owner(session, asset.owner_ref, user_id)
        return
    if asset.owner_class == "owner" and asset.owner_ref == user_id:
        return
    if asset.club_id is not None:
        require_owner(session, asset.club_id, user_id)
        return
    raise LegacyError("not_asset_owner", 403)


def offer_gift(session: Session, *, asset_id: str, user_id: str, recipient_ref: str) -> ClubLegacyGift:
    asset = session.get(ClubLegacyAsset, asset_id)
    if asset is None or asset.status != "owned":
        raise LegacyError("asset_unavailable", 409)
    if asset.owner_class == "club":
        require_owner(session, asset.owner_ref, user_id)
    elif asset.owner_class == "owner" and asset.owner_ref != user_id:
        raise LegacyError("not_asset_owner", 403)
    elif asset.owner_class not in {"club", "owner"} and asset.club_id is not None:
        require_owner(session, asset.club_id, user_id)
    asset.status = "offered"
    gift = ClubLegacyGift(asset_id=asset.id, sender_user_id=user_id, recipient_ref=recipient_ref, status="offered")
    session.add(gift)
    session.flush()
    return gift


def _is_gift_recipient(session: Session, gift: ClubLegacyGift, actor_user_id: str) -> bool:
    if actor_user_id == gift.recipient_ref:
        return True
    club = session.get(ClubProfile, gift.recipient_ref)
    if club is not None and club.owner_user_id == actor_user_id:
        return True
    from app.owner_console.models import OwnerSquadPlayer

    player = session.get(OwnerSquadPlayer, gift.recipient_ref)
    if player is not None and player.club_id is not None:
        player_club = session.get(ClubProfile, player.club_id)
        if player_club is not None and player_club.owner_user_id == actor_user_id:
            return True
    return False


def resolve_gift(session: Session, *, gift_id: str, accept: bool, actor_user_id: str | None = None) -> ClubLegacyGift:
    gift = session.get(ClubLegacyGift, gift_id)
    if gift is None or gift.status != "offered":
        raise LegacyError("gift_not_open", 409)
    asset = session.get(ClubLegacyAsset, gift.asset_id)
    if asset is None:
        raise LegacyError("asset_unavailable", 409)
    if not actor_user_id:
        raise LegacyError("gift_actor_required", 403, "An authenticated actor is required to resolve this gift.")

    from app.models.user import User, UserRole

    actor = session.get(User, actor_user_id)
    is_admin = actor is not None and actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}
    is_recipient = _is_gift_recipient(session, gift, actor_user_id)
    if not (is_recipient or is_admin):
        raise LegacyError("not_gift_recipient", 403, "Caller is not authorized to resolve this gift.")
    if accept:
        asset.owner_class = "player"
        asset.owner_ref = gift.recipient_ref
        asset.status = "owned"
        gift.status = "accepted"
        session.add(
            ClubLegacyRelationshipEvent(
                gift_id=gift.id,
                asset_id=asset.id,
                actor_user_id=actor_user_id,
                recipient_ref=gift.recipient_ref,
                kind="accepted",
                loyalty=RELATIONSHIP_LOYALTY,
                morale=RELATIONSHIP_MORALE,
            )
        )
    else:
        asset.status = "owned"
        gift.status = "declined"
    session.flush()
    return gift


def list_asset(session: Session, *, asset_id: str, user_id: str, price, kind: str = "fixed") -> ClubLegacyListing:
    asset = session.get(ClubLegacyAsset, asset_id)
    if asset is None or asset.status != "owned":
        raise LegacyError("asset_unavailable", 409)
    if asset.owner_class == "club":
        require_owner(session, asset.owner_ref, user_id)
    elif asset.owner_class == "owner" and asset.owner_ref != user_id:
        raise LegacyError("not_asset_owner", 403)
    fee_rate, _, _ = market_limits(session)
    gross = money(price)
    asset.status = "listed"
    listing = ClubLegacyListing(
        asset_id=asset.id,
        seller_user_id=user_id,
        price=gross,
        fee=money(gross * fee_rate),
        status="auction" if kind == "auction" else "open",
    )
    session.add(listing)
    session.flush()
    return listing


def buy_listing(
    session: Session, *, listing_id: str, buyer_user_id: str, buyer_club_id: str, idempotency_key: str
) -> ClubLegacyListing:
    existing = session.scalar(select(ClubLegacyListing).where(ClubLegacyListing.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    listing = session.get(ClubLegacyListing, listing_id)
    if listing is None or listing.status != "open":
        raise LegacyError("listing_closed", 409)
    asset = session.get(ClubLegacyAsset, listing.asset_id)
    if asset is None:
        raise LegacyError("asset_unavailable", 409)
    require_owner(session, buyer_club_id, buyer_user_id)
    _reject_related_trade(session, asset=asset, buyer_club_id=buyer_club_id, actor_user_id=buyer_user_id)
    fee_rate, _, _ = market_limits(session)
    fee = money(Decimal(listing.price) * fee_rate)
    listing.fee = fee
    listing.status = "escrow"
    session.flush()
    seller_club_id = asset.club_id or buyer_club_id
    previous_class = asset.owner_class
    previous_ref = asset.owner_ref
    savepoint = session.begin_nested()
    try:
        source = ledger.wallet_account(session, ledger.club_account(buyer_club_id), ledger.GTEX)
        destination = ledger.wallet_account(session, ledger.club_account(seller_club_id), ledger.GTEX)
        post_club_legacy_transfer(
            session,
            idempotency_key=f"sale:{idempotency_key}",
            source=source,
            destination=destination,
            amount=Decimal(listing.price),
            description="Asset resale",
        )
        if fee > 0:
            fee_source = ledger.wallet_account(session, ledger.club_account(seller_club_id), ledger.GTEX)
            fee_destination = ledger.wallet_account(session, ledger.PLATFORM_FEES, ledger.GTEX)
            post_club_legacy_transfer(
                session,
                idempotency_key=f"sale-fee:{idempotency_key}",
                source=fee_source,
                destination=fee_destination,
                amount=fee,
                description="Club Legacy transfer fee",
            )
        asset.owner_class = "club"
        asset.owner_ref = buyer_club_id
        asset.club_id = buyer_club_id
        asset.status = "owned"
        listing.status = "sold"
        listing.idempotency_key = idempotency_key
        session.add(
            ClubLegacyProvenance(
                asset_id=asset.id,
                from_owner_class=previous_class,
                from_owner_ref=previous_ref,
                to_owner_class="club",
                to_owner_ref=buyer_club_id,
                price=money(listing.price),
                actor_user_id=buyer_user_id,
                idempotency_key=f"sale-provenance:{idempotency_key}",
            )
        )
        session.flush()
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        listing.status = "open"
        session.flush()
        raise
    return listing


def _reject_related_trade(session: Session, *, asset: ClubLegacyAsset, buyer_club_id: str, actor_user_id: str) -> None:
    seller_club = session.get(ClubProfile, asset.club_id) if asset.club_id else None
    buyer_club = session.get(ClubProfile, buyer_club_id)
    if (
        seller_club is not None
        and buyer_club is not None
        and seller_club.owner_user_id == buyer_club.owner_user_id
        and seller_club.id != buyer_club.id
    ):
        remember_refusal(
            session,
            club_id=seller_club.id,
            actor_user_id=actor_user_id,
            action="related_club_refused",
            detail={
                "buyer_club_id": buyer_club_id,
                "seller_club_id": seller_club.id,
                "asset_id": asset.id,
                "reason": "wash_trade",
            },
        )
        from app.club_legacy.full.phase8 import log_trade_review

        log_trade_review(
            session,
            listing_id=None,
            from_club_id=seller_club.id,
            to_club_id=buyer_club_id,
            kind="sister_club",
            note="Sister-club marketplace trade is blocked and left reviewable.",
        )
        log_trade_review(
            session,
            listing_id=None,
            from_club_id=seller_club.id,
            to_club_id=buyer_club_id,
            kind="related_party",
            note="Related-party marketplace trade is blocked and left reviewable.",
        )
        raise LegacyError("wash_trade", 409, "Related clubs cannot trade this asset with each other.")


def place_bid(session: Session, *, listing_id: str, bidder_user_id: str, amount) -> ClubLegacyBid:
    listing = session.get(ClubLegacyListing, listing_id)
    if listing is None or listing.status != "auction":
        raise LegacyError("auction_closed", 409)
    asset = session.get(ClubLegacyAsset, listing.asset_id)
    if bidder_user_id == listing.seller_user_id:
        remember_refusal(
            session,
            club_id=asset.club_id if asset is not None else None,
            actor_user_id=bidder_user_id,
            action="seller_bid_refused",
            detail={"listing_id": listing.id, "reason": "wash_trade"},
        )
        from app.club_legacy.full.phase8 import log_trade_review

        log_trade_review(
            session,
            listing_id=listing.id,
            from_club_id=asset.club_id if asset is not None else None,
            to_club_id=asset.club_id if asset is not None else None,
            kind="related_party",
            note="The seller cannot bid on their own auction.",
        )
        raise LegacyError("wash_trade", 409, "The seller cannot bid on their own auction.")

    if asset is not None and asset.club_id is not None:
        seller_club = session.get(ClubProfile, asset.club_id)
        bidder_clubs = session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == bidder_user_id)).all()
        for club in bidder_clubs:
            if (
                seller_club is not None
                and club.owner_user_id == seller_club.owner_user_id
                and club.id != seller_club.id
            ):
                remember_refusal(
                    session,
                    club_id=seller_club.id,
                    actor_user_id=bidder_user_id,
                    action="related_club_refused",
                    detail={"listing_id": listing.id, "buyer_club_id": club.id, "reason": "wash_trade"},
                )
                raise LegacyError("wash_trade", 409, "Related clubs cannot trade this asset with each other.")
    bid_amount = money(amount)
    leading = session.scalar(
        select(ClubLegacyBid).where(ClubLegacyBid.listing_id == listing.id, ClubLegacyBid.status == "leading")
    )
    if leading is not None and bid_amount <= Decimal(leading.amount):
        raise LegacyError("bid_too_low", 409)
    if leading is not None:
        leading.status = "outbid"
    bid = ClubLegacyBid(listing_id=listing.id, bidder_user_id=bidder_user_id, amount=bid_amount, status="leading")
    session.add(bid)
    session.flush()
    return bid


def asset_dict(asset: ClubLegacyAsset) -> dict:
    return {
        "id": asset.id,
        "owner_class": asset.owner_class,
        "owner_ref": asset.owner_ref,
        "club_id": asset.club_id,
        "status": asset.status,
        "edition_number": asset.edition_number,
        "idempotency_key": asset.idempotency_key,
    }


def provenance_dict(row: ClubLegacyProvenance) -> dict:
    return {
        "id": row.id,
        "asset_id": row.asset_id,
        "from_owner_class": row.from_owner_class,
        "from_owner_ref": row.from_owner_ref,
        "to_owner_class": row.to_owner_class,
        "to_owner_ref": row.to_owner_ref,
        "price": str(row.price),
        "actor_user_id": row.actor_user_id,
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
    }


def gift_dict(gift: ClubLegacyGift) -> dict:
    return {
        "id": gift.id,
        "asset_id": gift.asset_id,
        "recipient_ref": gift.recipient_ref,
        "status": gift.status,
    }


def listing_dict(listing: ClubLegacyListing) -> dict:
    return {
        "id": listing.id,
        "asset_id": listing.asset_id,
        "price": str(listing.price),
        "fee": str(listing.fee),
        "status": listing.status,
        "seller_user_id": listing.seller_user_id,
    }
