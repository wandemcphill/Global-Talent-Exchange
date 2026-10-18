from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.club_ownership import ClubHolding, ClubToken
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.owner_console import engine, ledger, service, staff
from app.owner_console.models import LedgerEvent, OwnerClubState, OwnerCompetition, OwnerCompetitionEntry, OwnerSponsorDeal, SupportUnitHolding
from app.owner_console.service import OwnerError

CONTINENT_LABELS = {"africa": "Africa", "europe": "Europe", "south_america": "South America", "north_america": "North America", "asia": "Asia", "oceania": "Oceania"}
FACILITY_UNIT_VALUE = 4000
CASH_WEIGHT = Decimal("0.5")
FAN_VALUE = 2


def continent(country_code: str | None) -> dict[str, str] | None:
    if not country_code:
        return None
    code = staff.continent_for(country_code)
    return {"code": code, "label": CONTINENT_LABELS[code]}


def competition_record(session: Session, club_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(OwnerCompetitionEntry, OwnerCompetition.name, OwnerCompetition.tier)
        .join(OwnerCompetition, OwnerCompetition.id == OwnerCompetitionEntry.competition_id)
        .where(OwnerCompetitionEntry.club_id == club_id)
        .order_by(OwnerCompetitionEntry.created_at.desc())
    ).all()
    return [
        {"competition": name, "tier": tier, "position": e.final_position, "played": e.played, "won": e.won, "drawn": e.drawn, "lost": e.lost,
         "goals_for": e.goals_for, "goals_against": e.goals_against, "year": e.created_at.year if e.created_at else None}
        for e, name, tier in rows
    ]


def _public_state(session: Session, club_id: str) -> tuple[OwnerClubState, ClubProfile]:
    state, profile = service.get_state(session, club_id), session.get(ClubProfile, club_id)
    if state is None or profile is None or profile.visibility != "public":
        raise OwnerError("club_not_found", 404)
    return state, profile


def public_page(session: Session, club_id: str) -> dict[str, Any]:
    state, profile = _public_state(session, club_id)
    health = service.club_health(session, state)
    owner = session.get(User, state.owner_user_id)
    record = competition_record(session, club_id)
    trophies = sorted([r for r in record if r["position"] and r["position"] <= 3], key=lambda r: r["position"])
    first_title = min((r["year"] for r in record if r["position"] == 1 and r["year"]), default=None)
    members = staff.active_staff(session, club_id)
    manager = state.manager_json or {}
    facilities = state.facilities_json or {}
    deals = session.scalars(select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == club_id, OwnerSponsorDeal.status == "active")).all()
    supporters = session.scalar(select(func.count()).select_from(SupportUnitHolding).where(SupportUnitHolding.club_id == club_id, SupportUnitHolding.units > 0)) or 0
    milestones = [m for m in (
        {"label": "Club founded", "year": profile.founded_at.year} if profile.founded_at else None,
        {"label": "Joined the GTEX world", "year": state.created_at.year} if state.created_at else None,
        {"label": "First title", "year": first_title} if first_title else None,
        {"label": f"{health['academy_output']} academy graduate(s) rated 60+", "year": None} if health["academy_output"] else None,
    ) if m]
    return {
        "club_id": club_id,
        "overview": {
            "club_name": state.club_name, "short_name": profile.short_name, "crest_url": profile.crest_asset_ref,
            "primary_color": profile.primary_color, "secondary_color": profile.secondary_color,
            "city": profile.city_name, "region": profile.region_name, "country_code": profile.country_code, "continent": continent(profile.country_code),
            "founded": profile.founded_at.year if profile.founded_at else None, "venue": profile.home_venue_name, "description": profile.description,
            "status": "active" if state.stage == "active" else "building", "prestige": state.prestige, "fans": state.fans,
            "fan_engagement": health["fan_engagement"], "squad_size": health["squad_size"], "academy_players": health["academy_players"],
        },
        "honours": {"trophies": trophies, "record": record, "milestones": milestones},
        "staff": {
            "owner": (owner.display_name or owner.username) if owner else None,
            "executives": [{"role": s.role, "role_label": staff.ROLES[s.role], "name": s.name, "quality": s.quality, "style": (s.personality_json or {}).get("risk_appetite")} for s in members.values()],
            "manager": {"name": manager.get("name"), "temperament": manager.get("temperament"), "tactical_preference": manager.get("tactical_preference")} if manager.get("name") else None,
        },
        "facilities": {k: int(facilities.get(k, 1)) for k in engine.FACILITY_KINDS},
        "commercial": {"sponsors": [{"sponsor": d.sponsor_name, "slot": d.slot} for d in deals], "supporter_holders": supporters, "fans": state.fans},
    }


