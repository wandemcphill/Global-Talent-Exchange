from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.owner_console import engine, ledger, service
from app.owner_console.models import OwnerClubState, OwnerCompetition, OwnerCompetitionEntry, OwnerInboxItem, OwnerSponsorDeal, OwnerSquadPlayer
from app.owner_console.service import OwnerError
from app.owner_console.staff_models import OwnerClubStaff, OwnerDelegatedAction, OwnerDelegationPolicy, OwnerShowroomLink

ROLES = {"gm": "General Manager", "hoyd": "Head of Youth Development"}
MODES = ("owner_only", "approval", "auto")
TASKS: dict[str, dict[str, Any]] = {
    "contract_renewal": {"role": "hoyd", "label": "Academy contract renewals", "mode": "auto", "budget": 1000, "kind": "regen_breakthrough"},
    "youth_intake": {"role": "hoyd", "label": "Youth scouting intakes", "mode": "auto", "budget": 3000, "kind": None},
    "small_signing": {"role": "gm", "label": "Manager budget requests and small signings", "mode": "auto", "budget": 5000, "kind": "manager_request"},
    "transfer_bid": {"role": "gm", "label": "Bids for your players (sales above the cap stay with you)", "mode": "auto", "budget": 10000, "kind": "transfer_bid"},
}
RESERVED = {"player_sale_above_threshold": "Sales above the threshold", "manager_hire_fire": "Hiring or firing the manager", "capital_move": "Money moved between clubs"}
SALARY_MIN, SALARY_MAX = 300, 3000
MAX_SALARY_CYCLES = 7
INTAKE_EVERY_DAYS = 7
_ATTRS = {"gm": ("negotiation", "scouting", "financial_discipline", "judgement"), "hoyd": ("talent_identification", "coaching", "mentoring", "patience")}
_FIRST = ("Chidi", "Amara", "Kwame", "Femi", "Zainab", "Tunde", "Ngozi", "Ibrahim", "Ayo", "Kemi", "Musa", "Efosa")
_LAST = ("Okafor", "Mensah", "Adeyemi", "Bello", "Nwosu", "Diallo", "Eze", "Balogun", "Abubakar", "Osei")
_CONTINENTS = {
    "africa": "NG GH KE ZA EG MA SN CI CM DZ TN UG TZ ET ML BF RW ZM ZW AO",
    "europe": "GB EN ES DE FR IT PT NL BE CH AT SE NO DK PL IE SC WL HR RS TR GR UA CZ",
    "south_america": "BR AR UY CO CL PE EC PY VE BO",
    "north_america": "US CA MX CR JM PA HN",
    "asia": "JP KR CN IN SA AE QA IR IQ ID TH VN",
    "oceania": "AU NZ FJ",
}


def continent_for(country_code: str | None) -> str:
    code = (country_code or "").upper()
    return next((c for c, codes in _CONTINENTS.items() if code in codes.split()), "africa")


def salary_for(quality: int) -> Decimal:
    q = engine.clamp(quality, 1, 20)
    return ledger.D(SALARY_MIN + (SALARY_MAX - SALARY_MIN) * (q - 1) / 19)


