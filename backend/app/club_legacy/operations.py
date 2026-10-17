"""Club Legacy phases 2-9. Money moves only through the wallet ledger."""

from __future__ import annotations

from decimal import Decimal
import random

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import (
    PRESEASON_RESPONSE,
    LegacyError,
    policy_for,
    require_owner,
)
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyBid,
    ClubLegacyCase,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
    ClubLegacyGift,
    ClubLegacyKitVersion,
    ClubLegacyListing,
    ClubLegacyManagerOffer,
    ClubLegacyPolicy,
    ClubLegacyPreseasonInvite,
    ClubLegacyPreseasonSettlement,
    ClubLegacyPreseasonWindow,
    ClubLegacyPromise,
    ClubLegacyReport,
    ClubLegacySponsorContract,
    ClubLegacyStake,
)
from app.club_legacy.ratings import development_score, financial_strength, prestige_score
from app.models.club_profile import ClubProfile
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState

JET_CAP = 5
COACH_CAP = 10
CATALOGUE = (
    {
        "sku": "gtex-jet-harbour",
        "name": "Harbour Jet",
        "category": "jet",
        "price": "50000",
        "supply_cap": 5,
        "fallback_label": "Static jet card",
    },
    {
        "sku": "gtex-coach-lagoon",
        "name": "Lagoon Coach",
        "category": "coach",
        "price": "8000",
        "supply_cap": 10,
        "fallback_label": "Static coach card",
    },
    {
        "sku": "gtex-watch-icon",
        "name": "Icon Watch",
        "category": "watch",
        "price": "20000",
        "supply_cap": 1,
        "fallback_label": "Static watch card",
    },
)
TV_SHARES = {
    "foundation": Decimal("0.30"),
    "growing": Decimal("0.40"),
    "established": Decimal("0.50"),
    "elite": Decimal("0.60"),
    "legacy": Decimal("0.70"),
}
HOST_CUT_OF_CLUB_POOL = Decimal("0.40")


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def seed_catalogue(session: Session) -> None:
    existing = {item.sku for item in session.scalars(select(ClubLegacyCatalogueItem)).all()}
    for spec in CATALOGUE:
        if spec["sku"] in existing:
            continue
        session.add(
            ClubLegacyCatalogueItem(
                sku=spec["sku"],
                name=spec["name"],
                category=spec["category"],
                price=_q(spec["price"]),
                supply_cap=spec["supply_cap"],
                minted_count=0,
                fallback_label=spec["fallback_label"],
            )
        )
    session.flush()


def hire_executive(
    session: Session, club_id: str, user_id: str, *, role: str, name: str, personality: str, wage
) -> ClubLegacyExecutive:
    if role not in {"gm", "hoyd", "football_manager"}:
        raise LegacyError("unknown_role")
    require_owner(session, club_id, user_id)
    current = session.scalar(
        select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id, ClubLegacyExecutive.role == role)
    )
    attributes = _attributes(role, name)
    attributes.update(_hiring_fit(session, club_id))
    if current is None:
        current = ClubLegacyExecutive(
            club_id=club_id,
            role=role,
            name=name,
            personality=personality,
            attributes_json=attributes,
            wage=_q(wage),
            status="hired",
        )
        session.add(current)
    else:
        current.name = name
        current.personality = personality
        current.attributes_json = attributes
        current.wage = _q(wage)
        current.status = "hired"
    session.flush()
    return current


def _attributes(role: str, name: str) -> dict[str, int]:
    rng = random.Random(f"{role}:{name}")
    keys = {
        "gm": ("intelligence", "talent_evaluation", "financial_acumen", "negotiation"),
        "hoyd": ("talent_identification", "potential_assessment", "recruitment_network", "judgement"),
        "football_manager": ("tactics", "squad_judgement", "training", "morale"),
    }[role]
    return {key: rng.randint(40, 85) for key in keys}


