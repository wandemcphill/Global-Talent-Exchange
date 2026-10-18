"""Phase 3: club page, owner net worth from stake and personal assets, ledger history."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.geography import continent_name
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
    ClubLegacySponsorContract,
    ClubLegacyStake,
)
from app.club_legacy.ratings import development_score, prestige_score
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_hall_of_fame import ClubHallOfFameEntry
from app.models.club_profile import ClubProfile
from app.models.club_trophy import ClubTrophy
from app.models.wallet import LedgerEntry, LedgerTransaction
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState, OwnerSponsorDeal, OwnerSquadPlayer


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _showroom_or_fallback(session: Session, club_id: str) -> dict[str, Any]:
    try:
        from app.club_legacy.operations import showroom

        room = showroom(session, club_id)
    except Exception as exc:
        return {
            "mode": "static-fallback",
            "fallback": "static-card",
            "preview_bytes": 0,
            "within_budget": True,
            "exhibits": [],
            "model_error": exc.__class__.__name__,
        }
    if not isinstance(room, dict):
        return {
            "mode": "static-fallback",
            "fallback": "static-card",
            "exhibits": [],
            "model_error": "invalid_showroom",
        }
    room.setdefault("fallback", "static-card")
    return room


def _history(session: Session, club_id: str, state: OwnerClubState | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    progress = session.scalar(select(ClubDynastyProgress).where(ClubDynastyProgress.club_id == club_id))
    if progress is not None and (int(progress.seasons_completed or 0) > 0 or progress.last_season_label):
        rows.append(
            {
                "kind": "season",
                "label": progress.last_season_label or f"{progress.seasons_completed} seasons",
                "seasons_completed": int(progress.seasons_completed or 0),
            }
        )
    inductees = session.scalars(select(ClubHallOfFameEntry).where(ClubHallOfFameEntry.club_id == club_id)).all()
    for entry in inductees:
        rows.append({"kind": "hall_of_fame", "label": entry.entry_label, "category": entry.entry_category})
    for item in (state.value_history_json if state else []) or []:
        if isinstance(item, dict) and item.get("label"):
            rows.append({"kind": "value", "label": str(item["label"])})
    return rows


def _roster(session: Session, club_id: str) -> list[dict[str, Any]]:
    players = session.scalars(
        select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).order_by(OwnerSquadPlayer.name.asc())
    ).all()
    return [
        {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "rating": player.rating,
            "potential": player.potential,
            "status": player.status,
        }
        for player in players
    ]


def _honours(session: Session, club_id: str) -> list[dict[str, Any]]:
    trophies = session.scalars(
        select(ClubTrophy).where(ClubTrophy.club_id == club_id).order_by(ClubTrophy.awarded_at.asc())
    ).all()
    return [
        {
            "id": trophy.id,
            "name": trophy.trophy_name,
            "competition": trophy.competition_source,
            "season": trophy.season_label,
        }
        for trophy in trophies
    ]


def _commercial(session: Session, club_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    contracts = session.scalars(
        select(ClubLegacySponsorContract).where(ClubLegacySponsorContract.club_id == club_id)
    ).all()
    for contract in contracts:
        rows.append(
            {
                "kind": "sponsor",
                "name": contract.sponsor_name,
                "placement": contract.placement,
                "status": contract.status,
            }
        )
    deals = session.scalars(select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == club_id)).all()
    for deal in deals:
        rows.append({"kind": "deal", "name": deal.sponsor_name, "placement": deal.slot, "status": deal.status})
    return rows


def club_page(session: Session, club_id: str) -> dict[str, Any]:
    profile = session.get(ClubProfile, club_id)
    if profile is None:
        raise LegacyError("club_not_found", 404)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    staff = session.scalars(select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id)).all()
    assets = session.scalars(
        select(ClubLegacyAsset).where(ClubLegacyAsset.club_id == club_id, ClubLegacyAsset.owner_class == "club")
    ).all()
    facilities = state.facilities_json if state else {}
    facility_rows = [
        {"name": str(name), "level": int(level or 0)} for name, level in sorted((facilities or {}).items())
    ]
    location = {
        "city": profile.city_name,
        "country_code": profile.country_code,
        "continent_code": profile.continent_code,
        "continent_name": continent_name(profile.continent_code),
    }
    history = _history(session, club_id, state)
    roster = _roster(session, club_id)
    honours = _honours(session, club_id)
    commercial = _commercial(session, club_id)
    staff_rows = [
        {
            "id": item.id,
            "role": item.role,
            "name": item.name,
            "personality": item.personality,
            "wage": str(item.wage),
            "contract_months": item.contract_months,
            "authority": item.authority,
            "status": item.status,
        }
        for item in staff
    ]
    room = _showroom_or_fallback(session, club_id)
    from app.club_legacy.operations import _asset_dict

    return {
        "club_id": club_id,
        "name": profile.club_name,
        "city": profile.city_name,
        "country_code": profile.country_code,
        "continent_code": profile.continent_code,
        "location": location,
        "history": history,
        "roster": roster,
        "honours": honours,
        "staff": [{"role": item.role, "name": item.name} for item in staff],
        "facilities": facilities or {},
        "commercial": commercial,
        "development": development_score(facilities),
        "prestige": prestige_score(session, club_id),
        "club_assets": [_asset_dict(session, asset) for asset in assets],
        "showroom_fallback": "static-card",
        "showroom": room,
        "financial_history": financial_history(session, club_id),
        "sections": {
            "location": location,
            "history": history,
            "roster": roster,
            "honours": honours,
            "staff": staff_rows,
            "facilities": facility_rows,
            "commercial": commercial,
        },
    }


def owner_net_worth(session: Session, user_id: str) -> dict[str, str]:
    """Stake times club valuation, plus cash and assets the person owns. Not the whole club."""
    from app.club_legacy.operations import club_valuation

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


def financial_history(session: Session, club_id: str) -> list[dict[str, Any]]:
    """Wallet ledger rows for this club. Missing history is an empty list."""
    account = ledger.wallet_account(session, ledger.club_account(club_id), ledger.GTEX)
    pairs = session.execute(
        select(LedgerEntry, LedgerTransaction)
        .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transaction_id)
        .where(LedgerEntry.account_id == account.id)
        .order_by(LedgerEntry.created_at.asc())
    ).all()
    rows = []
    for entry, transaction in pairs:
        reason = transaction.reason.value if hasattr(transaction.reason, "value") else str(transaction.reason)
        created = entry.created_at.isoformat() if entry.created_at is not None else None
        rows.append(
            {
                "entry_id": entry.id,
                "transaction_id": transaction.id,
                "amount": str(entry.amount),
                "reason": reason,
                "description": transaction.description,
                "idempotency_key": transaction.idempotency_key,
                "created_at": created,
            }
        )
    return rows
