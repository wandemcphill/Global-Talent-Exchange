"""Regen age follows the GTEX world clock. Real players and legends follow the human calendar."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.world_clock import WorldClockState
from app.services.world_clock_service import WorldClockService

LEGEND_TIERS = frozenset({"legend", "legendary", "icon", "immortal", "world_class", "hero"})
HUMAN_TIERS = frozenset({"marquee", "active", "established"})
REGEN_SOURCES = frozenset({"gtex_regen", "gtex_national_seed", "gtex_request_son", "regen"})
LEGEND_SOURCES = frozenset({"gtex_legend", "gtex_legend_prime"})


def is_regen_player(player: object) -> bool:
    tier = str(getattr(player, "real_player_tier", "") or "").strip().lower()
    source = str(getattr(player, "source_provider", "") or "").strip().lower()
    if getattr(player, "legendary_profile_id", None):
        return False
    if source in LEGEND_SOURCES or tier in LEGEND_TIERS or tier in HUMAN_TIERS:
        return False
    if tier == "regen" or source in REGEN_SOURCES:
        return True
    return not bool(getattr(player, "is_real_player", True))


def age_years(dob: date | None, on: date | None) -> int | None:
    if dob is None or on is None:
        return None
    age = on.year - dob.year
    if (on.month, on.day) < (dob.month, dob.day):
        age -= 1
    return age


def world_date(session: Session) -> date:
    state = session.get(WorldClockState, "default")
    if state is None:
        return date.today()
    return WorldClockService(session).now_virtual().date()


def aging_date_for_player(player: object, session: Session, *, competition_date: date | None = None) -> date:
    if is_regen_player(player):
        return competition_date or world_date(session)
    return date.today()
