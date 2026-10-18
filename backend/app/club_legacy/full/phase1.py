"""Phase 1: location, ledger idempotency, settings, audit, and separate ratings."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.geography import backfill_missing_continents, continent_for_country, continent_name
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import ClubLegacyAuditEvent, ClubLegacySettings
from app.club_legacy.ratings import development_score, financial_strength, prestige_score
from app.models.base import utcnow
from app.models.club_profile import ClubProfile

DEFAULT_TRANSFER_FEE_RATE = Decimal("0.0500")
DEFAULT_INVENTORY_CAPS: dict[str, int] = {"jet": 5, "coach": 10}
DEFAULT_PRESEASON_SHARES: dict[str, str] = {
    "foundation": "0.30",
    "growing": "0.40",
    "established": "0.50",
    "elite": "0.60",
    "legacy": "0.70",
    "host_cut_of_club_pool": "0.40",
    "gift_foundation": "0.40",
}
_SHARE_KEYS = tuple(DEFAULT_PRESEASON_SHARES)


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def resolve_location(
    *,
    city_name: str | None,
    country_code: str | None,
    continent_code: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """City, country, and continent are one check. Unknown countries stay unset."""
    city = (city_name or "").strip()[:120] or None
    country = (country_code or "").strip().upper()[:8] or None
    supplied = (continent_code or "").strip().upper()[:2] or None
    derived = continent_for_country(country)
    if supplied and supplied != (derived or ""):
        raise LegacyError(
            "location_mismatch",
            400,
            "City, country, and continent must agree. An unknown country does not invent a continent.",
        )
    return city, country, derived


def apply_club_location(
    profile: ClubProfile,
    *,
    city_name: str | None,
    country_code: str | None,
    continent_code: str | None = None,
) -> ClubProfile:
    city, country, continent = resolve_location(
        city_name=city_name, country_code=country_code, continent_code=continent_code
    )
    profile.city_name = city
    profile.country_code = country
    profile.continent_code = continent
    return profile


def backfill_locations(session: Session) -> int:
    """Fill a missing continent from a known country. Unknown countries stay null."""
    updated = backfill_missing_continents(session)
    session.flush()
    return updated


def current_settings(session: Session) -> ClubLegacySettings:
    row = session.scalar(select(ClubLegacySettings).where(ClubLegacySettings.settings_key == "current"))
    if row is None:
        row = ClubLegacySettings(
            settings_key="current",
            transfer_fee_rate=DEFAULT_TRANSFER_FEE_RATE,
            inventory_caps_json=dict(DEFAULT_INVENTORY_CAPS),
            preseason_shares_json=dict(DEFAULT_PRESEASON_SHARES),
        )
        session.add(row)
        session.flush()
    return row


def settings_dict(row: ClubLegacySettings) -> dict[str, Any]:
    caps = row.inventory_caps_json or {}
    shares = dict(DEFAULT_PRESEASON_SHARES)
    shares.update({key: str(value) for key, value in (row.preseason_shares_json or {}).items()})
    return {
        "settings_key": row.settings_key,
        "transfer_fee_rate": str(Decimal(row.transfer_fee_rate).quantize(Decimal("0.0001"))),
        "inventory_caps": {key: int(caps[key]) for key in caps},
        "preseason_shares": shares,
    }


def update_settings(
    session: Session,
    *,
    actor_user_id: str,
    transfer_fee_rate,
    inventory_caps: dict[str, Any],
    preseason_shares: dict[str, Any],
) -> ClubLegacySettings:
    rate = Decimal(str(transfer_fee_rate)).quantize(Decimal("0.0001"))
    if rate < 0 or rate >= 1:
        raise LegacyError("invalid_fee_rate", 400, "Transfer fee rate must be from 0 up to, but not including, 1.")
    caps: dict[str, int] = {}
    for key, value in inventory_caps.items():
        amount = int(value)
        if amount < 1:
            raise LegacyError("invalid_inventory_cap", 400, f"{key} cap must be at least 1.")
        caps[str(key)] = amount
    for required in ("jet", "coach"):
        if required not in caps:
            raise LegacyError("invalid_inventory_cap", 400, f"{required} cap is required.")
    shares: dict[str, str] = {}
    for key in _SHARE_KEYS:
        if key not in preseason_shares:
            raise LegacyError("invalid_preseason_share", 400, f"{key} share is required.")
        value = Decimal(str(preseason_shares[key]))
        if value < 0 or value > 1:
            raise LegacyError("invalid_preseason_share", 400, f"{key} share must be between 0 and 1.")
        shares[key] = str(value.quantize(Decimal("0.0001")))
    row = current_settings(session)
    row.transfer_fee_rate = rate
    row.inventory_caps_json = caps
    row.preseason_shares_json = shares
    row.updated_by_user_id = actor_user_id
    row.updated_at = utcnow()
    audit_once(
        session,
        club_id=None,
        actor_user_id=actor_user_id,
        action="settings_updated",
        detail={"transfer_fee_rate": str(rate), "inventory_caps": caps, "preseason_shares": shares},
    )
    session.flush()
    return row


def transfer_fee(session: Session, price) -> Decimal:
    """Fee from the current settings row."""
    row = current_settings(session)
    rate = Decimal(row.transfer_fee_rate)
    return _q(Decimal(price) * rate)


def inventory_cap(session: Session, category: str) -> int | None:
    row = current_settings(session)
    raw = row.inventory_caps_json or {}
    if category in raw and raw[category] is not None:
        return int(raw[category])
    if category in DEFAULT_INVENTORY_CAPS:
        return DEFAULT_INVENTORY_CAPS[category]
    return None


def preseason_split(session: Session, *, stage: str, tv_pool, gift_pool) -> dict[str, Decimal]:
    """Allocate a pre-season pool from the current settings row. The parts sum to the pool."""
    row = current_settings(session)
    shares = dict(DEFAULT_PRESEASON_SHARES)
    shares.update({key: str(value) for key, value in (row.preseason_shares_json or {}).items()})
    if stage not in shares:
        raise LegacyError("unknown_stage", 400, f"No pre-season share is configured for {stage}.")
    club_rate = Decimal(str(shares[stage]))
    host_cut = Decimal(str(shares["host_cut_of_club_pool"]))
    pool = _q(tv_pool)
    platform = _q(pool * (Decimal("1") - club_rate))
    club_pool = pool - platform
    host = _q(club_pool * host_cut)
    participants = club_pool - host
    if platform + host + participants != pool:
        raise LegacyError("allocation_mismatch", 500)
    gift = _q(gift_pool)
    gift_rate = Decimal(str(shares["gift_foundation"])) if stage == "foundation" else club_rate
    gift_club = _q(gift * gift_rate)
    gift_platform = gift - gift_club
    if gift_platform + gift_club != gift:
        raise LegacyError("allocation_mismatch", 500)
    return {
        "platform": platform,
        "host": host,
        "participants": participants,
        "gift_platform": gift_platform,
        "gift_club": gift_club,
        "club_rate": club_rate,
    }


def audit_once(
    session: Session,
    *,
    club_id: str | None,
    actor_user_id: str | None,
    action: str,
    detail: dict[str, Any],
    idempotency_key: str | None = None,
) -> ClubLegacyAuditEvent:
    if idempotency_key:
        existing = session.scalar(
            select(ClubLegacyAuditEvent).where(ClubLegacyAuditEvent.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return existing
    event = ClubLegacyAuditEvent(
        club_id=club_id,
        actor_user_id=actor_user_id,
        action=action,
        detail_json=detail,
        idempotency_key=idempotency_key,
    )
    session.add(event)
    session.flush()
    return event


def post_economic(
    session: Session,
    *,
    idempotency_key: str,
    source,
    destination,
    amount: Decimal,
    actor_user_id: str | None,
    club_id: str | None,
    action: str,
    description: str,
    detail: dict[str, Any] | None = None,
) -> list:
    """One ledger post per idempotency key, plus one audit row for that key."""
    entries = post_club_legacy_transfer(
        session,
        idempotency_key=idempotency_key,
        source=source,
        destination=destination,
        amount=amount,
        actor=None,
        description=description,
    )
    audit_once(
        session,
        club_id=club_id,
        actor_user_id=actor_user_id,
        action=action,
        detail={
            "idempotency_key": idempotency_key,
            "amount": str(_q(amount)),
            "description": description,
            **(detail or {}),
        },
        idempotency_key=f"audit:{idempotency_key}",
    )
    return entries


def separate_ratings(session: Session, club_id: str, facilities: dict | None, cash: Decimal) -> dict[str, int]:
    profile = session.get(ClubProfile, club_id)
    continent = profile.continent_code if profile else None
    return {
        "prestige": prestige_score(session, club_id),
        "development": development_score(facilities),
        "financial_strength": financial_strength(cash),
        "continent_code": continent,
        "continent_name": continent_name(continent),
    }