def _hiring_fit(session: Session, club_id: str) -> dict[str, int]:
    profile = session.get(ClubProfile, club_id)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    kept = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyPromise)
            .where(ClubLegacyPromise.club_id == club_id, ClubLegacyPromise.status == "kept")
        )
        or 0
    )
    facility = development_score(state.facilities_json if state else {})
    city_bonus = 10 if profile and profile.city_name else 0
    owner_trust = min(100, 40 + int(kept) * 10)
    return {
        "facility_level": facility,
        "city_bonus": city_bonus,
        "owner_trust": owner_trust,
        "fit": min(100, facility // 2 + city_bonus + owner_trust // 5),
    }


def recruitment_report(session: Session, club_id: str, user_id: str) -> ClubLegacyReport:
    require_owner(session, club_id, user_id)
    hoyd = session.scalar(
        select(ClubLegacyExecutive).where(
            ClubLegacyExecutive.club_id == club_id,
            ClubLegacyExecutive.role == "hoyd",
            ClubLegacyExecutive.status == "hired",
        )
    )
    skill = int((hoyd.attributes_json or {}).get("talent_identification", 45)) if hoyd else 45
    prestige = prestige_score(session, club_id)
    rng = random.Random(f"intake:{club_id}:{skill}")
    low = 48 + skill // 10
    high = min(94, low + 18 + rng.randint(0, 12))
    if prestige < 30 and rng.random() < 0.15:
        high = min(94, high + 8)
    confidence = min(80, 35 + skill // 3)
    report = ClubLegacyReport(
        club_id=club_id,
        role="hoyd" if hoyd else "owner",
        kind="recruitment",
        summary=f"Prospect band {low}-{high}. Not a guaranteed star.",
        reason=f"HoYD identification {skill}/100 and club prestige {prestige}. Smaller clubs can still find the top of the band.",
        confidence=confidence,
        consequence="A signing in this band can develop or stall. Wealth does not reserve world-class regens.",
    )
    session.add(report)
    session.flush()
    return report


def assert_staff_can_spend(session: Session, club_id: str, task_key: str, amount: Decimal) -> None:
    policy = policy_for(session, club_id, task_key)
    if policy is None or policy.mode == "owner_only":
        raise LegacyError("manual_only", 409, "The owner still handles this task.")
    if policy.mode == "automatic" and policy.max_amount is not None and task_key == PRESEASON_RESPONSE:
        if amount < policy.max_amount:
            raise LegacyError(
                "below_minimum_fee", 409, f"Appearance fee {amount} is below the automatic minimum {policy.max_amount}."
            )
    if policy.mode == "automatic" and policy.max_amount is not None and task_key != PRESEASON_RESPONSE:
        if amount > policy.max_amount:
            raise LegacyError(
                "over_threshold",
                409,
                f"{task_key} of {amount} exceeds the current automatic limit of {policy.max_amount}.",
            )


def club_page(session: Session, club_id: str) -> dict:
    profile = session.get(ClubProfile, club_id)
    if profile is None:
        raise LegacyError("club_not_found", 404)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    staff = session.scalars(select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id)).all()
    assets = session.scalars(
        select(ClubLegacyAsset).where(ClubLegacyAsset.club_id == club_id, ClubLegacyAsset.owner_class == "club")
    ).all()
    return {
        "club_id": club_id,
        "name": profile.club_name,
        "city": profile.city_name,
        "country_code": profile.country_code,
        "continent_code": profile.continent_code,
        "staff": [{"role": item.role, "name": item.name} for item in staff],
        "facilities": state.facilities_json if state else {},
        "development": development_score(state.facilities_json if state else {}),
        "prestige": prestige_score(session, club_id),
        "club_assets": [_asset_dict(session, asset) for asset in assets],
        "showroom_fallback": "static-card",
        "showroom": showroom(session, club_id),
    }


def showroom(session: Session, club_id: str) -> dict:
    """Lightweight showroom. Preview geometry stays in the client; this is the ownership record."""
    seed_catalogue(session)
    profile = session.get(ClubProfile, club_id)
    if profile is None:
        raise LegacyError("club_not_found", 404)
    owned = session.scalars(select(ClubLegacyAsset).where(ClubLegacyAsset.club_id == club_id)).all()
    personal = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.owner_class == "owner",
            ClubLegacyAsset.owner_ref == profile.owner_user_id,
            or_(ClubLegacyAsset.club_id.is_(None), ClubLegacyAsset.club_id != club_id),
        )
    ).all()
    seen = {asset.id for asset in owned}
    exhibits = [
        _exhibit(session, asset, owned=True)
        for asset in [*owned, *(asset for asset in personal if asset.id not in seen)]
    ]
    owned_skus = set()
    for asset in [*owned, *personal]:
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        if item is not None:
            owned_skus.add(item.sku)
    for item in session.scalars(select(ClubLegacyCatalogueItem).order_by(ClubLegacyCatalogueItem.sku.asc())).all():
        if item.sku in owned_skus:
            continue
        if item.supply_cap is not None and item.minted_count >= item.supply_cap:
            continue
        exhibits.append(
            {
                "id": f"catalogue:{item.sku}",
                "name": item.name,
                "category": item.category,
                "owner_class": None,
                "ownership_label": "Not owned",
                "status": "available",
                "edition_number": None,
                "fallback_label": item.fallback_label,
                "model_file": _model_file(item.category),
                "owned": False,
            }
        )
    preview_bytes = 180 * 120 * 4
    return {
        "mode": "lightweight-preview",
        "fallback": "static-card",
        "preview_bytes": preview_bytes,
        "within_budget": preview_bytes <= 250_000,
        "exhibits": exhibits,
    }


def _exhibit(session: Session, asset: ClubLegacyAsset, *, owned: bool) -> dict:
    payload = _asset_dict(session, asset)
    payload["ownership_label"] = _ownership_label(asset.owner_class)
    payload["owned"] = owned and asset.status == "owned"
    return payload


def _ownership_label(owner_class: str | None) -> str:
    return {"club": "Club", "owner": "Owner", "player": "Player", "manager": "Manager"}.get(
        owner_class or "", "Not owned"
    )


def _asset_dict(session: Session, asset: ClubLegacyAsset) -> dict:
    item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
    return {
        "id": asset.id,
        "name": item.name if item else "Asset",
        "category": item.category if item else None,
        "owner_class": asset.owner_class,
        "owner_ref": asset.owner_ref,
        "status": asset.status,
        "edition_number": asset.edition_number,
        "fallback_label": item.fallback_label if item else "Static card",
        "model_file": _model_file(item.category if item else None),
    }


