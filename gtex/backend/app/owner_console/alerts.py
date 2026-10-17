from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.owner_console import service
from app.owner_console.models import OwnerClubState, OwnerInboxItem, OwnerSquadPlayer

RESPONSE_HOURS = {"transfer_bid": 48, "regen_breakthrough": 72, "sponsor_opportunity": 72, "regen_endorsement": 72, "competition_invite": 24}
DEFAULT_RESPONSE_HOURS = 96
EXPIRY_DEFAULTS = {
    "transfer_bid": "reject", "regen_breakthrough": "acknowledge", "player_unrest": "ignore", "facility_request": "reject",
    "manager_request": "reject", "sponsor_opportunity": "reject", "regen_endorsement": "reject", "competition_invite": "decline",
    "manager_meeting": "ignore",
}
WARN_BEFORE = timedelta(hours=6)
# Decisions created before deadlines existed get a fresh clock from rollout.
CLOCK_START = datetime(2026, 10, 17, tzinfo=timezone.utc)
JUMP_PCT = Decimal("10")
WONDERKID_MAX_AGE = 21
REGEN_PROVIDERS = ("gtex_national_seed", "gtex_regen")


def response_hours(kind: str) -> int:
    return RESPONSE_HOURS.get(kind, DEFAULT_RESPONSE_HOURS)


def respond_by(item: OwnerInboxItem) -> datetime | None:
    if not item.is_decision or item.created_at is None:
        return None
    return max(service.aware(item.created_at), CLOCK_START) + timedelta(hours=response_hours(item.kind))


def expiry_action(item: OwnerInboxItem) -> dict[str, str] | None:
    actions = item.actions_json or []
    wanted = EXPIRY_DEFAULTS.get(item.kind)
    return next((a for a in actions if a.get("key") == wanted), actions[-1] if actions else None)


def _note(item: OwnerInboxItem, kind: str, *, title: str, what: str, why: str, priority: str, payload: dict[str, Any]) -> OwnerInboxItem:
    return OwnerInboxItem(user_id=item.user_id, club_id=item.club_id, kind=kind, sender="GTEX Board Office", title=title, what=what, why=why, actions_json=[], payload_json=payload, priority=priority, is_decision=False)


def expire_decision(session: Session, item: OwnerInboxItem) -> None:
    action = expiry_action(item)
    label = action["label"] if action else "No action"
    hours = response_hours(item.kind)
    outcome = "No action taken."
    if action:
        try:
            with session.begin_nested():
                resolved = service.resolve_item(session, item.user_id, item.id, action["key"])
                outcome = resolved.outcome_text or outcome
        except (service.OwnerError, KeyError):
            outcome = "Closed without effect."
    item.status = "expired"
    item.resolution = f"expired:{action['key']}" if action else "expired"
    item.outcome_text = f"Expired after {hours}h with no response. {outcome}"
    item.resolved_at = service.now()
    session.add(_note(item, "decision_expired", title=f"Expired: {item.title}", what=outcome,
        why=f"No response within {hours} hours, so the safe default \"{label}\" was applied.", priority="normal", payload={"subject": item.id, "decision_id": item.id}))


def warn_decision(session: Session, item: OwnerInboxItem, due: datetime) -> None:
    action = expiry_action(item)
    label = action["label"] if action else "No action"
    session.add(_note(item, "decision_expiring", title=f"6 hours left: {item.title}",
        what=f"Respond by {due:%a %d %b, %H:%M} UTC or \"{label}\" is applied automatically.",
        why="Decisions expire with the game's safe default when the owner does not respond.", priority="high",
        payload={"subject": item.id, "decision_id": item.id, "respond_by": due.isoformat()}))
    item.payload_json = {**(item.payload_json or {}), "expiry_warned": True}


