"""Phase 2: GM and HoYD contracts, delegation, academy intake, and pre-season."""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import (
    PRESEASON_RESPONSE,
    LegacyError,
    policy_for,
    recommend,
    require_owner,
)
from app.club_legacy.models import (
    ClubLegacyExecutive,
    ClubLegacyPreseasonInvite,
    ClubLegacyPromise,
    ClubLegacyRecommendation,
    ClubLegacyReport,
)
from app.club_legacy.ratings import development_score, prestige_score
from app.models.club_profile import ClubProfile
from app.owner_console.models import OwnerClubState, OwnerSquadPlayer

ROLE_AUTHORITY = {
    "gm": "operations",
    "hoyd": "academy",
    "football_manager": "matches",
}
PATHWAYS = {
    "promotion": "academy_promotion",
    "loan": "academy_loan",
    "sale": "academy_sale",
}


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _attributes(role: str, name: str) -> dict[str, int]:
    rng = random.Random(f"{role}:{name}")
    keys = {
        "gm": ("intelligence", "talent_evaluation", "financial_acumen", "negotiation"),
        "hoyd": ("talent_identification", "potential_assessment", "recruitment_network", "judgement"),
        "football_manager": ("tactics", "squad_judgement", "training", "morale"),
    }[role]
    return {key: rng.randint(40, 85) for key in keys}


def _hiring_fit(session: Session, club_id: str) -> dict[str, int]:
    profile = session.get(ClubProfile, club_id)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    kept = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyPromise)
            .where(ClubLegacyPromise.club_id == club_id, ClubLegacyPromise.status == "kept")
        )
        or 0
    )
    facility = development_score(state.facilities_json if state else {})
    city_bonus = 10 if profile and profile.city_name else 0
    owner_trust = min(100, 40 + int(kept) * 10)
    return {
        "facility_level": facility,
        "city_bonus": city_bonus,
        "owner_trust": owner_trust,
        "fit": min(100, facility // 2 + city_bonus + owner_trust // 5),
    }


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
    if role not in ROLE_AUTHORITY:
        raise LegacyError("unknown_role")
    if not (personality or "").strip():
        raise LegacyError("personality_required")
    months = int(contract_months)
    if months < 1 or months > 60:
        raise LegacyError("invalid_contract", 400, "Contract length must be between 1 and 60 months.")
    require_owner(session, club_id, user_id)
    current = session.scalar(
        select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id, ClubLegacyExecutive.role == role)
    )
    if current is not None:
        raise LegacyError("role_filled", 409, f"This club already has a {role}.")
    attributes = _attributes(role, name)
    attributes.update(_hiring_fit(session, club_id))
    hired = ClubLegacyExecutive(
        club_id=club_id,
        role=role,
        name=name.strip(),
        personality=personality.strip(),
        attributes_json=attributes,
        wage=_q(wage),
        contract_months=months,
        authority=(authority or ROLE_AUTHORITY[role]).strip()[:64],
        status="hired",
    )
    session.add(hired)
    session.flush()
    return hired


def good_prospect_chance(quality: int) -> float:
    """Higher HoYD quality raises the chance of a good prospect. It never reaches certainty."""
    bounded = max(0, min(100, int(quality)))
    return 0.08 + (bounded / 100) * 0.32


def star_chance(quality: int) -> float:
    """A star remains unlikely. Quality lifts the chance and the cap stays well below 1."""
    bounded = max(0, min(100, int(quality)))
    return min(0.12, 0.02 + (bounded / 100) * 0.10)