def _model_file(category: str | None) -> str:
    return {
        "jet": "assets/showroom/harbour_jet.glb",
        "coach": "assets/showroom/lagoon_coach.glb",
        "watch": "assets/showroom/icon_watch.glb",
    }.get(category or "", "assets/showroom/icon_watch.glb")


def club_valuation(session: Session, club_id: str) -> Decimal:
    cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
    asset_value = Decimal("0")
    assets = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.club_id == club_id, ClubLegacyAsset.owner_class == "club", ClubLegacyAsset.status == "owned"
        )
    ).all()
    for asset in assets:
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        if item is not None:
            asset_value += Decimal(item.price)
    return _q(cash + asset_value)


def owner_net_worth(session: Session, user_id: str) -> dict:
    personal_cash = ledger.balance(session, ledger.user_account(user_id), ledger.GTEX)
    personal_assets = Decimal("0")
    for asset in session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.owner_class == "owner",
            ClubLegacyAsset.owner_ref == user_id,
            ClubLegacyAsset.status == "owned",
        )
    ).all():
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        if item is not None:
            personal_assets += Decimal(item.price)
    equity = Decimal("0")
    for stake in session.scalars(select(ClubLegacyStake).where(ClubLegacyStake.holder_user_id == user_id)).all():
        equity += _q(club_valuation(session, stake.club_id) * Decimal(stake.percentage) / Decimal("100"))
    return {
        "personal_cash": str(_q(personal_cash)),
        "personal_assets": str(_q(personal_assets)),
        "equity": str(equity),
        "net_worth": str(_q(personal_cash + personal_assets + equity)),
    }


def purchase_asset(
    session: Session, *, club_id: str, user_id: str, sku: str, owner_class: str, idempotency_key: str
) -> ClubLegacyAsset:
    require_owner(session, club_id, user_id)
    if owner_class not in {"club", "owner"}:
        raise LegacyError("invalid_owner_class")
    existing = session.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    seed_catalogue(session)
    item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == sku).with_for_update())
    if item is None:
        raise LegacyError("unknown_item", 404)
    if item.supply_cap is not None and item.minted_count >= item.supply_cap:
        raise LegacyError("sold_out", 409)
    _enforce_club_cap(session, club_id, item.category)
    item.minted_count += 1
    owner_ref = club_id if owner_class == "club" else user_id
    asset = ClubLegacyAsset(
        catalogue_id=item.id,
        edition_number=item.minted_count,
        owner_class=owner_class,
        owner_ref=owner_ref,
        club_id=club_id,
        status="owned",
        idempotency_key=idempotency_key,
    )
    session.add(asset)
    session.flush()
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


def _enforce_club_cap(session: Session, club_id: str, category: str) -> None:
    cap = {"jet": JET_CAP, "coach": COACH_CAP}.get(category)
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


def offer_gift(session: Session, *, asset_id: str, user_id: str, recipient_ref: str) -> ClubLegacyGift:
    asset = session.get(ClubLegacyAsset, asset_id)
    if asset is None or asset.status != "owned":
        raise LegacyError("asset_unavailable", 409)
    if asset.owner_class == "club":
        require_owner(session, asset.owner_ref, user_id)
    elif asset.owner_ref != user_id:
        raise LegacyError("not_asset_owner", 403)
    asset.status = "offered"
    gift = ClubLegacyGift(asset_id=asset.id, sender_user_id=user_id, recipient_ref=recipient_ref, status="offered")
    session.add(gift)
    session.flush()
    return gift


