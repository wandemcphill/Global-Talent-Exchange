"""Prestige, development, and financial strength stay separate numbers."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.club_legacy.geography import continent_name
from app.models.club_profile import ClubProfile
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState


def financial_strength(cash: Decimal) -> int:
    amount = Decimal(cash)
    if amount <= 0:
        return 0
    if amount < Decimal("10000"):
        return 25
    if amount < Decimal("100000"):
        return 55
    return 80


def development_score(facilities: dict | None) -> int:
    level = int((facilities or {}).get("academy", 1) or 1)
    return max(0, min(100, level * 20))


def prestige_score(session: Session, club_id: str) -> int:
    profile = session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
    if profile is None:
        return 0
    return max(0, int(profile.current_score))


def legacy_snapshot(session: Session, state: OwnerClubState) -> dict:
    profile = session.get(ClubProfile, state.club_id)
    cash = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
    continent_code = profile.continent_code if profile else None
    return {
        "club_id": state.club_id,
        "city": profile.city_name if profile else None,
        "country_code": profile.country_code if profile else None,
        "continent_code": continent_code,
        "continent_name": continent_name(continent_code),
        "prestige": prestige_score(session, state.club_id),
        "development": development_score(state.facilities_json),
        "financial_strength": financial_strength(cash),
    }
