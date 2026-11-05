from __future__ import annotations

from datetime import datetime, timezone
import math
import secrets
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.owner_console import competitions as comps, engine, ledger, money, prestige_campus_comms, service, storytelling
from app.owner_console.models import (
    OwnerBroadcastEvent,
    OwnerClubState,
    OwnerCompetitionEntry,
    OwnerInboxItem,
    OwnerMatch,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerError, require_state

DESTINATION_ORDER = (
    "executive_office",
    "managers_office",
    "general_managers_office",
    "academy_department",
    "medical_department",
    "finance_commercial_office",
)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _resolve_staff_directory(state: OwnerClubState) -> dict[str, dict[str, Any]]:
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))

    # General Manager
    gm_raw = exec_staff.get("general_manager")
    gm_appointed = bool(gm_raw and isinstance(gm_raw, dict) and gm_raw.get("name"))
    if gm_appointed:
        gm = dict(gm_raw)
        gm_name = str(gm.get("name") or "General Manager")
        gm_label = "General Manager"
        gm_status = "appointed"
        gm_negotiation = _safe_int(gm.get("negotiation"), 15)
        gm_discipline = _safe_int(gm.get("financial_discipline"), 15)
        gm_salary = _safe_int(gm.get("salary_gtex", gm.get("salary", 350)), 350)
        gm_mood = _safe_int(gm.get("mood"), 78)
        gm_loyalty = _safe_int(gm.get("loyalty"), 14)
        gm_agenda = str(gm.get("personal_agenda") or "Maximize sponsor yield & wage-to-turnover discipline")
        gm_trait = str(gm.get("signature_trait") or gm.get("special_trait") or "Clause Architect")
    else:
        gm = {}
        gm_name = "Vacant (Provisional Operations Lead)"
        gm_label = "General Manager (Vacant)"
        gm_status = "vacant"
        gm_negotiation = 10
        gm_discipline = 10
        gm_salary = 0
        gm_mood = 70
        gm_loyalty = 10
        gm_agenda = "Maintain baseline administrative routines until a permanent General Manager is appointed"
        gm_trait = "Provisional Caretaker"

    # Head of Youth Development
    hoyd_raw = exec_staff.get("head_of_youth_development")
    hoyd_appointed = bool(hoyd_raw and isinstance(hoyd_raw, dict) and hoyd_raw.get("name"))
    if hoyd_appointed:
        hoyd = dict(hoyd_raw)
        hoyd_name = str(hoyd.get("name") or "Head of Youth Development")
        hoyd_label = "Head of Youth Development"
        hoyd_status = "appointed"
        hoyd_youth = _safe_int(hoyd.get("youth_development"), 15)
        hoyd_salary = _safe_int(hoyd.get("salary_gtex", hoyd.get("salary", 300)), 300)
        hoyd_mood = _safe_int(hoyd.get("mood"), 82)
        hoyd_loyalty = _safe_int(hoyd.get("loyalty"), 15)
        hoyd_agenda = str(hoyd.get("personal_agenda") or "Fast-track academy wonderkids & senior pathway integration")
        hoyd_trait = str(hoyd.get("signature_trait") or hoyd.get("special_trait") or "Bloodline Whisperer")
    else:
        hoyd = {}
        hoyd_name = "Vacant (Provisional Academy Coordinator)"
        hoyd_label = "Head of Youth Development (Vacant)"
        hoyd_status = "vacant"
        hoyd_youth = 10
        hoyd_salary = 0
        hoyd_mood = 70
        hoyd_loyalty = 10
        hoyd_agenda = "Coordinate basic youth drills until a dedicated Head of Youth Development is appointed"
        hoyd_trait = "Provisional Caretaker"

    # Medical Director
    med_raw = exec_staff.get("medical_director")
    med_appointed = bool(med_raw and isinstance(med_raw, dict) and med_raw.get("name"))
    if med_appointed:
        med = dict(med_raw)
        med_name = str(med.get("name") or "Medical Director")
        med_label = "Medical Director"
        med_status = "appointed"
        med_expertise = _safe_int(med.get("medical_expertise"), 10)
        med_salary = _safe_int(med.get("salary_gtex", med.get("salary", 300)), 300)
        med_mood = _safe_int(med.get("mood"), 84)
        med_loyalty = _safe_int(med.get("loyalty"), 16)
        med_agenda = str(med.get("personal_agenda") or "Zero-tolerance sports science load management")
        med_trait = str(med.get("signature_trait") or med.get("special_trait") or "Strict Recovery Veto")
    else:
        med = {}
        med_name = "Vacant (Provisional Medical Caretaker)"
        med_label = "Medical Director (Vacant)"
        med_status = "vacant"
        med_expertise = 10
        med_salary = 0
        med_mood = 70
        med_loyalty = 10
        med_agenda = "Interim triage & basic athlete first-aid until a Medical Director is appointed"
        med_trait = "Provisional Caretaker"

    # Chief Scout
    scout_raw = exec_staff.get("chief_scout")
    scout_appointed = bool(scout_raw and isinstance(scout_raw, dict) and scout_raw.get("name"))
    if scout_appointed:
        scout = dict(scout_raw)
        scout_name = str(scout.get("name") or "Chief Scout")
        scout_label = "Chief Scout"
        scout_status = "appointed"
        scout_reach = _safe_int(scout.get("scouting_reach"), 15)
        scout_salary = _safe_int(scout.get("salary_gtex", scout.get("salary", 250)), 250)
        scout_mood = _safe_int(scout.get("mood"), 76)
        scout_loyalty = _safe_int(scout.get("loyalty"), 13)
        scout_agenda = str(scout.get("personal_agenda") or "Uncover unheralded continental wonderkids")
        scout_trait = str(scout.get("signature_trait") or scout.get("special_trait") or "Underground Agent Network")
    else:
        scout = {}
        scout_name = "Vacant (Regional Scout Pool)"
        scout_label = "Chief Scout (Vacant)"
        scout_status = "vacant"
        scout_reach = 10
        scout_salary = 0
        scout_mood = 70
        scout_loyalty = 10
        scout_agenda = "Monitor local domestic fixture lists until a Chief Scout is appointed"
        scout_trait = "Provisional Caretaker"

    mgr_name = str(mgr.get("name") or mgr.get("display_name") or "First-Team Manager")

    return {
        "first_team_manager": {
            "role_key": "first_team_manager",
            "role_label": "First-Team Manager",
            "name": mgr_name,
            "status": "appointed",
            "is_appointed": True,
            "mood": _safe_int(mgr.get("mood"), 75),
            "loyalty": _safe_int(mgr.get("loyalty"), 12),
            "temperament": str(mgr.get("temperament") or "ambitious"),
            "tactical_preference": str(mgr.get("tactical_preference") or "Balanced Possession"),
            "youth_development": _safe_int(mgr.get("youth_development"), 12),
            "salary_gtex": _safe_int(mgr.get("salary_gtex", 500), 500),
            "personal_agenda": str(mgr.get("personal_agenda") or "Win silverware & enforce high-press identity"),
            "signature_trait": str(mgr.get("signature_trait") or mgr.get("special_trait") or "Touchline Firebrand"),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_mgr", mgr_name),
        },
        "general_manager": {
            "role_key": "general_manager",
            "role_label": gm_label,
            "name": gm_name,
            "status": gm_status,
            "is_appointed": gm_appointed,
            "mood": gm_mood,
            "loyalty": gm_loyalty,
            "negotiation": gm_negotiation,
            "financial_discipline": gm_discipline,
            "salary_gtex": gm_salary,
            "personal_agenda": gm_agenda,
            "signature_trait": gm_trait,
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_gm", gm_name),
        },
        "head_of_youth_development": {
            "role_key": "head_of_youth_development",
            "role_label": hoyd_label,
            "name": hoyd_name,
            "status": hoyd_status,
            "is_appointed": hoyd_appointed,
            "mood": hoyd_mood,
            "loyalty": hoyd_loyalty,
            "youth_development": hoyd_youth,
            "salary_gtex": hoyd_salary,
            "personal_agenda": hoyd_agenda,
            "signature_trait": hoyd_trait,
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_hoyd", hoyd_name),
        },
        "medical_director": {
            "role_key": "medical_director",
            "role_label": med_label,
            "name": med_name,
            "status": med_status,
            "is_appointed": med_appointed,
            "mood": med_mood,
            "loyalty": med_loyalty,
            "medical_expertise": med_expertise,
            "salary_gtex": med_salary,
            "personal_agenda": med_agenda,
            "signature_trait": med_trait,
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_med", med_name),
        },
        "chief_scout": {
            "role_key": "chief_scout",
            "role_label": scout_label,
            "name": scout_name,
            "status": scout_status,
            "is_appointed": scout_appointed,
            "mood": scout_mood,
            "loyalty": scout_loyalty,
            "scouting_reach": scout_reach,
            "salary_gtex": scout_salary,
            "personal_agenda": scout_agenda,
            "signature_trait": scout_trait,
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_scout", scout_name),
        },
    }


def _collect_club_fixtures(session: Session, club_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = list(session.scalars(select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.club_id == club_id)).all())
    comp_ids = list({e.competition_id for e in entries})
    upcoming: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    if not comp_ids:
        return upcoming, recent

    matches = list(
        session.scalars(
            select(OwnerMatch)
            .where(
                OwnerMatch.competition_id.in_(comp_ids),
                or_(OwnerMatch.home_club_id == club_id, OwnerMatch.away_club_id == club_id),
            )
            .order_by(OwnerMatch.round_number.asc())
        ).all()
    )
    for m in matches:
        mapped = comps.mapped_match_dict(session, m)
        if mapped.get("status") == "scheduled":
            upcoming.append(mapped)
        else:
            recent.append(mapped)
    recent.reverse()
    return upcoming, recent