def resolve_gift(session: Session, *, gift_id: str, accept: bool) -> ClubLegacyGift:
    gift = session.get(ClubLegacyGift, gift_id)
    if gift is None or gift.status != "offered":
        raise LegacyError("gift_not_open", 409)
    asset = session.get(ClubLegacyAsset, gift.asset_id)
    if accept:
        asset.owner_class = "player"
        asset.owner_ref = gift.recipient_ref
        asset.status = "owned"
        gift.status = "accepted"
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
    asset.status = "listed"
    listing = ClubLegacyListing(
        asset_id=asset.id,
        seller_user_id=user_id,
        price=_q(price),
        fee=_q(Decimal(price) * Decimal("0.05")),
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
    require_owner(session, buyer_club_id, buyer_user_id)
    seller_club = session.get(ClubProfile, asset.club_id) if asset.club_id else None
    buyer_club = session.get(ClubProfile, buyer_club_id)
    if (
        seller_club is not None
        and buyer_club is not None
        and seller_club.owner_user_id == buyer_club.owner_user_id
        and seller_club.id != buyer_club.id
    ):
        raise LegacyError("wash_trade", 409, "Related clubs cannot trade this asset with each other.")
    listing.status = "escrow"
    session.flush()
    source = ledger.wallet_account(session, ledger.club_account(buyer_club_id), ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(asset.club_id or buyer_club_id), ledger.GTEX)
    try:
        post_club_legacy_transfer(
            session,
            idempotency_key=f"sale:{idempotency_key}",
            source=source,
            destination=destination,
            amount=Decimal(listing.price),
            description="Asset resale",
        )
    except Exception:
        listing.status = "open"
        session.flush()
        raise
    asset.owner_class = "club"
    asset.owner_ref = buyer_club_id
    asset.club_id = buyer_club_id
    asset.status = "owned"
    listing.status = "sold"
    listing.idempotency_key = idempotency_key
    session.flush()
    return listing


def development_stage_name(score: int) -> str:
    if score < 20:
        return "foundation"
    if score < 40:
        return "growing"
    if score < 60:
        return "established"
    if score < 80:
        return "elite"
    return "legacy"


def open_window(session: Session, *, name: str, starts_on: str, ends_on: str) -> ClubLegacyPreseasonWindow:
    window = ClubLegacyPreseasonWindow(name=name, starts_on=starts_on, ends_on=ends_on, status="open")
    session.add(window)
    session.flush()
    return window


def _reject_related_clubs(session: Session, from_club_id: str, to_club_id: str) -> None:
    home = session.get(ClubProfile, from_club_id)
    away = session.get(ClubProfile, to_club_id)
    if home is not None and away is not None and home.owner_user_id == away.owner_user_id:
        raise LegacyError("related_club_blocked", 409, "Clubs with the same owner cannot arrange this friendly.")


def _reject_blocked_calendar(session: Session, match_on: str) -> None:
    from app.models.admin_rules import AdminCalendarRule

    rules = session.scalars(select(AdminCalendarRule).where(AdminCalendarRule.active.is_(True))).all()
    for rule in rules:
        for block in (rule.config_json or {}).get("blocked_ranges", []):
            if str(block.get("start")) <= match_on <= str(block.get("end")):
                raise LegacyError("calendar_blocked", 409, "The competition calendar blocks that date.")


def _reject_manager_clash(session: Session, from_club_id: str, to_club_id: str, match_on: str) -> None:
    from app.owner_console.models import OwnerMatch

    scheduled = session.scalars(
        select(OwnerMatch).where(
            OwnerMatch.status == "scheduled",
            (OwnerMatch.home_club_id.in_([from_club_id, to_club_id]))
            | (OwnerMatch.away_club_id.in_([from_club_id, to_club_id])),
        )
    ).all()
    for match in scheduled:
        played = match.played_at.date().isoformat() if match.played_at else None
        if played == match_on:
            raise LegacyError("manager_unavailable", 409, "The football manager already has a match that day.")


def invite_preseason(
    session: Session, *, window_id: str, from_club_id: str, to_club_id: str, match_on: str, appearance_fee, user_id: str
) -> ClubLegacyPreseasonInvite:
    require_owner(session, from_club_id, user_id)
    _reject_related_clubs(session, from_club_id, to_club_id)
    _reject_blocked_calendar(session, match_on)
    _reject_manager_clash(session, from_club_id, to_club_id, match_on)
    window = session.get(ClubLegacyPreseasonWindow, window_id)
    if window is None or not (window.starts_on <= match_on <= window.ends_on):
        raise LegacyError("outside_window", 409, "That date is outside the pre-season window.")
    conflict = session.scalar(
        select(ClubLegacyPreseasonInvite).where(
            ClubLegacyPreseasonInvite.match_on == match_on,
            ClubLegacyPreseasonInvite.status == "accepted",
            (ClubLegacyPreseasonInvite.from_club_id.in_([from_club_id, to_club_id]))
            | (ClubLegacyPreseasonInvite.to_club_id.in_([from_club_id, to_club_id])),
        )
    )
    if conflict is not None:
        raise LegacyError("date_conflict", 409, "One of the clubs already has a pre-season match that day.")
    invite = ClubLegacyPreseasonInvite(
        window_id=window_id,
        from_club_id=from_club_id,
        to_club_id=to_club_id,
        match_on=match_on,
        appearance_fee=_q(appearance_fee),
        status="pending",
    )
    session.add(invite)
    session.flush()
    return invite


def respond_preseason(
    session: Session, *, invite_id: str, user_id: str, decision: str, as_staff: bool = False
) -> ClubLegacyPreseasonInvite:
    invite = session.get(ClubLegacyPreseasonInvite, invite_id)
    if invite is None or invite.status != "pending":
        raise LegacyError("invite_not_open", 409)
    require_owner(session, invite.to_club_id, user_id)
    if as_staff:
        assert_staff_can_spend(session, invite.to_club_id, PRESEASON_RESPONSE, Decimal(invite.appearance_fee))
    if decision == "reject":
        invite.status = "rejected"
    elif decision == "accept":
        invite.status = "accepted"
    else:
        raise LegacyError("unknown_decision")
    session.flush()
    return invite


def settle_preseason(session: Session, *, invite_id: str, tv_pool, gift_pool=0) -> ClubLegacyPreseasonSettlement:
    existing = session.scalar(
        select(ClubLegacyPreseasonSettlement).where(ClubLegacyPreseasonSettlement.invite_id == invite_id)
    )
    if existing is not None:
        return existing
    invite = session.get(ClubLegacyPreseasonInvite, invite_id)
    if invite is None or invite.status != "accepted":
        raise LegacyError("invite_not_accepted", 409)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == invite.to_club_id))
    stage = development_stage_name(development_score(state.facilities_json if state else {}))
    pool = _q(tv_pool)
    club_rate = TV_SHARES[stage]
    platform = _q(pool * (Decimal("1") - club_rate))
    club_pool = pool - platform
    host = _q(club_pool * HOST_CUT_OF_CLUB_POOL)
    participants = club_pool - host
    if platform + host + participants != pool:
        raise LegacyError("allocation_mismatch", 500)
    gift = _q(gift_pool)
    gift_club = _q(gift * Decimal("0.40")) if stage == "foundation" else _q(gift * club_rate)
    gift_platform = gift - gift_club
    if gift_platform + gift_club != gift:
        raise LegacyError("allocation_mismatch", 500)
    repeats = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyPreseasonSettlement)
            .join(ClubLegacyPreseasonInvite, ClubLegacyPreseasonInvite.id == ClubLegacyPreseasonSettlement.invite_id)
            .where(
                (
                    (ClubLegacyPreseasonInvite.from_club_id == invite.from_club_id)
                    & (ClubLegacyPreseasonInvite.to_club_id == invite.to_club_id)
                )
                | (
                    (ClubLegacyPreseasonInvite.from_club_id == invite.to_club_id)
                    & (ClubLegacyPreseasonInvite.to_club_id == invite.from_club_id)
                )
            )
        )
        or 0
    )
    reputation = 4 if int(repeats) else 10
    settlement = ClubLegacyPreseasonSettlement(
        invite_id=invite.id,
        idempotency_key=f"preseason:{invite.id}",
        platform_amount=platform,
        host_amount=host,
        participant_amount=participants,
        reputation_delta=reputation,
        audience=100,
        gift_platform_amount=gift_platform,
        gift_club_amount=gift_club,
    )
    session.add(settlement)
    session.flush()
    source = ledger.wallet_account(session, ledger.PLATFORM_SPONSORS, ledger.GTEX)
    host_account = ledger.wallet_account(session, ledger.club_account(invite.from_club_id), ledger.GTEX)
    away_account = ledger.wallet_account(session, ledger.club_account(invite.to_club_id), ledger.GTEX)
    if host > 0:
        post_club_legacy_transfer(
            session,
            idempotency_key=f"preseason:{invite.id}:host",
            source=source,
            destination=host_account,
            amount=host,
            description="Pre-season host share",
        )
    if participants > 0:
        post_club_legacy_transfer(
            session,
            idempotency_key=f"preseason:{invite.id}:participant",
            source=source,
            destination=away_account,
            amount=participants,
            description="Pre-season participant share",
        )
    session.flush()
    return settlement