def owner_stake(session: Session, club_id: str, owner_id: str) -> Decimal:
    token = session.scalar(select(ClubToken).where(ClubToken.club_id == club_id))
    if token is None or not token.total_supply:
        return Decimal("1")
    outside = session.scalar(select(func.coalesce(func.sum(ClubHolding.tokens_owned), 0)).where(ClubHolding.club_id == club_id, ClubHolding.user_id != owner_id)) or 0
    return max(Decimal("0"), Decimal("1") - Decimal(outside) / Decimal(token.total_supply))


def valuation(session: Session, state: OwnerClubState) -> dict[str, str]:
    cash = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
    parts = {
        "squad": ledger.D(service.squad_value(service.squad(session, state.club_id))),
        "facilities": ledger.D(sum(int(v) for v in (state.facilities_json or {}).values()) * FACILITY_UNIT_VALUE),
        "cash": ledger.D(cash * CASH_WEIGHT),
        "fan_base": ledger.D(state.fans * FAN_VALUE),
    }
    return {**{k: str(v) for k, v in parts.items()}, "total": str(service.club_value(session, state)), "club_cash": str(cash)}


def net_worth(session: Session, user_id: str) -> dict[str, Any]:
    wallet = ledger.wallet_classes(session, user_id)
    cash = ledger.D(wallet["gtex_total"])
    clubs, equity = [], Decimal("0")
    for state in service.user_states(session, user_id):
        value = valuation(session, state)
        stake = owner_stake(session, state.club_id, user_id)
        stake_value = ledger.D(Decimal(value["total"]) * stake)
        equity += stake_value
        clubs.append({"club_id": state.club_id, "club_name": state.club_name, "valuation": value, "stake_pct": str(ledger.D(stake * 100)), "stake_value": str(stake_value)})
    liabilities = Decimal("0")
    return {
        "personal_cash": str(cash), "fan_coin": wallet["fan_total"], "equity": str(ledger.D(equity)), "liabilities": str(liabilities),
        "net_worth": str(ledger.D(cash + equity - liabilities)), "clubs": clubs,
        "method": "Net worth = your GTEX wallet + your ownership share of each club's valuation - liabilities. Club valuation = squad market value + facility levels x 4,000 + 50% of club cash + fans x 2. Fan Coin is non-withdrawable and is not counted. Past spending is never added.",
    }


def money_history(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    state = service.require_state(session, club_id, user_id)
    acct = ledger.club_account(club_id)
    events = session.scalars(
        select(LedgerEvent).where(LedgerEvent.currency == ledger.GTEX, LedgerEvent.status == "completed", (LedgerEvent.source_account == acct) | (LedgerEvent.destination_account == acct)).order_by(LedgerEvent.created_at.asc())
    ).all()
    income: dict[str, Decimal] = {}
    spend: dict[str, Decimal] = {}
    running = Decimal("0")
    rows = []
    for e in events:
        incoming = e.destination_account == acct
        amount = ledger.D(e.net_amount if incoming else e.gross_amount)
        bucket = income if incoming else spend
        bucket[e.event_type] = bucket.get(e.event_type, Decimal("0")) + amount
        running += amount if incoming else -amount
        rows.append({"id": e.id, "event_type": e.event_type, "direction": "in" if incoming else "out", "amount": str(amount), "balance_after": str(running), "memo": e.memo, "created_at": e.created_at.isoformat() if e.created_at else None})
    return {
        "club_id": club_id, "club_name": state.club_name,
        "lifetime_income": str(ledger.D(sum(income.values(), Decimal("0")))), "lifetime_spend": str(ledger.D(sum(spend.values(), Decimal("0")))),
        "income_by_type": {k: str(v) for k, v in sorted(income.items(), key=lambda x: -x[1])},
        "spend_by_type": {k: str(v) for k, v in sorted(spend.items(), key=lambda x: -x[1])},
        "value_history": state.value_history_json or [],
        "events": list(reversed(rows))[:100],
    }