def _build_or_sync_daily_operational_decisions(
    session: Session,
    state: OwnerClubState,
    *,
    staff: dict[str, dict[str, Any]],
    squad_players: list[OwnerSquadPlayer],
    campus_effects: dict[str, Any],
    sponsor_info: dict[str, Any],
    cash_gtex: int,
) -> list[dict[str, Any]]:
    """Builds or returns deterministic, world-day-anchored operational recommendations for each department."""
    facs = dict(state.facilities_json or {})
    world_day = int(state.world_day or 1)
    club_id = state.club_id

    existing_store = dict(facs.get("_daily_operational_decisions") or {})
    if existing_store.get("world_day") == world_day and isinstance(existing_store.get("items"), list):
        return list(existing_store["items"])

    now_iso = datetime.now(timezone.utc).isoformat()
    decisions: list[dict[str, Any]] = []

    # 1. Manager's Office Recommendation: Pre-Match Win Bonus or Tactical Mentality Alignment
    pledged_bonus = _safe_int(facs.get("_pledged_win_bonus_gtex"), 0)
    mgr = staff["first_team_manager"]
    if pledged_bonus == 0 and cash_gtex >= 1200:
        bonus_amt = 1200
        decisions.append(
            {
                "decision_id": f"op_mgr_bonus_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "managers_office",
                "department_label": "Manager's Office",
                "proposer_role": "first_team_manager",
                "proposer_name": mgr["name"],
                "proposer_portrait_url": mgr["portrait_url"],
                "operation_key": "pledge_win_bonus",
                "title": "Pledge Pre-Match Squad Victory Bonus (1,200 GTX)",
                "what": (
                    f"{mgr['name']} recommends pledging a 1,200 GTX dressing-room victory bonus ahead of the next fixture "
                    f"to elevate squad morale (+8) and sharpen touchline focus (+5 Manager Mood)."
                ),
                "why": f"Current squad morale averages {int(sum(p.morale for p in squad_players) / max(1, len(squad_players)))}% under '{state.mentality}' mentality.",
                "cost_gtex": bonus_amt,
                "priority": "high",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": "Approve 1,200 GTX Bonus", "style": "primary"},
                    {"key": "reject", "label": "Decline Proposal", "style": "ghost"},
                ],
                "payload": {"amount_gtex": bonus_amt, "note": f"World Day {world_day} Manager-recommended win bonus"},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )
    else:
        target_mentality = "attacking" if state.mentality != "attacking" else "balanced"
        decisions.append(
            {
                "decision_id": f"op_mgr_tactics_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "managers_office",
                "department_label": "Manager's Office",
                "proposer_role": "first_team_manager",
                "proposer_name": mgr["name"],
                "proposer_portrait_url": mgr["portrait_url"],
                "operation_key": "align_tactical_mentality",
                "title": f"Adopt '{target_mentality.title()}' Tactical Match Plan",
                "what": (
                    f"{mgr['name']} requests formal owner sign-off to transition first-team training drills to an "
                    f"'{target_mentality}' tactical mentality (+4 Manager Mood, +2 Squad Morale)."
                ),
                "why": f"Current mentality is '{state.mentality}'. Aligning tactical identity strengthens match preparation.",
                "cost_gtex": 0,
                "priority": "normal",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": f"Adopt {target_mentality.title()} Plan", "style": "primary"},
                    {"key": "reject", "label": "Keep Current Setup", "style": "ghost"},
                ],
                "payload": {"mentality": target_mentality},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )

    # 2. General Manager's Office Recommendation: Advance Campus Construction or Upgrade Weakest Facility
    gm = staff["general_manager"]
    projects = [
        p
        for p in (facs.get("_construction_projects") or [])
        if p.get("status") not in ("completed", "cancelled") and _safe_int(p.get("progress_pct"), 0) < 100
    ]
    if projects:
        active_proj = projects[0]
        decisions.append(
            {
                "decision_id": f"op_gm_campus_stage_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "general_managers_office",
                "department_label": "General Manager's Office",
                "proposer_role": "general_manager",
                "proposer_name": gm["name"],
                "proposer_portrait_url": gm["portrait_url"],
                "operation_key": "advance_campus_stage",
                "title": f"Sign Off Next Construction Stage: {active_proj.get('module_name', 'Campus Module')}",
                "what": (
                    f"{gm['name']} has cleared contractor inspection for {active_proj.get('module_name')} "
                    f"(currently {active_proj.get('progress_pct', 25)}% in '{active_proj.get('stage', 'groundworks')}'). "
                    f"Sign off to advance construction progress by +25%."
                ),
                "why": "Advancing campus modules toward operational completion unlocks permanent matchday and sporting bonuses.",
                "cost_gtex": 0,
                "priority": "high",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": "Authorize Stage Sign-Off", "style": "primary"},
                    {"key": "reject", "label": "Hold Inspection", "style": "ghost"},
                ],
                "payload": {"instance_id": active_proj.get("instance_id")},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )
    else:
        weakest_fac = min(engine.FACILITY_KINDS, key=lambda k: _safe_int(facs.get(k, 1), 1))
        cur_lvl = _safe_int(facs.get(weakest_fac, 1), 1)
        if cur_lvl < 5:
            up_cost = service.facility_cost(cur_lvl)
            decisions.append(
                {
                    "decision_id": f"op_gm_facility_{weakest_fac}_d{world_day}",
                    "world_day": world_day,
                    "source_type": "department_recommendation",
                    "department": "general_managers_office",
                    "department_label": "General Manager's Office",
                    "proposer_role": "general_manager",
                    "proposer_name": gm["name"],
                    "proposer_portrait_url": gm["portrait_url"],
                    "operation_key": "upgrade_facility",
                    "title": f"Modernise {weakest_fac.title()} Infrastructure to Level {cur_lvl + 1}",
                    "what": (
                        f"{gm['name']} recommends committing {up_cost:,} GTX from the club treasury to upgrade "
                        f"{weakest_fac.title()} facilities from Level {cur_lvl} to Level {cur_lvl + 1}."
                    ),
                    "why": f"{weakest_fac.title()} (Level {cur_lvl}) is currently the club's lowest-rated operational pillar.",
                    "cost_gtex": up_cost,
                    "priority": "normal",
                    "status": "open",
                    "actions": [
                        {"key": "approve", "label": f"Approve {up_cost:,} GTX Upgrade", "style": "primary"},
                        {"key": "reject", "label": "Defer Expenditure", "style": "ghost"},
                    ],
                    "payload": {"facility": weakest_fac, "cost_gtex": up_cost},
                    "created_at": now_iso,
                    "resolved_at": None,
                    "resolution": None,
                    "outcome": None,
                }
            )

    # 3. Academy Department Recommendation: Youth Intake or Improved Academy Contract
    hoyd = staff["head_of_youth_development"]
    regens = [p for p in squad_players if p.is_regen]
    acad_lvl = _safe_int(facs.get("academy", 1), 1)
    intake_cost = 1500 * acad_lvl
    uncontracted_regen = next(
        (p for p in regens if (p.personality_json or {}).get("contract_tier") != "improved_youth"),
        None,
    )
    if uncontracted_regen and cash_gtex >= 1000:
        decisions.append(
            {
                "decision_id": f"op_hoyd_contract_{uncontracted_regen.id}_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "academy_department",
                "department_label": "Academy Department",
                "proposer_role": "head_of_youth_development",
                "proposer_name": hoyd["name"],
                "proposer_portrait_url": hoyd["portrait_url"],
                "operation_key": "academy_contract",
                "title": f"Award Improved Scholar Contract to {uncontracted_regen.name} (1,000 GTX)",
                "what": (
                    f"{hoyd['name']} recommends securing academy prospect {uncontracted_regen.name} "
                    f"({uncontracted_regen.position}, OVR {uncontracted_regen.rating} / POT {uncontracted_regen.potential}) "
                    f"on an improved youth contract (+12 Morale, +2 Loyalty, -25 Transfer Pressure)."
                ),
                "why": f"Campus academy ceiling bonus (+{campus_effects.get('academy_ceiling_bonus', 0)}) makes retaining top prospects vital.",
                "cost_gtex": 1000,
                "priority": "normal",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": "Award 1,000 GTX Contract", "style": "primary"},
                    {"key": "reject", "label": "Hold Current Terms", "style": "ghost"},
                ],
                "payload": {"player_id": uncontracted_regen.id, "player_name": uncontracted_regen.name},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )
    else:
        est_count = 1 + acad_lvl // 2 + _safe_int(campus_effects.get("academy_intake_bonus_count"), 0)
        decisions.append(
            {
                "decision_id": f"op_hoyd_intake_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "academy_department",
                "department_label": "Academy Department",
                "proposer_role": "head_of_youth_development",
                "proposer_name": hoyd["name"],
                "proposer_portrait_url": hoyd["portrait_url"],
                "operation_key": "academy_intake",
                "title": f"Commission Regional Youth Academy Intake ({intake_cost:,} GTX)",
                "what": (
                    f"{hoyd['name']} requests {intake_cost:,} GTX to induct {est_count} new youth prospect(s) "
                    f"with +{campus_effects.get('regen_intake_quality_pct', 0)}% campus intake quality bonus."
                ),
                "why": f"Level {acad_lvl} Academy & operational campus pitches support {est_count} incoming scholars.",
                "cost_gtex": intake_cost,
                "priority": "normal",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": f"Approve {intake_cost:,} GTX Intake", "style": "primary"},
                    {"key": "reject", "label": "Pass This Window", "style": "ghost"},
                ],
                "payload": {"cost_gtex": intake_cost, "expected_count": est_count},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )

    # 4. Medical Department Recommendation: Sports-Science Conditioning & Rehab Protocol
    med = staff["medical_director"]
    injured_count = sum(1 for p in squad_players if _safe_int(p.injured_days, 0) > 0)
    low_fit_count = sum(1 for p in squad_players if _safe_int((p.personality_json or {}).get("fitness", 95), 95) < 90)
    protocol_cost = 800
    decisions.append(
        {
            "decision_id": f"op_med_protocol_d{world_day}",
            "world_day": world_day,
            "source_type": "department_recommendation",
            "department": "medical_department",
            "department_label": "Medical Department",
            "proposer_role": "medical_director",
            "proposer_name": med["name"],
            "proposer_portrait_url": med["portrait_url"],
            "operation_key": "medical_conditioning_protocol",
            "title": f"Authorize Hydro & Cryo Recovery Protocol ({protocol_cost:,} GTX)",
            "what": (
                f"{med['name']} recommends an intensive sports-science conditioning & hydrotherapy cycle "
                f"({protocol_cost:,} GTX) to restore +6% fitness across the squad and accelerate active rehabilitation by 1 day."
            ),
            "why": (
                f"Currently monitoring {injured_count} injured player(s) and {low_fit_count} player(s) below 90% conditioning "
                f"(Campus Injury Reduction: -{campus_effects.get('injury_reduction_pct', 0)}%)."
            ),
            "cost_gtex": protocol_cost,
            "priority": "high" if injured_count > 0 or low_fit_count >= 3 else "normal",
            "status": "open",
            "actions": [
                {"key": "approve", "label": f"Authorize {protocol_cost:,} GTX Protocol", "style": "primary"},
                {"key": "reject", "label": "Standard Recovery Only", "style": "ghost"},
            ],
            "payload": {"cost_gtex": protocol_cost},
            "created_at": now_iso,
            "resolved_at": None,
            "resolution": None,
            "outcome": None,
        }
    )

    # 5. Finance & Commercial Office Recommendation: Sign Unlocked Commercial Sponsor Offer
    unlocked_offers = [o for o in (sponsor_info.get("offers") or []) if not o.get("locked")]
    active_deals_count = len([d for d in (sponsor_info.get("active_deals") or []) if d.get("status") == "active"])
    if unlocked_offers and active_deals_count < 4:
        best_offer = max(unlocked_offers, key=lambda o: _safe_int(o.get("per_match_gross_gtex"), 0))
        decisions.append(
            {
                "decision_id": f"op_fin_sponsor_{best_offer['offer_id']}_d{world_day}",
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": "finance_commercial_office",
                "department_label": "Finance & Commercial Office",
                "proposer_role": "general_manager",
                "proposer_name": gm["name"],
                "proposer_portrait_url": gm["portrait_url"],
                "operation_key": "sign_sponsor_offer",
                "title": f"Ratify Commercial Partnership: {best_offer['sponsor_name']} ({best_offer['slot']})",
                "what": (
                    f"{gm['name']} has finalized terms with {best_offer['sponsor_name']} for the {best_offer['slot']} package: "
                    f"+{best_offer['upfront_signing_bonus_gtex']:,} GTX immediate signing bonus and "
                    f"{best_offer['per_match_gross_gtex']:,} GTX/match over {best_offer.get('matches_duration', 10)} matches."
                ),
                "why": (
                    f"Includes +{campus_effects.get('sponsor_revenue_bonus_pct', 0)}% campus commercial uplift and "
                    f"+1 Club Prestige upon contract execution."
                ),
                "cost_gtex": 0,
                "revenue_gtex": _safe_int(best_offer.get("upfront_signing_bonus_gtex"), 0),
                "priority": "high",
                "status": "open",
                "actions": [
                    {"key": "approve", "label": f"Ratify {best_offer['sponsor_name']} Deal", "style": "primary"},
                    {"key": "reject", "label": "Pass Offer", "style": "ghost"},
                ],
                "payload": {"offer_id": best_offer["offer_id"], "sponsor_name": best_offer["sponsor_name"]},
                "created_at": now_iso,
                "resolved_at": None,
                "resolution": None,
                "outcome": None,
            }
        )

    facs["_daily_operational_decisions"] = {
        "world_day": world_day,
        "club_id": club_id,
        "items": decisions,
    }
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.flush()
    return decisions