def offer_sponsor(
    session: Session, *, club_id: str, user_id: str, sponsor_name: str, placement: str, fee
) -> ClubLegacySponsorContract:
    require_owner(session, club_id, user_id)
    contract = ClubLegacySponsorContract(
        club_id=club_id, sponsor_name=sponsor_name, placement=placement, fee=_q(fee), status="offered"
    )
    session.add(contract)
    session.flush()
    return contract


def approve_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None:
        raise LegacyError("contract_not_found", 404)
    require_owner(session, contract.club_id, user_id)
    contract.status = "approved"
    source = ledger.wallet_account(session, ledger.PLATFORM_SPONSORS, ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(contract.club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"sponsor:{contract.id}",
        source=source,
        destination=destination,
        amount=Decimal(contract.fee),
        description=f"Sponsor {contract.sponsor_name}",
    )
    session.flush()
    return contract


def publish_kit(
    session: Session, *, club_id: str, user_id: str, contract_id: str, template_name: str, zones: dict
) -> ClubLegacyKitVersion:
    require_owner(session, club_id, user_id)
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.status != "approved" or contract.club_id != club_id:
        raise LegacyError("sponsor_not_approved", 409, "Publish only after the sponsor contract is approved.")
    if zones.get("front") != contract.placement and contract.placement not in zones.values():
        raise LegacyError("placement_mismatch", 409, "Published zones must match the contract placement.")
    version = (
        session.scalar(
            select(func.count()).select_from(ClubLegacyKitVersion).where(ClubLegacyKitVersion.club_id == club_id)
        )
        or 0
    ) + 1
    kit = ClubLegacyKitVersion(
        club_id=club_id,
        version=int(version),
        template_name=template_name,
        zones_json=zones,
        status="published",
        contract_id=contract.id,
    )
    session.add(kit)
    session.flush()
    return kit


def offer_score(wage, prestige: int, ambition: int, seed: int) -> tuple[int, int, int]:
    rng = random.Random(seed)
    money = min(40, int(Decimal(wage) / Decimal("1000")))
    project = min(40, int(prestige / 2) + max(0, 20 - ambition))
    noise = rng.randint(0, 30)
    return money, project, money + project + noise


def decide_manager_offer(
    session: Session, *, club_id: str, user_id: str, candidate_name: str, wage, prestige: int, ambition: int, seed: int
) -> ClubLegacyManagerOffer:
    require_owner(session, club_id, user_id)
    money, project, total = offer_score(wage, prestige, ambition, seed)
    outcome = "accepted" if total >= 70 else "declined"
    offer = ClubLegacyManagerOffer(
        club_id=club_id,
        candidate_name=candidate_name,
        wage=_q(wage),
        prestige=prestige,
        ambition=ambition,
        seed=seed,
        outcome=outcome,
        money_score=money,
        project_score=project,
    )
    session.add(offer)
    session.flush()
    return offer


def make_promise(session: Session, *, club_id: str, user_id: str, subject: str) -> ClubLegacyPromise:
    require_owner(session, club_id, user_id)
    promise = ClubLegacyPromise(club_id=club_id, subject=subject, status="open", trust=50)
    session.add(promise)
    session.flush()
    return promise


def resolve_promise(session: Session, *, promise_id: str, kept: bool) -> ClubLegacyPromise:
    promise = session.get(ClubLegacyPromise, promise_id)
    if promise is None:
        raise LegacyError("promise_not_found", 404)
    promise.status = "kept" if kept else "broken"
    promise.trust = min(100, promise.trust + 10) if kept else max(0, promise.trust - 20)
    session.flush()
    return promise


def open_case(session: Session, *, club_id: str, rule_code: str, allegation: str, evidence: str) -> ClubLegacyCase:
    if rule_code == "luxury_possession":
        raise LegacyError("not_misconduct", 409, "Expensive possessions alone are not a disciplinary case.")
    case = ClubLegacyCase(club_id=club_id, rule_code=rule_code, allegation=allegation, evidence=evidence, status="open")
    session.add(case)
    session.flush()
    return case


def rule_case(session: Session, *, case_id: str, sanction: str, reason: str) -> ClubLegacyCase:
    case = session.get(ClubLegacyCase, case_id)
    if case is None:
        raise LegacyError("case_not_found", 404)
    case.status = "ruled"
    case.sanction = sanction
    case.reason = reason
    session.flush()
    return case


def appeal_case(session: Session, *, case_id: str, outcome: str) -> ClubLegacyCase:
    case = session.get(ClubLegacyCase, case_id)
    if case is None or case.status != "ruled":
        raise LegacyError("appeal_unavailable", 409)
    case.status = "appealed"
    case.appeal_outcome = outcome
    session.flush()
    return case


def set_stake(session: Session, *, club_id: str, holder_user_id: str, percentage) -> ClubLegacyStake:
    stake = session.scalar(
        select(ClubLegacyStake).where(
            ClubLegacyStake.club_id == club_id, ClubLegacyStake.holder_user_id == holder_user_id
        )
    )
    percent = _q(percentage)
    if percent <= 0 or percent > 100:
        raise LegacyError("invalid_percentage")
    others = session.scalars(select(ClubLegacyStake).where(ClubLegacyStake.club_id == club_id)).all()
    total = (
        sum((Decimal(row.percentage) for row in others if row.holder_user_id != holder_user_id), Decimal("0")) + percent
    )
    if total > Decimal("100"):
        raise LegacyError("stake_total", 409, f"Stakes would total {total}, above 100.")
    if stake is None:
        stake = ClubLegacyStake(
            club_id=club_id, holder_user_id=holder_user_id, percentage=percent, voting_rights=percent
        )
        session.add(stake)
    else:
        stake.percentage = percent
        stake.voting_rights = percent
    session.flush()
    return stake


def economic_interest(session: Session, *, club_id: str, holder_user_id: str) -> Decimal:
    stake = session.scalar(
        select(ClubLegacyStake).where(
            ClubLegacyStake.club_id == club_id, ClubLegacyStake.holder_user_id == holder_user_id
        )
    )
    if stake is None:
        return Decimal("0.00")
    return _q(club_valuation(session, club_id) * Decimal(stake.percentage) / Decimal("100"))


def simulate_season(session: Session, club_id: str) -> dict:
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    development = development_score(state.facilities_json if state else {})
    cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
    jets = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyAsset)
            .join(ClubLegacyCatalogueItem, ClubLegacyCatalogueItem.id == ClubLegacyAsset.catalogue_id)
            .where(ClubLegacyAsset.club_id == club_id, ClubLegacyCatalogueItem.category == "jet")
        )
        or 0
    )
    return {
        "club_id": club_id,
        "development": development,
        "financial_strength": financial_strength(cash),
        "prestige": prestige_score(session, club_id),
        "jets": int(jets),
        "can_progress_without_jets": int(jets) == 0 and development >= 20,
    }