def sweep_decisions(session: Session, user_id: str | None = None, at: datetime | None = None) -> dict[str, int]:
    at = at or service.now()
    stmt = select(OwnerInboxItem).where(OwnerInboxItem.status == "open", OwnerInboxItem.is_decision.is_(True))
    if user_id:
        stmt = stmt.where(OwnerInboxItem.user_id == user_id)
    expired = warned = 0
    for item in session.scalars(stmt).all():
        due = respond_by(item)
        if due is None:
            continue
        if at >= due:
            expire_decision(session, item)
            expired += 1
        elif due - at <= WARN_BEFORE and not (item.payload_json or {}).get("expiry_warned"):
            warn_decision(session, item, due)
            warned += 1
    session.flush()
    return {"expired": expired, "warned": warned}


def _dob_cutoff(today: date) -> date:
    try:
        return today.replace(year=today.year - WONDERKID_MAX_AGE - 1)
    except ValueError:
        return date(today.year - WONDERKID_MAX_AGE - 1, 3, 1)


def _age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def sweep_price_jumps(session: Session, at: datetime | None = None) -> int:
    from app.players.token_service import PlayerTokenMarketService

    at = at or service.now()
    watchers: dict[str, dict[str, str]] = {}
    for user_id, player_id, shares in session.execute(select(PlayerShareHolding.user_id, PlayerShareHolding.player_id, PlayerShareHolding.share_count).where(PlayerShareHolding.share_count > 0)):
        watchers.setdefault(player_id, {})[user_id] = f"You hold {shares:,} shares."
    clubs = {s.club_id: s for s in session.scalars(select(OwnerClubState)).all()}
    squad_club: dict[tuple[str, str], str] = {}
    for ref, club_id in session.execute(select(OwnerSquadPlayer.player_ref, OwnerSquadPlayer.club_id).where(OwnerSquadPlayer.player_ref.is_not(None), OwnerSquadPlayer.status.in_(("active", "listed")))):
        state = clubs.get(club_id)
        if state:
            watchers.setdefault(ref, {})[state.owner_user_id] = f"He plays for your club {state.club_name}."
            squad_club[(ref, state.owner_user_id)] = club_id
    if not watchers:
        return 0
    today = at.date()
    kids = {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(list(watchers)), Player.source_provider.in_(REGEN_PROVIDERS), Player.date_of_birth > _dob_cutoff(today))).all()}
    if not kids:
        return 0
    markets = {m.player_id: m for m in session.scalars(select(PlayerShareMarket).where(PlayerShareMarket.player_id.in_(list(kids)))).all()}
    changes = PlayerTokenMarketService(session)._price_change_7d(markets) if markets else {}
    year, week, _ = at.isocalendar()
    created = 0
    for player_id, change in changes.items():
        if abs(change) < JUMP_PCT:
            continue
        player, market = kids[player_id], markets[player_id]
        subject = f"{player_id}:{year}-W{week:02d}"
        name = player.full_name
        for user_id, reason in watchers[player_id].items():
            seen = session.scalars(select(OwnerInboxItem.payload_json).where(OwnerInboxItem.user_id == user_id, OwnerInboxItem.kind == "wonderkid_price_jump")).all()
            if any((p or {}).get("subject") == subject for p in seen):
                continue
            up = change > 0
            session.add(OwnerInboxItem(
                user_id=user_id, club_id=squad_club.get((player_id, user_id)), kind="wonderkid_price_jump", sender="GTEX Share Market",
                title=f"{name} {'up' if up else 'down'} {abs(change):.1f}% this week",
                what=f"Wonderkid {name} ({_age(player.date_of_birth, today)}) moved {change:+.1f}% in 7 days to {Decimal(market.share_price_coin):.2f} GTX a share.",
                why=reason, actions_json=[], is_decision=False, priority="high" if abs(change) >= 2 * JUMP_PCT else "normal",
                payload_json={"subject": subject, "player_id": player_id, "change_pct": str(change), "direction": "up" if up else "down"},
            ))
            created += 1
    session.flush()
    return created
