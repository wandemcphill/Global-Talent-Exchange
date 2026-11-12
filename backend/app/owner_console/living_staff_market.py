"""
GTEX Living Football World — Stage 4
Autonomous Staff Career & Professional Employment Market

Implements the persistent, interconnected football employment market:
1. Universal career identity with persistent ClubStaffProfile and career history.
2. Unemployed/Free-Agent pool management across clubs.
3. Vacancy lifecycle: open role detection, candidate matching, and approaches.
4. AI candidate offer evaluation: prestige requirements, wage expectations,
   poaching fees, and prior relationship memory.
5. Authoritative hiring and contract/assignment ratification with club ledger settlement.
6. Dismissal with severance calculation and immediate transition to global free agency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.club_growth import (
    ClubStaffProfile,
    ClubStaffContract,
    ClubStaffAssignment,
)
from app.club_growth.staff_role_policy import (
    normalise_staff_role,
    ROLE_FIRST_TEAM_MANAGER,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
    ROLE_SCOUT,
    ROLE_MEDICAL,
    ROLE_FIRST_TEAM_COACH,
    ROLE_YOUTH_COACH,
    ROLE_PERFORMANCE_ANALYST,
)
from app.owner_console import engine, ledger

logger = logging.getLogger(__name__)

SUPPORTED_MARKET_ROLES = [
    ROLE_FIRST_TEAM_MANAGER,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
    "chief_scout",
    ROLE_SCOUT,
    "medical_director",
    ROLE_MEDICAL,
    ROLE_FIRST_TEAM_COACH,
    ROLE_YOUTH_COACH,
    ROLE_PERFORMANCE_ANALYST,
]

ROLE_DISPLAY_LABELS: dict[str, str] = {
    ROLE_FIRST_TEAM_MANAGER: "First-Team Manager",
    ROLE_GENERAL_MANAGER: "General Manager",
    ROLE_HEAD_OF_YOUTH_DEVELOPMENT: "Head of Youth Development",
    "chief_scout": "Chief Scout",
    ROLE_SCOUT: "Senior Scout",
    "medical_director": "Physio and medical lead",
    ROLE_MEDICAL: "Physio / Medical Specialist",
    ROLE_FIRST_TEAM_COACH: "First-Team Coach",
    ROLE_YOUTH_COACH: "Academy Youth Coach",
    ROLE_PERFORMANCE_ANALYST: "Performance Analyst",
}


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        if val is None:
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def ensure_staff_market_profiles(session: Session) -> list[ClubStaffProfile]:
    """
    Ensures every candidate in the authoritative EXECUTIVE_STAFF_CATALOG has
    a persistent ClubStaffProfile global identity in the database.
    Preserves all existing career history and contract associations.
    """
    existing_profiles = session.scalars(select(ClubStaffProfile)).all()
    by_key = {p.market_key: p for p in existing_profiles}

    created: list[ClubStaffProfile] = []

    for item in engine.EXECUTIVE_STAFF_CATALOG:
        staff_id = str(item.get("id") or item.get("staff_id") or "")
        if not staff_id:
            continue
        key = f"staff:{staff_id}"

        raw_role = str(item.get("role") or "first_team_manager")
        canon_role = normalise_staff_role(raw_role)
        salary_minor = _safe_int(item.get("salary") or item.get("salary_gtex") or 600) * 100
        rating = _safe_int(item.get("rating"), 0) or _safe_int(
            item.get("tactical_flexibility") or item.get("youth_development") or 72
        )

        if key in by_key:
            profile = by_key[key]
            meta = dict(profile.metadata_json or {})
            if str(meta.get("employment_status") or "unemployed") == "unemployed" and profile.staff_type != canon_role:
                profile.staff_type = canon_role
                profile.rating = rating
                profile.salary_minor = salary_minor
                style = str(meta.get("style") or item.get("style") or "Balanced")
                profile.skills_json = [canon_role, style]
                meta["preferred_roles"] = [canon_role, raw_role]
                if item.get("source_job"):
                    meta["source_job"] = item.get("source_job")
                profile.metadata_json = meta
            continue

        meta = {
            "staff_id": staff_id,
            "employment_status": "unemployed",
            "current_club_id": None,
            "min_prestige": _safe_int(item.get("min_prestige"), 15),
            "temperament": str(item.get("temperament") or "pragmatic"),
            "style": str(item.get("style") or "Balanced"),
            "ambition": _safe_int(item.get("ambition"), 10),
            "loyalty": _safe_int(item.get("loyalty"), 12),
            "experience_years": max(3, _safe_int(item.get("min_prestige"), 15) // 5),
            "career_history": [],
            "previous_relationships": {},
            "preferred_roles": [canon_role, raw_role],
            "portrait_url": item.get("portrait_url"),
            "gender": item.get("gender"),
            "age": item.get("age"),
            "nation": item.get("nation"),
            "origin": item.get("origin") or "catalog",
        }

        # Add starter historical background if defined
        if "reputation" in item:
            meta["reputation"] = _safe_int(item["reputation"], 50)
        else:
            meta["reputation"] = min(95, max(30, rating))

        profile = ClubStaffProfile(
            market_key=key,
            display_name=str(item.get("name") or "Executive Professional"),
            staff_type=canon_role,
            rarity=str(item.get("rarity") or ("elite" if rating >= 82 else "standard")),
            rating=rating,
            salary_minor=salary_minor,
            skills_json=[canon_role, meta["style"]],
            active=True,
            metadata_json=meta,
        )
        session.add(profile)
        created.append(profile)
        by_key[key] = profile

    if created:
        session.flush()
    from app.owner_console.staff_supply import replenish_scarce_staff

    replenish_scarce_staff(session)
    return list(session.scalars(select(ClubStaffProfile)).all())


def get_club_vacancies(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """
    Scans the club's leadership roster and identifies unfilled executive roles.
    Returns status of all core positions (appointed vs vacant) and matching free agents.
    """
    from app.owner_console import service

    state = service.require_state(session, club_id, user_id)
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    core_roles = [
        ROLE_FIRST_TEAM_MANAGER,
        ROLE_GENERAL_MANAGER,
        ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        "chief_scout",
        "medical_director",
    ]

    vacancies = []
    filled = []

    for r in core_roles:
        staff_data = exec_staff.get(r)
        if not staff_data and r == ROLE_FIRST_TEAM_MANAGER:
            staff_data = state.manager_json

        is_appointed = bool(
            staff_data and isinstance(staff_data, dict) and staff_data.get("name") and not staff_data.get("is_default")
        )

        display_label = ROLE_DISPLAY_LABELS.get(r, r.replace("_", " ").title())

        if is_appointed:
            filled.append(
                {
                    "role_key": r,
                    "role_label": display_label,
                    "incumbent_name": staff_data.get("name"),
                    "staff_id": staff_data.get("id") or staff_data.get("staff_id"),
                    "appointed_at": staff_data.get("appointed_at"),
                    "salary_gtex": _safe_int(staff_data.get("salary") or staff_data.get("salary_gtex") or 600),
                    "mood": _safe_int(staff_data.get("mood"), 75),
                }
            )
        else:
            vacancies.append(
                {
                    "role_key": r,
                    "role_label": display_label,
                    "is_urgent": r == ROLE_FIRST_TEAM_MANAGER,
                    "provisional_name": (
                        staff_data.get("name") if isinstance(staff_data, dict) else "Provisional Caretaker"
                    ),
                    "recommended_min_rating": max(50, state.prestige),
                }
            )

    return {
        "club_id": club_id,
        "club_prestige": state.prestige,
        "vacancies_count": len(vacancies),
        "vacancies": vacancies,
        "filled_roles": filled,
    }


def list_staff_market_candidates(
    session: Session,
    user_id: str,
    club_id: str,
    role: str | None = None,
    employment_status: str | None = "unemployed",
    limit: int = 50,
    offset: int = 0,
    wage_max: int | None = None,
    style: str | None = None,
    temperament: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """
    Queries the global professional staff employment market.
    Enriches candidates with club prestige suitability, wage expectation, and past tenures.
    """
    from app.owner_console import service

    state = service.require_state(session, club_id, user_id)
    ensure_staff_market_profiles(session)

    stmt = select(ClubStaffProfile).where(ClubStaffProfile.active.is_(True))

    if role:
        canon_role = normalise_staff_role(role)
        stmt = stmt.where(
            or_(
                ClubStaffProfile.staff_type == canon_role,
                ClubStaffProfile.staff_type == role,
            )
        )

    profiles = session.scalars(stmt.order_by(ClubStaffProfile.rating.desc())).all()
    style_query = (style or "").strip().lower()
    temperament_query = (temperament or "").strip().lower()
    search_query = (search or "").strip().lower()

    candidates = []
    for p in profiles:
        meta = dict(p.metadata_json or {})
        status = meta.get("employment_status", "unemployed")

        if employment_status and status != employment_status and employment_status != "all":
            continue

        annual_salary_gtex = p.salary_minor // 100 if p.salary_minor else 600
        if wage_max is not None and annual_salary_gtex > int(wage_max):
            continue
        candidate_style = str(meta.get("style") or "")
        candidate_temperament = str(meta.get("temperament") or "")
        if style_query and style_query not in candidate_style.lower():
            continue
        if temperament_query and temperament_query not in candidate_temperament.lower():
            continue
        if (
            search_query
            and search_query
            not in " ".join([p.display_name or "", candidate_style, candidate_temperament, p.staff_type or ""]).lower()
        ):
            continue

        min_p = _safe_int(meta.get("min_prestige"), 15)
        can_attract = state.prestige >= min_p
        prestige_delta = state.prestige - min_p

        # Suitability indicator
        if can_attract and prestige_delta >= 10:
            interest_level = "very_high"
        elif can_attract:
            interest_level = "interested"
        elif prestige_delta >= -15:
            interest_level = "requires_premium"  # Can be convinced with wage premium
        else:
            interest_level = "unlikely"

        candidates.append(
            {
                "profile_id": p.id,
                "market_key": p.market_key,
                "staff_id": meta.get("staff_id") or p.market_key.replace("staff:", ""),
                "name": p.display_name,
                "role_key": p.staff_type,
                "role_label": ROLE_DISPLAY_LABELS.get(p.staff_type, p.staff_type.replace("_", " ").title()),
                "rating": p.rating,
                "rarity": p.rarity,
                "skills": p.skills_json or [],
                "reputation": _safe_int(meta.get("reputation"), 60),
                "experience_years": _safe_int(meta.get("experience_years"), 5),
                "temperament": meta.get("temperament", "balanced"),
                "style": meta.get("style", "Balanced"),
                "ambition": _safe_int(meta.get("ambition"), 10),
                "loyalty": _safe_int(meta.get("loyalty"), 12),
                "expected_salary_gtex": annual_salary_gtex,
                "min_prestige": min_p,
                "employment_status": status,
                "current_club_id": meta.get("current_club_id"),
                "can_attract": can_attract,
                "interest_level": interest_level,
                "career_history": meta.get("career_history", []),
                "supply_origin": meta.get("origin") or "catalog",
                "portrait_url": meta.get("portrait_url"),
                "gender": meta.get("gender"),
                "age": meta.get("age"),
                "nation": meta.get("nation"),
            }
        )

    start = max(0, int(offset or 0))
    page_size = max(1, min(100, int(limit or 50)))
    page = candidates[start : start + page_size]
    from app.owner_console.staff_supply import general_manager_supply

    return {
        "club_id": club_id,
        "club_prestige": state.prestige,
        "total_count": len(candidates),
        "candidates": page,
        "supply": general_manager_supply(session),
    }


def evaluate_staff_contract_offer(
    club_prestige: int,
    candidate_profile: ClubStaffProfile,
    offered_salary_gtex: int,
    contract_years: int,
    marquee_premium: bool = False,
    past_sentiment: str | None = None,
    showroom_wage_bonus_pct: float = 0.0,
) -> dict[str, Any]:
    """
    Authoritative AI evaluation of a club contract offer by a professional candidate.
    Evaluates prestige threshold, salary competitiveness, ambition, loyalty, and
    Prestige Showroom operational perks (e.g., private jet charter bonus).
    """
    meta = dict(candidate_profile.metadata_json or {})
    min_prestige = _safe_int(meta.get("min_prestige"), 15)
    expected_salary = candidate_profile.salary_minor // 100 if candidate_profile.salary_minor else 600
    ambition = _safe_int(meta.get("ambition"), 10)
    loyalty = _safe_int(meta.get("loyalty"), 12)
    name = candidate_profile.display_name

    # Loyal candidates value multi-year contract stability (3+ years)
    loyalty_stability_bonus = 0.05 if (contract_years >= 3 and loyalty >= 14) else 0.0
    showroom_bonus_ratio = max(0.0, float(showroom_wage_bonus_pct or 0.0) / 100.0)
    prestige_perk_offset = 4 if showroom_wage_bonus_pct >= 6.0 else (2 if showroom_wage_bonus_pct >= 3.0 else 0)

    # 1. Strained prior relationship check
    if past_sentiment == "hostile":
        return {
            "accepted": False,
            "outcome": "rejected",
            "reason": "strained_prior_relationship",
            "message": f"{name} declined negotiations citing previous unresolved conflict with club leadership.",
        }

    # 2. Club Prestige Check
    prestige_gap = min_prestige - (club_prestige + prestige_perk_offset)
    if prestige_gap > 0 and not marquee_premium:
        # Candidate requires higher prestige unless compensated with a wage premium
        wage_ratio = (offered_salary_gtex / max(1, expected_salary)) + showroom_bonus_ratio
        if wage_ratio < 1.4:
            return {
                "accepted": False,
                "outcome": "rejected",
                "reason": "insufficient_prestige",
                "message": f"{name} requires at least {min_prestige} club prestige (current: {club_prestige}). A 40%+ marquee wage premium is required to consider this appointment.",
                "required_salary_gtex": int(expected_salary * 1.4),
            }

    # 3. Wage Competitiveness Check
    wage_ratio = (offered_salary_gtex / max(1, expected_salary)) + loyalty_stability_bonus + showroom_bonus_ratio
    if wage_ratio < 0.75:
        return {
            "accepted": False,
            "outcome": "rejected",
            "reason": "insufficient_wage",
            "message": f"Offer rejected. The proposed salary of ₦{offered_salary_gtex:,} GTEX is substantially below {name}'s market expectation of ₦{expected_salary:,} GTEX.",
            "counter_salary_gtex": expected_salary,
        }
    elif wage_ratio < 0.95:
        # Close enough for a counter-offer
        counter_wage = int(expected_salary * 1.05) if ambition >= 14 else expected_salary
        return {
            "accepted": False,
            "outcome": "counter_offer",
            "reason": "salary_below_market",
            "message": f"{name} is intrigued by the project but requests ₦{counter_wage:,} GTEX per annum.",
            "counter_salary_gtex": counter_wage,
            "counter_years": contract_years,
        }

    # 4. Contract Duration Check
    if contract_years < 1:
        return {
            "accepted": False,
            "outcome": "rejected",
            "reason": "duration_too_short",
            "message": f"{name} requires at least a 1-year binding contract commitment.",
        }

    # Offer Accepted!
    return {
        "accepted": True,
        "outcome": "accepted",
        "message": f"{name} has accepted the offer and agreed terms as your new {candidate_profile.staff_type}!",
        "agreed_salary_gtex": offered_salary_gtex,
        "contract_years": contract_years,
        "showroom_wage_bonus_pct": round(float(showroom_wage_bonus_pct or 0.0), 1),
    }


def hire_staff_from_market(
    session: Session,
    user_id: str,
    club_id: str,
    profile_id: str,
    role: str | None = None,
    offered_salary_gtex: int | None = None,
    contract_years: int = 3,
    marquee_wage_premium: bool = False,
    pitch_note: str | None = None,
) -> dict[str, Any]:
    """
    Submits a contract offer to hire a candidate from the professional employment market.
    If accepted:
    - Ratifies ClubStaffContract and ClubStaffAssignment.
    - Synchronizes facilities_json['_executive_staff'] and manager_json.
    - Updates ClubStaffProfile with employment_status='employed' and appends career history.
    - Settles upfront contract fees via club ledger.
    """
    from app.owner_console import living_cinema_showroom, service

    state = service.require_state(session, club_id, user_id)
    profile = session.get(ClubStaffProfile, profile_id)
    if profile is None:
        raise service.OwnerError("staff_profile_not_found", 404, f"Staff profile {profile_id} not found.")

    target_role = normalise_staff_role(role or profile.staff_type)
    expected_salary = profile.salary_minor // 100 if profile.salary_minor else 600
    salary = int(offered_salary_gtex or expected_salary)
    years = max(1, min(int(contract_years or 3), 5))

    meta = dict(profile.metadata_json or {})
    past_sentiment = meta.get("previous_relationships", {}).get(club_id, {}).get("sentiment")
    perks = living_cinema_showroom.compute_club_showroom_perks(session, club_id)
    showroom_bonus_pct = float(perks.get("recruitment_wage_bonus_pct") or 0.0)

    # Evaluate AI decision
    evaluation = evaluate_staff_contract_offer(
        club_prestige=state.prestige,
        candidate_profile=profile,
        offered_salary_gtex=salary,
        contract_years=years,
        marquee_premium=marquee_wage_premium,
        past_sentiment=past_sentiment,
        showroom_wage_bonus_pct=showroom_bonus_pct,
    )

    if not evaluation["accepted"]:
        return {
            "status": evaluation["outcome"],
            "success": False,
            "reason": evaluation.get("reason"),
            "message": evaluation.get("message"),
            "counter_salary_gtex": evaluation.get("counter_salary_gtex"),
            "required_salary_gtex": evaluation.get("required_salary_gtex"),
            "cinematic_event": None,
        }

    # Total upfront contract fee or annual budget
    total_contract_fee = salary * years if years != 3 else max(salary, int(expected_salary * 1.5))
    if marquee_wage_premium:
        total_contract_fee = int(total_contract_fee * 1.4)

    # Financial settlement is a hard precondition for an appointment. Never create
    # a contract or change employment state when the club cannot fund the upfront fee.
    club_acct = ledger.club_account(club_id)
    club_bal = ledger.balance(session, club_acct, ledger.GTEX)
    logger.info("Executing staff appointment for club %s; ledger balance: %s GTEX", club_id, club_bal)
    if club_bal < total_contract_fee:
        return {
            "status": "rejected",
            "success": False,
            "reason": "insufficient_funds",
            "message": (
                f"Appointment not completed: the club has {club_bal} GTEX available, "
                f"but the upfront contract fee is {total_contract_fee} GTEX."
            ),
            "required_salary_gtex": salary,
        }

    # The ledger must successfully settle before any contract or assignment is written.
    ledger.record(
        session,
        event_type="staff_hire",
        source=club_acct,
        destination=ledger.WORLD_CLUBS,
        currency=ledger.GTEX,
        gross=total_contract_fee,
        club_id=club_id,
        user_id=user_id,
        related_type="staff",
        related_id=profile.id,
        memo=f"Upfront contract salary for {profile.display_name} ({ROLE_DISPLAY_LABELS.get(target_role, target_role)})",
        check_funds=True,
    )

    now = datetime.now(timezone.utc)

    # 1. Terminate any existing active contract/assignment for this role at this club
    existing_assignment = session.scalar(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == club_id,
            ClubStaffAssignment.role_key == target_role,
            ClubStaffAssignment.active.is_(True),
        )
    )
    if existing_assignment:
        existing_assignment.active = False
        old_contract = session.get(ClubStaffContract, existing_assignment.staff_contract_id)
        if old_contract and old_contract.status == "active":
            old_contract.status = "terminated"
            old_contract.terminated_at = now

    # 2. Create authoritative ClubStaffContract
    new_contract = ClubStaffContract(
        club_id=club_id,
        staff_profile_id=profile.id,
        status="active",
        salary_minor=salary * 100,
        commission_bps=profile.commission_bps or 0,
        duration_days=years * 365,
        role_scope=target_role,
        exclusive=True,
        started_at=now,
        ends_at=now + timedelta(days=years * 365),
        accepted_at=now,
        metadata_json={
            "source": "living_staff_market_stage4",
            "upfront_fee_gtex": total_contract_fee,
            "marquee_wage_premium": marquee_wage_premium,
            "pitch_note": pitch_note,
        },
    )
    session.add(new_contract)
    session.flush()

    # 3. Create authoritative ClubStaffAssignment
    new_assignment = ClubStaffAssignment(
        club_id=club_id,
        staff_contract_id=new_contract.id,
        role_key=target_role,
        active=True,
        metadata_json={"appointed_by": user_id, "world_day": state.world_day},
    )
    session.add(new_assignment)

    # 4. Synchronize facilities_json and manager_json
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    appointed_dict = {
        "id": meta.get("staff_id") or profile.id,
        "staff_id": meta.get("staff_id") or profile.id,
        "profile_id": profile.id,
        "contract_id": new_contract.id,
        "name": profile.display_name,
        "role": target_role,
        "role_label": ROLE_DISPLAY_LABELS.get(target_role, target_role.replace("_", " ").title()),
        "rating": profile.rating,
        "style": meta.get("style", "Balanced"),
        "temperament": meta.get("temperament", "pragmatic"),
        "ambition": meta.get("ambition", 10),
        "loyalty": meta.get("loyalty", 12),
        "salary": salary,
        "salary_gtex": salary,
        "appointed_at": now.isoformat(),
        "mood": 85,
        "contract_years": years,
        "is_appointed": True,
    }
    exec_staff[target_role] = appointed_dict
    facs["_executive_staff"] = exec_staff
    state.facilities_json = facs

    if target_role == ROLE_FIRST_TEAM_MANAGER:
        state.manager_json = engine.manager_profile(appointed_dict)
        service._morale_shift(session, club_id, 4)

    # 5. Update Profile Career History and Employment Status
    career_history = list(meta.get("career_history") or [])
    career_entry = {
        "club_id": club_id,
        "club_name": state.club_name or "Club",
        "role": target_role,
        "started_at": now.strftime("%Y-%m-%d"),
        "contract_years": years,
        "salary_gtex": salary,
        "status": "ongoing",
    }
    career_history.append(career_entry)

    meta["employment_status"] = "employed"
    meta["current_club_id"] = club_id
    meta["career_history"] = career_history
    profile.metadata_json = meta
    session.flush()

    from app.owner_console import living_cinema_showroom

    cinematic_event = living_cinema_showroom.record_staff_arrival_cinematic(
        session=session,
        user_id=user_id,
        club_id=club_id,
        appointed_staff=appointed_dict,
        contract_id=new_contract.id,
        total_contract_fee=total_contract_fee,
    )

    return {
        "status": "accepted",
        "success": True,
        "message": evaluation["message"],
        "contract_id": new_contract.id,
        "assignment_id": new_assignment.id,
        "appointed_staff": appointed_dict,
        "total_contract_fee": total_contract_fee,
        "cinematic_event": cinematic_event,
    }


def dismiss_staff_with_free_agency(
    session: Session,
    user_id: str,
    club_id: str,
    role: str,
    reason: str = "tactical_restructure",
) -> dict[str, Any]:
    """
    Authoritatively dismisses a staff member from the club.
    Guarantees:
    1. Pays severance compensation from club ledger.
    2. Terminates ClubStaffContract and deactivates ClubStaffAssignment.
    3. Removes from facilities_json and resets manager to caretaker if applicable.
    4. PRESERVES ClubStaffProfile identity and career history.
    5. Sets employment_status='unemployed', immediately re-entering the global free-agent market.
    """
    from app.owner_console import service

    state = service.require_state(session, club_id, user_id)
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    current = exec_staff.get(role)
    if not current and role == ROLE_FIRST_TEAM_MANAGER:
        current = state.manager_json

    if not current or current.get("is_default"):
        raise service.OwnerError("no_appointed_staff", 400, f"No appointed staff member found for role '{role}'.")

    staff_name = str(current.get("name") or "Staff Member")
    loyalty = _safe_int(current.get("loyalty"), 10)
    salary_gtex = _safe_int(current.get("salary") or current.get("salary_gtex"), 600)

    # Severance compensation: base fee + remaining contract fraction
    severance_compensation = 1_500 + loyalty * 80 + (salary_gtex // 2)

    try:
        ledger.record(
            session,
            event_type="staff_compensation",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_CLUBS,
            currency=ledger.GTEX,
            gross=severance_compensation,
            club_id=club_id,
            user_id=user_id,
            related_type="staff",
            related_id=current.get("id") or current.get("staff_id"),
            memo=f"Severance compensation for dismissed {role}: {staff_name}",
            check_funds=False,
        )
    except Exception as exc:
        logger.warning("Staff severance ledger record bypassed: %s", exc)

    now = datetime.now(timezone.utc)

    # 1. Terminate contract & assignment
    contract_id = current.get("contract_id")
    if contract_id:
        contract = session.get(ClubStaffContract, contract_id)
        if contract:
            contract.status = "terminated"
            contract.terminated_at = now

    for assignment in session.scalars(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == club_id,
            ClubStaffAssignment.role_key == role,
            ClubStaffAssignment.active.is_(True),
        )
    ):
        assignment.active = False

    # 2. Update facilities_json and manager_json
    if role in exec_staff:
        del exec_staff[role]
    facs["_executive_staff"] = exec_staff
    state.facilities_json = facs

    if role == ROLE_FIRST_TEAM_MANAGER:
        state.manager_json = engine.manager_profile(engine.DEFAULT_MANAGER)
        service._morale_shift(session, club_id, -5)

    # 3. Locate ClubStaffProfile and update career history & free-agency status
    profile_id = current.get("profile_id")
    profile = None
    if profile_id:
        profile = session.get(ClubStaffProfile, profile_id)
    if not profile:
        market_key = f"staff:{current.get('id') or current.get('staff_id')}"
        profile = session.scalar(select(ClubStaffProfile).where(ClubStaffProfile.market_key == market_key))

    if profile:
        meta = dict(profile.metadata_json or {})
        career_history = list(meta.get("career_history") or [])

        # Update last entry or add exit record
        if career_history and career_history[-1].get("status") == "ongoing":
            career_history[-1]["status"] = "dismissed"
            career_history[-1]["ended_at"] = now.strftime("%Y-%m-%d")
            career_history[-1]["reason_for_leaving"] = reason
            career_history[-1]["severance_paid"] = severance_compensation
        else:
            career_history.append(
                {
                    "club_id": club_id,
                    "club_name": state.club_name or "Club",
                    "role": role,
                    "ended_at": now.strftime("%Y-%m-%d"),
                    "status": "dismissed",
                    "reason_for_leaving": reason,
                    "severance_paid": severance_compensation,
                }
            )

        meta["employment_status"] = "unemployed"
        meta["current_club_id"] = None
        meta["career_history"] = career_history
        meta["reputation"] = max(25, _safe_int(meta.get("reputation"), 60) - 4)

        # Store prior sentiment memory
        prev_rels = dict(meta.get("previous_relationships") or {})
        prev_rels[club_id] = {
            "sentiment": "cool",
            "dismissed_at": now.isoformat(),
            "reason": reason,
        }
        meta["previous_relationships"] = prev_rels
        profile.metadata_json = meta
        session.flush()

    return {
        "status": "dismissed",
        "success": True,
        "role": role,
        "staff_name": staff_name,
        "severance_paid": severance_compensation,
        "entered_free_agency": True,
        "profile_id": profile.id if profile else None,
    }


def get_candidate_career_dossier(
    session: Session,
    user_id: str,
    club_id: str,
    profile_id: str,
) -> dict[str, Any]:
    """
    Retrieves full biographical, tactical, and career history dossier for a staff professional.
    """
    from app.owner_console import service

    state = service.require_state(session, club_id, user_id)
    profile = session.get(ClubStaffProfile, profile_id)
    if not profile:
        raise service.OwnerError("staff_profile_not_found", 404, f"Candidate profile {profile_id} not found.")

    meta = dict(profile.metadata_json or {})
    min_p = _safe_int(meta.get("min_prestige"), 15)
    salary_gtex = profile.salary_minor // 100 if profile.salary_minor else 600

    evaluation = evaluate_staff_contract_offer(
        club_prestige=state.prestige,
        candidate_profile=profile,
        offered_salary_gtex=salary_gtex,
        contract_years=3,
    )

    return {
        "profile_id": profile.id,
        "market_key": profile.market_key,
        "name": profile.display_name,
        "role_key": profile.staff_type,
        "role_label": ROLE_DISPLAY_LABELS.get(profile.staff_type, profile.staff_type.replace("_", " ").title()),
        "rating": profile.rating,
        "rarity": profile.rarity,
        "skills": profile.skills_json or [],
        "reputation": _safe_int(meta.get("reputation"), 60),
        "experience_years": _safe_int(meta.get("experience_years"), 5),
        "temperament": meta.get("temperament", "pragmatic"),
        "style": meta.get("style", "Balanced"),
        "ambition": _safe_int(meta.get("ambition"), 10),
        "loyalty": _safe_int(meta.get("loyalty"), 12),
        "expected_salary_gtex": salary_gtex,
        "min_prestige": min_p,
        "employment_status": meta.get("employment_status", "unemployed"),
        "current_club_id": meta.get("current_club_id"),
        "career_history": meta.get("career_history", []),
        "club_prestige": state.prestige,
        "interest_preview": evaluation["outcome"],
        "interest_message": evaluation["message"],
    }


def evaluate_external_poaching_approach(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    role: str = ROLE_FIRST_TEAM_MANAGER,
    rival_club_name: str = "Continental Sporting FC",
) -> dict[str, Any]:
    """
    Simulates a rival club poaching approach for an employed high-performing or low-loyalty
    staff member, presenting the Owner with a Retention vs. Buyout Release negotiation.
    """
    from app.owner_console import living_club_world, service
    from app.owner_console.models import OwnerClubEvent, OwnerClubRelationship

    state = service.require_state(session, club_id, user_id)
    target_role = normalise_staff_role(role)
    roster = living_club_world.resolve_club_staff_roster(state)
    slot = roster.get(target_role)
    if not slot or not slot.get("is_appointed"):
        raise service.OwnerError("role_vacant", 400, f"Cannot evaluate poaching approach: {target_role} is vacant.")

    staff_name = str(slot.get("name") or "Appointed Executive")
    role_label = ROLE_DISPLAY_LABELS.get(target_role, target_role.replace("_", " ").title())
    current_salary = max(600, int(slot.get("salary_gtex") or (state.manager_json or {}).get("salary_gtex") or 1200))
    rival_salary = int(round(current_salary * 1.35))
    buyout_clause_gtex = max(1800, int(round(current_salary * 2.5)))

    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.participant_b_id == target_role,
        )
    )
    loyalty_val = int(rel.loyalty if rel else 58)
    trust_val = int(rel.trust if rel else 60)

    ev = OwnerClubEvent(
        club_id=club_id,
        category="staff_market",
        event_type="external_staff_poaching_approach",
        severity="high",
        status="open",
        source_type="rival_club_poaching",
        source_id=f"{target_role}:{state.world_day or 1}",
        title=f"Rival Poaching Approach: {rival_club_name} Target {staff_name}",
        description=(
            f"{rival_club_name} have formally approached {staff_name} ({role_label}) with a "
            f"{rival_salary:,} GTEX/yr contract and a {buyout_clause_gtex:,} GTEX buyout clause offer."
        ),
        participants_json=[
            {"role": target_role, "name": staff_name, "loyalty": loyalty_val, "trust": trust_val},
            {"role": "rival_club", "name": rival_club_name},
        ],
        world_day=state.world_day or 1,
        actions_json=[
            {
                "choice": "match_rival_offer",
                "label": f"Match Wage ({rival_salary:,} GTEX/yr) & Pay Loyalty Bonus",
            },
            {
                "choice": "promise_facility_upgrade",
                "label": "Reaffirm Sporting Project & Facility Investment",
            },
            {
                "choice": "accept_buyout_release",
                "label": f"Accept {buyout_clause_gtex:,} GTEX Buyout & Release to {rival_club_name}",
            },
        ],
        consequences_json={
            "role": target_role,
            "role_label": role_label,
            "staff_name": staff_name,
            "rival_club_name": rival_club_name,
            "current_salary_gtex": current_salary,
            "rival_offered_salary_gtex": rival_salary,
            "buyout_clause_gtex": buyout_clause_gtex,
            "loyalty_before": loyalty_val,
            "trust_before": trust_val,
        },
    )
    session.add(ev)
    session.flush()

    return {
        "event_id": ev.id,
        "club_id": club_id,
        "status": ev.status,
        "role": target_role,
        "role_label": role_label,
        "staff_name": staff_name,
        "rival_club_name": rival_club_name,
        "current_salary_gtex": current_salary,
        "rival_offered_salary_gtex": rival_salary,
        "buyout_clause_gtex": buyout_clause_gtex,
        "options": ev.actions_json,
    }


def resolve_external_poaching_approach(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    event_id: str,
    choice: str,
) -> dict[str, Any]:
    """
    Resolves an external rival poaching approach:
    - match_rival_offer: Debits retention loyalty bonus, upgrades salary, boosts loyalty/trust.
    - promise_facility_upgrade: Retains staff via project alignment (requires trust >= 35).
    - accept_buyout_release: Credits buyout_clause_gtex to club treasury, releases staff to rival club,
      vacates the local role, and preserves career history.
    """
    from decimal import Decimal
    from sqlalchemy.orm.attributes import flag_modified
    from app.owner_console import living_club_world, service
    from app.owner_console.models import OwnerClubEvent

    state = service.require_state(session, club_id, user_id)
    ev = session.get(OwnerClubEvent, event_id)
    if ev is None or ev.club_id != club_id or ev.event_type != "external_staff_poaching_approach":
        raise service.OwnerError("poaching_event_not_found", 404, f"Poaching event {event_id} not found.")

    if ev.status == "resolved":
        return {
            "event_id": ev.id,
            "status": "resolved",
            "already_resolved": True,
            "resolution": ev.consequences_json,
        }

    valid_choices = {"match_rival_offer", "promise_facility_upgrade", "accept_buyout_release"}
    if choice not in valid_choices:
        raise service.OwnerError("invalid_poaching_choice", 400, f"Invalid choice '{choice}'.")

    meta = dict(ev.consequences_json or {})
    target_role = str(meta.get("role") or ROLE_FIRST_TEAM_MANAGER)
    staff_name = str(meta.get("staff_name") or "Appointed Executive")
    rival_club = str(meta.get("rival_club_name") or "Continental Sporting FC")
    current_salary = int(meta.get("current_salary_gtex") or 1000)
    rival_salary = int(meta.get("rival_offered_salary_gtex") or int(current_salary * 1.35))
    buyout_gtex = int(meta.get("buyout_clause_gtex") or 2500)

    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    if choice == "match_rival_offer":
        retention_bonus = max(250, int(round(current_salary * 0.4)))
        ledger.record(
            session,
            event_type="staff_retention_bonus",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_CLUBS,
            currency=ledger.GTEX,
            gross=Decimal(str(retention_bonus)),
            club_id=club_id,
            user_id=user_id,
            related_type="staff_poaching",
            related_id=ev.id,
            memo=f"Retention contract bonus for {staff_name} to fend off {rival_club}",
            check_funds=True,
        )
        if target_role in exec_staff and isinstance(exec_staff[target_role], dict):
            exec_staff[target_role]["salary_gtex"] = rival_salary
            facs["_executive_staff"] = exec_staff
            state.facilities_json = facs
            flag_modified(state, "facilities_json")
        if target_role == ROLE_FIRST_TEAM_MANAGER and isinstance(state.manager_json, dict):
            mgr = dict(state.manager_json)
            mgr["salary_gtex"] = rival_salary
            state.manager_json = mgr
            flag_modified(state, "manager_json")

        rel = living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id=f"owner:{user_id}",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id=target_role,
            part_b_name=staff_name,
            delta_loyalty=10,
            delta_trust=8,
            delta_tension=-6,
            reason=f"Matched rival offer from {rival_club} ({rival_salary:,} GTEX/yr)",
        )
        outcome_payload = {
            "choice": choice,
            "retained": True,
            "new_salary_gtex": rival_salary,
            "retention_bonus_paid_gtex": retention_bonus,
            "buyout_credited_gtex": 0,
            "loyalty_after": rel.loyalty,
            "trust_after": rel.trust,
        }

    elif choice == "promise_facility_upgrade":
        rel = living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id=f"owner:{user_id}",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id=target_role,
            part_b_name=staff_name,
            delta_alignment=8,
            delta_influence=6,
            delta_respect=5,
            delta_tension=-4,
            reason=f"Convinced {staff_name} to reject {rival_club} via sporting project commitment",
        )
        outcome_payload = {
            "choice": choice,
            "retained": True,
            "new_salary_gtex": current_salary,
            "retention_bonus_paid_gtex": 0,
            "buyout_credited_gtex": 0,
            "alignment_after": rel.alignment,
            "influence_after": rel.influence,
        }

    else:
        # accept_buyout_release -> Credit buyout clause to club treasury and vacate slot
        ledger.record(
            session,
            event_type="staff_buyout_compensation",
            source=ledger.WORLD_CLUBS,
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=Decimal(str(buyout_gtex)),
            club_id=club_id,
            user_id=user_id,
            related_type="staff_poaching",
            related_id=ev.id,
            memo=f"Buyout clause compensation from {rival_club} for {staff_name}",
            check_funds=False,
        )

        # Terminate active assignment/contract at this club
        active_assign = session.scalar(
            select(ClubStaffAssignment).where(
                ClubStaffAssignment.club_id == club_id,
                ClubStaffAssignment.role_key == target_role,
                ClubStaffAssignment.active.is_(True),
            )
        )
        if active_assign:
            active_assign.active = False
            contract = session.get(ClubStaffContract, active_assign.staff_contract_id)
            if contract:
                contract.status = "terminated"
                contract.terminated_at = datetime.now(timezone.utc)
                profile = session.get(ClubStaffProfile, contract.staff_profile_id)
                if profile:
                    p_meta = dict(profile.metadata_json or {})
                    hist = list(p_meta.get("career_history") or [])
                    hist.append(
                        {
                            "event": "poached_via_buyout",
                            "from_club_id": club_id,
                            "to_club_name": rival_club,
                            "role": target_role,
                            "buyout_clause_gtex": buyout_gtex,
                            "world_day": state.world_day or 1,
                        }
                    )
                    p_meta["career_history"] = hist
                    p_meta["employment_status"] = "employed"
                    p_meta["current_club_id"] = f"rival:{rival_club.lower().replace(' ', '_')}"
                    profile.metadata_json = p_meta
                    flag_modified(profile, "metadata_json")

        exec_staff.pop(target_role, None)
        facs["_executive_staff"] = exec_staff
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        if target_role == ROLE_FIRST_TEAM_MANAGER:
            state.manager_json = {"name": "", "is_vacant": True, "status": "vacant", "is_appointed": False}
            flag_modified(state, "manager_json")

        outcome_payload = {
            "choice": choice,
            "retained": False,
            "released_to": rival_club,
            "role_vacated": target_role,
            "buyout_credited_gtex": buyout_gtex,
            "treasury_balance_gtex": float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
        }

    meta.update(outcome_payload)
    ev.consequences_json = meta
    ev.status = "resolved"
    ev.resolved_at = datetime.now(timezone.utc)
    flag_modified(ev, "consequences_json")
    session.flush()

    return {
        "event_id": ev.id,
        "status": "resolved",
        "already_resolved": False,
        "resolution": outcome_payload,
    }
