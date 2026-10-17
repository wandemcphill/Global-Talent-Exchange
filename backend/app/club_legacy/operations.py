"""Club Legacy phases 2-9. Money moves only through the wallet ledger."""

from __future__ import annotations

from decimal import Decimal
import random

from sqlalchemy import func, select
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
    ClubLegacyCase,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
    ClubLegacyGift,
    ClubLegacyKitVersion,
    ClubLegacyListing,
    ClubLegacyManagerOffer,
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
    }


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
    }


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
    item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == sku))
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


def list_asset(session: Session, *, asset_id: str, user_id: str, price) -> ClubLegacyListing:
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
        status="open",
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
    source = ledger.wallet_account(session, ledger.club_account(buyer_club_id), ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(asset.club_id or buyer_club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"sale:{idempotency_key}",
        source=source,
        destination=destination,
        amount=Decimal(listing.price),
        description="Asset resale",
    )
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


def invite_preseason(
    session: Session, *, window_id: str, from_club_id: str, to_club_id: str, match_on: str, appearance_fee, user_id: str
) -> ClubLegacyPreseasonInvite:
    require_owner(session, from_club_id, user_id)
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


def settle_preseason(session: Session, *, invite_id: str, tv_pool) -> ClubLegacyPreseasonSettlement:
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