def roll_prospect(*, quality: int, prestige: int, seed: int) -> dict[str, Any]:
    rng = random.Random(int(seed))
    star_roll = rng.random()
    good_roll = rng.random()
    gem_roll = rng.random()
    small_club = int(prestige) < 35
    if star_roll < star_chance(quality):
        potential = rng.randint(86, 93)
        band = "high"
    elif good_roll < good_prospect_chance(quality) or (small_club and gem_roll < 0.15):
        potential = rng.randint(75, 85)
        band = "good"
    else:
        potential = rng.randint(48, 74)
        band = "ordinary"
    confidence = min(85, 30 + max(0, min(100, int(quality))) // 2)
    return {
        "potential": potential,
        "band": band,
        "confidence": confidence,
        "guaranteed_star": False,
        "small_club_path": small_club,
    }


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
        reason=(
            f"HoYD identification {skill}/100 and club prestige {prestige}. "
            "Smaller clubs can still find the top of the band."
        ),
        confidence=confidence,
        consequence="A signing in this band can develop or stall. Wealth does not reserve world-class regens.",
    )
    session.add(report)
    session.flush()
    return report


def _hoyd_quality(session: Session, club_id: str) -> tuple[ClubLegacyExecutive | None, int]:
    hoyd = session.scalar(
        select(ClubLegacyExecutive).where(
            ClubLegacyExecutive.club_id == club_id,
            ClubLegacyExecutive.role == "hoyd",
            ClubLegacyExecutive.status == "hired",
        )
    )
    if hoyd is None:
        return None, 45
    return hoyd, int((hoyd.attributes_json or {}).get("talent_identification", 45))


def academy_plan(session: Session, club_id: str, user_id: str, *, seed: int) -> dict[str, Any]:
    """HoYD intake. Quality shifts the odds. A small club can still roll a high potential."""
    require_owner(session, club_id, user_id)
    hoyd, quality = _hoyd_quality(session, club_id)
    prestige = prestige_score(session, club_id)
    rolled = roll_prospect(quality=quality, prestige=prestige, seed=seed)
    facilities = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    facility = development_score(facilities.facilities_json if facilities else {})
    cost = _q(Decimal(180) + Decimal(quality) * Decimal("4") + Decimal(facility))
    suitability = (
        f"HoYD quality {quality}/100, facilities {facility}, city fit included in hiring. "
        f"This club's prestige is {prestige}, which shifts the odds and does not reserve a star."
    )
    if hoyd is None:
        suitability = "No HoYD is hired, so the owner is running this intake. " + suitability
    uncertainty = (
        f"Confidence {rolled['confidence']}/99. The roll can miss. "
        "A high potential is possible for a small club and is never guaranteed."
    )
    consequence = (
        f"Scouting this intake costs {cost}. Promoting, loaning, or selling the prospect "
        "still needs the owner's authority."
    )
    report = ClubLegacyReport(
        club_id=club_id,
        role="hoyd" if hoyd else "owner",
        kind="academy",
        summary=f"Prospect potential {rolled['potential']} ({rolled['band']}). Not a guaranteed star.",
        reason=suitability,
        confidence=int(rolled["confidence"]),
        consequence=consequence,
    )
    session.add(report)
    session.flush()
    recommendation = recommend(
        session,
        club_id=club_id,
        user_id=user_id,
        task_key="academy_intake",
        amount=cost,
        reason=suitability + " " + uncertainty,
        confidence=int(rolled["confidence"]),
        consequence=consequence,
    )
    return {"report": report, "recommendation": recommendation, "prospect": rolled, "cost": cost}


def pathway_recommendation(
    session: Session,
    club_id: str,
    user_id: str,
    *,
    kind: str,
    player_id: str,
    amount,
    note: str = "",
) -> ClubLegacyRecommendation:
    """Recommend promotion, loan, or sale. This does not move the player or spend the money."""
    if kind not in PATHWAYS:
        raise LegacyError("unknown_pathway")
    player = session.get(OwnerSquadPlayer, player_id)
    if player is None or player.club_id != club_id:
        raise LegacyError("player_not_found", 404)
    status_before = player.status
    task_key = PATHWAYS[kind]
    suitability = note.strip() or f"{player.name} is a {player.position} rated {player.rating}."
    record = recommend(
        session,
        club_id=club_id,
        user_id=user_id,
        task_key=task_key,
        amount=_q(amount),
        reason=f"{kind.title()} suits {player.name}. {suitability}",
        confidence=55,
        consequence=(
            f"The {kind} costs {_q(amount)} and waits for the current owner policy. "
            "Staff cannot complete it on their own when the owner has kept authority."
        ),
    )
    session.refresh(player)
    if player.status != status_before:
        player.status = status_before
    session.flush()
    return record


