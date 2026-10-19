"""Club Legacy phases 2-9. Money moves only through the wallet ledger."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import (
    PRESEASON_RESPONSE,
    LegacyError,
    policy_for,
    require_owner,
)
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
from app.models.club_profile import ClubProfile
from app.owner_console import ledger

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
    session: Session,
    club_id: str,
    user_id: str,
    *,
    role: str,
    name: str,
    personality: str,
    wage,
    contract_months: int = 24,
    authority: str | None = None,
) -> ClubLegacyExecutive:
    from app.club_legacy.full.phase2 import hire_executive as hire_full

    return hire_full(
        session,
        club_id,
        user_id,
        role=role,
        name=name,
        personality=personality,
        wage=wage,
        contract_months=contract_months,
        authority=authority,
    )


def recruitment_report(session: Session, club_id: str, user_id: str) -> ClubLegacyReport:
    from app.club_legacy.full.phase2 import recruitment_report as report_full

    return report_full(session, club_id, user_id)


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
    from app.club_legacy.full.phase3 import club_page as page_full

    return page_full(session, club_id)


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
                "sku": item.sku,
                "name": item.name,
                "category": item.category,
                "price": str(item.price),
                "supply_cap": item.supply_cap,
                "minted_count": item.minted_count,
                "owner_class": None,
                "ownership_label": "Not owned",
                "status": "available",
                "edition_number": None,
                "fallback_label": item.fallback_label,
                "model_file": _model_file(item.category),
                "preview_file": _preview_file(item.category),
                "owned": False,
            }
        )
    exhibits.extend(_facility_exhibits())
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
        "sku": item.sku if item else None,
        "name": item.name if item else "Asset",
        "category": item.category if item else None,
        "price": str(item.price) if item else None,
        "supply_cap": item.supply_cap if item else None,
        "minted_count": item.minted_count if item else None,
        "owner_class": asset.owner_class,
        "owner_ref": asset.owner_ref,
        "status": asset.status,
        "edition_number": asset.edition_number,
        "fallback_label": item.fallback_label if item else "Static card",
        "model_file": _model_file(item.category if item else None),
        "preview_file": _preview_file(item.category if item else None),
    }


def _facility_exhibits() -> list[dict]:
    return [
        _facility("facility:legacy-arena", "Legacy Arena", "stadium", "Stadium preview"),
        _facility("facility:performance-campus", "Performance Campus", "campus", "Campus preview"),
    ]


def _facility(exhibit_id: str, name: str, category: str, fallback: str) -> dict:
    return {
        "id": exhibit_id,
        "name": name,
        "category": category,
        "owner_class": "club",
        "ownership_label": "Club",
        "status": "facility",
        "edition_number": None,
        "fallback_label": fallback,
        "model_file": _model_file(category),
        "preview_file": _preview_file(category),
        "owned": True,
    }


def _model_file(category: str | None) -> str:
    return {
        "jet": "assets/showroom/sovereign_900x_jet.glb",
        "aircraft": "assets/showroom/sovereign_900x_jet.glb",
        "coach": "assets/showroom/vanguard_xii_coach.glb",
        "team_transport": "assets/showroom/vanguard_xii_coach.glb",
        "vehicle": "assets/showroom/veloce_gt9_hypercar.glb",
        "watch": "assets/showroom/chronos_tourbillon_watch.glb",
        "watch_collectible": "assets/showroom/chronos_tourbillon_watch.glb",
        "stadium": "assets/showroom/arena_imperiale_stadium.glb",
        "stadium_facility": "assets/showroom/arena_imperiale_stadium.glb",
        "campus": "assets/showroom/apex_performance_campus.glb",
        "training_academy_facility": "assets/showroom/apex_performance_campus.glb",
    }.get(category or "", "assets/showroom/chronos_tourbillon_watch.glb")


def _preview_file(category: str | None) -> str:
    return _model_file(category).removesuffix(".glb") + ".png"


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
    from app.club_legacy.full.phase8 import owner_net_worth as net_worth

    return net_worth(session, user_id)


def purchase_asset(
    session: Session, *, club_id: str, user_id: str, sku: str, owner_class: str, idempotency_key: str
) -> ClubLegacyAsset:
    from app.club_legacy.full.phase4 import purchase_asset as impl

    return impl(
        session, club_id=club_id, user_id=user_id, sku=sku, owner_class=owner_class, idempotency_key=idempotency_key
    )


def _enforce_club_cap(session: Session, club_id: str, category: str) -> None:
    from app.club_legacy.full.phase4 import _enforce_club_cap as impl

    return impl(session, club_id, category)


def offer_gift(session: Session, *, asset_id: str, user_id: str, recipient_ref: str) -> ClubLegacyGift:
    from app.club_legacy.full.phase4 import offer_gift as impl

    return impl(session, asset_id=asset_id, user_id=user_id, recipient_ref=recipient_ref)


def resolve_gift(session: Session, *, gift_id: str, accept: bool, actor_user_id: str | None = None) -> ClubLegacyGift:
    from app.club_legacy.full.phase4 import resolve_gift as impl

    return impl(session, gift_id=gift_id, accept=accept, actor_user_id=actor_user_id)


def list_asset(session: Session, *, asset_id: str, user_id: str, price, kind: str = "fixed") -> ClubLegacyListing:
    from app.club_legacy.full.phase4 import list_asset as impl

    return impl(session, asset_id=asset_id, user_id=user_id, price=price, kind=kind)


def buy_listing(
    session: Session, *, listing_id: str, buyer_user_id: str, buyer_club_id: str, idempotency_key: str
) -> ClubLegacyListing:
    from app.club_legacy.full.phase4 import buy_listing as impl

    return impl(
        session,
        listing_id=listing_id,
        buyer_user_id=buyer_user_id,
        buyer_club_id=buyer_club_id,
        idempotency_key=idempotency_key,
    )


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
    from app.club_legacy.full.phase5 import open_window as impl

    return impl(session, name=name, starts_on=starts_on, ends_on=ends_on)


def _reject_related_clubs(session: Session, from_club_id: str, to_club_id: str) -> None:
    from app.club_legacy.full.phase5 import reject_related_clubs

    reject_related_clubs(session, from_club_id, to_club_id, actor_user_id=None)


def _reject_blocked_calendar(session: Session, match_on: str) -> None:
    from app.club_legacy.full.phase5 import reject_blocked_calendar

    reject_blocked_calendar(session, match_on)


def _reject_manager_clash(session: Session, from_club_id: str, to_club_id: str, match_on: str) -> None:
    from app.club_legacy.full.phase5 import reject_manager_clash

    reject_manager_clash(session, from_club_id, to_club_id, match_on)


def invite_preseason(
    session: Session, *, window_id: str, from_club_id: str, to_club_id: str, match_on: str, appearance_fee, user_id: str
) -> ClubLegacyPreseasonInvite:
    from app.club_legacy.full.phase5 import invite_preseason as impl

    return impl(
        session,
        window_id=window_id,
        from_club_id=from_club_id,
        to_club_id=to_club_id,
        match_on=match_on,
        appearance_fee=appearance_fee,
        user_id=user_id,
    )


def respond_preseason(
    session: Session,
    *,
    invite_id: str,
    user_id: str,
    decision: str,
    as_staff: bool = False,
    appearance_fee=None,
    match_on: str | None = None,
) -> ClubLegacyPreseasonInvite:
    from app.club_legacy.full.phase5 import respond_preseason as impl

    return impl(
        session,
        invite_id=invite_id,
        user_id=user_id,
        decision=decision,
        as_staff=as_staff,
        appearance_fee=appearance_fee,
        match_on=match_on,
    )


def settle_preseason(session: Session, *, invite_id: str, tv_pool, gift_pool=0) -> ClubLegacyPreseasonSettlement:
    from app.club_legacy.full.phase5 import settle_preseason as impl

    return impl(session, invite_id=invite_id, tv_pool=tv_pool, gift_pool=gift_pool)


def offer_sponsor(
    session: Session,
    *,
    club_id: str,
    user_id: str,
    sponsor_name: str,
    placement: str,
    fee,
    zones: list[str] | None = None,
) -> ClubLegacySponsorContract:
    from app.club_legacy.full.phase6 import offer_sponsor as impl

    return impl(
        session,
        club_id=club_id,
        user_id=user_id,
        sponsor_name=sponsor_name,
        placement=placement,
        fee=fee,
        zones=zones,
    )


def approve_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    from app.club_legacy.full.phase6 import approve_sponsor as impl

    return impl(session, contract_id=contract_id, user_id=user_id)


def publish_kit(
    session: Session, *, club_id: str, user_id: str, contract_id: str, template_name: str, zones: dict
) -> ClubLegacyKitVersion:
    from app.club_legacy.full.phase6 import publish_kit as impl

    return impl(
        session,
        club_id=club_id,
        user_id=user_id,
        contract_id=contract_id,
        template_name=template_name,
        zones=zones,
    )


def offer_score(wage, prestige: int, ambition: int, seed: int) -> tuple[int, int, int]:
    from app.club_legacy.full.phase7 import offer_score as score_offer

    return score_offer(wage, prestige, ambition, seed)


def decide_manager_offer(
    session: Session, *, club_id: str, user_id: str, candidate_name: str, wage, prestige: int, ambition: int, seed: int
) -> ClubLegacyManagerOffer:
    from app.club_legacy.full.phase7 import decide_manager_offer as decide

    return decide(
        session,
        club_id=club_id,
        user_id=user_id,
        candidate_name=candidate_name,
        wage=wage,
        prestige=prestige,
        ambition=ambition,
        seed=seed,
    )


def make_promise(session: Session, *, club_id: str, user_id: str, subject: str, manager_id: str | None = None):
    from app.club_legacy.full.phase7 import make_promise as open_promise

    return open_promise(session, club_id=club_id, user_id=user_id, subject=subject, manager_id=manager_id)


def resolve_promise(session: Session, *, promise_id: str, kept: bool):
    from app.club_legacy.full.phase7 import resolve_promise as settle_promise

    return settle_promise(session, promise_id=promise_id, kept=kept)


def open_case(session: Session, *, club_id: str, rule_code: str, allegation: str, evidence: str):
    from app.club_legacy.full.phase8 import open_case as open_disciplinary_case

    return open_disciplinary_case(
        session, club_id=club_id, rule_code=rule_code, allegation=allegation, evidence=evidence
    )


def rule_case(session: Session, *, case_id: str, sanction: str, reason: str):
    from app.club_legacy.full.phase8 import rule_case as apply_ruling

    return apply_ruling(session, case_id=case_id, sanction=sanction, reason=reason)


def appeal_case(session: Session, *, case_id: str, outcome: str):
    from app.club_legacy.full.phase8 import appeal_case as lodge_appeal

    return lodge_appeal(session, case_id=case_id, outcome=outcome)


def set_stake(session: Session, *, club_id: str, holder_user_id: str, percentage, voting_rights=None):
    from app.club_legacy.full.phase8 import set_stake as record_stake

    return record_stake(
        session,
        club_id=club_id,
        holder_user_id=holder_user_id,
        percentage=percentage,
        voting_rights=voting_rights,
    )


def economic_interest(session: Session, *, club_id: str, holder_user_id: str) -> Decimal:
    from app.club_legacy.full.phase8 import economic_interest as interest

    return interest(session, club_id=club_id, holder_user_id=holder_user_id)


def simulate_season(session: Session, club_id: str) -> dict:
    from app.club_legacy.full.phase9 import simulate_season as run_season

    return run_season(session, club_id)


def place_bid(session: Session, *, listing_id: str, bidder_user_id: str, amount) -> ClubLegacyBid:
    from app.club_legacy.full.phase4 import place_bid as impl

    return impl(session, listing_id=listing_id, bidder_user_id=bidder_user_id, amount=amount)


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
    from app.club_legacy.full.phase6 import report_delivery as impl

    return impl(session, contract_id=contract_id, user_id=user_id, impressions=impressions, note=note)


def renew_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    from app.club_legacy.full.phase6 import renew_sponsor as impl

    return impl(session, contract_id=contract_id, user_id=user_id)


def approach_manager(session: Session, *, executive_id: str, from_club_id: str, user_id: str) -> ClubLegacyExecutive:
    from app.club_legacy.full.phase7 import approach_manager as open_talks

    return open_talks(session, executive_id=executive_id, from_club_id=from_club_id, user_id=user_id)


def load_catalogue(session: Session, rounds: int = 40) -> dict:
    from app.club_legacy.full.phase9 import load_catalogue as read_catalogue

    return read_catalogue(session, rounds)


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
        "auctionable_assets": _auctionable_assets(session, club_id),
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
                "can_bid": asset.club_id != club_id and listing.status == "auction",
            }
        )
    return rows


def _auctionable_assets(session: Session, club_id: str) -> list[dict]:
    listed_ids = select(ClubLegacyListing.asset_id).where(ClubLegacyListing.status.in_(("open", "auction")))
    assets = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.club_id == club_id,
            ClubLegacyAsset.owner_class == "club",
            ClubLegacyAsset.status == "owned",
            ClubLegacyAsset.id.not_in(listed_ids),
        )
    ).all()
    rows = []
    for asset in assets:
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        rows.append(
            {
                "asset_id": asset.id,
                "name": item.name if item is not None else "Asset",
                "category": item.category if item is not None else None,
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
        asset_id = str(payload.get("asset_id") or "").strip()
        if not asset_id:
            raise LegacyError("asset_required", 400, "Choose the asset to auction.")
        listing = list_asset(
            session,
            asset_id=asset_id,
            user_id=user_id,
            price=payload.get("price", "1500"),
            kind="auction",
        )
        return {"id": listing.id, "status": listing.status}
    if action == "place_bid":
        listing_id = str(payload.get("listing_id") or "").strip()
        if not listing_id:
            raise LegacyError("listing_required", 400, "Choose the auction to bid on.")
        bid = place_bid(
            session,
            listing_id=listing_id,
            bidder_user_id=user_id,
            amount=payload.get("amount", "2000"),
        )
        return {"id": bid.id, "amount": str(bid.amount), "status": bid.status}
    if action == "purchase":
        sku = str(payload.get("sku") or "").strip()
        if not sku:
            raise LegacyError("sku_required", 400, "Choose the SKU to purchase.")
        idempotency_key = str(payload.get("idempotency_key") or "").strip()
        if not idempotency_key:
            raise LegacyError("idempotency_key_required", 400, "An idempotency key is required.")
        owner_class = str(payload.get("owner_class") or "club").strip()
        asset = purchase_asset(
            session,
            club_id=club_id,
            user_id=user_id,
            sku=sku,
            owner_class=owner_class,
            idempotency_key=idempotency_key,
        )
        return {
            "id": asset.id,
            "status": asset.status,
            "edition_number": asset.edition_number,
            "owner_class": asset.owner_class,
            "owner_ref": asset.owner_ref,
        }
    if action == "gift":
        asset_id = str(payload.get("asset_id") or "").strip()
        if not asset_id:
            raise LegacyError("asset_required", 400, "Choose the asset to gift.")
        recipient_ref = str(payload.get("recipient_ref") or "").strip()
        if not recipient_ref:
            raise LegacyError("recipient_required", 400, "Recipient reference is required.")
        gift = offer_gift(
            session,
            asset_id=asset_id,
            user_id=user_id,
            recipient_ref=recipient_ref,
        )
        return {"id": gift.id, "asset_id": gift.asset_id, "status": gift.status, "recipient_ref": gift.recipient_ref}
    if action == "accept_gift":
        gift_id = str(payload.get("gift_id") or "").strip()
        if not gift_id:
            raise LegacyError("gift_required", 400, "Choose the gift to accept.")
        gift = resolve_gift(session, gift_id=gift_id, accept=True, actor_user_id=user_id)
        return {"id": gift.id, "asset_id": gift.asset_id, "status": gift.status, "recipient_ref": gift.recipient_ref}
    raise LegacyError("unknown_action", 404)


def metrics(session: Session) -> dict:
    from app.club_legacy.full.phase9 import metrics as legacy_metrics

    return legacy_metrics(session)