def candidates(state: OwnerClubState, role: str, country_code: str | None) -> list[dict[str, Any]]:
    rng = engine.seeded("staff", role, state.club_id, state.world_day // 7)
    region = continent_for(country_code)
    out = []
    for i in range(3):
        quality = rng.randint(6, 18)
        out.append({
            "candidate_id": f"{role}-{state.world_day // 7}-{i}", "role": role, "name": f"{rng.choice(_FIRST)} {rng.choice(_LAST)}", "quality": quality,
            "attributes": {a: engine.clamp(quality + rng.randint(-3, 3), 1, 20) for a in _ATTRS[role]},
            "personality": {"risk_appetite": rng.choice(("cautious", "balanced", "bold")), "network": region},
            "salary_per_cycle": str(salary_for(quality)),
        })
    return out


def _owned(session: Session, user_id: str, club_id: str) -> OwnerClubState:
    return service.require_state(session, club_id, user_id)


def active_staff(session: Session, club_id: str) -> dict[str, OwnerClubStaff]:
    return {s.role: s for s in session.scalars(select(OwnerClubStaff).where(OwnerClubStaff.club_id == club_id, OwnerClubStaff.status == "active")).all()}


def policies(session: Session, club_id: str) -> dict[str, OwnerDelegationPolicy]:
    have = {p.task: p for p in session.scalars(select(OwnerDelegationPolicy).where(OwnerDelegationPolicy.club_id == club_id)).all()}
    for task, spec in TASKS.items():
        if task not in have:
            have[task] = OwnerDelegationPolicy(club_id=club_id, task=task, mode=spec["mode"], budget_cap=ledger.D(spec["budget"]), version=1)
            session.add(have[task])
    session.flush()
    return have


def hire(session: Session, user_id: str, club_id: str, candidate_id: str) -> OwnerClubStaff:
    state = _owned(session, user_id, club_id)
    profile = session.get(ClubProfile, club_id)
    role = candidate_id.split("-")[0]
    pick = next((c for c in candidates(state, role, profile.country_code if profile else None) if c["candidate_id"] == candidate_id), None) if role in ROLES else None
    if pick is None:
        raise OwnerError("candidate_not_available", 404)
    if role in active_staff(session, club_id):
        raise OwnerError("role_already_filled", 409)
    staff = OwnerClubStaff(club_id=club_id, owner_user_id=user_id, role=role, name=pick["name"], quality=pick["quality"], attributes_json=pick["attributes"], personality_json=pick["personality"], salary_per_cycle=ledger.D(pick["salary_per_cycle"]), last_paid_day=state.world_day)
    session.add(staff)
    session.flush()
    return staff


def release(session: Session, user_id: str, club_id: str, staff_id: str) -> OwnerClubStaff:
    _owned(session, user_id, club_id)
    staff = session.get(OwnerClubStaff, staff_id)
    if staff is None or staff.club_id != club_id or staff.status != "active":
        raise OwnerError("staff_not_found", 404)
    staff.status = "released"
    return staff


def set_policy(session: Session, user_id: str, club_id: str, task: str, mode: str, budget_cap: Decimal) -> OwnerDelegationPolicy:
    _owned(session, user_id, club_id)
    if task not in TASKS:
        raise OwnerError("reserved_or_unknown_task", 400)
    if mode not in MODES or budget_cap < 0:
        raise OwnerError("invalid_policy", 400)
    policy = policies(session, club_id)[task]
    policy.mode, policy.budget_cap, policy.version, policy.updated_at = mode, ledger.D(budget_cap), policy.version + 1, service.now()
    return policy


def pay_salaries(session: Session, state: OwnerClubState) -> int:
    paid = 0
    for staff in active_staff(session, state.club_id).values():
        cycles = min(state.world_day - staff.last_paid_day, MAX_SALARY_CYCLES)
        if cycles <= 0:
            continue
        try:
            with session.begin_nested():
                ledger.record(session, event_type="staff_salary", source=ledger.club_account(state.club_id), destination=ledger.WORLD_CLUBS, currency=ledger.GTEX, gross=staff.salary_per_cycle * cycles, club_id=state.club_id, user_id=state.owner_user_id, related_type="staff", related_id=f"{staff.id}:{state.world_day}", memo=f"{ROLES[staff.role]} {staff.name}: {cycles} cycle(s)")
            paid += 1
        except ledger.LedgerError:
            session.add(OwnerInboxItem(user_id=state.owner_user_id, club_id=state.club_id, kind="staff_unpaid", sender=staff.name, title=f"{staff.name} was not paid", what=f"Club cash could not cover {ledger.D(staff.salary_per_cycle * cycles)} GTX salary.", why="Unpaid staff stop acting on your behalf until the club can pay.", actions_json=[], payload_json={"staff_id": staff.id}, priority="high", is_decision=False))
        staff.last_paid_day = state.world_day
    return paid


def _judge(session: Session, staff: OwnerClubStaff, item: OwnerInboxItem, task: str) -> tuple[str, str, int]:
    p = item.payload_json or {}
    q = staff.quality
    confidence = int(engine.clamp(40 + q * 3, 0, 100))
    if task == "transfer_bid":
        target = session.get(OwnerSquadPlayer, p.get("player_id")) if p.get("player_id") else None
        value = Decimal(str(target.value_coin)) if target else Decimal(0)
        bid = Decimal(str(p.get("bid") or 0))
        bar = Decimal("1.05") + Decimal(20 - q) / Decimal(200)
        if value and bid >= value * bar:
            return "accept", f"Bid is {bid / value:.0%} of value; above my {bar:.0%} bar.", confidence
        return "reject", f"Bid {bid:,.0f} is under my {bar:.0%}-of-value bar{'' if value else ' (no valuation on file)'}.", confidence
    if task == "contract_renewal":
        return "new_contract", "High-ceiling academy player; securing him protects his value.", confidence
    return "approve", "Request fits squad depth and is inside the delegated budget.", confidence


def _cost(item: OwnerInboxItem, task: str) -> Decimal:
    p = item.payload_json or {}
    return ledger.D({"transfer_bid": p.get("bid"), "small_signing": p.get("budget"), "contract_renewal": 1000}.get(task) or 0)


def _report(session: Session, state: OwnerClubState, staff: OwnerClubStaff, kind: str, title: str, what: str, why: str, subject: str) -> None:
    session.add(OwnerInboxItem(user_id=state.owner_user_id, club_id=state.club_id, kind=kind, sender=f"{staff.name} ({ROLES[staff.role]})", title=title, what=what, why=why, actions_json=[], payload_json={"subject": subject, "staff_id": staff.id}, priority="normal", is_decision=False))


def _seen(session: Session, club_id: str, subject: str) -> bool:
    return session.scalar(select(OwnerDelegatedAction.id).where(OwnerDelegatedAction.club_id == club_id, OwnerDelegatedAction.subject == subject).limit(1)) is not None


def run_club(session: Session, state: OwnerClubState) -> dict[str, int]:
    pay_salaries(session, state)
    staff = active_staff(session, state.club_id)
    unpaid = {i.payload_json.get("staff_id") for i in session.scalars(select(OwnerInboxItem).where(OwnerInboxItem.club_id == state.club_id, OwnerInboxItem.kind == "staff_unpaid", OwnerInboxItem.status == "open")).all()}
    pol = policies(session, state.club_id)
    done = {"executed": 0, "recommended": 0}
    by_kind = {spec["kind"]: task for task, spec in TASKS.items() if spec["kind"]}
    items = session.scalars(select(OwnerInboxItem).where(OwnerInboxItem.club_id == state.club_id, OwnerInboxItem.status == "open", OwnerInboxItem.is_decision.is_(True), OwnerInboxItem.kind.in_(list(by_kind)))).all()
    for item in items:
        task = by_kind[item.kind]
        member, policy = staff.get(TASKS[task]["role"]), pol[task]
        if member is None or member.id in unpaid or policy.mode == "owner_only" or _seen(session, state.club_id, item.id):
            continue
        action, reason, confidence = _judge(session, member, item, task)
        auto = policy.mode == "auto" and _cost(item, task) <= policy.budget_cap and any(a.get("key") == action for a in item.actions_json or [])
        record = OwnerDelegatedAction(club_id=state.club_id, staff_id=member.id, task=task, subject=item.id, policy_version=policy.version, mode=policy.mode, recommendation=action, reason=reason, confidence=confidence, status="recommended")
        session.add(record)
        if auto:
            try:
                with session.begin_nested():
                    resolved = service.resolve_item(session, state.owner_user_id, item.id, action)
                record.status, record.outcome = "executed", resolved.outcome_text
                _report(session, state, member, "staff_action_report", f"{member.name} handled: {item.title}", resolved.outcome_text or action, f"{reason} Delegated under policy v{policy.version} ({TASKS[task]['label']}).", item.id)
                done["executed"] += 1
                continue
            except (OwnerError, KeyError, ledger.LedgerError) as exc:
                record.outcome = f"Could not act: {exc}"
        label = next((a.get("label") for a in item.actions_json or [] if a.get("key") == action), action)
        item.why = f"{item.why or ''} {ROLES[member.role]} recommends \"{label}\" ({confidence}% confident): {reason}".strip()
        _report(session, state, member, "staff_recommendation", f"{member.name} recommends: {label}", item.title, reason + ("" if policy.mode == "approval" else " Above the delegated cap, so it needs you."), item.id)
        done["recommended"] += 1
    hoyd, intake = staff.get("hoyd"), pol["youth_intake"]
    level = int((state.facilities_json or {}).get("academy", 1))
    subject = f"intake:{state.club_id}:{state.world_day // INTAKE_EVERY_DAYS}"
    if hoyd and hoyd.id not in unpaid and intake.mode == "auto" and 1500 * level <= intake.budget_cap and not _seen(session, state.club_id, subject):
        record = OwnerDelegatedAction(club_id=state.club_id, staff_id=hoyd.id, task="youth_intake", subject=subject, policy_version=intake.version, mode="auto", recommendation="intake", reason=f"Academy level {level} intake fits the {intake.budget_cap:,.0f} GTX budget.", confidence=int(40 + hoyd.quality * 3), status="recommended")
        session.add(record)
        try:
            with session.begin_nested():
                regens = service.academy_intake(session, state.owner_user_id, state.club_id)
            record.status, record.outcome = "executed", f"{len(regens)} prospects joined the academy."
            _report(session, state, hoyd, "staff_action_report", f"{hoyd.name} ran a scouting intake", record.outcome, record.reason, subject)
            done["executed"] += 1
        except OwnerError as exc:
            record.outcome = f"Could not act: {exc}"
    session.flush()
    return done


def sweep_user(session: Session, user_id: str) -> None:
    for state in service.user_states(session, user_id):
        if state.stage in ("competition", "active"):
            run_club(session, state)


def sweep_all(session: Session) -> int:
    clubs = {s.club_id for s in session.scalars(select(OwnerClubStaff).where(OwnerClubStaff.status == "active")).all()}
    for club_id in clubs:
        state = service.get_state(session, club_id)
        if state and state.stage in ("competition", "active"):
            run_club(session, state)
    return len(clubs)


def staff_dict(s: OwnerClubStaff) -> dict[str, Any]:
    return {"id": s.id, "role": s.role, "role_label": ROLES[s.role], "name": s.name, "quality": s.quality, "attributes": s.attributes_json, "personality": s.personality_json, "salary_per_cycle": str(s.salary_per_cycle), "hired_at": s.hired_at.isoformat() if s.hired_at else None}


def staff_overview(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    state = _owned(session, user_id, club_id)
    profile = session.get(ClubProfile, club_id)
    staff = active_staff(session, club_id)
    actions = session.scalars(select(OwnerDelegatedAction).where(OwnerDelegatedAction.club_id == club_id).order_by(OwnerDelegatedAction.created_at.desc()).limit(20)).all()
    return {
        "staff": [staff_dict(s) for s in staff.values()],
        "candidates": {role: candidates(state, role, profile.country_code if profile else None) for role in ROLES if role not in staff},
        "policies": [{"task": t, "label": TASKS[t]["label"], "role": TASKS[t]["role"], "mode": p.mode, "budget_cap": str(p.budget_cap), "version": p.version} for t, p in policies(session, club_id).items()],
        "reserved": [{"task": k, "label": v} for k, v in RESERVED.items()],
        "modes": list(MODES),
        "actions": [{"id": a.id, "task": a.task, "mode": a.mode, "policy_version": a.policy_version, "recommendation": a.recommendation, "reason": a.reason, "confidence": a.confidence, "status": a.status, "outcome": a.outcome, "created_at": a.created_at.isoformat() if a.created_at else None} for a in actions],
        "salary_range": [SALARY_MIN, SALARY_MAX],
    }


def share_code(session: Session, user_id: str, club_id: str) -> str:
    _owned(session, user_id, club_id)
    link = session.scalar(select(OwnerShowroomLink).where(OwnerShowroomLink.club_id == club_id))
    if link is None:
        link = OwnerShowroomLink(club_id=club_id, code=secrets.token_urlsafe(9)[:12])
        session.add(link)
        session.flush()
    return link.code


def showroom(session: Session, club_id: str) -> dict[str, Any]:
    state = service.get_state(session, club_id)
    if state is None:
        raise OwnerError("club_not_found", 404)
    profile = session.get(ClubProfile, club_id)
    finishes = session.execute(select(OwnerCompetitionEntry.final_position, OwnerCompetition.name, OwnerCompetition.tier, OwnerCompetitionEntry.created_at).join(OwnerCompetition, OwnerCompetition.id == OwnerCompetitionEntry.competition_id).where(OwnerCompetitionEntry.club_id == club_id, OwnerCompetitionEntry.final_position.is_not(None), OwnerCompetitionEntry.final_position <= 3)).all()
    deals = session.scalars(select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == club_id, OwnerSponsorDeal.status == "active")).all()
    players = sorted(service.squad(session, club_id), key=lambda p: p.rating, reverse=True)[:5]
    health = service.club_health(session, state)
    facilities = state.facilities_json or {}
    return {
        "club_name": state.club_name, "short_name": profile.short_name if profile else None, "city": profile.city_name if profile else None,
        "country_code": profile.country_code if profile else None, "primary_color": profile.primary_color if profile else "#10B981",
        "secondary_color": profile.secondary_color if profile else "#0F172A", "founded": profile.founded_at.year if profile and profile.founded_at else None,
        "crest_url": profile.crest_asset_ref if profile else None,
        "trophies": [{"competition": n, "tier": t, "position": pos, "year": c.year if c else None} for pos, n, t, c in sorted(finishes, key=lambda r: r[0])],
        "facilities": {k: int(facilities.get(k, 1)) for k in engine.FACILITY_KINDS},
        "sponsors": [{"sponsor": d.sponsor_name, "slot": d.slot} for d in deals],
        "top_players": [{"name": p.name, "position": p.position, "rating": p.rating, "age": p.age, "is_regen": p.is_regen} for p in players],
        "fans": health.get("fans"), "prestige": health.get("prestige"),
    }


PUBLIC_SHOWROOM_KEYS = ("club_name", "short_name", "city", "country_code", "primary_color", "secondary_color", "founded", "crest_url", "trophies")


def public_showroom(session: Session, club_id: str) -> dict[str, Any]:
    full = showroom(session, club_id)
    return {k: full[k] for k in PUBLIC_SHOWROOM_KEYS}