def _staff_policy(session: Session, club_id: str, task_key: str, amount: Decimal):
    from app.club_legacy.operations import assert_staff_can_spend

    policy = policy_for(session, club_id, task_key)
    if policy is None or policy.mode == "owner_only":
        raise LegacyError("manual_only", 409, "The owner still handles this task.")
    if policy.mode == "approval_required":
        raise LegacyError("approval_required", 409, "The owner has to approve this before it runs.")
    assert_staff_can_spend(session, club_id, task_key, amount)
    return policy


def execute_as_executive(session: Session, *, recommendation_id: str, actor_user_id: str) -> ClubLegacyRecommendation:
    """Run a recommendation only if the policy that is current right now allows it."""
    record = session.get(ClubLegacyRecommendation, recommendation_id)
    if record is None:
        raise LegacyError("recommendation_not_found", 404)
    require_owner(session, record.club_id, actor_user_id)
    if record.status != "recommended":
        raise LegacyError("recommendation_already_settled", 409)
    _staff_policy(session, record.club_id, record.task_key, Decimal(record.amount))
    if record.task_key == PRESEASON_RESPONSE:
        record.status = "executed"
        record.outcome = "Executed under the current automatic pre-season policy."
        session.flush()
        return record
    from app.club_legacy.delegation import execute

    return execute(session, recommendation_id=recommendation_id, actor_user_id=actor_user_id)


def gm_respond_preseason(session: Session, *, invite_id: str, user_id: str, decision: str) -> dict[str, Any]:
    """The GM may answer a pre-season invite only inside the policy that is current now."""
    invite = session.get(ClubLegacyPreseasonInvite, invite_id)
    if invite is None or invite.status != "pending":
        raise LegacyError("invite_not_open", 409)
    require_owner(session, invite.to_club_id, user_id)
    gm = session.scalar(
        select(ClubLegacyExecutive).where(
            ClubLegacyExecutive.club_id == invite.to_club_id,
            ClubLegacyExecutive.role == "gm",
            ClubLegacyExecutive.status == "hired",
        )
    )
    if gm is None:
        raise LegacyError("gm_required", 409, "Hire a general manager before delegating pre-season.")
    policy = policy_for(session, invite.to_club_id, PRESEASON_RESPONSE)
    if policy is not None and policy.mode == "approval_required":
        record = recommend(
            session,
            club_id=invite.to_club_id,
            user_id=user_id,
            task_key=PRESEASON_RESPONSE,
            amount=Decimal(invite.appearance_fee),
            reason=f"GM {gm.name} recommends {decision} for the pre-season invite on {invite.match_on}.",
            confidence=60,
            consequence="The invite stays pending until the owner approves it under the current policy.",
        )
        return {"invite_status": invite.status, "recommendation_id": record.id, "acted": False}
    _staff_policy(session, invite.to_club_id, PRESEASON_RESPONSE, Decimal(invite.appearance_fee))
    from app.club_legacy.operations import respond_preseason

    updated = respond_preseason(session, invite_id=invite.id, user_id=user_id, decision=decision)
    return {"invite_status": updated.status, "recommendation_id": None, "acted": True}


def executive_dict(item: ClubLegacyExecutive) -> dict[str, Any]:
    return {
        "id": item.id,
        "role": item.role,
        "name": item.name,
        "personality": item.personality,
        "wage": str(item.wage),
        "contract_months": item.contract_months,
        "authority": item.authority,
        "status": item.status,
        "attributes": item.attributes_json or {},
        "fit": (item.attributes_json or {}).get("fit"),
    }
