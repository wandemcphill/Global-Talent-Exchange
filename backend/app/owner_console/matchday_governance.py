"""Matchday end-whistle -> Owner Authority governance bridge.

When a match is authoritatively complete, gift income that fans sent to a club during that match and
post-match squad bonuses are recorded as *governed* decisions rather than being silently absorbed or
unilaterally spent. Allocation of gift income is the reserved ``financial_planning`` activity, so it
always escalates to the club owner's inbox. Post-match squad bonuses are governed as
``operational_expenditure``, automatically approved when within the club's delegated financial
threshold and escalated to the owner when exceeding threshold.

Invariants
----------
* Completion comes from the canonical ``CompetitionMatch`` row, never from a client signal.
* Gift totals are read from the insert-only owner ledger; this module never moves money.
* Ownership is enforced: a caller only ever sees/creates decisions for clubs they own, and callers who
  own no affected club receive an empty result (no ownership information leaks).
* Idempotent per (club, match, activity): repeated end-whistle calls return the existing decisions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.competition_match import CompetitionMatch
from app.owner_console import delegation_service
from app.owner_console.delegation_service import DelegationError
from app.owner_console.ledger import FAN
from app.owner_console.models import ClubDelegatedDecision, LedgerEvent, OwnerClubState

GOVERNANCE_SOURCE = "matchday_full_time"
GIFT_INCOME_ACTIVITY = "financial_planning"
BONUS_ACTIVITY = "operational_expenditure"

# Acting role for system-generated proposals. Never "owner": an owner-direct proposal would bypass the
# reserved-decision escalation this bridge exists to enforce.
PROPOSING_ROLE = "general_manager"


def _is_match_complete(match: CompetitionMatch) -> bool:
    return str(match.status or "").lower() == "completed" or match.completed_at is not None


def _gift_totals(session: Session, match_id: str, club_id: str) -> tuple[int, Decimal, Decimal]:
    row = session.execute(
        select(
            func.count(LedgerEvent.id),
            func.coalesce(func.sum(LedgerEvent.gross_amount), 0),
            func.coalesce(func.sum(LedgerEvent.net_amount), 0),
        ).where(
            LedgerEvent.event_type == "gift",
            LedgerEvent.currency == FAN,
            LedgerEvent.status == "completed",
            LedgerEvent.related_object_type == "match",
            LedgerEvent.related_object_id == match_id,
            LedgerEvent.club_id == club_id,
        )
    ).one()
    return int(row[0]), Decimal(str(row[1])), Decimal(str(row[2]))


def _existing_decision(
    session: Session, club_id: str, match_id: str, activity_key: str = GIFT_INCOME_ACTIVITY
) -> ClubDelegatedDecision | None:
    candidates = session.scalars(
        select(ClubDelegatedDecision).where(
            ClubDelegatedDecision.club_id == club_id,
            ClubDelegatedDecision.activity_key == activity_key,
        )
    ).all()
    for decision in candidates:
        payload = decision.payload_json or {}
        if payload.get("source") == GOVERNANCE_SOURCE and payload.get("match_id") == match_id:
            return decision
    return None


def _result(club_id: str, outcome: str, decision: ClubDelegatedDecision | None = None, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"club_id": club_id, "outcome": outcome}
    if decision is not None:
        body["decision_id"] = decision.id
        body["decision_status"] = decision.status
        body["requires_owner_approval"] = bool(decision.requires_owner_approval)
    body.update(extra)
    return body


def _govern_club_gifts(session: Session, match_id: str, state: OwnerClubState) -> dict[str, Any]:
    club_id = state.club_id
    existing = _existing_decision(session, club_id, match_id, GIFT_INCOME_ACTIVITY)
    if existing is not None:
        return _result(club_id, "already_recorded", existing)

    gift_count, gross, net = _gift_totals(session, match_id, club_id)
    if gift_count == 0:
        return _result(club_id, "no_gift_income")

    decision = delegation_service.propose_delegated_decision(
        session,
        club_id,
        GIFT_INCOME_ACTIVITY,
        PROPOSING_ROLE,
        title="Allocate matchday gift income",
        summary=(
            f"Fans sent {gift_count} gift(s) worth {gross} FAN coin during match {match_id} "
            f"({net} FAN coin credited to the club after platform fees). "
            "Review how this income is allocated."
        ),
        financial_amount_gtex=None,  # gifts are FAN_COIN; never mix currencies into GTEX thresholds
        payload={
            "source": GOVERNANCE_SOURCE,
            "match_id": match_id,
            "gift_count": gift_count,
            "gross_fan_coin": str(gross),
            "net_fan_coin": str(net),
            "currency": FAN,
        },
    )
    return _result(club_id, "proposed", decision, gift_count=gift_count, net_fan_coin=str(net))


def _govern_club_bonus(
    session: Session,
    match_id: str,
    state: OwnerClubState,
    bonus_amount_gtex: Decimal,
    bonus_note: str | None = None,
) -> dict[str, Any]:
    club_id = state.club_id
    existing = _existing_decision(session, club_id, match_id, BONUS_ACTIVITY)
    if existing is not None:
        return _result(
            club_id,
            "already_recorded",
            existing,
            decision_type="post_match_bonus",
            bonus_amount_gtex=str(bonus_amount_gtex),
        )

    summary = f"Post-match squad performance bonus of {bonus_amount_gtex:,.0f} GTX proposed for match {match_id}." + (
        f" Note: {bonus_note}" if bonus_note else ""
    )
    decision = delegation_service.propose_delegated_decision(
        session,
        club_id,
        BONUS_ACTIVITY,
        PROPOSING_ROLE,
        title="Approve post-match squad bonus",
        summary=summary,
        financial_amount_gtex=bonus_amount_gtex,
        payload={
            "source": GOVERNANCE_SOURCE,
            "match_id": match_id,
            "action": "post_match_bonus",
            "bonus_amount_gtex": str(bonus_amount_gtex),
            "note": bonus_note or "",
        },
    )
    return _result(
        club_id,
        "proposed",
        decision,
        decision_type="post_match_bonus",
        bonus_amount_gtex=str(bonus_amount_gtex),
    )


def record_full_time_governance(
    session: Session,
    *,
    match_id: str,
    user_id: str,
    bonus_amount_gtex: Decimal | float | None = None,
    bonus_note: str | None = None,
) -> dict[str, Any]:
    """Record governed decisions (gift income, post-match bonuses) for every club the caller owns in the match."""
    match = session.get(CompetitionMatch, match_id)
    if match is None:
        raise DelegationError("Match not found.", 404, code="match_not_found")
    if not _is_match_complete(match):
        raise DelegationError("Match has not reached full time.", 409, code="match_not_complete")

    meta = match.metadata_json or {}
    resolved_bonus: Decimal | None = None
    if bonus_amount_gtex is not None:
        try:
            val = Decimal(str(bonus_amount_gtex))
            if val > Decimal("0"):
                resolved_bonus = val
        except Exception:
            resolved_bonus = None
    elif meta.get("post_match_bonus_gtex") is not None:
        try:
            val = Decimal(str(meta["post_match_bonus_gtex"]))
            if val > Decimal("0"):
                resolved_bonus = val
        except Exception:
            resolved_bonus = None

    results: list[dict[str, Any]] = []

    # 1. Gift income governance
    gifted_club_ids = set(
        session.scalars(
            select(LedgerEvent.club_id)
            .where(
                LedgerEvent.event_type == "gift",
                LedgerEvent.related_object_type == "match",
                LedgerEvent.related_object_id == match_id,
                LedgerEvent.club_id.is_not(None),
            )
            .distinct()
        ).all()
    )
    # Include clubs that already have a decision so the response stays stable across retries.
    owned_gifted_states = (
        session.scalars(
            select(OwnerClubState).where(
                OwnerClubState.owner_user_id == user_id,
                OwnerClubState.club_id.in_(gifted_club_ids),
            )
        ).all()
        if gifted_club_ids
        else []
    )
    for state in sorted(owned_gifted_states, key=lambda s: s.club_id):
        res = _govern_club_gifts(session, match_id, state)
        if res.get("outcome") != "no_gift_income":
            results.append(res)

    # 2. Post-match squad bonus governance
    if resolved_bonus is not None:
        participating_club_ids = {match.home_club_id, match.away_club_id}
        owned_match_states = session.scalars(
            select(OwnerClubState).where(
                OwnerClubState.owner_user_id == user_id,
                OwnerClubState.club_id.in_(participating_club_ids),
            )
        ).all()
        for state in sorted(owned_match_states, key=lambda s: s.club_id):
            bonus_res = _govern_club_bonus(session, match_id, state, resolved_bonus, bonus_note)
            results.append(bonus_res)

    return {"match_id": match_id, "results": results}