def build_authoritative_daily_briefing(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Compiles the authoritative 6-section Owner Daily Briefing from real club, squad, medical, academy, campus, and ledger state."""
    state = require_state(session, club_id, user_id)
    world_day = int(state.world_day or 1)
    facs = dict(state.facilities_json or {})

    cached = facs.get("_daily_briefing")
    if (
        cached
        and not force_refresh
        and cached.get("world_day") == world_day
        and "executive_briefing" in cached
        and "medical_directors_report" in cached
        and "financial_commercial_report" in cached
    ):
        return cached

    campus_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state, reconcile=True)
    facs = dict(state.facilities_json or {})
    staff = _resolve_staff_directory(state)
    squad_players = list(
        session.scalars(
            select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).order_by(OwnerSquadPlayer.rating.desc())
        ).all()
    )
    squad_size = len(squad_players)
    econ = ledger.club_economy(session, club_id)
    cash_bal = _safe_int(econ.get("cash_gtex"), 0)
    fan_coin_bal = _safe_int(ledger.balance(session, ledger.club_account(club_id), ledger.FAN), 0)
    distributable_gtex = _safe_int(money.distributable(session, club_id), 0)
    club_val = _safe_int(service.club_value(session, state), cash_bal)
    tier_label = engine.prestige_tier_label(state.prestige)

    upcoming_fixtures, recent_results = _collect_club_fixtures(session, club_id)
    sponsor_info = service.get_sponsor_offers(session, user_id, club_id)
    dept_decisions = _build_or_sync_daily_operational_decisions(
        session,
        state,
        staff=staff,
        squad_players=squad_players,
        campus_effects=campus_effects,
        sponsor_info=sponsor_info,
        cash_gtex=cash_bal,
    )
    # Refresh facs after _build_or_sync_daily_operational_decisions
    facs = dict(state.facilities_json or {})

    open_inbox_rows = list(
        session.scalars(
            select(OwnerInboxItem)
            .where(
                OwnerInboxItem.club_id == club_id,
                OwnerInboxItem.status == "open",
                OwnerInboxItem.archived_at.is_(None),
            )
            .order_by(OwnerInboxItem.created_at.desc())
        ).all()
    )
    open_inbox_decisions = [service.inbox_dict(i) for i in open_inbox_rows if i.is_decision]
    open_dept_decisions = [d for d in dept_decisions if d.get("status") == "open"]

    # Preserve existing boardroom dilemma if already generated/resolved for this world_day
    existing_dilemma = (cached or {}).get("boardroom_dilemma") if (cached or {}).get("world_day") == world_day else None
    dilemma = existing_dilemma or engine.generate_boardroom_dilemma(
        club_id=club_id,
        world_day=world_day,
        gm_name=staff["general_manager"]["name"],
        manager_name=staff["first_team_manager"]["name"],
        hoyd_name=staff["head_of_youth_development"]["name"],
    )
    has_open_dilemma = bool(dilemma and dilemma.get("status") == "open")
    total_open_decisions = len(open_inbox_decisions) + len(open_dept_decisions) + (1 if has_open_dilemma else 0)

    # Squad & Conditioning Metrics
    avg_morale = int(sum(p.morale for p in squad_players) / max(1, squad_size))
    fitness_values = [_safe_int((p.personality_json or {}).get("fitness", 95), 95) for p in squad_players]
    avg_fitness = int(sum(fitness_values) / max(1, len(fitness_values)))
    injured_players_rows = [p for p in squad_players if _safe_int(p.injured_days, 0) > 0]
    available_players_rows = [p for p in squad_players if _safe_int(p.injured_days, 0) <= 0]
    regens = [p for p in squad_players if p.is_regen]
    ready_prospects = [p for p in regens if p.rating >= 58 and _safe_int(p.injured_days, 0) <= 0]

    # Medical recovery parameters (exact same formula as service.tick_club)
    med_expertise = staff["medical_director"]["medical_expertise"]
    med_bonus = max(0, med_expertise // 5)
    rehab_campus_bonus = _safe_int(campus_effects.get("rehab_daily_bonus_days"), 0)
    medical_facility_level = _safe_int(facs.get("medical", 1), 1)
    daily_injury_heal_days = max(1, 1 + medical_facility_level // 2 + med_bonus + rehab_campus_bonus)
    daily_fitness_recovery = _safe_int(campus_effects.get("daily_fitness_recovery"), 6)
    injury_reduction_pct = _safe_int(campus_effects.get("injury_reduction_pct"), 0)

    # Active XI calculation
    strength_info = engine.club_strength(
        [service.player_dict(pl) for pl in squad_players],
        state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER),
        facs,
        campus_effects=campus_effects,
    )
    active_xi_ids = set(strength_info.get("xi") or [])

    # Campus modules & construction projects
    placed_modules = list(facs.get("_campus_modules") or [])
    operational_modules = [m for m in placed_modules if m.get("status") == "operational"]
    construction_projects = [
        p for p in (facs.get("_construction_projects") or []) if p.get("status") not in ("completed", "cancelled")
    ]

    # Daily staff wage upkeep
    exec_staff_raw = dict(facs.get("_executive_staff") or {})
    total_staff_salary = sum(
        _safe_int(s.get("salary_gtex", s.get("salary", 300)), 300)
        for s in exec_staff_raw.values()
        if isinstance(s, dict) and not s.get("upfront_paid", True)
    )
    daily_staff_upkeep_gtex = max(10, total_staff_salary // 30) if exec_staff_raw else 0

    # Urgent Risks Detection (grounded in actual club state)
    urgent_risks: list[dict[str, Any]] = []
    if injured_players_rows:
        urgent_risks.append(
            {
                "risk_id": "risk_medical_load",
                "severity": "high" if len(injured_players_rows) >= 2 else "medium",
                "department": "medical_department",
                "title": f"{len(injured_players_rows)} Squad Player(s) in Active Rehabilitation",
                "detail": ", ".join(f"{p.name} ({p.injured_days}d remaining)" for p in injured_players_rows[:4]),
            }
        )
    low_morale_players = [p for p in squad_players if p.morale < 60]
    if low_morale_players:
        urgent_risks.append(
            {
                "risk_id": "risk_squad_morale",
                "severity": "high" if any(p.morale < 45 for p in low_morale_players) else "medium",
                "department": "managers_office",
                "title": f"{len(low_morale_players)} Player(s) Reporting Dressing-Room Unrest",
                "detail": ", ".join(f"{p.name} (Morale {p.morale}%)" for p in low_morale_players[:4]),
            }
        )
    if squad_size < 16:
        urgent_risks.append(
            {
                "risk_id": "risk_squad_depth",
                "severity": "high",
                "department": "managers_office",
                "title": f"Thin First-Team Squad ({squad_size} Registered Players)",
                "detail": "Minimum recommended competitive depth is 16 players.",
            }
        )
    if cash_bal < 2500:
        urgent_risks.append(
            {
                "risk_id": "risk_liquidity",
                "severity": "high",
                "department": "finance_commercial_office",
                "title": f"Low Treasury Liquidity ({cash_bal:,} GTX)",
                "detail": "Sign a commercial sponsor offer or inject capital before commissioning major upgrades.",
            }
        )
    if construction_projects:
        urgent_risks.append(
            {
                "risk_id": "risk_construction",
                "severity": "normal",
                "department": "general_managers_office",
                "title": f"{len(construction_projects)} Active Campus Construction Project(s) Underway",
                "detail": ", ".join(
                    f"{p.get('module_name')} ({p.get('progress_pct', 25)}% · {p.get('stage', 'groundworks')})"
                    for p in construction_projects[:3]
                ),
            }
        )

    # Recent match performance stats
    wins = 0
    draws = 0
    losses = 0
    for m in recent_results:
        hg = _safe_int(m.get("home_goals", m.get("home_score", 0)), 0)
        ag = _safe_int(m.get("away_goals", m.get("away_score", 0)), 0)
        is_home = m.get("home_club_id") == club_id
        my_g = hg if is_home else ag
        opp_g = ag if is_home else hg
        if my_g > opp_g:
            wins += 1
        elif my_g == opp_g:
            draws += 1
        else:
            losses += 1
    matches_played = len(recent_results)
    win_rate_pct = int(round((wins / matches_played) * 100)) if matches_played > 0 else 0

    active_sponsor_deals = sponsor_info.get("active_deals") or []
    per_match_sponsor_income_gtex = sum(
        _safe_int(d.get("per_match_gross"), 0) for d in active_sponsor_deals if d.get("status") == "active"
    )
    daily_wage_bill_gtex = daily_staff_upkeep_gtex + sum(
        max(10, _safe_int(p.value_coin, 1000) // 100) for p in squad_players
    )

    # --- SECTION A: EXECUTIVE BRIEFING ---
    fin_pos = {
        "cash_gtex": cash_bal,
        "fan_coin": fan_coin_bal,
        "fan_coin_balance": fan_coin_bal,
        "club_valuation_gtex": club_val,
        "distributable_gtex": distributable_gtex,
        "daily_staff_upkeep_gtex": daily_staff_upkeep_gtex,
        "daily_wage_bill_gtex": daily_wage_bill_gtex,
        "daily_sponsor_income_gtex": per_match_sponsor_income_gtex,
        "pending_payouts_gtex": _safe_int(econ.get("pending_payouts"), 0),
    }
    squad_cond = {
        "squad_size": squad_size,
        "available_players": len(available_players_rows),
        "available_count": len(available_players_rows),
        "injured_players": len(injured_players_rows),
        "injured_count": len(injured_players_rows),
        "avg_fitness": avg_fitness,
        "avg_morale": avg_morale,
        "low_morale_count": len(low_morale_players),
        "team_strength": _safe_int(strength_info.get("strength"), 68),
        "team_strength_rating": _safe_int(strength_info.get("strength"), 68),
        "mentality": state.mentality,
        "squad_depth": "thin" if squad_size < 16 else "healthy" if squad_size < 26 else "deep",
    }
    match_perf = {
        "matches_played": matches_played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": sum(
            m.get("home_goals", 0) if m.get("home_club_id") == club_id else m.get("away_goals", 0)
            for m in recent_results
        ),
        "goals_against": sum(
            m.get("away_goals", 0) if m.get("home_club_id") == club_id else m.get("home_goals", 0)
            for m in recent_results
        ),
        "win_rate_pct": win_rate_pct,
        "recent_results": recent_results[:3],
        "upcoming_fixtures": upcoming_fixtures[:3],
    }
    acad_summ = {
        "academy_level": _safe_int(facs.get("academy", 1), 1),
        "total_youth_players": len(regens),
        "regen_count": len(regens),
        "ready_for_first_team": len(ready_prospects),
        "ready_prospects_count": len(ready_prospects),
        "high_potential_prospects": len([r for r in regens if r.potential >= 80]),
        "intake_quality_bonus": _safe_int(campus_effects.get("regen_intake_quality_pct"), 0),
        "regen_potential_bonus": _safe_int(campus_effects.get("regen_potential_bonus"), 0),
        "regen_intake_quality_pct": _safe_int(campus_effects.get("regen_intake_quality_pct"), 0),
        "regen_development_speed_pct": _safe_int(campus_effects.get("regen_development_speed_pct"), 0),
    }
    med_summ = {
        "medical_level": medical_facility_level,
        "injured_count": len(injured_players_rows),
        "daily_injury_heal_days": daily_injury_heal_days,
        "injury_incidence_reduction_pct": injury_reduction_pct,
        "daily_fitness_recovery_bonus": daily_fitness_recovery,
        "daily_fitness_recovery": daily_fitness_recovery,
    }
    stad_ops = {
        "stadium_level": _safe_int(facs.get("stadium", 1), 1),
        "operational_stadium_capacity": _safe_int(campus_effects.get("stadium_capacity"), 15000),
        "stadium_capacity": _safe_int(campus_effects.get("stadium_capacity"), 15000),
        "placed_buildings_count": len(operational_modules),
        "operational_modules_count": len(operational_modules),
        "active_construction_count": len(construction_projects),
        "active_construction_projects_count": len(construction_projects),
        "gate_revenue_bonus_pct": _safe_int(campus_effects.get("matchday_revenue_bonus_pct"), 15),
        "sponsor_bonus_pct": _safe_int(campus_effects.get("commercial_growth_bonus_pct"), 0),
        "active_projects": construction_projects[:4],
    }

    executive_briefing = {
        "section_key": "executive_briefing",
        "title": "Executive Briefing · Club Condition & Strategic Posture",
        "lead_role": "Office of the Club Owner",
        "role": "Executive Office",
        "sender": "Office of the Club Owner",
        "summary": (
            f"Club condition is rated {tier_label}. Treasury balance: {cash_bal:,.0f} GTEX. "
            f"Squad: {len(available_players_rows)}/{squad_size} players available ({len(injured_players_rows)} injured, {avg_morale}% morale). "
            f"Total {total_open_decisions} decision(s) require boardroom attention."
        ),
        "world_day": world_day,
        "last_world_tick_date": state.last_world_tick_date.isoformat() if state.last_world_tick_date else None,
        "financial_position": fin_pos,
        "squad_condition": squad_cond,
        "squad_condition_and_availability": squad_cond,
        "match_performance": match_perf,
        "recent_match_performance": match_perf,
        "upcoming_fixtures_and_commitments": upcoming_fixtures[:3],
        "academy_summary": acad_summ,
        "academy_and_youth_activity": acad_summ,
        "medical_summary": med_summ,
        "medical_and_rehabilitation": med_summ,
        "stadium_and_campus": stad_ops,
        "stadium_and_campus_operations": stad_ops,
        "outstanding_decisions_count": total_open_decisions,
        "urgent_risks": urgent_risks,
    }

    # --- SECTION B: MANAGER'S REPORT ---
    positions_count: dict[str, int] = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in available_players_rows:
        pos_key = str(p.position or "MID").upper()[:3]
        if pos_key in positions_count:
            positions_count[pos_key] += 1
        elif pos_key.startswith("G"):
            positions_count["GK"] += 1
        elif pos_key.startswith("D"):
            positions_count["DEF"] += 1
        elif pos_key.startswith("F") or pos_key.startswith("S"):
            positions_count["FWD"] += 1
        else:
            positions_count["MID"] += 1
    thin_positions = [
        pos for pos, cnt in positions_count.items() if (pos == "GK" and cnt < 2) or (pos != "GK" and cnt < 4)
    ]
    fatigued_players = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "fitness": _safe_int((p.personality_json or {}).get("fitness", 95), 95),
            "morale": p.morale,
        }
        for p in available_players_rows
        if _safe_int((p.personality_json or {}).get("fitness", 95), 95) < 85
    ]
    mgr_recommendations = [d for d in dept_decisions if d.get("department") == "managers_office"]
    next_fix = upcoming_fixtures[0] if upcoming_fixtures else None
    last_res = recent_results[0] if recent_results else None

    managers_report = {
        "section_key": "managers_report",
        "role": "First-Team Manager",
        "sender": staff["first_team_manager"]["name"],
        "staff_profile": staff["first_team_manager"],
        "title": "First-Team Performance, Tactics & Match Preparation",
        "summary": (
            f"First-team squad ({len(available_players_rows)}/{squad_size} available) is operating on a "
            f"'{state.mentality}' tactical mentality with {avg_morale}% average morale and {avg_fitness}% conditioning."
        ),
        "first_team_performance": {
            "matches_played": matches_played,
            "record_summary": f"{wins}W - {draws}D - {losses}L ({win_rate_pct}% Win Rate)",
            "last_match": last_res,
            "team_strength": _safe_int(strength_info.get("strength"), 68),
        },
        "tactical_and_squad_concerns": {
            "active_mentality": state.mentality,
            "formation": str(
                facs.get("_tactical_formation") or staff["first_team_manager"].get("preferred_formation") or "4-3-3"
            ),
            "thin_positions": thin_positions,
            "position_depth": positions_count,
            "training_efficiency_bonus_pct": _safe_int(campus_effects.get("training_efficiency_bonus_pct"), 0),
        },
        "player_morale": {
            "avg_morale": avg_morale,
            "low_morale_count": len(low_morale_players),
            "low_morale_players": [
                {"id": p.id, "name": p.name, "position": p.position, "morale": p.morale, "rating": p.rating}
                for p in low_morale_players[:5]
            ],
            "dressing_room_leaders": [
                {"id": p.id, "name": p.name, "position": p.position, "morale": p.morale, "rating": p.rating}
                for p in squad_players[:3]
            ],
        },
        "fitness_and_selection": {
            "avg_fitness": avg_fitness,
            "available_count": len(available_players_rows),
            "unavailable_injured_count": len(injured_players_rows),
            "fatigued_players": fatigued_players[:5],
            "starting_xi_count": len(active_xi_ids),
        },
        "upcoming_match_preparation": {
            "next_fixture": next_fix,
            "pledged_win_bonus_gtex": _safe_int(facs.get("_pledged_win_bonus_gtex"), 0),
            "home_advantage_bonus": _safe_int(campus_effects.get("home_advantage_bonus"), 0),
        },
        "recommendations": mgr_recommendations,
    }

    # --- SECTION C: GENERAL MANAGER'S REPORT ---
    delegation_policy = dict(
        facs.get("_delegation_policy")
        or {
            "mode": "balanced",
            "gm_transfer_autonomy": True,
            "hoyd_youth_contracts": True,
            "manager_tactics_autonomy": True,
        }
    )
    unsettled_players = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "transfer_pressure": _safe_int((p.personality_json or {}).get("transfer_pressure", 0), 0),
        }
        for p in squad_players
        if _safe_int((p.personality_json or {}).get("transfer_pressure", 0), 0) >= 40
    ]
    gm_recommendations = [d for d in dept_decisions if d.get("department") == "general_managers_office"]
    scheduled_meetings = [m for m in (facs.get("_club_meetings") or []) if m.get("status") == "scheduled"]

    general_managers_report = {
        "section_key": "general_managers_report",
        "role": "General Manager",
        "sender": staff["general_manager"]["name"],
        "staff_profile": staff["general_manager"],
        "title": "Club Administration, Campus Operations & Contracts",
        "summary": (
            f"Operating under '{delegation_policy.get('mode', 'balanced')}' delegation mode with "
            f"{len(operational_modules)} operational campus modules and {len(construction_projects)} active construction project(s)."
        ),
        "administrative_matters": {
            "delegation_policy": delegation_policy,
            "scheduled_meetings_count": len(scheduled_meetings),
            "scheduled_meetings": scheduled_meetings[:4],
            "integrity_score": service.integrity_score(session, user_id),
        },
        "club_operations": {
            "facility_levels": {k: _safe_int(facs.get(k, 1), 1) for k in engine.FACILITY_KINDS},
            "operational_modules_count": len(operational_modules),
            "active_construction_projects": construction_projects[:4],
        },
        "contracts_and_obligations": {
            "daily_staff_upkeep_gtex": daily_staff_upkeep_gtex,
            "unsettled_players_count": len(unsettled_players),
            "unsettled_players": unsettled_players[:5],
            "active_sponsor_obligations_count": len(sponsor_info.get("active_deals") or []),
        },
        "staff_and_organisation": {
            "executive_team": list(staff.values()),
            "poaching_risks": [s for s in staff.values() if _safe_int(s.get("mood"), 75) < 60],
        },
        "recommendations": gm_recommendations,
    }

    # --- SECTION D: HEAD OF YOUTH DEVELOPMENT'S REPORT ---
    watchlist_rows = storytelling.ensure_default_watchlist(session, state)
    watchlist_items = [storytelling.watchlist_dict(w) for w in watchlist_rows]
    acad_lvl = _safe_int(facs.get("academy", 1), 1)
    next_intake_cost = 1500 * acad_lvl
    projected_intake_size = 1 + acad_lvl // 2 + _safe_int(campus_effects.get("academy_intake_bonus_count"), 0)

    regen_dossiers: list[dict[str, Any]] = []
    recent_progression: list[dict[str, Any]] = []
    development_concerns: list[dict[str, Any]] = []
    for r in regens:
        g_log = list(r.growth_log_json or [])
        last_gain = g_log[-1] if g_log else None
        pers = dict(r.personality_json or {})
        inj_d = _safe_int(r.injured_days, 0)
        fit_v = _safe_int(pers.get("fitness", 95), 95)
        dossier = {
            "id": r.id,
            "name": r.name,
            "age": r.age,
            "position": r.position,
            "rating": r.rating,
            "potential": r.potential,
            "morale": r.morale,
            "fitness": fit_v,
            "injured_days": inj_d,
            "contract_tier": pers.get("contract_tier", "scholar"),
            "squad_status": pers.get("squad_status", "academy" if r.rating < 60 else "senior"),
            "ready_for_promotion": r.rating >= 58 and pers.get("squad_status") != "senior",
            "last_growth": last_gain,
            "portrait_url": storytelling.resolve_player_portrait_url(session, r.id, r.name),
        }
        regen_dossiers.append(dossier)
        if last_gain:
            recent_progression.append(
                {
                    "player_id": r.id,
                    "player_name": r.name,
                    "day": last_gain.get("day", world_day),
                    "gain": _safe_int(last_gain.get("gain"), 0),
                    "rating": r.rating,
                    "potential": r.potential,
                    "explanation": last_gain.get("explanation", ""),
                }
            )
        if inj_d > 0:
            development_concerns.append(
                {
                    "player_id": r.id,
                    "player_name": r.name,
                    "concern_type": "injury_rehab_restriction",
                    "detail": f"In rehabilitation ({inj_d}d remaining); normal technical growth restricted until cleared.",
                }
            )
        elif r.morale < 60:
            development_concerns.append(
                {
                    "player_id": r.id,
                    "player_name": r.name,
                    "concern_type": "low_morale",
                    "detail": f"Morale at {r.morale}% may slow daily training progression.",
                }
            )

    hoyd_recommendations = [d for d in dept_decisions if d.get("department") == "academy_department"]

    hoyd_report = {
        "section_key": "hoyd_report",
        "role": "Head of Youth Development",
        "sender": staff["head_of_youth_development"]["name"],
        "staff_profile": staff["head_of_youth_development"],
        "title": "Academy Pipeline, Regen Progression & Youth Recruitment",
        "summary": (
            f"Academy Complex (Level {acad_lvl}) is developing {len(regens)} homegrown regen(s), with "
            f"{len(ready_prospects)} ready for senior minutes and +{campus_effects.get('regen_development_speed_pct', 0)}% campus development speed."
        ),
        "academy_development": {
            "academy_facility_level": acad_lvl,
            "regen_count": len(regens),
            "ready_for_senior_count": len(ready_prospects),
            "campus_intake_quality_pct": _safe_int(campus_effects.get("regen_intake_quality_pct"), 0),
            "campus_ceiling_bonus": _safe_int(campus_effects.get("academy_ceiling_bonus"), 0),
            "campus_development_speed_pct": _safe_int(campus_effects.get("regen_development_speed_pct"), 0),
        },
        "prospective_youth_players": regen_dossiers,
        "player_progression": recent_progression[:8],
        "intake_recommendations": {
            "next_intake_cost_gtex": next_intake_cost,
            "projected_cohort_size": projected_intake_size,
            "intake_sequence": _safe_int(state.academy_intake_sequence, 0),
            "recommendation_note": (
                f"Next youth intake costs {next_intake_cost:,} GTX and will induct {projected_intake_size} prospect(s)."
            ),
        },
        "youth_recruitment_opportunities": watchlist_items[:6],
        "development_concerns": development_concerns,
        "recommendations": hoyd_recommendations,
    }

    # --- SECTION E: MEDICAL DIRECTOR'S REPORT ---
    injured_dossiers: list[dict[str, Any]] = []
    for p in injured_players_rows:
        inj_d = _safe_int(p.injured_days, 0)
        est_world_days = int(math.ceil(inj_d / max(1, daily_injury_heal_days)))
        pers = dict(p.personality_json or {})
        raw_injury_type = pers.get("last_injury_type")
        injury_type = str(raw_injury_type).strip() if raw_injury_type else "Injury type not recorded"
        injured_dossiers.append(
            {
                "id": p.id,
                "name": p.name,
                "position": p.position,
                "rating": p.rating,
                "injured_days": inj_d,
                "daily_heal_rate_days": daily_injury_heal_days,
                "estimated_recovery_world_days": est_world_days,
                "injury_type": injury_type,
                "rehab_status": "intensive_rehabilitation" if inj_d >= 7 else "light_rehab_transition",
                "workload_tier": pers.get("last_training_workload_tier", "rehabilitation"),
                "fitness": _safe_int(pers.get("fitness", 80), 80),
                "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
            }
        )

    special_attention_players: list[dict[str, Any]] = []
    for p in available_players_rows:
        pers = dict(p.personality_json or {})
        fit_v = _safe_int(pers.get("fitness", 95), 95)
        eff_risk = _safe_float(pers.get("last_injury_risk", 0.0), 0.0)
        workload_mins = _safe_int(pers.get("last_training_workload_minutes", 45), 45)
        workload_tier = str(pers.get("last_training_workload_tier") or "standard")
        if fit_v < 88 or eff_risk >= 0.04 or workload_tier == "high_intensity":
            special_attention_players.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "rating": p.rating,
                    "fitness": fit_v,
                    "workload_minutes": workload_mins,
                    "workload_tier": workload_tier,
                    "effective_injury_risk_pct": round(eff_risk * 100, 2),
                    "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
                }
            )

    med_recommendations = [d for d in dept_decisions if d.get("department") == "medical_department"]

    medical_directors_report = {
        "section_key": "medical_directors_report",
        "role": "Medical Director",
        "sender": staff["medical_director"]["name"],
        "staff_profile": staff["medical_director"],
        "title": "Injury Rehabilitation, Sports Science & Squad Conditioning",
        "summary": (
            f"Medical Department (Level {medical_facility_level}) reports {len(injured_dossiers)} injured player(s) in rehab "
            f"(healing {daily_injury_heal_days}d per world tick, -{injury_reduction_pct}% campus injury-incidence mitigation)."
        ),
        "injured_players": injured_dossiers,
        "rehabilitation_status": {
            "active_rehab_count": len(injured_dossiers),
            "daily_injury_heal_days": daily_injury_heal_days,
            "campus_rehab_daily_bonus_days": rehab_campus_bonus,
        },
        "medical_facility_performance": {
            "medical_facility_level": medical_facility_level,
            "injury_reduction_pct": injury_reduction_pct,
            "fatigue_recovery_pct": _safe_int(campus_effects.get("fatigue_recovery_pct"), 0),
            "stamina_retention_pct": _safe_int(campus_effects.get("stamina_retention_pct"), 0),
            "daily_fitness_recovery": daily_fitness_recovery,
        },
        "squad_fitness_concerns": {
            "avg_squad_fitness": avg_fitness,
            "below_85_fitness_count": len(fatigued_players),
            "low_fitness_players": fatigued_players[:6],
        },
        "players_requiring_special_attention": special_attention_players[:6],
        "recommendations": med_recommendations,
    }

    # --- SECTION F: FINANCIAL AND COMMERCIAL REPORT ---
    recent_ledger_rows = ledger.events_for(session, user_id=user_id, club_ids=[club_id], limit=25)
    serialized_ledger = [ledger.serialize(e) for e in recent_ledger_rows]
    club_acct = ledger.club_account(club_id)
    total_income_gtex = 0.0
    total_expenditure_gtex = 0.0
    for ev in recent_ledger_rows:
        if ev.currency != ledger.GTEX:
            continue
        if ev.destination_account == club_acct:
            total_income_gtex += float(ev.net_amount)
        elif ev.source_account == club_acct:
            total_expenditure_gtex += float(ev.gross_amount)

    active_sponsor_deals = sponsor_info.get("active_deals") or []
    per_match_sponsor_income_gtex = sum(
        _safe_int(d.get("per_match_gross"), 0) for d in active_sponsor_deals if d.get("status") == "active"
    )
    last_home_match = next((m for m in recent_results if m.get("home_club_id") == club_id), None)
    stadium_cap = _safe_int(campus_effects.get("stadium_capacity"), 15000)
    projected_attendance = engine.calculate_match_attendance(
        stadium_level=_safe_int(facs.get("stadium", 1), 1),
        fans=int(state.fans or 1200),
        prestige=int(state.prestige or 20),
        campus_effects=campus_effects,
        gf=1,
        ga=1,
    )
    fin_recommendations = [d for d in dept_decisions if d.get("department") == "finance_commercial_office"]

    financial_commercial_report = {
        "section_key": "financial_commercial_report",
        "role": "Finance & Commercial Directorate",
        "sender": staff["general_manager"]["name"],
        "staff_profile": staff["general_manager"],
        "title": "Treasury Balance, Ledger Cashflow, Sponsorships & Matchday Economics",
        "summary": (
            f"Club treasury holds {cash_bal:,} GTX ({distributable_gtex:,} GTX distributable) with "
            f"{len(active_sponsor_deals)} active sponsor deal(s) generating {per_match_sponsor_income_gtex:,} GTX/match."
        ),
        "balances": {
            "cash_gtex": cash_bal,
            "fan_coin_balance": fan_coin_bal,
            "distributable_gtex": distributable_gtex,
            "club_valuation_gtex": club_val,
            "pending_payouts_gtex": _safe_int(econ.get("pending_payouts"), 0),
        },
        "current_club_balance": {
            "cash_gtex": cash_bal,
            "fan_coin": fan_coin_bal,
            "distributable_gtex": distributable_gtex,
            "club_valuation_gtex": club_val,
        },
        "recent_income_and_expenditure": {
            "recent_income_gtex": int(round(total_income_gtex)),
            "recent_expenditure_gtex": int(round(total_expenditure_gtex)),
            "net_cashflow_gtex": int(round(total_income_gtex - total_expenditure_gtex)),
            "earnings_by_source": econ.get("earnings_sources") or {},
            "recent_ledger_events": serialized_ledger[:10],
            "recent_ledger_entries": serialized_ledger[:10],
        },
        "wage_obligations": {
            "total_daily_obligations_gtex": daily_wage_bill_gtex,
            "daily_staff_wage_upkeep_gtex": daily_staff_upkeep_gtex,
            "projected_30d_staff_upkeep_gtex": daily_staff_upkeep_gtex * 30,
            "appointed_executive_count": len(exec_staff_raw),
        },
        "sponsor_income": {
            "active_deals": active_sponsor_deals,
            "per_match_sponsor_income_gtex": per_match_sponsor_income_gtex,
            "sponsor_revenue_bonus_pct": _safe_int(campus_effects.get("sponsor_revenue_bonus_pct"), 0),
            "available_offers": sponsor_info.get("offers") or [],
        },
        "matchday_revenue": {
            "stadium_capacity": stadium_cap,
            "operational_stadium_capacity": stadium_cap,
            "last_home_attendance": last_home_match.get("attendance") if last_home_match else None,
            "last_gate_receipts_gtex": last_home_match.get("gate_receipts_gtex") if last_home_match else None,
            "last_tv_revenue_gtex": last_home_match.get("tv_revenue") if last_home_match else None,
            "projected_next_home_attendance": projected_attendance["attendance"],
            "projected_next_gate_receipts_gtex": projected_attendance["gate_receipts_gtex"],
            "projected_next_home_gate_gtex": projected_attendance["gate_receipts_gtex"],
            "matchday_revenue_bonus_pct": _safe_int(campus_effects.get("matchday_revenue_bonus_pct"), 0),
            "vip_hospitality_flat_gtex": _safe_int(campus_effects.get("vip_hospitality_flat_gtex"), 0),
            "broadcast_revenue_bonus_pct": _safe_int(campus_effects.get("broadcast_revenue_bonus_pct"), 0),
        },
        "outstanding_commitments": {
            "pledged_win_bonus_gtex": _safe_int(facs.get("_pledged_win_bonus_gtex"), 0),
            "active_construction_projects": construction_projects[:4],
        },
        "upcoming_financial_events": [
            {
                "event_type": "next_matchday_settlement",
                "label": (
                    f"Next Fixture vs {next_fix.get('away_name') if next_fix.get('home_club_id') == club_id else next_fix.get('home_name')}"
                    if next_fix
                    else "Upcoming League Matchday Settlement"
                ),
                "projected_gate_gtex": projected_attendance["gate_receipts_gtex"],
                "projected_sponsor_gtex": per_match_sponsor_income_gtex,
            }
        ],
        "recommendations": fin_recommendations,
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    briefing = {
        "id": f"briefing:{club_id}:{world_day}",
        "club_id": club_id,
        "club_name": state.club_name,
        "world_day": world_day,
        "world_date": state.last_world_tick_date.isoformat() if state.last_world_tick_date else None,
        "headline": f"Daily Owner Briefing · {state.club_name or 'Club'} ({tier_label})",
        "summary": (
            f"Treasury stands at {cash_bal:,.0f} GTEX. Squad morale averages {avg_morale}% ({avg_fitness}% fitness) "
            f"across {squad_size} players ({len(injured_dossiers)} in rehab), with {len(ready_prospects)} academy prospect(s) "
            f"pushing for senior minutes and {total_open_decisions} decision(s) awaiting owner action."
        ),
        "body": (
            f"Good morning, Director. Here is your authoritative operational briefing for World Day {world_day}. "
            f"All six club departments have submitted live reports below."
        ),
        "created_at": (cached or {}).get("created_at") if (cached or {}).get("world_day") == world_day else now_iso,
        "generated_at": now_iso,
        "metrics": {
            "cash_gtex": cash_bal,
            "prestige": state.prestige,
            "prestige_tier": tier_label,
            "squad_size": squad_size,
            "available_squad": len(available_players_rows),
            "injured_count": len(injured_dossiers),
            "avg_morale": avg_morale,
            "avg_fitness": avg_fitness,
            "ready_academy_prospects": len(ready_prospects),
            "open_decisions": total_open_decisions,
            "stadium_capacity": stadium_cap,
        },
        "sections": [
            {
                "section_key": "executive_briefing",
                "role": "Executive Office",
                "sender": "Office of the Club Owner",
                "title": executive_briefing["title"],
                "summary": (
                    f"Liquidity: {cash_bal:,} GTX · Valuation: {club_val:,} GTX · Squad: {len(available_players_rows)}/{squad_size} fit · "
                    f"Stadium Cap: {stadium_cap:,} · Open Decisions: {total_open_decisions}."
                ),
            },
            {
                "section_key": "managers_report",
                "role": "First-Team Manager",
                "sender": staff["first_team_manager"]["name"],
                "title": managers_report["title"],
                "summary": managers_report["summary"],
            },
            {
                "section_key": "general_managers_report",
                "role": "General Manager",
                "sender": staff["general_manager"]["name"],
                "title": general_managers_report["title"],
                "summary": general_managers_report["summary"],
            },
            {
                "section_key": "hoyd_report",
                "role": "Head of Youth Development",
                "sender": staff["head_of_youth_development"]["name"],
                "title": hoyd_report["title"],
                "summary": hoyd_report["summary"],
            },
            {
                "section_key": "medical_directors_report",
                "role": "Medical Director",
                "sender": staff["medical_director"]["name"],
                "title": medical_directors_report["title"],
                "summary": medical_directors_report["summary"],
            },
            {
                "section_key": "financial_commercial_report",
                "role": "Finance & Commercial",
                "sender": staff["general_manager"]["name"],
                "title": financial_commercial_report["title"],
                "summary": financial_commercial_report["summary"],
            },
        ],
        "executive_briefing": executive_briefing,
        "managers_report": managers_report,
        "general_managers_report": general_managers_report,
        "hoyd_report": hoyd_report,
        "medical_directors_report": medical_directors_report,
        "financial_commercial_report": financial_commercial_report,
        "boardroom_dilemma": dilemma,
        "department_decisions": dept_decisions,
    }

    facs["_daily_briefing"] = briefing
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.flush()
    return briefing


def get_club_operations_hub(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Returns the complete Living Club Management Centre state for all 6 3D rooms, daily briefing, decisions, and timeline."""
    state = require_state(session, club_id, user_id)
    briefing = build_authoritative_daily_briefing(session, user_id, club_id, force_refresh=force_refresh)
    facs = dict(state.facilities_json or {})
    world_day = int(state.world_day or 1)
    staff = _resolve_staff_directory(state)

    # Fetch open and resolved inbox items
    inbox_rows = list(
        session.scalars(
            select(OwnerInboxItem)
            .where(OwnerInboxItem.club_id == club_id, OwnerInboxItem.user_id == user_id)
            .order_by(OwnerInboxItem.created_at.desc())
            .limit(80)
        ).all()
    )
    open_inbox_decisions = [
        {
            "decision_id": i.id,
            "world_day": world_day,
            "source_type": "inbox_item",
            "department": (
                "managers_office"
                if i.kind in ("manager_request", "manager_meeting", "player_unrest")
                else (
                    "academy_department"
                    if i.kind == "regen_breakthrough"
                    else (
                        "finance_commercial_office"
                        if i.kind in ("sponsor_opportunity", "regen_endorsement", "transfer_bid")
                        else "general_managers_office"
                    )
                )
            ),
            "department_label": (
                "Manager's Office"
                if i.kind in ("manager_request", "manager_meeting", "player_unrest")
                else (
                    "Academy Department"
                    if i.kind == "regen_breakthrough"
                    else (
                        "Finance & Commercial Office"
                        if i.kind in ("sponsor_opportunity", "regen_endorsement", "transfer_bid")
                        else "General Manager's Office"
                    )
                )
            ),
            "proposer_role": i.kind,
            "proposer_name": i.sender,
            "operation_key": i.kind,
            "title": i.title,
            "what": i.what,
            "why": i.why,
            "priority": i.priority,
            "status": i.status,
            "actions": i.actions_json or [],
            "payload": i.payload_json or {},
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
            "resolution": i.resolution,
            "outcome": i.outcome_text,
        }
        for i in inbox_rows
        if i.is_decision and i.status == "open" and i.archived_at is None
    ]

    dept_decisions = list(
        (facs.get("_daily_operational_decisions") or {}).get("items") or briefing.get("department_decisions") or []
    )
    dilemma = briefing.get("boardroom_dilemma")

    actionable_decisions: list[dict[str, Any]] = []
    if dilemma:
        actionable_decisions.append(
            {
                "decision_id": "boardroom_dilemma",
                "world_day": world_day,
                "source_type": "boardroom_dilemma",
                "department": "executive_office",
                "department_label": "Executive Office",
                "proposer_role": "boardroom",
                "proposer_name": f"{dilemma.get('role_a')} vs {dilemma.get('role_b')}",
                "operation_key": "resolve_dilemma",
                "title": dilemma.get("title", "Boardroom Dilemma"),
                "what": dilemma.get("conflict_summary", ""),
                "why": "Executive alignment decision affecting staff mood, squad morale, and treasury policy.",
                "priority": "high",
                "status": dilemma.get("status", "open"),
                "actions": [
                    {
                        "key": c.get("choice_id"),
                        "label": c.get("label"),
                        "summary": c.get("summary"),
                        "effects_preview": c.get("effects_preview"),
                        "style": "primary",
                    }
                    for c in (dilemma.get("choices") or [])
                ],
                "payload": dilemma,
                "created_at": briefing.get("created_at"),
                "resolved_at": dilemma.get("resolved_at"),
                "resolution": dilemma.get("selected_choice_id"),
                "outcome": dilemma.get("resolution_outcome"),
            }
        )
    actionable_decisions.extend(dept_decisions)
    actionable_decisions.extend(open_inbox_decisions)

    # Decision History (persisted across world days + resolved inbox items)
    persisted_decision_history = list(facs.get("_operational_decision_history") or [])
    resolved_inbox_history = [
        {
            "decision_id": i.id,
            "world_day": world_day,
            "source_type": "inbox_item",
            "title": i.title,
            "sender": i.sender,
            "status": i.status,
            "resolution": i.resolution,
            "outcome": i.outcome_text,
            "resolved_at": (i.resolved_at or i.created_at).isoformat() if (i.resolved_at or i.created_at) else None,
        }
        for i in inbox_rows
        if i.status == "resolved" and (i.is_decision or i.kind in ("operational_decision", "meeting_minutes"))
    ]
    seen_hist_ids = {h.get("decision_id") for h in persisted_decision_history}
    combined_history = list(persisted_decision_history)
    for rh in resolved_inbox_history:
        if rh["decision_id"] not in seen_hist_ids:
            combined_history.append(rh)

    # Broadcast events for timeline
    b_rows = list(
        session.scalars(
            select(OwnerBroadcastEvent)
            .where(OwnerBroadcastEvent.club_id == club_id, OwnerBroadcastEvent.status == "active")
            .order_by(OwnerBroadcastEvent.created_at.desc())
            .limit(12)
        ).all()
    )
    previous_events: list[dict[str, Any]] = []
    for b in b_rows:
        previous_events.append(
            {
                "event_id": f"broadcast:{b.id}",
                "event_type": b.event_type,
                "headline": b.headline,
                "summary": b.summary,
                "world_day": _safe_int((b.payload_json or {}).get("world_day"), world_day),
                "occurred_at": b.created_at.isoformat() if b.created_at else None,
            }
        )
    for m in briefing["executive_briefing"]["match_performance"]["recent_results"]:
        previous_events.append(
            {
                "event_id": f"match:{m.get('id')}",
                "event_type": "match_result",
                "headline": f"Round {m.get('round_number', m.get('round', 1))}: {m.get('home_name')} {m.get('home_score', m.get('home_goals', 0))} - {m.get('away_score', m.get('away_goals', 0))} {m.get('away_name')}",
                "summary": f"Attendance: {m.get('attendance') or 'N/A'} · Gate: {m.get('gate_receipts_gtex') or 0} GTX · TV: {m.get('tv_revenue') or 0} GTX",
                "world_day": world_day,
                "occurred_at": m.get("played_at"),
            }
        )

    open_decisions_list = [d for d in actionable_decisions if d.get("status") == "open"]
    resolved_today_list = [d for d in actionable_decisions if d.get("status") in ("resolved", "approved", "rejected")]

    now_iso = (
        state.last_world_tick_date.isoformat() if state.last_world_tick_date else datetime.now(timezone.utc).isoformat()
    )

    timeline_events: list[dict[str, Any]] = []
    for ev in previous_events:
        timeline_events.append(
            {
                "id": ev["event_id"],
                "world_day": ev["world_day"],
                "department": "club_operations",
                "title": ev["headline"],
                "detail": ev["summary"],
                "category": ev["event_type"],
                "created_at": ev.get("occurred_at") or now_iso,
            }
        )
    for h in combined_history[:10]:
        timeline_events.append(
            {
                "id": f"decision:{h.get('decision_id')}",
                "world_day": _safe_int(h.get("world_day"), world_day),
                "department": h.get("department", "executive_office"),
                "title": h.get("title", "Operational Decision"),
                "detail": h.get("outcome") or h.get("resolution") or f"Status: {h.get('status')}",
                "category": "decision",
                "created_at": h.get("resolved_at") or now_iso,
            }
        )
    if not timeline_events:
        timeline_events.append(
            {
                "id": f"init:{club_id}:{world_day}",
                "world_day": world_day,
                "department": "executive_office",
                "title": "Living Club Operations Hub Active",
                "detail": f"All 6 departmental centres synchronized for Day {world_day}.",
                "category": "system",
                "created_at": now_iso,
            }
        )

    operational_timeline = {
        "current_operational_day": {
            "world_day": world_day,
            "world_date": state.last_world_tick_date.isoformat() if state.last_world_tick_date else None,
            "briefing_id": briefing["id"],
            "open_decisions_count": len(open_decisions_list),
            "resolved_today_count": len(resolved_today_list),
        },
        "previous_club_events": previous_events[:10],
        "outstanding_decisions": open_decisions_list,
        "scheduled_activities": (
            list(briefing["general_managers_report"]["administrative_matters"]["scheduled_meetings"])
            + [
                {
                    "activity_id": p.get("project_id"),
                    "activity_type": "campus_construction",
                    "title": f"Campus Construction: {p.get('module_name')} (Level {p.get('target_level', 1)})",
                    "status": p.get("stage", "in_progress"),
                    "progress_pct": p.get("progress_pct", 25),
                    "scheduled_world_day": p.get("start_world_day", world_day),
                }
                for p in briefing["executive_briefing"]["stadium_and_campus"]["active_projects"]
            ]
        ),
        "upcoming_commitments": briefing["executive_briefing"]["match_performance"]["upcoming_fixtures"],
        "newly_generated_reports": [
            {
                "section_key": s["section_key"],
                "role": s["role"],
                "sender": s["sender"],
                "title": s["title"],
                "generated_world_day": world_day,
            }
            for s in briefing["sections"]
        ],
        "decision_history": combined_history[:25],
    }

    # Build the 6 Interactive 3D Operational Destinations
    chat_history = list(facs.get("_staff_chat_history") or [])

    destinations = [
        {
            "destination_key": "executive_office",
            "destination_id": "executive_office",
            "label": "Executive Office",
            "title": "Executive Office",
            "short_label": "Executive",
            "subtitle": "Owner's Daily Briefing, Strategic Decisions & Club Command",
            "lead_role_key": "general_manager",
            "wing_label": "Central Penthouses · Floor 4",
            "glb_model": "/models/campus/club_hq.glb",
            "model_glb_url": "/models/campus/club_hq.glb",
            "exterior_glb": "/models/campus/club_hq.glb",
            "accent_color": "#10b981",
            "position_3d": [0, 0, 0],
            "camera_position": [0, 13, 21],
            "camera_target": [0, 2.5, 0],
            "camera_preset": {"position": [0, 13, 21], "target": [0, 2.5, 0], "fov": 42},
            "staff_lead": {
                "role_key": "general_manager",
                "role_label": "Chairman & Majority Owner",
                "name": "Office of the Club Owner",
                "style": "Strategic Governance",
                "mood": 92,
                "loyalty": 20,
                "specialty": "Club Strategy & Treasury Oversight",
                "portrait_url": storytelling.resolve_club_crest_url(session, club_id, state.club_name),
            },
            "alert_count": len(open_decisions_list),
            "status_badge": (
                f"{len(open_decisions_list)} Action(s) Pending" if open_decisions_list else "All Briefings Clear"
            ),
            "hotspots": [
                {
                    "id": "exec_desk",
                    "hotspot_id": "exec_desk",
                    "label": "Chairman's Briefing Desk",
                    "action": "inspect_briefing",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "dilemma_table",
                    "hotspot_id": "dilemma_table",
                    "label": "Boardroom Dilemma Holo-Table",
                    "action": "inspect_decisions",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "world_chronometer",
                    "hotspot_id": "world_chronometer",
                    "label": "World-Clock Timeline Wall",
                    "action": "inspect_timeline",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "executive_briefing",
            "report": briefing["executive_briefing"],
            "open_decisions": [
                d for d in open_decisions_list if d.get("department") in ("executive_office", "boardroom")
            ],
            "open_decisions_count": len(
                [d for d in open_decisions_list if d.get("department") in ("executive_office", "boardroom")]
            ),
            "recent_messages": [m for m in chat_history if m.get("role") in ("general_manager", "owner")][-6:],
        },
        {
            "destination_key": "managers_office",
            "destination_id": "managers_office",
            "label": "Manager's Office",
            "title": "Manager's Office",
            "short_label": "Manager",
            "subtitle": "First-Team Squad, Tactical Mentality & Matchday Preparation",
            "lead_role_key": "first_team_manager",
            "wing_label": "West Sporting Wing · Floor 2",
            "glb_model": "/models/campus/stadium_main.glb",
            "model_glb_url": "/models/campus/stadium_main.glb",
            "exterior_glb": "/models/campus/stadium_main.glb",
            "accent_color": "#38bdf8",
            "position_3d": [-15, 0, 6],
            "camera_position": [-19, 10, 18],
            "camera_target": [-14, 2, 4],
            "camera_preset": {"position": [-19, 10, 18], "target": [-14, 2, 4], "fov": 40},
            "staff_lead": staff["first_team_manager"],
            "alert_count": len([d for d in open_decisions_list if d.get("department") == "managers_office"]),
            "status_badge": f"Mentality: {str(state.mentality or 'balanced').title()}",
            "hotspots": [
                {
                    "id": "tactical_pitch_table",
                    "hotspot_id": "tactical_pitch_table",
                    "label": "3D Tactical Formation Table",
                    "action": "set_mentality",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "dugout_prep_screen",
                    "hotspot_id": "dugout_prep_screen",
                    "label": "Matchday Win-Bonus Console",
                    "action": "pledge_win_bonus",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "manager_desk",
                    "hotspot_id": "manager_desk",
                    "label": f"Direct Line: {staff['first_team_manager']['name']}",
                    "action": "chat_manager",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "managers_report",
            "report": briefing["managers_report"],
            "open_decisions": [d for d in open_decisions_list if d.get("department") == "managers_office"],
            "open_decisions_count": len([d for d in open_decisions_list if d.get("department") == "managers_office"]),
            "recent_messages": [m for m in chat_history if m.get("role") in ("first_team_manager", "manager")][-6:],
        },
        {
            "destination_key": "general_managers_office",
            "destination_id": "general_managers_office",
            "label": "General Manager's Office",
            "title": "General Manager's Office",
            "short_label": "General Mgr",
            "subtitle": "Club Administration, Delegation Policy & Campus Masterplan",
            "lead_role_key": "general_manager",
            "wing_label": "East Executive Wing · Floor 3",
            "glb_model": "/models/campus/vip_skybox_concourse.glb",
            "model_glb_url": "/models/campus/vip_skybox_concourse.glb",
            "exterior_glb": "/models/campus/vip_skybox_concourse.glb",
            "accent_color": "#a855f7",
            "position_3d": [15, 0, 6],
            "camera_position": [19, 10, 18],
            "camera_target": [14, 2, 4],
            "camera_preset": {"position": [19, 10, 18], "target": [14, 2, 4], "fov": 40},
            "staff_lead": staff["general_manager"],
            "alert_count": len([d for d in open_decisions_list if d.get("department") == "general_managers_office"]),
            "status_badge": f"Mode: {str(briefing['general_managers_report']['administrative_matters']['delegation_policy'].get('mode', 'balanced')).title()}",
            "hotspots": [
                {
                    "id": "delegation_console",
                    "hotspot_id": "delegation_console",
                    "label": "Authority & Delegation Matrix",
                    "action": "configure_delegation",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "campus_blueprint",
                    "hotspot_id": "campus_blueprint",
                    "label": "Campus Construction Blueprint",
                    "action": "inspect_campus",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "gm_desk",
                    "hotspot_id": "gm_desk",
                    "label": f"Direct Line: {staff['general_manager']['name']}",
                    "action": "chat_gm",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "general_managers_report",
            "report": briefing["general_managers_report"],
            "open_decisions": [d for d in open_decisions_list if d.get("department") == "general_managers_office"],
            "open_decisions_count": len(
                [d for d in open_decisions_list if d.get("department") == "general_managers_office"]
            ),
            "recent_messages": [m for m in chat_history if m.get("role") == "general_manager"][-6:],
        },
        {
            "destination_key": "academy_department",
            "destination_id": "academy_department",
            "label": "Academy Department",
            "title": "Academy Department",
            "short_label": "Academy",
            "subtitle": "Youth Development Pipeline, Regen Progression & Scouting Intake",
            "lead_role_key": "head_of_youth_development",
            "wing_label": "North Youth Precinct · Floor 1",
            "glb_model": "/models/campus/elite_academy_complex.glb",
            "model_glb_url": "/models/campus/elite_academy_complex.glb",
            "exterior_glb": "/models/campus/elite_academy_complex.glb",
            "accent_color": "#f59e0b",
            "position_3d": [-14, 0, -14],
            "camera_position": [-18, 9, -10],
            "camera_target": [-13, 2, -14],
            "camera_preset": {"position": [-18, 9, -10], "target": [-13, 2, -14], "fov": 40},
            "staff_lead": staff["head_of_youth_development"],
            "alert_count": len([d for d in open_decisions_list if d.get("department") == "academy_department"]),
            "status_badge": f"{len(briefing['hoyd_report']['prospective_youth_players'])} Academy Regen(s)",
            "hotspots": [
                {
                    "id": "youth_pitch_lab",
                    "hotspot_id": "youth_pitch_lab",
                    "label": "Youth Intake Commissioning Desk",
                    "action": "commission_intake",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "regen_scanner",
                    "hotspot_id": "regen_scanner",
                    "label": "Scholar Contract & Promotion Terminal",
                    "action": "manage_regens",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "hoyd_desk",
                    "hotspot_id": "hoyd_desk",
                    "label": f"Direct Line: {staff['head_of_youth_development']['name']}",
                    "action": "chat_hoyd",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "hoyd_report",
            "report": briefing["hoyd_report"],
            "open_decisions": [d for d in open_decisions_list if d.get("department") == "academy_department"],
            "open_decisions_count": len(
                [d for d in open_decisions_list if d.get("department") == "academy_department"]
            ),
            "recent_messages": [m for m in chat_history if m.get("role") == "head_of_youth_development"][-6:],
        },
        {
            "destination_key": "medical_department",
            "destination_id": "medical_department",
            "label": "Medical Department",
            "title": "Medical Department",
            "short_label": "Medical",
            "subtitle": "Injury Rehabilitation, Hydrotherapy & Workload Telemetry",
            "lead_role_key": "medical_director",
            "wing_label": "South Sports-Science Lab · Floor 1",
            "glb_model": "/models/campus/recovery_hydro_hub.glb",
            "model_glb_url": "/models/campus/recovery_hydro_hub.glb",
            "exterior_glb": "/models/campus/recovery_hydro_hub.glb",
            "accent_color": "#ec4899",
            "position_3d": [14, 0, -14],
            "camera_position": [18, 9, -10],
            "camera_target": [13, 2, -14],
            "camera_preset": {"position": [18, 9, -10], "target": [13, 2, -14], "fov": 40},
            "staff_lead": staff["medical_director"],
            "alert_count": len([d for d in open_decisions_list if d.get("department") == "medical_department"])
            + len(briefing["medical_directors_report"]["injured_players"]),
            "status_badge": (
                f"{len(briefing['medical_directors_report']['injured_players'])} In Rehab"
                if briefing["medical_directors_report"]["injured_players"]
                else f"{briefing['medical_directors_report']['squad_fitness_concerns']['avg_squad_fitness']}% Avg Fitness"
            ),
            "hotspots": [
                {
                    "id": "hydro_rehab_pods",
                    "hotspot_id": "hydro_rehab_pods",
                    "label": "Hydro & Cryo Rehabilitation Bay",
                    "action": "run_conditioning",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "workload_telemetry",
                    "hotspot_id": "workload_telemetry",
                    "label": "Player Strain & Load Monitor",
                    "action": "inspect_workloads",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "med_desk",
                    "hotspot_id": "med_desk",
                    "label": f"Direct Line: {staff['medical_director']['name']}",
                    "action": "chat_med",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "medical_directors_report",
            "report": briefing["medical_directors_report"],
            "open_decisions": [d for d in open_decisions_list if d.get("department") == "medical_department"],
            "open_decisions_count": len(
                [d for d in open_decisions_list if d.get("department") == "medical_department"]
            ),
            "recent_messages": [m for m in chat_history if m.get("role") == "medical_director"][-6:],
        },
        {
            "destination_key": "finance_commercial_office",
            "destination_id": "finance_commercial_office",
            "label": "Finance & Commercial Office",
            "title": "Finance & Commercial Office",
            "short_label": "Finance",
            "subtitle": "Club Treasury, Authoritative Ledger, Sponsorships & Matchday Revenue",
            "lead_role_key": "general_manager",
            "wing_label": "East Treasury Vault · Floor 3",
            "glb_model": "/models/campus/high_performance_centre.glb",
            "model_glb_url": "/models/campus/high_performance_centre.glb",
            "exterior_glb": "/models/campus/high_performance_centre.glb",
            "accent_color": "#22d3ee",
            "position_3d": [0, 0, -18],
            "camera_position": [0, 11, -12],
            "camera_target": [0, 2, -18],
            "camera_preset": {"position": [0, 11, -12], "target": [0, 2, -18], "fov": 40},
            "staff_lead": staff["general_manager"],
            "alert_count": len([d for d in open_decisions_list if d.get("department") == "finance_commercial_office"]),
            "status_badge": f"{briefing['metrics']['cash_gtex']:,} GTX",
            "hotspots": [
                {
                    "id": "ledger_vault",
                    "hotspot_id": "ledger_vault",
                    "label": "Authoritative GTEX Ledger Terminal",
                    "action": "inspect_ledger",
                    "offset": [0, 1.2, 0.5],
                },
                {
                    "id": "sponsor_wall",
                    "hotspot_id": "sponsor_wall",
                    "label": "Commercial Partnership Board",
                    "action": "sign_sponsor",
                    "offset": [2.5, 1.2, -1.0],
                },
                {
                    "id": "matchday_econ",
                    "hotspot_id": "matchday_econ",
                    "label": "Gate & Broadcast Revenue Desk",
                    "action": "inspect_matchday_econ",
                    "offset": [-2.5, 1.5, -2.5],
                },
            ],
            "report_section_key": "financial_commercial_report",
            "report": briefing["financial_commercial_report"],
            "open_decisions": [d for d in open_decisions_list if d.get("department") == "finance_commercial_office"],
            "open_decisions_count": len(
                [d for d in open_decisions_list if d.get("department") == "finance_commercial_office"]
            ),
            "recent_messages": [m for m in chat_history if m.get("role") == "general_manager"][-6:],
        },
    ]

    actionable_decisions_payload = {
        "department_decisions": [d for d in actionable_decisions if d.get("source_type") != "inbox_item"],
        "inbox_decisions": open_inbox_decisions,
        "boardroom_dilemma": dilemma,
        "total_open_count": len(open_decisions_list),
        "items": actionable_decisions,
    }

    return {
        "club": {
            "club_id": state.club_id,
            "club_name": state.club_name,
            "crest_url": storytelling.resolve_club_crest_url(session, club_id, state.club_name),
            "prestige": state.prestige,
            "prestige_tier": engine.prestige_tier_label(state.prestige),
            "world_day": world_day,
            "world_date": state.last_world_tick_date.isoformat() if state.last_world_tick_date else None,
            "mentality": state.mentality,
            "stage": state.stage,
            "fans": state.fans,
        },
        "daily_briefing": briefing,
        "destinations": destinations,
        "actionable_decisions": actionable_decisions_payload,
        "operational_timeline": timeline_events,
        "operational_timeline_summary": operational_timeline,
        "decision_history": combined_history[:25],
    }


def execute_owner_operational_decision(
    session: Session,
    user_id: str,
    club_id: str,
    decision_id: str,
    *,
    action: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Executes an authoritative owner decision (department recommendation, inbox decision, or boardroom dilemma)."""
    state = require_state(session, club_id, user_id)
    world_day = int(state.world_day or 1)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Ensure today's briefing & department decisions exist
    build_authoritative_daily_briefing(session, user_id, club_id, force_refresh=False)
    facs = dict(state.facilities_json or {})

    # 1. Boardroom Dilemma Resolution
    cur_briefing = dict(facs.get("_daily_briefing") or {})
    cur_dilemma = dict(cur_briefing.get("boardroom_dilemma") or {})
    if decision_id in ("boardroom_dilemma", cur_dilemma.get("dilemma_id")):
        if cur_dilemma.get("status") == "resolved":
            raise OwnerError("decision_already_resolved", 409, "Today's boardroom dilemma has already been resolved.")
        res = storytelling.resolve_briefing_dilemma(session, user_id, club_id, action)
        facs = dict(state.facilities_json or {})
        hist = list(facs.get("_operational_decision_history") or [])
        hist.insert(
            0,
            {
                "decision_id": decision_id,
                "world_day": world_day,
                "source_type": "boardroom_dilemma",
                "department": "executive_office",
                "title": cur_dilemma.get("title", "Boardroom Dilemma"),
                "status": "resolved",
                "resolution": action,
                "outcome": res.get("outcome"),
                "note": note,
                "resolved_at": now_iso,
            },
        )
        facs["_operational_decision_history"] = hist[:50]
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        hub = get_club_operations_hub(session, user_id, club_id, force_refresh=True)
        return {
            "status": "resolved",
            "decision_id": decision_id,
            "resolution": action,
            "outcome": res.get("outcome"),
            "decision": {
                "decision_id": decision_id,
                "status": "resolved",
                "resolution": action,
                "outcome": res.get("outcome"),
            },
            "operations_hub": hub,
        }

    # 2. Department Operational Recommendation Resolution
    dept_store = dict(facs.get("_daily_operational_decisions") or {})
    dept_items = list(dept_store.get("items") or [])
    target_rec = next((d for d in dept_items if d.get("decision_id") == decision_id), None)

    if target_rec is not None:
        if target_rec.get("status") != "open":
            raise OwnerError(
                "decision_already_resolved",
                409,
                f"Decision '{decision_id}' has already been resolved ({target_rec.get('resolution')}).",
            )

        norm_action = action.strip().lower()
        if norm_action not in ("approve", "accept", "reject", "decline"):
            raise OwnerError("invalid_decision_action", 400, f"Action '{action}' must be 'approve' or 'reject'.")

        is_approved = norm_action in ("approve", "accept")
        op_key = str(target_rec.get("operation_key") or "")
        payload = dict(target_rec.get("payload") or {})
        proposer_role = str(target_rec.get("proposer_role") or "general_manager")
        ledger_event_id: str | None = None
        outcome_text = ""

        if not is_approved:
            # Rejection path: adjust proposer mood slightly and record rejection
            exec_staff = dict(facs.get("_executive_staff") or {})
            if proposer_role == "first_team_manager":
                mgr = dict(state.manager_json or {})
                mgr["mood"] = int(engine.clamp(_safe_int(mgr.get("mood"), 75) - 3, 0, 100))
                state.manager_json = mgr
                flag_modified(state, "manager_json")
            elif proposer_role in exec_staff and isinstance(exec_staff[proposer_role], dict):
                st = dict(exec_staff[proposer_role])
                st["mood"] = int(engine.clamp(_safe_int(st.get("mood"), 75) - 3, 0, 100))
                exec_staff[proposer_role] = st
                facs["_executive_staff"] = exec_staff
            outcome_text = (
                f"Proposal rejected by Club Owner ({target_rec.get('proposer_name')} mood -3). No funds committed."
            )
            resolution_label = "rejected"
        else:
            resolution_label = "approved"
            if op_key == "pledge_win_bonus":
                amt = _safe_int(payload.get("amount_gtex"), 1200)
                res = service.pledge_win_bonus(
                    session, user_id, club_id, amt, note or str(payload.get("note") or "Approved in Executive Briefing")
                )
                facs = dict(state.facilities_json or {})
                outcome_text = (
                    f"Approved {amt:,} GTX pre-match win bonus. Squad morale +{res['squad_morale_boost']}, "
                    f"Manager mood +{res['manager_mood_boost']}."
                )
            elif op_key == "align_tactical_mentality":
                new_mentality = str(payload.get("mentality") or "attacking")
                state.mentality = new_mentality
                mgr = dict(state.manager_json or {})
                mgr["mood"] = int(engine.clamp(_safe_int(mgr.get("mood"), 75) + 4, 0, 100))
                state.manager_json = mgr
                flag_modified(state, "manager_json")
                for p in session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all():
                    p.morale = int(engine.clamp(p.morale + 2, 0, 100))
                outcome_text = f"Adopted '{new_mentality}' tactical match plan (+4 Manager Mood, +2 Squad Morale)."
            elif op_key == "advance_campus_stage":
                inst_id = str(payload.get("instance_id") or "")
                res = prestige_campus_comms.start_campus_construction(
                    session,
                    user_id,
                    club_id,
                    operation="advance_stage",
                    instance_id=inst_id,
                )
                facs = dict(state.facilities_json or {})
                proj = res.get("project") or {}
                outcome_text = (
                    f"Advanced {proj.get('module_name', 'Campus Module')} to {proj.get('progress_pct', 100)}% "
                    f"({proj.get('stage', 'completed')})."
                )
            elif op_key == "upgrade_facility":
                fac_kind = str(payload.get("facility") or "training")
                res = service.upgrade_facility(session, user_id, club_id, fac_kind)
                facs = dict(state.facilities_json or {})
                outcome_text = f"Upgraded {fac_kind.title()} facility to Level {res['level']} for {res['cost']:,} GTX. {res['effect']}"
            elif op_key == "academy_contract":
                pid = str(payload.get("player_id") or "")
                res = service.academy_contract(session, user_id, club_id, pid)
                facs = dict(state.facilities_json or {})
                outcome_text = (
                    f"Awarded improved academy contract to {res['player']['name']} for {res['cost_gtex']:,} GTX "
                    f"(+{res['morale_boost']} Morale, +{res['loyalty_boost']} Loyalty)."
                )
            elif op_key == "academy_intake":
                regens = service.academy_intake(session, user_id, club_id)
                facs = dict(state.facilities_json or {})
                names = ", ".join(f"{r.name} ({r.position}, OVR {r.rating}/POT {r.potential})" for r in regens)
                outcome_text = f"Commissioned Academy Intake: inducted {len(regens)} new prospect(s) ({names})."
            elif op_key == "medical_conditioning_protocol":
                cost = _safe_int(payload.get("cost_gtex"), 800)
                club_acct = ledger.club_account(club_id)
                bal = ledger.balance(session, club_acct, ledger.GTEX)
                if bal < cost:
                    raise OwnerError(
                        "insufficient_club_cash",
                        400,
                        f"Club balance ({bal} GTX) is insufficient for {cost} GTX medical conditioning protocol.",
                    )
                leg = ledger.record(
                    session,
                    event_type="medical_conditioning_protocol",
                    source=club_acct,
                    destination=ledger.WORLD_CLUBS,
                    currency=ledger.GTEX,
                    gross=cost,
                    club_id=club_id,
                    user_id=user_id,
                    related_type="medical_protocol",
                    related_id=decision_id,
                    memo=f"Sports-science hydro & cryo recovery protocol (World Day {world_day})",
                )
                ledger_event_id = leg.id
                squad_rows = list(
                    session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all()
                )
                rehab_accelerated = 0
                for p in squad_rows:
                    pers = dict(p.personality_json or {})
                    cur_fit = _safe_int(pers.get("fitness", 95), 95)
                    pers["fitness"] = int(engine.clamp(cur_fit + 6, 0, 100))
                    p.personality_json = pers
                    flag_modified(p, "personality_json")
                    if _safe_int(p.injured_days, 0) > 0:
                        p.injured_days = max(0, int(p.injured_days) - 1)
                        rehab_accelerated += 1
                exec_staff = dict(facs.get("_executive_staff") or {})
                if "medical_director" in exec_staff and isinstance(exec_staff["medical_director"], dict):
                    med_st = dict(exec_staff["medical_director"])
                    med_st["mood"] = int(engine.clamp(_safe_int(med_st.get("mood"), 84) + 6, 0, 100))
                    exec_staff["medical_director"] = med_st
                    facs["_executive_staff"] = exec_staff
                outcome_text = (
                    f"Executed Hydro & Cryo Conditioning Protocol ({cost:,} GTX): +6% squad fitness restored "
                    f"and {rehab_accelerated} injured player(s) accelerated by 1 rehab day."
                )
            elif op_key == "sign_sponsor_offer":
                offer_id = str(payload.get("offer_id") or "")
                res = service.sign_sponsor_offer(session, user_id, club_id, offer_id)
                facs = dict(state.facilities_json or {})
                deal = res.get("deal") or {}
                outcome_text = (
                    f"Ratified {deal.get('sponsor_name', payload.get('sponsor_name'))} sponsorship: "
                    f"+{res.get('upfront_bonus_credited_gtex', 0):,} GTX signing bonus credited to treasury (+1 Prestige)."
                )
            else:
                raise OwnerError("unsupported_operation", 400, f"Unsupported operation key '{op_key}'.")

        # Update the target recommendation item in `_daily_operational_decisions`
        for d in dept_items:
            if d.get("decision_id") == decision_id:
                d["status"] = resolution_label
                d["resolution"] = resolution_label
                d["outcome"] = outcome_text
                d["resolved_at"] = now_iso
                d["ledger_event_id"] = ledger_event_id
                if note:
                    d["decision_note"] = note

        facs["_daily_operational_decisions"] = {
            "world_day": world_day,
            "club_id": club_id,
            "items": dept_items,
        }

        # Append to durable `_operational_decision_history`
        hist = list(facs.get("_operational_decision_history") or [])
        hist.insert(
            0,
            {
                "decision_id": decision_id,
                "world_day": world_day,
                "source_type": "department_recommendation",
                "department": target_rec.get("department"),
                "department_label": target_rec.get("department_label"),
                "proposer_name": target_rec.get("proposer_name"),
                "title": target_rec.get("title"),
                "status": resolution_label,
                "resolution": resolution_label,
                "outcome": outcome_text,
                "ledger_event_id": ledger_event_id,
                "note": note,
                "resolved_at": now_iso,
            },
        )
        facs["_operational_decision_history"] = hist[:50]

        # Also record a resolved OwnerInboxItem audit log row so Inbox & Archive reflect the decision
        session.add(
            OwnerInboxItem(
                user_id=user_id,
                club_id=club_id,
                save_context_id=f"club:{club_id}",
                category="archive",
                kind="operational_decision",
                priority=str(target_rec.get("priority") or "normal"),
                sender=str(target_rec.get("proposer_name") or "Executive Staff"),
                title=str(target_rec.get("title") or "Owner Operational Decision"),
                what=str(target_rec.get("what") or ""),
                why=str(target_rec.get("why") or ""),
                payload_json={
                    "decision_id": decision_id,
                    "operation_key": op_key,
                    "ledger_event_id": ledger_event_id,
                    "world_day": world_day,
                    "note": note,
                },
                is_decision=True,
                is_read=True,
                status="resolved",
                resolution=resolution_label,
                outcome_text=outcome_text,
                resolved_at=datetime.now(timezone.utc),
            )
        )

        # Echo into staff room feed
        staff_room = list(facs.get("_staff_room_feed") or [])
        staff_room.insert(
            0,
            {
                "id": f"sr_dec_{secrets.token_hex(3)}",
                "sender_name": str(target_rec.get("proposer_name") or "Executive Staff"),
                "sender_role": str(target_rec.get("department_label") or "Department Head"),
                "department": str(target_rec.get("department_label") or "Club Operations"),
                "body": f"[{resolution_label.upper()}] {target_rec.get('title')} — {outcome_text}",
                "world_day": world_day,
                "created_at": now_iso,
            },
        )
        facs["_staff_room_feed"] = staff_room[:40]

        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()

        hub = get_club_operations_hub(session, user_id, club_id, force_refresh=True)
        return {
            "status": resolution_label,
            "decision_id": decision_id,
            "resolution": resolution_label,
            "outcome": outcome_text,
            "ledger_event_id": ledger_event_id,
            "decision": {
                "decision_id": decision_id,
                "status": resolution_label,
                "resolution": resolution_label,
                "outcome": outcome_text,
            },
            "operations_hub": hub,
        }

    # 3. Fallback to OwnerInboxItem Decision Resolution
    inbox_item = session.get(OwnerInboxItem, decision_id)
    if inbox_item is not None and inbox_item.club_id == club_id:
        resolved_item = service.resolve_item(session, user_id, decision_id, action)
        facs = dict(state.facilities_json or {})
        hist = list(facs.get("_operational_decision_history") or [])
        hist.insert(
            0,
            {
                "decision_id": resolved_item.id,
                "world_day": world_day,
                "source_type": "inbox_item",
                "department": "executive_office",
                "proposer_name": resolved_item.sender,
                "title": resolved_item.title,
                "status": resolved_item.status,
                "resolution": resolved_item.resolution,
                "outcome": resolved_item.outcome_text,
                "note": note,
                "resolved_at": now_iso,
            },
        )
        facs["_operational_decision_history"] = hist[:50]
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        hub = get_club_operations_hub(session, user_id, club_id, force_refresh=True)
        return {
            "status": resolved_item.status,
            "decision_id": resolved_item.id,
            "resolution": resolved_item.resolution,
            "outcome": resolved_item.outcome_text,
            "decision": {
                "decision_id": resolved_item.id,
                "status": resolved_item.status,
                "resolution": resolved_item.resolution,
                "outcome": resolved_item.outcome_text,
            },
            "operations_hub": hub,
        }

    raise OwnerError("decision_not_found", 404, f"Operational decision '{decision_id}' not found for club '{club_id}'.")