def place_bid(session: Session, *, listing_id: str, bidder_user_id: str, amount) -> ClubLegacyBid:
    listing = session.get(ClubLegacyListing, listing_id)
    if listing is None or listing.status != "auction":
        raise LegacyError("auction_closed", 409)
    if bidder_user_id == listing.seller_user_id:
        raise LegacyError("wash_trade", 409, "The seller cannot bid on their own auction.")
    bid_amount = _q(amount)
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


def close_auction(session: Session, *, listing_id: str, buyer_club_id: str) -> ClubLegacyListing:
    listing = session.get(ClubLegacyListing, listing_id)
    if listing is None or listing.status != "auction":
        raise LegacyError("auction_closed", 409)
    winning = session.scalar(
        select(ClubLegacyBid).where(ClubLegacyBid.listing_id == listing.id, ClubLegacyBid.status == "leading")
    )
    if winning is None:
        listing.status = "cancelled"
        asset = session.get(ClubLegacyAsset, listing.asset_id)
        asset.status = "owned"
        session.flush()
        return listing
    listing.price = winning.amount
    listing.status = "open"
    session.flush()
    return buy_listing(
        session,
        listing_id=listing.id,
        buyer_user_id=winning.bidder_user_id,
        buyer_club_id=buyer_club_id,
        idempotency_key=f"auction:{listing.id}",
    )


