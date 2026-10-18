"""Phase 7: manager terms, promises, poaching, and retention.

Money moves the offer score. It does not decide every appointment, and a
happy manager can refuse a richer rival with the same score.
"""

from __future__ import annotations

from decimal import Decimal
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError, require_owner
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyExecutive,
    ClubLegacyManager,
    ClubLegacyManagerOffer,
    ClubLegacyPromise,
    ClubLegacyRelationshipEvent,
)
from app.models.club_profile import ClubProfile
from app.owner_console import ledger

POACH_SHARE = Decimal("0.20")
GIFT_DELTA_CAP = 4
GIFT_SCORE_CEILING = 99
RELATIONSHIP_MAX = 100
BROKEN_PROMISE_DELTA = -15
KEPT_PROMISE_DELTA = 8


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def offer_score(wage, prestige: int, ambition: int, seed: int) -> tuple[int, int, int]:
    rng = random.Random(seed)
    money = min(40, int(Decimal(wage) / Decimal("1000")))
    project = min(40, int(prestige / 2) + max(0, 20 - int(ambition)))
    noise = rng.randint(0, 30)
    return money, project, money + project + noise


def relationship_bonus(score: int) -> int:
    return max(-16, min(16, (int(score) - 50) // 3))


def expectation_gap(wage, wage_expectation) -> int:
    expected = Decimal(wage_expectation or 0)
    if expected <= 0:
        return 0
    raw = int((Decimal(wage) / expected - 1) * Decimal("5"))
    return max(-5, min(5, raw))


def score_terms(wage, prestige: int, ambition: int, seed: int, relationship: int, wage_expectation) -> dict[str, int]:
    """Appointment and retention share this score. Relationship is read, not invented."""
    money, project, base_total = offer_score(wage, prestige, ambition, seed)
    relation = relationship_bonus(relationship)
    gap = expectation_gap(wage, wage_expectation)
    return {
        "money": money,
        "project": project,
        "noise": base_total - money - project,
        "base_total": base_total,
        "relationship": relation,
        "relationship_score": int(relationship),
        "expectation_gap": gap,
        "total": base_total + relation + gap,
    }


def _reject_related_clubs(session: Session, from_club_id: str, to_club_id: str) -> None:
    home = session.get(ClubProfile, from_club_id)
    away = session.get(ClubProfile, to_club_id)
    if home is not None and away is not None and home.owner_user_id == away.owner_user_id:
        raise LegacyError("related_club_blocked", 409, "Clubs with the same owner cannot arrange this move.")


def poach_compensation(wage) -> Decimal:
    return _q(Decimal(wage) * POACH_SHARE)


def pay_poach_compensation(
    session: Session,
    *,
    idempotency_key: str,
    from_club_id: str,
    to_club_id: str,
    wage,
    description: str,
) -> Decimal:
    amount = poach_compensation(wage)
    source = ledger.wallet_account(session, ledger.club_account(from_club_id), ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(to_club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=idempotency_key,
        source=source,
        destination=destination,
        amount=amount,
        description=description,
    )
    return amount


def register_manager(
    session: Session,
    *,
    name: str,
    personality: str,
    ambition: int,
    wage_expectation,
    seed: int = 1,
    club_id: str | None = None,
) -> ClubLegacyManager:
    if not name.strip():
        raise LegacyError("manager_name_required")
    if not personality.strip():
        raise LegacyError("personality_required")
    if int(ambition) < 0 or int(ambition) > 20:
        raise LegacyError("invalid_ambition")
    expected = _q(wage_expectation)
    if expected <= 0:
        raise LegacyError("invalid_wage_expectation")
    manager = ClubLegacyManager(
        club_id=club_id,
        name=name.strip(),
        personality=personality.strip(),
        ambition=int(ambition),
        wage_expectation=expected,
        wage=Decimal("0.00"),
        relationship_score=50,
        status="available" if club_id is None else "employed",
        seed=int(seed),
    )
    session.add(manager)
    session.flush()
    return manager


def _manager(session: Session, manager_id: str) -> ClubLegacyManager:
    manager = session.get(ClubLegacyManager, manager_id)
    if manager is None:
        raise LegacyError("manager_not_found", 404)
    return manager


def _record_relationship(
    session: Session,
    manager: ClubLegacyManager,
    *,
    kind: str,
    club_id: str | None,
    score_before: int,
    score_after: int,
) -> ClubLegacyRelationshipEvent:
    event = ClubLegacyRelationshipEvent(
        manager_id=manager.id,
        club_id=club_id,
        kind=kind,
        delta=score_after - score_before,
        score_before=score_before,
        score_after=score_after,
    )
    session.add(event)
    manager.relationship_score = score_after
    session.flush()
    return event


def present_offer(
    session: Session,
    *,
    club_id: str,
    user_id: str,
    manager_id: str,
    wage,
    contract_length: int,
    role: str,
    prestige: int,
    seed: int,
) -> ClubLegacyManagerOffer:
    require_owner(session, club_id, user_id)
    manager = _manager(session, manager_id)
    if int(contract_length) < 1:
        raise LegacyError("invalid_contract_length")
    if not role.strip():
        raise LegacyError("role_required")
    scored = score_terms(
        wage, int(prestige), manager.ambition, int(seed), manager.relationship_score, manager.wage_expectation
    )
    offer = ClubLegacyManagerOffer(
        club_id=club_id,
        candidate_name=manager.name,
        wage=_q(wage),
        prestige=int(prestige),
        ambition=manager.ambition,
        seed=int(seed),
        outcome="pending",
        money_score=scored["money"],
        project_score=scored["project"],
        contract_length=int(contract_length),
        role=role.strip(),
        manager_id=manager.id,
        personality=manager.personality,
        wage_expectation=manager.wage_expectation,
        relationship_score=manager.relationship_score,
        total_score=scored["total"],
        expectation_gap=scored["expectation_gap"],
    )
    session.add(offer)
    session.flush()
    return offer


def respond_to_offer(
    session: Session,
    *,
    offer_id: str,
    decision: str,
    wage=None,
    contract_length: int | None = None,
    role: str | None = None,
) -> ClubLegacyManagerOffer:
    offer = session.get(ClubLegacyManagerOffer, offer_id)
    if offer is None or offer.outcome not in {"pending", "counter"}:
        raise LegacyError("offer_not_open", 409)
    choice = decision.strip().lower()
    if choice in {"accept", "accepted"}:
        offer.outcome = "accepted"
        if offer.manager_id:
            manager = _manager(session, offer.manager_id)
            manager.club_id = offer.club_id
            manager.status = "employed"
            manager.wage = offer.wage
        session.flush()
        return offer
    if choice in {"reject", "rejected", "decline", "declined"}:
        offer.outcome = "rejected"
        session.flush()
        return offer
    if choice != "counter":
        raise LegacyError("unknown_decision")
    if wage is None or contract_length is None or role is None or not str(role).strip():
        raise LegacyError("counter_terms_required")
    offer.outcome = "countered"
    counter = ClubLegacyManagerOffer(
        club_id=offer.club_id,
        candidate_name=offer.candidate_name,
        wage=_q(wage),
        prestige=offer.prestige,
        ambition=offer.ambition,
        seed=offer.seed,
        outcome="counter",
        money_score=offer.money_score,
        project_score=offer.project_score,
        contract_length=int(contract_length),
        role=str(role).strip(),
        parent_offer_id=offer.id,
        manager_id=offer.manager_id,
        personality=offer.personality,
        wage_expectation=offer.wage_expectation,
        relationship_score=offer.relationship_score,
        total_score=offer.total_score,
        expectation_gap=offer.expectation_gap,
    )
    if offer.manager_id:
        manager = _manager(session, offer.manager_id)
        scored = score_terms(
            counter.wage,
            counter.prestige,
            manager.ambition,
            counter.seed,
            manager.relationship_score,
            manager.wage_expectation,
        )
        counter.money_score = scored["money"]
        counter.project_score = scored["project"]
        counter.relationship_score = manager.relationship_score
        counter.total_score = scored["total"]
        counter.expectation_gap = scored["expectation_gap"]
    session.add(counter)
    session.flush()
    return counter


def offer_history(session: Session, manager_id: str) -> list[ClubLegacyManagerOffer]:
    _manager(session, manager_id)
    return list(
        session.scalars(
            select(ClubLegacyManagerOffer)
            .where(ClubLegacyManagerOffer.manager_id == manager_id)
            .order_by(ClubLegacyManagerOffer.created_at.asc(), ClubLegacyManagerOffer.id.asc())
        ).all()
    )


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


def make_promise(
    session: Session, *, club_id: str, user_id: str, subject: str, manager_id: str | None = None
) -> ClubLegacyPromise:
    require_owner(session, club_id, user_id)
    if manager_id is not None:
        manager = _manager(session, manager_id)
        if manager.club_id not in {None, club_id}:
            raise LegacyError("manager_at_other_club", 409)
    promise = ClubLegacyPromise(club_id=club_id, subject=subject, status="open", trust=50, manager_id=manager_id)
    session.add(promise)
    session.flush()
    return promise


def resolve_promise(session: Session, *, promise_id: str, kept: bool) -> ClubLegacyPromise:
    promise = session.get(ClubLegacyPromise, promise_id)
    if promise is None:
        raise LegacyError("promise_not_found", 404)
    promise.status = "kept" if kept else "broken"
    promise.trust = min(100, promise.trust + 10) if kept else max(0, promise.trust - 20)
    if promise.manager_id:
        manager = _manager(session, promise.manager_id)
        before = int(manager.relationship_score)
        if kept:
            after = min(RELATIONSHIP_MAX, before + KEPT_PROMISE_DELTA)
            kind = "promise_kept"
        else:
            after = max(0, before + BROKEN_PROMISE_DELTA)
            kind = "promise_broken"
        _record_relationship(session, manager, kind=kind, club_id=promise.club_id, score_before=before, score_after=after)
    session.flush()
    return promise


def record_gift(session: Session, *, manager_id: str, club_id: str | None = None) -> ClubLegacyRelationshipEvent:
    """A gift moves the relationship by a small capped amount and cannot reach the maximum."""
    manager = _manager(session, manager_id)
    before = int(manager.relationship_score)
    delta = min(GIFT_DELTA_CAP, max(0, GIFT_SCORE_CEILING - before))
    after = before + delta
    return _record_relationship(
        session, manager, kind="gift", club_id=club_id or manager.club_id, score_before=before, score_after=after
    )


def approach_manager(session: Session, *, executive_id: str, from_club_id: str, user_id: str) -> ClubLegacyExecutive:
    executive = session.get(ClubLegacyExecutive, executive_id)
    if executive is None or executive.status != "hired":
        raise LegacyError("executive_unavailable", 404)
    require_owner(session, from_club_id, user_id)
    if executive.club_id == from_club_id:
        raise LegacyError("already_on_staff", 409)
    _reject_related_clubs(session, from_club_id, executive.club_id)
    pay_poach_compensation(
        session,
        idempotency_key=f"compensation:{executive.id}:{from_club_id}",
        from_club_id=from_club_id,
        to_club_id=executive.club_id,
        wage=executive.wage,
        description=f"Compensation for {executive.name}",
    )
    executive.status = "in_talks"
    session.flush()
    return executive


def poach_manager(session: Session, *, manager_id: str, from_club_id: str, user_id: str) -> ClubLegacyManager:
    manager = _manager(session, manager_id)
    require_owner(session, from_club_id, user_id)
    if manager.club_id is None or manager.status not in {"employed", "in_talks"}:
        raise LegacyError("manager_unemployed", 409)
    if manager.club_id == from_club_id:
        raise LegacyError("already_on_staff", 409)
    _reject_related_clubs(session, from_club_id, manager.club_id)
    pay_poach_compensation(
        session,
        idempotency_key=f"compensation:manager:{manager.id}:{from_club_id}",
        from_club_id=from_club_id,
        to_club_id=manager.club_id,
        wage=manager.wage,
        description=f"Compensation for {manager.name}",
    )
    manager.status = "in_talks"
    session.flush()
    return manager


def consider_retention(
    session: Session,
    *,
    manager_id: str,
    rival_wage,
    rival_prestige: int,
    seed: int,
) -> dict:
    """Retention uses the same score as appointment. A happy manager can refuse a richer rival."""
    manager = _manager(session, manager_id)
    if manager.club_id is None:
        raise LegacyError("manager_unemployed", 409)
    stay = score_terms(
        manager.wage,
        int(rival_prestige),
        manager.ambition,
        int(seed),
        manager.relationship_score,
        manager.wage_expectation,
    )
    rival = score_terms(
        rival_wage,
        int(rival_prestige),
        manager.ambition,
        int(seed),
        50,
        manager.wage_expectation,
    )
    stays = stay["total"] >= rival["total"]
    richer = Decimal(rival_wage) > Decimal(manager.wage)
    return {
        "decision": "stay" if stays else "leave",
        "refused_richer": stays and richer,
        "relationship_score": manager.relationship_score,
        "stay": stay,
        "rival": rival,
    }


def offer_dict(offer: ClubLegacyManagerOffer) -> dict:
    return {
        "id": offer.id,
        "club_id": offer.club_id,
        "manager_id": offer.manager_id,
        "candidate_name": offer.candidate_name,
        "wage": str(offer.wage),
        "contract_length": offer.contract_length,
        "role": offer.role,
        "outcome": offer.outcome,
        "parent_offer_id": offer.parent_offer_id,
        "personality": offer.personality,
        "ambition": offer.ambition,
        "wage_expectation": str(offer.wage_expectation) if offer.wage_expectation is not None else None,
        "relationship_score": offer.relationship_score,
        "money_score": offer.money_score,
        "project_score": offer.project_score,
        "total_score": offer.total_score,
        "seed": offer.seed,
    }


def manager_dict(manager: ClubLegacyManager) -> dict:
    return {
        "id": manager.id,
        "club_id": manager.club_id,
        "name": manager.name,
        "personality": manager.personality,
        "ambition": manager.ambition,
        "wage_expectation": str(manager.wage_expectation),
        "wage": str(manager.wage),
        "relationship_score": manager.relationship_score,
        "status": manager.status,
    }