def report_delivery(
    session: Session, *, contract_id: str, user_id: str, impressions: int, note: str
) -> ClubLegacySponsorContract:
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.status != "approved":
        raise LegacyError("delivery_unavailable", 409)
    require_owner(session, contract.club_id, user_id)
    if impressions < 0:
        raise LegacyError("invalid_impressions")
    contract.impressions = impressions
    contract.delivery_report = note
    contract.status = "completed"
    session.flush()
    return contract


def renew_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    previous = session.get(ClubLegacySponsorContract, contract_id)
    if previous is None or previous.status != "completed":
        raise LegacyError("renewal_unavailable", 409)
    require_owner(session, previous.club_id, user_id)
    renewed = ClubLegacySponsorContract(
        club_id=previous.club_id,
        sponsor_name=previous.sponsor_name,
        placement=previous.placement,
        fee=previous.fee,
        status="offered",
        renewed_from_id=previous.id,
    )
    session.add(renewed)
    session.flush()
    return renewed


def approach_manager(session: Session, *, executive_id: str, from_club_id: str, user_id: str) -> ClubLegacyExecutive:
    executive = session.get(ClubLegacyExecutive, executive_id)
    if executive is None or executive.status != "hired":
        raise LegacyError("executive_unavailable", 404)
    require_owner(session, from_club_id, user_id)
    if executive.club_id == from_club_id:
        raise LegacyError("already_on_staff", 409)
    _reject_related_clubs(session, from_club_id, executive.club_id)
    compensation = _q(Decimal(executive.wage) * Decimal("0.20"))
    source = ledger.wallet_account(session, ledger.club_account(from_club_id), ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(executive.club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"compensation:{executive.id}:{from_club_id}",
        source=source,
        destination=destination,
        amount=compensation,
        description=f"Compensation for {executive.name}",
    )
    executive.status = "in_talks"
    session.flush()
    return executive


def load_catalogue(session: Session, rounds: int = 40) -> dict:
    import time

    started = time.perf_counter()
    for _ in range(rounds):
        session.scalars(select(ClubLegacyCatalogueItem)).all()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {"rounds": rounds, "elapsed_ms": elapsed_ms, "within_budget": elapsed_ms < 1000}


def desk_snapshot(session: Session, club_id: str, user_id: str) -> dict:
    require_owner(session, club_id, user_id)
    staff = session.scalars(select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id)).all()
    policies = session.scalars(select(ClubLegacyPolicy).where(ClubLegacyPolicy.club_id == club_id)).all()
    invites = session.scalars(
        select(ClubLegacyPreseasonInvite).where(
            (ClubLegacyPreseasonInvite.from_club_id == club_id) | (ClubLegacyPreseasonInvite.to_club_id == club_id)
        )
    ).all()
    sponsors = session.scalars(
        select(ClubLegacySponsorContract).where(ClubLegacySponsorContract.club_id == club_id)
    ).all()
    offers = session.scalars(select(ClubLegacyManagerOffer).where(ClubLegacyManagerOffer.club_id == club_id)).all()
    promises = session.scalars(select(ClubLegacyPromise).where(ClubLegacyPromise.club_id == club_id)).all()
    cases = session.scalars(select(ClubLegacyCase).where(ClubLegacyCase.club_id == club_id)).all()
    stakes = session.scalars(select(ClubLegacyStake).where(ClubLegacyStake.club_id == club_id)).all()
    return {
        "staff": [
            {
                "id": item.id,
                "role": item.role,
                "name": item.name,
                "status": item.status,
                "fit": (item.attributes_json or {}).get("fit"),
            }
            for item in staff
        ],
        "policies": [
            {
                "task_key": item.task_key,
                "mode": item.mode,
                "max_amount": str(item.max_amount) if item.max_amount is not None else None,
            }
            for item in policies
        ],
        "finance": {**owner_net_worth(session, user_id), "club_valuation": str(club_valuation(session, club_id))},
        "preseason": [
            {
                "id": item.id,
                "match_on": item.match_on,
                "status": item.status,
                "appearance_fee": str(item.appearance_fee),
            }
            for item in invites
        ],
        "sponsors": [
            {
                "id": item.id,
                "sponsor_name": item.sponsor_name,
                "placement": item.placement,
                "status": item.status,
                "impressions": item.impressions,
            }
            for item in sponsors
        ],
        "offers": [
            {"id": item.id, "candidate_name": item.candidate_name, "outcome": item.outcome, "wage": str(item.wage)}
            for item in offers
        ],
        "promises": [
            {"id": item.id, "subject": item.subject, "status": item.status, "trust": item.trust} for item in promises
        ],
        "cases": [
            {"id": item.id, "rule_code": item.rule_code, "status": item.status, "sanction": item.sanction}
            for item in cases
        ],
        "stakes": [{"holder_user_id": item.holder_user_id, "percentage": str(item.percentage)} for item in stakes],
        "market": _market_rows(session, club_id),
    }


def _market_rows(session: Session, club_id: str) -> list[dict]:
    listings = session.scalars(
        select(ClubLegacyListing)
        .where(ClubLegacyListing.status.in_(("open", "auction")))
        .order_by(ClubLegacyListing.price.asc())
    ).all()
    rows = []
    for listing in listings:
        asset = session.get(ClubLegacyAsset, listing.asset_id)
        if asset is None:
            continue
        if asset.club_id != club_id and listing.status != "auction":
            continue
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        leading = session.scalar(
            select(ClubLegacyBid).where(ClubLegacyBid.listing_id == listing.id, ClubLegacyBid.status == "leading")
        )
        rows.append(
            {
                "id": listing.id,
                "name": item.name if item else "Asset",
                "status": listing.status,
                "price": str(listing.price),
                "leading_bid": str(leading.amount) if leading is not None else None,
                "asset_id": asset.id,
            }
        )
    return rows


def perform_desk_action(session: Session, club_id: str, user_id: str, action: str, payload: dict) -> dict:
    require_owner(session, club_id, user_id)
    if action == "hire":
        hired = hire_executive(
            session,
            club_id,
            user_id,
            role=payload["role"],
            name=payload["name"],
            personality=payload.get("personality", "cautious"),
            wage=payload.get("wage", "1000"),
        )
        return {"id": hired.id, "fit": hired.attributes_json.get("fit")}
    if action == "preset":
        from app.club_legacy.delegation import apply_preset

        policy = apply_preset(session, club_id, payload["preset"], actor_user_id=user_id)
        return {"task_key": policy.task_key, "mode": policy.mode}
    if action == "preseason_window":
        window = open_window(session, name=payload["name"], starts_on=payload["starts_on"], ends_on=payload["ends_on"])
        return {"id": window.id}
    if action == "preseason_invite":
        invite = invite_preseason(
            session,
            window_id=payload["window_id"],
            from_club_id=club_id,
            to_club_id=payload["to_club_id"],
            match_on=payload["match_on"],
            appearance_fee=payload["appearance_fee"],
            user_id=user_id,
        )
        return {"id": invite.id, "status": invite.status}
    if action == "sponsor_offer":
        contract = offer_sponsor(
            session,
            club_id=club_id,
            user_id=user_id,
            sponsor_name=payload["sponsor_name"],
            placement=payload["placement"],
            fee=payload["fee"],
        )
        return {"id": contract.id, "status": contract.status}
    if action == "manager_offer":
        offer = decide_manager_offer(
            session,
            club_id=club_id,
            user_id=user_id,
            candidate_name=payload["candidate_name"],
            wage=payload["wage"],
            prestige=int(payload.get("prestige", 10)),
            ambition=int(payload.get("ambition", 10)),
            seed=int(payload.get("seed", 1)),
        )
        return {"id": offer.id, "outcome": offer.outcome}
    if action == "open_case":
        case = open_case(
            session,
            club_id=club_id,
            rule_code=payload["rule_code"],
            allegation=payload["allegation"],
            evidence=payload["evidence"],
        )
        return {"id": case.id, "status": case.status}
    if action == "list_auction":
        asset_id = payload.get("asset_id")
        if not asset_id:
            asset = session.scalar(
                select(ClubLegacyAsset).where(
                    ClubLegacyAsset.club_id == club_id,
                    ClubLegacyAsset.owner_class == "club",
                    ClubLegacyAsset.status == "owned",
                )
            )
            if asset is None:
                raise LegacyError("asset_unavailable", 409)
            asset_id = asset.id
        listing = list_asset(
            session,
            asset_id=asset_id,
            user_id=user_id,
            price=payload.get("price", "1500"),
            kind="auction",
        )
        return {"id": listing.id, "status": listing.status}
    if action == "place_bid":
        listing_id = payload.get("listing_id")
        if not listing_id:
            listing = session.scalar(
                select(ClubLegacyListing).where(
                    ClubLegacyListing.status == "auction",
                    ClubLegacyListing.seller_user_id != user_id,
                )
            )
            if listing is None:
                raise LegacyError("auction_closed", 409)
            listing_id = listing.id
        bid = place_bid(
            session,
            listing_id=listing_id,
            bidder_user_id=user_id,
            amount=payload.get("amount", "2000"),
        )
        return {"id": bid.id, "amount": str(bid.amount), "status": bid.status}
    raise LegacyError("unknown_action", 404)


def metrics(session: Session) -> dict:
    def count(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "executives": count(ClubLegacyExecutive),
        "assets": count(ClubLegacyAsset),
        "invites": count(ClubLegacyPreseasonInvite),
        "settlements": count(ClubLegacyPreseasonSettlement),
        "cases": count(ClubLegacyCase),
        "rollback": "Disable the club_legacy feature flag. Legacy routes then return 404.",
    }
