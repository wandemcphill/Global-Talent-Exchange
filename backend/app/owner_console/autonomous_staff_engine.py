from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.owner_console import ledger
from app.owner_console.models import (
    ClubDelegatedDecision,
    ClubDelegationPolicy,
    OwnerClubDirective,
    OwnerClubMeeting,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerInboxItem,
    OwnerRecruitmentAssignment,
    OwnerScoutingWatchlist,
    OwnerSquadPlayer,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _personality_score(key: str, value: int | float) -> int:
    """Staff skills are 1-20. Personality attributes are 0-100."""
    number = float(value)
    if key in {"tactical_flexibility", "tactical_quality", "youth_development"} and number <= 20:
        number *= 5
    return _clamp(number)


def _stable_hash_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)


def _club_treasury_gtex(db: Session, state: OwnerClubState) -> float:
    try:
        return float(ledger.balance(db, ledger.club_account(state.club_id), ledger.GTEX))
    except Exception:
        fac = dict(state.facilities_json or {})
        if "_treasury_override_gtex" in fac:
            return float(fac["_treasury_override_gtex"])
        return 0.0


def _player_fitness(p: OwnerSquadPlayer) -> int | None:
    pers = dict(p.personality_json or {})
    if "fitness" not in pers or pers.get("fitness") is None:
        return None
    return _clamp(int(pers["fitness"]), 10, 100)


def _player_is_academy(p: OwnerSquadPlayer) -> bool:
    pers = dict(p.personality_json or {})
    return bool(p.is_regen or pers.get("is_academy") or (p.age is not None and int(p.age) <= 18))


def _optional_score(source: dict[str, Any] | None, *keys: str) -> int | None:
    record = source or {}
    for key in keys:
        if key not in record or record.get(key) is None:
            continue
        try:
            return int(record[key])
        except (TypeError, ValueError):
            continue
    return None


# ---------------------------------------------------------------------------
# SECTION 2: PERSISTENT STAFF IDENTITIES & FICTIONAL ARCHETYPES
# ---------------------------------------------------------------------------

MANAGER_ARCHETYPES: dict[str, dict[str, Any]] = {
    "youth_development_visionary": {
        "archetype_key": "youth_development_visionary",
        "archetype_label": "Youth-Development Visionary",
        "preferred_tactical_philosophy": "positional_play",
        "attacking_vs_defensive": 76,
        "preferred_formations": ["4-3-3", "4-2-3-1", "3-4-2-1"],
        "possession_vs_direct": 78,
        "pressing_philosophy": 74,
        "tactical_flexibility": 72,
        "adaptability": 75,
        "youth_development_commitment": 92,
        "trust_in_young_players": 89,
        "willingness_to_promote_academy": 91,
        "preference_for_experienced_players": 34,
        "player_discipline_philosophy": 70,
        "dressing_room_management_style": "collaborative_mentor",
        "tolerance_for_owner_interference": 58,
        "professional_independence": 72,
        "ambition": 82,
        "ego_reputation_sensitivity": 55,
        "loyalty": 78,
        "negotiating_temperament": "constructive",
        "risk_tolerance": 76,
        "communication_style": "measured_analytical",
        "ability_to_handle_pressure": 77,
        "preferred_squad_composition": "academy_core_with_leaders",
    },
    "veteran_pragmatist": {
        "archetype_key": "veteran_pragmatist",
        "archetype_label": "Experienced-Player Pragmatist",
        "preferred_tactical_philosophy": "catenaccio_pragmatism",
        "attacking_vs_defensive": 32,
        "preferred_formations": ["4-4-2", "5-3-2", "4-2-3-1"],
        "possession_vs_direct": 38,
        "pressing_philosophy": 42,
        "tactical_flexibility": 48,
        "adaptability": 52,
        "youth_development_commitment": 28,
        "trust_in_young_players": 24,
        "willingness_to_promote_academy": 26,
        "preference_for_experienced_players": 91,
        "player_discipline_philosophy": 88,
        "dressing_room_management_style": "authoritarian_strict",
        "tolerance_for_owner_interference": 30,
        "professional_independence": 86,
        "ambition": 79,
        "ego_reputation_sensitivity": 82,
        "loyalty": 64,
        "negotiating_temperament": "unyielding",
        "risk_tolerance": 29,
        "communication_style": "blunt_candid",
        "ability_to_handle_pressure": 88,
        "preferred_squad_composition": "experienced_battle_tested",
    },
    "high_pressing_autocrat": {
        "archetype_key": "high_pressing_autocrat",
        "archetype_label": "High-Pressing Tactical Autocrat",
        "preferred_tactical_philosophy": "gegenpress",
        "attacking_vs_defensive": 82,
        "preferred_formations": ["4-2-3-1", "4-3-3", "4-2-2-2"],
        "possession_vs_direct": 62,
        "pressing_philosophy": 94,
        "tactical_flexibility": 54,
        "adaptability": 58,
        "youth_development_commitment": 64,
        "trust_in_young_players": 62,
        "willingness_to_promote_academy": 60,
        "preference_for_experienced_players": 58,
        "player_discipline_philosophy": 90,
        "dressing_room_management_style": "intense_demanding",
        "tolerance_for_owner_interference": 18,
        "professional_independence": 95,
        "ambition": 92,
        "ego_reputation_sensitivity": 88,
        "loyalty": 56,
        "negotiating_temperament": "principled",
        "risk_tolerance": 80,
        "communication_style": "intense_demanding",
        "ability_to_handle_pressure": 84,
        "preferred_squad_composition": "high_energy_u24_pressers",
    },
    "balanced_collaborator": {
        "archetype_key": "balanced_collaborator",
        "archetype_label": "Balanced Tactical Modernist",
        "preferred_tactical_philosophy": "balanced_control",
        "attacking_vs_defensive": 60,
        "preferred_formations": ["4-2-3-1", "4-3-3", "3-5-2"],
        "possession_vs_direct": 64,
        "pressing_philosophy": 65,
        "tactical_flexibility": 80,
        "adaptability": 82,
        "youth_development_commitment": 58,
        "trust_in_young_players": 56,
        "willingness_to_promote_academy": 58,
        "preference_for_experienced_players": 62,
        "player_discipline_philosophy": 74,
        "dressing_room_management_style": "meritocratic_demanding",
        "tolerance_for_owner_interference": 52,
        "professional_independence": 74,
        "ambition": 76,
        "ego_reputation_sensitivity": 60,
        "loyalty": 75,
        "negotiating_temperament": "diplomatic",
        "risk_tolerance": 55,
        "communication_style": "diplomatic_warm",
        "ability_to_handle_pressure": 79,
        "preferred_squad_composition": "balanced_two_per_position",
    },
    "possession_architect": {
        "archetype_key": "possession_architect",
        "archetype_label": "Positional Play Architect",
        "preferred_tactical_philosophy": "positional_play",
        "attacking_vs_defensive": 78,
        "preferred_formations": ["4-3-3", "3-2-4-1", "4-2-3-1"],
        "possession_vs_direct": 92,
        "pressing_philosophy": 84,
        "tactical_flexibility": 65,
        "adaptability": 64,
        "youth_development_commitment": 78,
        "trust_in_young_players": 76,
        "willingness_to_promote_academy": 75,
        "preference_for_experienced_players": 48,
        "player_discipline_philosophy": 82,
        "dressing_room_management_style": "analytical_detached",
        "tolerance_for_owner_interference": 28,
        "professional_independence": 89,
        "ambition": 90,
        "ego_reputation_sensitivity": 84,
        "loyalty": 68,
        "negotiating_temperament": "principled",
        "risk_tolerance": 72,
        "communication_style": "measured_analytical",
        "ability_to_handle_pressure": 86,
        "preferred_squad_composition": "technical_specialists",
    },
}

GM_ARCHETYPES: dict[str, dict[str, Any]] = {
    "financially_conservative_guardian": {
        "archetype_key": "financially_conservative_guardian",
        "archetype_label": "Financially Conservative Sporting Director",
        "recruitment_philosophy": "undervalued_analytics",
        "financial_discipline": 92,
        "transfer_risk_tolerance": 28,
        "wage_structure_philosophy": "strict_tiered_cap",
        "contract_negotiation_ability": 88,
        "youth_recruitment_preference": 82,
        "commercial_ambition": 74,
        "squad_planning_philosophy": "long_term_succession",
        "relationship_with_first_team_manager": 70,
        "owner_alignment": 76,
        "delegation_preferences": "autonomous_within_caps",
        "decision_making_independence": 84,
        "communication_style": "measured_analytical",
        "negotiating_temperament": "principled",
    },
    "ambitious_squad_architect": {
        "archetype_key": "ambitious_squad_architect",
        "archetype_label": "Ambitious Marquee Squad Builder",
        "recruitment_philosophy": "proven_marquee",
        "financial_discipline": 54,
        "transfer_risk_tolerance": 84,
        "wage_structure_philosophy": "star_flexible",
        "contract_negotiation_ability": 85,
        "youth_recruitment_preference": 48,
        "commercial_ambition": 91,
        "squad_planning_philosophy": "win_now_window",
        "relationship_with_first_team_manager": 78,
        "owner_alignment": 72,
        "delegation_preferences": "executive_board_aligned",
        "decision_making_independence": 80,
        "communication_style": "intense_demanding",
        "negotiating_temperament": "transactional",
    },
    "analytics_moneyball_strategist": {
        "archetype_key": "analytics_moneyball_strategist",
        "archetype_label": "Data-Driven Recruitment Strategist",
        "recruitment_philosophy": "u23_resale_growth",
        "financial_discipline": 84,
        "transfer_risk_tolerance": 46,
        "wage_structure_philosophy": "incentive_heavy",
        "contract_negotiation_ability": 82,
        "youth_recruitment_preference": 88,
        "commercial_ambition": 76,
        "squad_planning_philosophy": "asset_value_protection",
        "relationship_with_first_team_manager": 72,
        "owner_alignment": 78,
        "delegation_preferences": "collaborative_signoff",
        "decision_making_independence": 79,
        "communication_style": "measured_analytical",
        "negotiating_temperament": "constructive",
    },
}

FICTIONAL_STAFF_CATALOG: dict[str, list[dict[str, Any]]] = {
    "general_manager": [
        {
            "id": "gm_matteo_valenti",
            "name": "Matteo Valenti",
            "role": "general_manager",
            "title": "General Manager",
            "specialty": "Cap Efficiency & Squad Architecture",
            "style": "analytics",
            "rating": 88,
            "salary_weekly": 44000,
            "bio": "Former sporting lawyer and recruitment strategist known for strict wage-band governance and multi-window squad succession planning.",
            "archetype_key": "financially_conservative_guardian",
        },
        {
            "id": "gm_helena_lindqvist",
            "name": "Helena Lindqvist",
            "role": "general_manager",
            "title": "General Manager",
            "specialty": "European Recruitment & Asset Value",
            "style": "youth_focus",
            "rating": 86,
            "salary_weekly": 41000,
            "bio": "Scandinavian football executive specialising in U23 talent pipelines, release-clause arbitrage, and sustainable club growth.",
            "archetype_key": "analytics_moneyball_strategist",
        },
        {
            "id": "gm_diego_montes",
            "name": "Diego Montes",
            "role": "general_manager",
            "title": "General Manager",
            "specialty": "Elite Negotiations & Commercial Scale",
            "style": "star_recruitment",
            "rating": 89,
            "salary_weekly": 48000,
            "bio": "High-profile dealmaker who builds title-contending squads through decisive flagship acquisitions and aggressive contract structuring.",
            "archetype_key": "ambitious_squad_architect",
        },
    ],
    "chief_scout": [
        {
            "id": "scout_lucas_vermeer",
            "name": "Lucas Vermeer",
            "role": "chief_scout",
            "title": "Chief Scout",
            "specialty": "Tactical Fit & GSI Profiling",
            "style": "analytics",
            "rating": 87,
            "salary_weekly": 28000,
            "bio": "Combines live video scouting across 18 leagues with predictive GSI trajectory modelling.",
            "personality_profile": {
                "archetype_key": "data_tactical_scout",
                "archetype_label": "Predictive Tactical Scout",
                "market_analytics": 91,
                "network_reach": 86,
                "value_discipline": 85,
                "gsi_accuracy": 90,
                "youth_bias": 78,
                "tactical_fit_rigor": 89,
                "professional_independence": 76,
                "communication_style": "measured_analytical",
            },
        },
    ],
    "head_of_youth_development": [
        {
            "id": "youth_claire_moreau",
            "name": "Claire Moreau",
            "role": "head_of_youth_development",
            "title": "Head of Youth Development",
            "specialty": "Academy-to-First-Team Pathway",
            "style": "youth_focus",
            "rating": 88,
            "salary_weekly": 27000,
            "bio": "Architect of an acclaimed U16-to-senior transition curriculum who fiercely defends minutes for elite academy graduates.",
            "personality_profile": {
                "archetype_key": "pathway_champion",
                "archetype_label": "Academy Pathway Champion",
                "academy_pathway_advocacy": 94,
                "talent_identification": 89,
                "technical_curriculum_focus": 88,
                "patience_with_prospects": 91,
                "readiness_threshold": 60,
                "professional_independence": 80,
                "communication_style": "diplomatic_warm",
            },
        },
    ],
    "medical_director": [
        {
            "id": "med_dr_arjun_mehta",
            "name": "Dr. Arjun Mehta",
            "role": "medical_director",
            "title": "Medical Director",
            "specialty": "Sports Science & Soft-Tissue Prevention",
            "style": "analytics",
            "rating": 89,
            "salary_weekly": 30000,
            "bio": "Orthopaedic and load-monitoring specialist who refuses to compromise player longevity for short-term fixture pressure.",
            "personality_profile": {
                "archetype_key": "conservative_load_scientist",
                "archetype_label": "Evidence-First Load Scientist",
                "protocol_strictness": 93,
                "load_management_conservatism": 88,
                "rehab_excellence": 90,
                "risk_tolerance": 22,
                "professional_independence": 88,
                "communication_style": "measured_analytical",
            },
        },
    ],
    "assistant_coaches": [
        {
            "id": "ac_marco_bellini",
            "name": "Marco Bellini",
            "role": "assistant_coach",
            "specialist_role": "attacking_development",
            "title": "Assistant Coach (Attacking Development)",
            "specialty": "Final-Third Combinations & Finishing",
            "rating": 84,
            "salary_weekly": 16000,
            "personality_profile": {
                "archetype_key": "attacking_specialist",
                "archetype_label": "Attacking Development Specialist",
                "specialist_domain": "attacking_development",
                "tactical_focus": "final_third_overloads",
                "youth_mentoring": 82,
                "intensity": 78,
                "professional_independence": 68,
                "communication_style": "diplomatic_warm",
            },
        },
        {
            "id": "ac_tomasz_kowalski",
            "name": "Tomasz Kowalski",
            "role": "assistant_coach",
            "specialist_role": "defensive_organisation",
            "title": "Assistant Coach (Defensive Organisation)",
            "specialty": "Rest-Defence & Compactness",
            "rating": 85,
            "salary_weekly": 16500,
            "personality_profile": {
                "archetype_key": "defensive_organiser",
                "archetype_label": "Defensive Organisation Specialist",
                "specialist_domain": "defensive_organisation",
                "tactical_focus": "compact_mid_block",
                "youth_mentoring": 64,
                "intensity": 85,
                "professional_independence": 74,
                "communication_style": "blunt_candid",
            },
        },
        {
            "id": "ac_javier_navarro",
            "name": "Javier Navarro",
            "role": "assistant_coach",
            "specialist_role": "goalkeeping",
            "title": "Goalkeeping Coach",
            "specialty": "Sweeper-Keeper Distribution & Shot-Stopping",
            "rating": 83,
            "salary_weekly": 14000,
            "personality_profile": {
                "archetype_key": "goalkeeping_specialist",
                "archetype_label": "Modern Sweeper-Keeper Coach",
                "specialist_domain": "goalkeeping",
                "tactical_focus": "build_up_under_press",
                "youth_mentoring": 75,
                "intensity": 76,
                "professional_independence": 66,
                "communication_style": "measured_analytical",
            },
        },
        {
            "id": "ac_sofia_bergstrom",
            "name": "Sofia Bergström",
            "role": "assistant_coach",
            "specialist_role": "fitness",
            "title": "Head of Fitness & Conditioning",
            "specialty": "High-Intensity Repeat Sprint Capacity",
            "rating": 86,
            "salary_weekly": 15500,
            "personality_profile": {
                "archetype_key": "conditioning_specialist",
                "archetype_label": "High-Intensity Conditioning Lead",
                "specialist_domain": "fitness",
                "tactical_focus": "high_pressing_endurance",
                "youth_mentoring": 72,
                "intensity": 90,
                "professional_independence": 77,
                "communication_style": "intense_demanding",
            },
        },
        {
            "id": "ac_jonas_richter",
            "name": "Jonas Richter",
            "role": "assistant_coach",
            "specialist_role": "tactical_analysis",
            "title": "Lead Tactical Analyst",
            "specialty": "Opposition Pressing Traps & Half-Space Metrics",
            "rating": 85,
            "salary_weekly": 15000,
            "personality_profile": {
                "archetype_key": "tactical_analyst",
                "archetype_label": "Lead Opposition & Data Analyst",
                "specialist_domain": "tactical_analysis",
                "tactical_focus": "half_space_progression",
                "youth_mentoring": 70,
                "intensity": 72,
                "professional_independence": 73,
                "communication_style": "measured_analytical",
            },
        },
        {
            "id": "ac_adama_diallo",
            "name": "Adama Diallo",
            "role": "assistant_coach",
            "specialist_role": "player_development",
            "title": "Individual Player Development Coach",
            "specialty": "U20 First-Team Transition & Technical Mastery",
            "rating": 84,
            "salary_weekly": 14500,
            "personality_profile": {
                "archetype_key": "development_mentor",
                "archetype_label": "Individual Pathway Development Coach",
                "specialist_domain": "player_development",
                "tactical_focus": "1v1_ball_retention",
                "youth_mentoring": 94,
                "intensity": 74,
                "professional_independence": 70,
                "communication_style": "diplomatic_warm",
            },
        },
    ],
}


def derive_manager_personality(manager_data: dict[str, Any]) -> dict[str, Any]:
    """Build or preserve a persistent 23-attribute personality profile for a First-Team Manager."""
    existing = manager_data.get("personality_profile")
    if isinstance(existing, dict) and existing.get("preferred_tactical_philosophy") and existing.get("archetype_key"):
        merged = dict(existing)
        for k in (
            "youth_development_commitment",
            "trust_in_young_players",
            "willingness_to_promote_academy",
            "preference_for_experienced_players",
            "tolerance_for_owner_interference",
            "professional_independence",
            "attacking_vs_defensive",
            "possession_vs_direct",
            "pressing_philosophy",
            "tactical_flexibility",
            "adaptability",
        ):
            if k in manager_data and isinstance(manager_data[k], (int, float)):
                merged[k] = _personality_score(k, manager_data[k])
        return merged

    explicit_archetype = str(manager_data.get("archetype_key") or "").strip()
    profile = dict(MANAGER_ARCHETYPES[explicit_archetype]) if explicit_archetype in MANAGER_ARCHETYPES else {}
    for numeric_key in (
        "attacking_vs_defensive",
        "possession_vs_direct",
        "pressing_philosophy",
        "tactical_flexibility",
        "adaptability",
        "youth_development_commitment",
        "trust_in_young_players",
        "willingness_to_promote_academy",
        "preference_for_experienced_players",
        "player_discipline_philosophy",
        "tolerance_for_owner_interference",
        "professional_independence",
        "ambition",
        "ego_reputation_sensitivity",
        "loyalty",
        "risk_tolerance",
        "ability_to_handle_pressure",
    ):
        if numeric_key in manager_data and isinstance(manager_data[numeric_key], (int, float)):
            profile[numeric_key] = _personality_score(numeric_key, manager_data[numeric_key])

    for str_key in (
        "preferred_tactical_philosophy",
        "dressing_room_management_style",
        "negotiating_temperament",
        "communication_style",
        "preferred_squad_composition",
    ):
        if str_key in manager_data and manager_data[str_key]:
            profile[str_key] = manager_data[str_key]

    if isinstance(manager_data.get("preferred_formations"), list) and manager_data["preferred_formations"]:
        profile["preferred_formations"] = list(manager_data["preferred_formations"])
    if "youth_development" in manager_data and isinstance(manager_data["youth_development"], (int, float)):
        yd_pct = _personality_score("youth_development", manager_data["youth_development"])
        profile.setdefault("youth_development_commitment", yd_pct)
        profile.setdefault("trust_in_young_players", yd_pct)
        profile.setdefault("willingness_to_promote_academy", yd_pct)
    if not profile.get("preferred_tactical_philosophy"):
        style_text = str(manager_data.get("style") or manager_data.get("mentality") or "").strip().lower()
        if "gegen" in style_text or "press" in style_text:
            profile["preferred_tactical_philosophy"] = "gegenpressing_counter_attack"
            profile.setdefault("pressing_philosophy", 90)
            profile.setdefault("attacking_vs_defensive", 80)

    staff_id = manager_data.get("id") or manager_data.get("manager_id")
    if staff_id:
        profile["staff_id"] = str(staff_id)
    name = str(manager_data.get("name") or manager_data.get("display_name") or "").strip()
    if name:
        profile["staff_name"] = name
    return profile


def derive_department_personality(role_key: str, staff_data: dict[str, Any]) -> dict[str, Any]:
    """The appointed person's own style, not another catalog employee's profile."""
    name = str(staff_data.get("name") or staff_data.get("display_name") or "").strip()
    style = str(staff_data.get("style") or staff_data.get("philosophy_summary") or "")
    philosophy = str(staff_data.get("philosophy_summary") or style or "")
    profile: dict[str, Any] = {
        "archetype_key": str(staff_data.get("archetype_key") or f"{role_key}_appointed"),
        "archetype_label": style or role_key.replace("_", " ").title(),
        "role_key": role_key,
    }
    if philosophy:
        profile["philosophy"] = philosophy
        profile["operating_philosophy"] = philosophy
    if style:
        profile["style"] = style
    if staff_data.get("communication_style"):
        profile["communication_style"] = staff_data["communication_style"]
    if staff_data.get("id") or staff_data.get("staff_id"):
        profile["staff_id"] = str(staff_data.get("id") or staff_data.get("staff_id"))
    if name:
        profile["staff_name"] = name
    filed = dict(staff_data.get("personality_profile") or {})
    for key in ("protocol_strictness", "financial_discipline", "professional_independence"):
        raw = staff_data.get(key) if staff_data.get(key) is not None else filed.get(key)
        if isinstance(raw, (int, float)):
            profile[key] = int(raw)
    return profile


def derive_gm_personality(gm_data: dict[str, Any]) -> dict[str, Any]:
    """Build or preserve a persistent 12-attribute personality profile for a General Manager."""
    existing = gm_data.get("personality_profile")
    if isinstance(existing, dict) and existing.get("recruitment_philosophy") and existing.get("archetype_key"):
        merged = dict(existing)
        for k in (
            "financial_discipline",
            "transfer_risk_tolerance",
            "contract_negotiation_ability",
            "youth_recruitment_preference",
            "commercial_ambition",
            "relationship_with_first_team_manager",
            "owner_alignment",
            "decision_making_independence",
        ):
            if k in gm_data and isinstance(gm_data[k], (int, float)):
                merged[k] = _clamp(gm_data[k])
        return merged

    explicit_archetype = str(gm_data.get("archetype_key") or "").strip()
    profile = dict(GM_ARCHETYPES[explicit_archetype]) if explicit_archetype in GM_ARCHETYPES else {}
    for numeric_key in (
        "financial_discipline",
        "transfer_risk_tolerance",
        "contract_negotiation_ability",
        "youth_recruitment_preference",
        "commercial_ambition",
        "relationship_with_first_team_manager",
        "owner_alignment",
        "decision_making_independence",
    ):
        if numeric_key in gm_data and isinstance(gm_data[numeric_key], (int, float)):
            profile[numeric_key] = _clamp(gm_data[numeric_key])
    for str_key in (
        "recruitment_philosophy",
        "wage_structure_philosophy",
        "squad_planning_philosophy",
        "delegation_preferences",
        "communication_style",
        "negotiating_temperament",
    ):
        if str_key in gm_data and gm_data[str_key]:
            profile[str_key] = gm_data[str_key]

    staff_id = gm_data.get("id") or gm_data.get("staff_id")
    if staff_id:
        profile["staff_id"] = str(staff_id)
    name = str(gm_data.get("name") or "").strip()
    if name:
        profile["staff_name"] = name
    return profile


def ensure_club_staff_identities(db: Session, state: OwnerClubState) -> dict[str, Any]:
    """Ensure the club's Manager, GM, Assistant Coaches, HOYD, Chief Scout, and Medical Director
    have persistent, individualized profiles and club culture state stored on `OwnerClubState`.
    """

    def _is_appointed_manager(raw: Any) -> bool:
        if not isinstance(raw, dict) or not raw or raw.get("is_vacant") or raw.get("is_default"):
            return False
        if raw.get("manager_id") == "gtex-staff-coach":
            return False
        raw_name = str(raw.get("name") or raw.get("display_name") or "").strip()
        return bool(raw_name and "vacant" not in raw_name.lower())

    mutated = False
    manager = dict(state.manager_json or {})
    if not _is_appointed_manager(manager):
        manager = {
            "id": None,
            "manager_id": None,
            "name": "First-Team Manager (Vacant)",
            "display_name": "First-Team Manager (Vacant)",
            "is_vacant": True,
            "is_appointed": False,
            "personality_profile": {},
        }
        mgr_profile = {}
    else:
        from app.owner_console import engine as _engine

        before_mgr = dict(manager)
        manager = _engine.apply_staff_influence(manager, "first_team_manager")
        if manager != before_mgr:
            mutated = True
        if not manager.get("id") and not manager.get("manager_id"):
            manager["id"] = f"mgr_{_stable_hash_int(str(manager.get('name') or state.club_id)) % 900000 + 100000}"
            mutated = True
        elif not manager.get("id") and manager.get("manager_id"):
            manager["id"] = str(manager["manager_id"])
            mutated = True
        if not manager.get("name") and manager.get("display_name"):
            manager["name"] = str(manager["display_name"])
            mutated = True
        manager["is_vacant"] = False
        manager["is_appointed"] = True
        mgr_profile = derive_manager_personality(manager)
        if manager.get("personality_profile") != mgr_profile or mutated:
            manager["personality_profile"] = mgr_profile
            state.manager_json = manager
            flag_modified(state, "manager_json")
            mutated = True

    def _is_appointed_record(raw: Any) -> bool:
        if not isinstance(raw, dict) or not raw or raw.get("is_vacant"):
            return False
        raw_name = str(raw.get("name") or raw.get("display_name") or "").strip()
        if not raw_name or "vacant" in raw_name.lower():
            return False
        return True

    def _vacant_identity(role_key: str, role_title: str) -> dict[str, Any]:
        return {
            "id": None,
            "staff_id": None,
            "role": role_key,
            "role_label": role_title,
            "name": f"{role_title} (Vacant)",
            "title": f"{role_title} (Vacant)",
            "is_vacant": True,
            "is_appointed": False,
            "personality_profile": {},
        }

    fac = dict(state.facilities_json or {})
    exec_staff = dict(fac.get("_executive_staff") or {})
    default_identities = dict(fac.get("_staff_default_identities") or {})

    gm_raw = exec_staff.get("general_manager")
    if _is_appointed_record(gm_raw):
        gm = dict(gm_raw)
        gm["is_vacant"] = False
        gm["is_appointed"] = True
        gm_profile = derive_gm_personality(gm)
        if gm.get("personality_profile") != gm_profile or exec_staff.get("general_manager") != gm:
            gm["personality_profile"] = gm_profile
            exec_staff["general_manager"] = gm
            mutated = True
    else:
        gm = _vacant_identity("general_manager", "General Manager")
        gm_profile = {}

    _role_titles = {
        "chief_scout": "Chief Scout",
        "head_of_youth_development": "Head of Youth Development",
        "medical_director": "Medical Director",
        "finance_commercial_director": "Finance & Commercial Director",
    }
    resolved_depts: dict[str, dict[str, Any]] = {}
    for role_key, role_title in _role_titles.items():
        raw_entry = exec_staff.get(role_key)
        if _is_appointed_record(raw_entry):
            current_entry = dict(raw_entry)
            current_entry["is_vacant"] = False
            current_entry["is_appointed"] = True
            appointed_name = str(current_entry.get("name") or "")
            stored_personality = dict(current_entry.get("personality_profile") or {})
            stored_name = str(stored_personality.get("staff_name") or "")
            if not stored_personality or (stored_name and stored_name != appointed_name):
                current_entry["personality_profile"] = derive_department_personality(role_key, current_entry)
            if exec_staff.get(role_key) != current_entry:
                exec_staff[role_key] = current_entry
                mutated = True
            resolved_depts[role_key] = current_entry
        else:
            resolved_depts[role_key] = _vacant_identity(role_key, role_title)

    coaching_staff = list(fac.get("_coaching_staff") or [])

    club_culture = dict(fac.get("_club_culture") or {})
    if mgr_profile and not club_culture.get("primary_identity"):
        identity = mgr_profile.get("preferred_tactical_philosophy") or mgr_profile.get("tactical_preference")
        dimensions: dict[str, int] = {}
        for dim, raw in (
            (
                "attacking_football",
                mgr_profile.get("attacking_vs_defensive") if "attacking_vs_defensive" in mgr_profile else None,
            ),
            (
                "possession_football",
                mgr_profile.get("possession_vs_direct") if "possession_vs_direct" in mgr_profile else None,
            ),
            ("high_pressing", mgr_profile.get("pressing_philosophy") if "pressing_philosophy" in mgr_profile else None),
            (
                "youth_development",
                (
                    mgr_profile.get("youth_development_commitment")
                    if "youth_development_commitment" in mgr_profile
                    else None
                ),
            ),
            (
                "experienced_recruitment",
                (
                    mgr_profile.get("preference_for_experienced_players")
                    if "preference_for_experienced_players" in mgr_profile
                    else None
                ),
            ),
            (
                "academy_first_recruitment",
                (
                    gm_profile.get("youth_recruitment_preference")
                    if "youth_recruitment_preference" in gm_profile
                    else None
                ),
            ),
        ):
            if raw is not None:
                dimensions[dim] = int(raw)
        if "possession_vs_direct" in mgr_profile and mgr_profile.get("possession_vs_direct") is not None:
            dimensions["counterattacking"] = _clamp(100 - int(mgr_profile["possession_vs_direct"]))
        if "attacking_vs_defensive" in mgr_profile and mgr_profile.get("attacking_vs_defensive") is not None:
            dimensions["defensive_solidity"] = _clamp(100 - int(mgr_profile["attacking_vs_defensive"]))
        youth_raw = (
            mgr_profile.get("youth_development_commitment") if "youth_development_commitment" in mgr_profile else None
        )
        secondary = "youth_development" if youth_raw is not None and int(youth_raw) >= 70 else None
        if identity or dimensions:
            club_culture = {
                "primary_identity": identity,
                "secondary_identity": secondary,
                "target_identity": None,
                "transition_progress_pct": 100 if identity else None,
                "dimensions": dimensions,
                "last_discussed_at": None,
            }
            fac["_club_culture"] = club_culture
            mutated = True

    if fac.get("_executive_staff") != exec_staff:
        fac["_executive_staff"] = exec_staff
        mutated = True
    if fac.get("_staff_default_identities") != default_identities:
        fac["_staff_default_identities"] = default_identities
        mutated = True

    if mutated:
        state.facilities_json = fac
        flag_modified(state, "facilities_json")
        db.flush()

    return {
        "first_team_manager": manager,
        "general_manager": gm,
        "chief_scout": resolved_depts["chief_scout"],
        "head_of_youth_development": resolved_depts["head_of_youth_development"],
        "medical_director": resolved_depts["medical_director"],
        "finance_commercial_director": resolved_depts["finance_commercial_director"],
        "assistant_coaches": coaching_staff,
        "club_culture": club_culture,
    }


def _ensure_academy_striker_prospect(db: Session, club_id: str, *, force: bool = False) -> OwnerSquadPlayer | None:
    """Ensure the club has at least one 16-year-old academy striker in `OwnerSquadPlayer`."""
    players = list(db.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    for p in players:
        if int(p.age or 20) <= 17 and str(p.position or "").upper() in ("ST", "CF", "FW", "FORWARD"):
            return p
    if not force:
        return None
    prospect = OwnerSquadPlayer(
        id=f"{club_id}-acad-st-16",
        club_id=club_id,
        name="Lucas Vance",
        position="ST",
        age=16,
        rating=66,
        potential=87,
        value_coin=Decimal("450.00"),
        morale=84,
        minutes=0,
        injured_days=0,
        is_regen=True,
        personality_json={"fitness": 92, "is_academy": True, "ambition": 16, "professionalism": 15},
        status="active",
        acquired_via="academy",
    )
    db.add(prospect)
    db.flush()
    return prospect


# ---------------------------------------------------------------------------
# SECTION 9: 9-DIMENSION RELATIONSHIP HEALTH & ARCHIVAL ON REPLACEMENT
# ---------------------------------------------------------------------------


def ensure_staff_relationship(
    db: Session,
    state: OwnerClubState,
    *,
    role_key: str,
    staff_id: str,
    staff_name: str,
    staff_title: str,
    personality_profile: dict[str, Any] | None = None,
) -> OwnerClubRelationship:
    """Fetch or create the active `OwnerClubRelationship` for the current staff member.
    Never transfers a predecessor's relationship history to a newly appointed replacement.
    """
    profile = dict(personality_profile or {})
    pairing_key = f"{state.club_id}:owner:{role_key}"
    existing = db.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == state.club_id,
            OwnerClubRelationship.pairing_key == pairing_key,
        )
    )
    fac = dict(state.facilities_json or {})
    culture = dict(fac.get("_club_culture") or {})
    culture_dims = dict(culture.get("dimensions") or {})

    mgr_youth = int(
        profile.get(
            "youth_development_commitment",
            profile.get("youth_recruitment_preference", 65),
        )
    )
    club_youth = int(culture_dims.get("youth_development", 65))
    culture_alignment = _clamp(100 - abs(mgr_youth - club_youth) // 2 - 10)
    initial_autonomy = _clamp(int(profile.get("professional_independence", 75)))
    ambition_compat = _clamp(78 - abs(int(profile.get("ambition", 75)) - 75) // 2)

    if existing is not None:
        meta = dict(existing.metadata_json or {})
        recorded_staff_id = str(meta.get("staff_id") or existing.participant_b_id or "")
        if (
            (recorded_staff_id and recorded_staff_id != staff_id)
            or (existing.participant_b_name and existing.participant_b_name != staff_name)
            or existing.status in ("former", "vacant", "resigned")
        ):
            # Archive predecessor relationship snapshot and reset for new appointee!
            archived = list(fac.get("_archived_staff_relationships") or [])
            archived.append(
                {
                    "relationship_id": existing.id,
                    "staff_id": recorded_staff_id,
                    "staff_name": existing.participant_b_name,
                    "role": role_key,
                    "trust": existing.trust,
                    "respect": existing.respect,
                    "alignment": existing.alignment,
                    "tension": existing.tension,
                    "loyalty": existing.loyalty,
                    "status": existing.status,
                    "metadata": meta,
                    "archived_at": _utcnow().isoformat(),
                }
            )
            fac["_archived_staff_relationships"] = archived[-25:]
            state.facilities_json = fac
            flag_modified(state, "facilities_json")

            existing.participant_b_id = staff_id
            existing.participant_b_name = staff_name
            existing.trust = 68
            existing.respect = 70
            existing.affinity = 66
            existing.tension = 16
            existing.alignment = 70
            existing.influence = 65
            existing.loyalty = int(profile.get("loyalty", 70))
            existing.status = "aligned"
            existing.metadata_json = {
                "staff_id": staff_id,
                "role_key": role_key,
                "role_title": staff_title,
                "ambition_compatibility": ambition_compat,
                "autonomy": initial_autonomy,
                "confidence": 75,
                "culture_alignment": culture_alignment,
                "interference_count": 0,
                "unresolved_disagreements": [],
                "ultimatum_active": False,
                "resignation_notice_served": False,
                "appointed_at": _utcnow().isoformat(),
            }
            flag_modified(existing, "metadata_json")
            existing.updated_at = _utcnow()
            db.flush()
            return existing

        changed = False
        if existing.participant_b_name != staff_name:
            existing.participant_b_name = staff_name
            changed = True
        if meta.get("staff_id") != staff_id:
            meta["staff_id"] = staff_id
            changed = True
        for k, default_v in (
            ("role_key", role_key),
            ("role_title", staff_title),
            ("ambition_compatibility", ambition_compat),
            ("autonomy", initial_autonomy),
            ("confidence", 75),
            ("culture_alignment", culture_alignment),
            ("interference_count", 0),
            ("unresolved_disagreements", []),
            ("ultimatum_active", False),
            ("resignation_notice_served", False),
        ):
            if k not in meta:
                meta[k] = default_v
                changed = True
        if changed:
            existing.metadata_json = meta
            flag_modified(existing, "metadata_json")
            existing.updated_at = _utcnow()
            db.flush()
        return existing

    rel = OwnerClubRelationship(
        id=str(uuid4()),
        club_id=state.club_id,
        pairing_key=pairing_key,
        participant_a_type="owner",
        participant_a_id="owner",
        participant_a_name="Club Owner",
        participant_b_type="staff",
        participant_b_id=staff_id,
        participant_b_name=staff_name,
        trust=68,
        respect=70,
        affinity=66,
        tension=16,
        alignment=70,
        influence=65,
        loyalty=int(profile.get("loyalty", 70)),
        status="aligned",
        metadata_json={
            "staff_id": staff_id,
            "role_key": role_key,
            "role_title": staff_title,
            "ambition_compatibility": ambition_compat,
            "autonomy": initial_autonomy,
            "confidence": 75,
            "culture_alignment": culture_alignment,
            "interference_count": 0,
            "unresolved_disagreements": [],
            "ultimatum_active": False,
            "resignation_notice_served": False,
            "appointed_at": _utcnow().isoformat(),
        },
        updated_at=_utcnow(),
    )
    db.add(rel)
    db.flush()
    return rel


def retire_staff_relationship_on_vacancy(db: Session, state: OwnerClubState, *, role_key: str) -> None:
    """Archive an executive/staff relationship when a role becomes vacant without immediate replacement."""
    clean_role = str(role_key or "").strip().lower()
    if clean_role == "head_coach":
        clean_role = "first_team_manager"
    pairing_key = f"{state.club_id}:owner:{clean_role}"
    existing = db.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == state.club_id,
            OwnerClubRelationship.pairing_key == pairing_key,
        )
    )
    if existing is None or existing.status in ("former", "vacant"):
        return
    fac = dict(state.facilities_json or {})
    archived = list(fac.get("_archived_staff_relationships") or [])
    meta = dict(existing.metadata_json or {})
    archived.append(
        {
            "relationship_id": existing.id,
            "staff_id": str(meta.get("staff_id") or existing.participant_b_id or ""),
            "staff_name": existing.participant_b_name,
            "role": clean_role,
            "trust": existing.trust,
            "respect": existing.respect,
            "alignment": existing.alignment,
            "tension": existing.tension,
            "loyalty": existing.loyalty,
            "status": existing.status,
            "metadata": meta,
            "archived_at": _utcnow().isoformat(),
        }
    )
    fac["_archived_staff_relationships"] = archived[-25:]
    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    existing.status = "former"
    meta["archived_world_day"] = int(state.world_day or 1)
    meta["vacated_at"] = _utcnow().isoformat()
    existing.metadata_json = meta
    flag_modified(existing, "metadata_json")
    existing.updated_at = _utcnow()
    db.flush()


def serialize_relationship_health(rel: OwnerClubRelationship) -> dict[str, Any]:
    meta = dict(rel.metadata_json or {})
    return {
        "relationship_id": rel.id,
        "staff_id": meta.get("staff_id", rel.participant_b_id),
        "actor_key": meta.get("role_key", rel.pairing_key.replace("owner:", "")),
        "actor_name": rel.participant_b_name,
        "actor_role": meta.get("role_title", "Club Staff"),
        "trust": rel.trust,
        "respect": rel.respect,
        "alignment": rel.alignment,
        "tension": rel.tension,
        "loyalty": rel.loyalty,
        "ambition_compatibility": int(meta.get("ambition_compatibility", 74)),
        "autonomy": int(meta.get("autonomy", 75)),
        "confidence": int(meta.get("confidence", 75)),
        "culture_alignment": int(meta.get("culture_alignment", 72)),
        "interference_count": int(meta.get("interference_count", 0)),
        "unresolved_disagreements": list(meta.get("unresolved_disagreements") or []),
        "ultimatum_active": bool(meta.get("ultimatum_active", False)),
        "resignation_notice_served": bool(meta.get("resignation_notice_served", False)),
        "status": rel.status,
    }


# ---------------------------------------------------------------------------
# SECTION 3 & 4: NATURAL LANGUAGE INTENT PARSER & LAYER A DECISION ENGINE
# ---------------------------------------------------------------------------

POSITION_SYNONYMS: dict[str, str] = {
    "left winger": "LW",
    "left wing": "LW",
    "lw": "LW",
    "right winger": "RW",
    "right wing": "RW",
    "rw": "RW",
    "striker": "ST",
    "centre forward": "ST",
    "center forward": "ST",
    "forward": "ST",
    "st": "ST",
    "centre-back": "CB",
    "centre back": "CB",
    "center-back": "CB",
    "center back": "CB",
    "cb": "CB",
    "left-back": "LB",
    "left back": "LB",
    "lb": "LB",
    "right-back": "RB",
    "right back": "RB",
    "rb": "RB",
    "defensive midfielder": "CDM",
    "cdm": "CDM",
    "attacking midfielder": "CAM",
    "cam": "CAM",
    "midfielder": "CM",
    "central midfielder": "CM",
    "cm": "CM",
    "goalkeeper": "GK",
    "keeper": "GK",
    "gk": "GK",
}


def classify_owner_request(
    message_text: str,
    recipient_role: str,
    squad_players: list[OwnerSquadPlayer],
    *,
    db: Session | None = None,
    club_id: str | None = None,
) -> dict[str, Any]:
    """Parse natural-language owner message into a structured intent with target player,
    position, GSI range, tactical direction, or escalation level.
    """
    raw = (message_text or "").strip()
    lower = raw.lower()

    age_match = re.search(r"\b(1[5-9]|2[0-1])(?:-|\s+)year(?:-|\s+)old\b", lower)
    requested_age = int(age_match.group(1)) if age_match else None
    is_academy_mention = any(
        kw in lower
        for kw in (
            "academy",
            "youth",
            "youngster",
            "16-year-old",
            "17-year-old",
            "u18",
            "u19",
            "prospect",
            "young player",
        )
    )

    # If the owner explicitly asks about a 16-year-old or academy player and none exists yet in a minimal test fixture, ensure one exists
    if is_academy_mention and db is not None and club_id is not None:
        created_or_found = _ensure_academy_striker_prospect(db, club_id, force=False)
        if created_or_found is not None and all(p.id != created_or_found.id for p in squad_players):
            squad_players = [*squad_players, created_or_found]

    matched_player: OwnerSquadPlayer | None = None
    for p in squad_players:
        p_name = (p.name or "").strip().lower()
        if p_name and (p_name in lower or any(part in lower and len(part) >= 4 for part in p_name.split())):
            matched_player = p
            break

    detected_position: str | None = None
    for phrase, pos_code in sorted(POSITION_SYNONYMS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(phrase)}s?\b", lower):
            detected_position = pos_code
            break

    if matched_player is None and (is_academy_mention or requested_age is not None):
        candidates = [
            p
            for p in squad_players
            if (_player_is_academy(p) or (p.age is not None and int(p.age) <= 19))
            and (detected_position is None or str(p.position or "").upper() == detected_position)
        ]
        if not candidates:
            candidates = [p for p in squad_players if _player_is_academy(p) or (p.age is not None and int(p.age) <= 19)]
        if candidates:
            target_age = requested_age

            def _age_rank(p: OwnerSquadPlayer) -> tuple[int, int, int]:
                age_gap = abs(int(p.age) - target_age) if p.age is not None and target_age is not None else 0
                potential = int(p.potential) if p.potential is not None else 0
                return (0 if p.age is not None else 1, age_gap, -potential)

            candidates.sort(key=_age_rank)
            matched_player = candidates[0]

    if matched_player is None and ("this player" in lower or "that player" in lower or "him" in lower):
        if squad_players:
            matched_player = sorted(
                squad_players,
                key=lambda p: (p.morale is None, int(p.morale) if p.morale is not None else 0),
            )[0]

    gsi_range_match = re.search(
        r"(?:gsi|rating|rated)?[^0-9]{0,20}\b(6\d|7\d|8\d|9\d)\s*(?:to|and|-|–)\s*(6\d|7\d|8\d|9\d)\b", lower
    )
    single_gsi_match = re.search(r"\b(?:gsi|rated|rating)\s*(?:of|above|over|around)?\s*(7\d|8\d|9\d)\b", lower)
    if gsi_range_match:
        min_gsi = min(int(gsi_range_match.group(1)), int(gsi_range_match.group(2)))
        max_gsi = max(int(gsi_range_match.group(1)), int(gsi_range_match.group(2)))
    elif single_gsi_match:
        val = int(single_gsi_match.group(1))
        min_gsi, max_gsi = val - 2, val + 2
    else:
        min_gsi, max_gsi = None, None

    expensive_request = any(
        kw in lower
        for kw in (
            "expensive",
            "marquee",
            "blockbuster",
            "record fee",
            "galáctico",
            "galactico",
            "superstar",
            "at any cost",
            "big money",
            "50m",
            "60m",
            "80m",
            "100m",
        )
    ) or (min_gsi is not None and min_gsi >= 88)

    is_challenge = any(
        kw in lower
        for kw in (
            "i insist",
            "i am the owner",
            "override",
            "do as i say",
            "not optional",
            "must play",
            "must start",
            "unacceptable",
            "ignoring my",
            "demand that you",
            "order you",
            "final warning",
            "play him anyway",
            "disagree with your decision",
            "challenge your",
        )
    )

    intent = "general_consultation"
    if any(
        kw in lower
        for kw in ("do not use", "don't use", "drop ", "bench ", "attitude", "discipline", "leave him out", "suspend")
    ):
        intent = "drop_or_discipline_player"
    elif any(
        kw in lower
        for kw in (
            "long-term identity",
            "club culture",
            "club philosophy",
            "academy-first",
            "experienced-player recruitment",
            "sporting identity",
            "define our club identity",
            "first-team opportunities",
        )
    ):
        intent = "club_culture_direction"
    elif is_academy_mention and any(
        kw in lower
        for kw in (
            "opportunity",
            "next match",
            "next fixture",
            "play",
            "start",
            "include",
            "promote",
            "minutes",
            "first-team",
            "first team",
            "chance",
            "debut",
        )
    ):
        intent = "academy_player_opportunity"
    elif is_challenge and any(
        kw in lower
        for kw in (
            "selection",
            "lineup",
            "play",
            "start",
            "striker",
            "youngster",
            "academy",
            "fixture",
            "match",
            "team",
        )
    ):
        intent = "challenge_or_override_decision"
    elif any(
        kw in lower
        for kw in (
            "sign ",
            "recruit",
            "transfer",
            "buy ",
            "acquire",
            "shortlist",
            "left winger",
            "new striker",
            "new centre-back",
        )
    ) and (detected_position is not None or "sign" in lower or "recruit" in lower or "transfer" in lower):
        intent = "transfer_recruitment_target"
    elif any(
        kw in lower
        for kw in (
            "spending money",
            "recruitment department",
            "wasting money",
            "overpaying",
            "wage bill",
            "transfer budget",
            "financial discipline",
        )
    ):
        intent = "recruitment_spending_critique"
    elif any(
        kw in lower
        for kw in (
            "too defensive",
            "more attacking",
            "attacking football",
            "possession football",
            "high-pressing",
            "high pressing",
            "counterattack",
            "playing style",
            "tactical",
            "mentality",
            "defensive football",
        )
    ):
        intent = "tactical_style_shift"
    elif any(
        kw in lower for kw in ("formation", "4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "5-3-2", "back four", "back three")
    ):
        intent = "formation_request"
    elif any(
        kw in lower
        for kw in (
            "clear him",
            "play through injury",
            "medical clearance",
            "rush him back",
            "painkillers",
            "injury load",
            "fitness",
        )
    ):
        intent = "medical_clearance_pressure"
    elif matched_player is not None and any(
        kw in lower for kw in ("play", "start", "next match", "next fixture", "opportunity", "lineup", "starting xi")
    ):
        intent = "player_selection_request"
    elif is_challenge:
        intent = "challenge_or_override_decision"

    requested_style = "balanced"
    if any(kw in lower for kw in ("more attacking", "attacking football", "too defensive", "front foot")):
        requested_style = "attacking"
    elif any(kw in lower for kw in ("more defensive", "defensive football", "compact", "clean sheet", "pragmatic")):
        requested_style = "defensive"
    elif any(kw in lower for kw in ("possession", "control the ball", "positional")):
        requested_style = "possession"
    elif any(kw in lower for kw in ("high-pressing", "high pressing", "gegenpress", "press higher")):
        requested_style = "high_pressing"
    elif any(kw in lower for kw in ("counterattack", "direct", "transition")):
        requested_style = "counterattacking"
    elif any(kw in lower for kw in ("academy", "youth", "young players", "first-team opportunities")):
        requested_style = "youth_development"

    return {
        "intent": intent,
        "raw_text": raw,
        "recipient_role": recipient_role,
        "target_player_id": matched_player.id if matched_player else None,
        "target_player_name": matched_player.name if matched_player else None,
        "target_player": (
            {
                "id": matched_player.id,
                "name": matched_player.name,
                "age": matched_player.age,
                "position": matched_player.position,
                "rating": matched_player.rating,
                "potential": matched_player.potential,
                "fitness": _player_fitness(matched_player),
                "injured_days": matched_player.injured_days,
                "morale": matched_player.morale,
                "is_academy": _player_is_academy(matched_player),
            }
            if matched_player
            else None
        ),
        "detected_position": detected_position or "LW",
        "min_gsi": min_gsi,
        "max_gsi": max_gsi,
        "expensive_request": expensive_request,
        "is_challenge": is_challenge,
        "is_academy_mention": is_academy_mention,
        "requested_style": requested_style,
    }


def evaluate_layer_a_staff_decision(
    db: Session,
    state: OwnerClubState,
    *,
    role_key: str,
    staff_id: str,
    staff_name: str,
    staff_title: str,
    personality: dict[str, Any],
    relationship: OwnerClubRelationship,
    intent_data: dict[str, Any],
    conversation_turn_count: int = 1,
) -> dict[str, Any]:
    """Authoritative Layer A decision engine.
    Evaluates structured club, squad, financial, personality, and relationship state
    and returns a deterministic, auditable decision outcome and state mutations.
    """
    intent = str(intent_data.get("intent") or "general_consultation")
    is_challenge = bool(intent_data.get("is_challenge", False))
    player = intent_data.get("target_player")
    rel_meta = dict(relationship.metadata_json or {})
    interference_count = int(rel_meta.get("interference_count", 0))
    unresolved = list(rel_meta.get("unresolved_disagreements") or [])

    independence = _optional_score(personality, "professional_independence", "decision_making_independence")
    interference_tolerance = _optional_score(personality, "tolerance_for_owner_interference")
    youth_commit = _optional_score(personality, "youth_development_commitment", "youth_recruitment_preference")
    trust_youth = _optional_score(personality, "trust_in_young_players")
    if trust_youth is None:
        trust_youth = youth_commit
    promote_academy = _optional_score(personality, "willingness_to_promote_academy")
    if promote_academy is None:
        promote_academy = youth_commit
    veteran_pref = _optional_score(personality, "preference_for_experienced_players")
    tactical_flex = _optional_score(personality, "tactical_flexibility")
    adaptability = _optional_score(personality, "adaptability")
    ego_sensitivity = _optional_score(personality, "ego_reputation_sensitivity")

    deltas = {
        "trust": 0,
        "respect": 0,
        "alignment": 0,
        "tension": 0,
        "loyalty": 0,
        "ambition_compatibility": 0,
        "autonomy": 0,
        "confidence": 0,
        "culture_alignment": 0,
    }
    state_effects: dict[str, Any] = {}
    reasoning_trace: dict[str, Any] = {
        "intent": intent,
        "staff_archetype": personality.get("archetype_key", "custom"),
        "staff_role": role_key,
        "conversation_turn_count": conversation_turn_count,
    }
    outcome = "accepted"

    is_selection_or_tactical_interference = intent in (
        "academy_player_opportunity",
        "player_selection_request",
        "drop_or_discipline_player",
        "formation_request",
        "challenge_or_override_decision",
    ) and role_key in ("first_team_manager", "head_coach")

    if is_selection_or_tactical_interference:
        if (
            is_challenge
            or (interference_tolerance is not None and interference_tolerance <= 45)
            or interference_count >= 1
        ):
            interference_count += 1
            rel_meta["interference_count"] = interference_count

    if intent in ("academy_player_opportunity", "player_selection_request"):
        if not player or not player.get("id") or not player.get("name"):
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = "No academy player is named on the squad for this request."
        else:
            p_age = int(player["age"]) if player.get("age") is not None else None
            p_rating = int(player["rating"]) if player.get("rating") is not None else None
            p_potential = int(player["potential"]) if player.get("potential") is not None else None
            p_fitness = int(player["fitness"]) if player.get("fitness") is not None else None
            p_injured = int(player["injured_days"]) if player.get("injured_days") is not None else 0
            p_name = str(player.get("name"))
            p_id = str(player.get("id"))

            youth_index = None
            readiness_threshold = None
            if None not in (youth_commit, trust_youth, promote_academy, veteran_pref):
                youth_index = round((youth_commit * 0.4) + (trust_youth * 0.3) + (promote_academy * 0.3))
                readiness_threshold = round(58 + (veteran_pref * 0.22) - (youth_index * 0.14))
            potential_term = (
                ((p_potential - p_rating) * 0.22) if p_rating is not None and p_potential is not None else 0
            )
            fitness_term = ((p_fitness - 80) * 0.15) if p_fitness is not None else 0
            effective_readiness = round(p_rating + potential_term + fitness_term) if p_rating is not None else None

            reasoning_trace.update(
                {
                    "player_id": p_id,
                    "player_name": p_name,
                    "player_age": p_age,
                    "player_rating": p_rating,
                    "player_potential": p_potential,
                    "player_fitness": p_fitness,
                    "player_injured_days": p_injured,
                    "manager_youth_index": youth_index,
                    "manager_veteran_preference": veteran_pref,
                    "computed_readiness_threshold": readiness_threshold,
                    "player_effective_readiness": effective_readiness,
                }
            )

            if p_rating is None:
                outcome = "deferred"
                reasoning_trace["verdict_reason"] = f"{p_name} has no filed rating, so no matchday role was assigned."
            elif role_key == "head_of_youth_development":
                if p_injured > 0 or (p_fitness is not None and p_fitness < 60):
                    outcome = "deferred"
                    reasoning_trace["verdict_reason"] = "Prospect requires medical recovery before first-team exposure."
                else:
                    outcome = "accepted"
                    deltas["trust"] = 4
                    deltas["alignment"] = 5
                    deltas["culture_alignment"] = 4
                    state_effects["hoyd_endorsement"] = {
                        "player_id": p_id,
                        "player_name": p_name,
                        "recommended_role": "first_team_pathway",
                    }
                    reasoning_trace["verdict_reason"] = (
                        "HOYD strongly endorses promoting the academy prospect and will table a joint development brief with the First-Team Manager."
                    )
            elif p_injured > 0 or (p_fitness is not None and p_fitness < 58):
                outcome = "declined"
                deltas["respect"] = 1
                reasoning_trace["verdict_reason"] = (
                    f"{p_name} is not medically or physically fit for competitive selection (fitness {p_fitness}%, injured_days={p_injured})."
                )
            elif p_rating < 52:
                outcome = "declined"
                deltas["tension"] = 3
                deltas["autonomy"] = -2
                reasoning_trace["verdict_reason"] = (
                    f"Despite strong commitment to youth, {p_name} (GSI {p_rating}) is below minimum senior competitive readiness."
                )
            elif youth_index is None or readiness_threshold is None or effective_readiness is None:
                outcome = "deferred"
                reasoning_trace["verdict_reason"] = (
                    f"{p_name}'s youth preference or readiness inputs are not filed, so no matchday role was assigned."
                )
            elif (
                youth_index >= 72
                and effective_readiness >= readiness_threshold
                and not (is_challenge and interference_count >= 3)
            ):
                outcome = "accepted" if p_rating >= 64 else "partially_accepted"
                assigned_role = "starting_xi" if p_rating >= 64 and youth_index >= 80 else "matchday_squad_bench"
                deltas["trust"] = 3
                deltas["alignment"] = 4
                deltas["culture_alignment"] = 3
                state_effects["manager_matchday_commitment"] = {
                    "player_id": p_id,
                    "player_name": p_name,
                    "matchday_role": assigned_role,
                    "decision_outcome": outcome,
                }
                reasoning_trace["verdict_reason"] = (
                    f"Manager's youth commitment ({youth_index}/100) and {p_name}'s readiness ({effective_readiness} vs threshold {readiness_threshold}) support inclusion ({assigned_role})."
                )
            elif (
                (veteran_pref is not None and veteran_pref >= 68)
                or youth_index <= 45
                or effective_readiness < readiness_threshold - 4
            ):
                if (
                    interference_count >= 4
                    and independence is not None
                    and independence >= 72
                    and interference_tolerance is not None
                    and interference_tolerance <= 45
                ):
                    outcome = "resignation_notice"
                elif (
                    interference_count == 3
                    and independence is not None
                    and independence >= 72
                    and interference_tolerance is not None
                    and interference_tolerance <= 45
                ):
                    outcome = "ultimatum"
                elif is_challenge or interference_count >= 2:
                    outcome = "formal_disagreement"
                else:
                    outcome = "declined"

                severity = 2 if (is_challenge or interference_count >= 2) else 1
                independence_penalty = max(0, (independence - 60) // 5) if independence is not None else 0
                tolerance_penalty = (
                    max(0, (70 - interference_tolerance) // 6) if interference_tolerance is not None else 0
                )
                deltas["tension"] = 8 * severity + independence_penalty
                deltas["autonomy"] = -(6 * severity + tolerance_penalty)
                deltas["trust"] = -(4 * severity)
                deltas["alignment"] = -(5 * severity)
                state_effects["manager_matchday_rejection"] = {
                    "player_id": p_id,
                    "player_name": p_name,
                    "reason": "insufficient_physical_and_tactical_maturity",
                }
                reasoning_trace["verdict_reason"] = (
                    f"Manager prioritises experienced players ({veteran_pref}/100) and evaluates {p_name} (age {p_age}, GSI {p_rating}) as below senior readiness threshold ({readiness_threshold})."
                )
            else:
                outcome = "partially_accepted"
                deltas["trust"] = 2
                deltas["alignment"] = 2
                deltas["autonomy"] = -1
                state_effects["manager_matchday_commitment"] = {
                    "player_id": p_id,
                    "player_name": p_name,
                    "matchday_role": "substitute_impact",
                    "decision_outcome": outcome,
                }
                reasoning_trace["verdict_reason"] = (
                    f"Manager balances development with competitive risk: {p_name} is not ready to lead the line from kick-off but will be named on the bench for controlled second-half substitute minutes."
                )

    elif intent == "drop_or_discipline_player":
        p_name = str((player or {}).get("name") or "the player")
        p_id = str((player or {}).get("id") or "unknown")
        p_morale = int(player["morale"]) if player and player.get("morale") is not None else None
        discipline_strictness = _optional_score(personality, "player_discipline_philosophy")
        reasoning_trace.update(
            {
                "player_id": p_id,
                "player_name": p_name,
                "player_morale": p_morale,
                "discipline_strictness": discipline_strictness,
            }
        )
        if (
            independence is not None
            and independence >= 80
            and interference_tolerance is not None
            and interference_tolerance <= 35
            and (is_challenge or interference_count >= 2)
        ):
            if interference_count >= 4:
                outcome = "resignation_notice"
            elif interference_count == 3:
                outcome = "ultimatum"
            else:
                outcome = "formal_disagreement"
            deltas["tension"] = 14
            deltas["autonomy"] = -12
            deltas["trust"] = -8
            reasoning_trace["verdict_reason"] = (
                "Manager guards dressing-room and selection authority against direct owner exclusion orders."
            )
        elif discipline_strictness is None or p_morale is None:
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                f"Discipline or morale for {p_name} is not filed, so nobody was dropped."
            )
        elif discipline_strictness >= 75 and p_morale <= 78:
            outcome = "accepted"
            deltas["alignment"] = 4
            deltas["trust"] = 2
            state_effects["manager_disciplinary_exclusion"] = {
                "player_id": p_id,
                "player_name": p_name,
                "matchday_role": "excluded_disciplinary",
            }
            reasoning_trace["verdict_reason"] = (
                f"Manager shares disciplinary standards ({discipline_strictness}/100) and agrees to rotate {p_name} out of the next fixture."
            )
        else:
            outcome = "counterproposal"
            deltas["tension"] = 4
            deltas["autonomy"] = -3
            reasoning_trace["verdict_reason"] = (
                f"Manager prefers handling {p_name}'s conduct internally via a private warning and training assessment before dropping a key starter."
            )

    elif intent in ("tactical_style_shift", "formation_request", "club_culture_direction"):
        req_style = intent_data.get("requested_style")
        atk_def = _optional_score(personality, "attacking_vs_defensive")
        poss_dir = _optional_score(personality, "possession_vs_direct")
        press = _optional_score(personality, "pressing_philosophy")

        measured_styles = {
            "attacking": atk_def,
            "defensive": atk_def,
            "possession": poss_dir,
            "high_pressing": press,
        }
        style_gap = None
        if req_style and req_style not in measured_styles:
            style_gap = 0
        elif req_style and measured_styles.get(req_style) is not None:
            if req_style == "attacking":
                style_gap = max(0, 72 - atk_def)
            elif req_style == "defensive":
                style_gap = max(0, atk_def - 42)
            elif req_style == "possession":
                style_gap = max(0, 72 - poss_dir)
            elif req_style == "high_pressing":
                style_gap = max(0, 75 - press)

        reasoning_trace.update(
            {
                "requested_style": req_style,
                "manager_attacking_vs_defensive": atk_def,
                "manager_possession_vs_direct": poss_dir,
                "manager_pressing_philosophy": press,
                "manager_tactical_flexibility": tactical_flex,
                "style_gap": style_gap,
            }
        )

        if intent != "club_culture_direction" and role_key not in ("first_team_manager", "head_coach"):
            philosophy = str(
                personality.get("philosophy")
                or personality.get("operating_philosophy")
                or personality.get("style")
                or "their filed brief"
            )
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                f"{staff_name} leaves the shape to the first-team manager. Their own brief is {philosophy}."
            )
        elif style_gap is None or tactical_flex is None or adaptability is None:
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                "The requested style or the manager's tactical scores are not filed, so the shape was left unchanged."
            )
        elif style_gap <= 15:
            outcome = "accepted"
            deltas["alignment"] = 5
            deltas["culture_alignment"] = 6
            deltas["trust"] = 3
            state_effects["culture_transition"] = {
                "target_identity": req_style,
                "progress_delta": 20,
                "mode": "aligned_acceleration",
            }
            reasoning_trace["verdict_reason"] = (
                f"Requested {req_style} direction aligns closely with staff philosophy (gap={style_gap})."
            )
        elif tactical_flex >= 62 and adaptability >= 60 and style_gap <= 35:
            outcome = "conditional_acceptance"
            deltas["alignment"] = 2
            deltas["culture_alignment"] = 3
            deltas["autonomy"] = -2
            state_effects["culture_transition"] = {
                "target_identity": req_style,
                "progress_delta": 12,
                "mode": "gradual_phased_transition",
            }
            reasoning_trace["verdict_reason"] = (
                f"Staff member agrees to a phased tactical transition toward {req_style} over multiple training cycles, conditioned on squad suitability."
            )
        else:
            outcome = "needs_meeting" if interference_count <= 1 else "formal_disagreement"
            deltas["tension"] = 9
            deltas["alignment"] = -7
            deltas["culture_alignment"] = -8
            deltas["autonomy"] = -5
            reasoning_trace["verdict_reason"] = (
                f"Fundamental philosophical gap (gap={style_gap}, flexibility={tactical_flex}). A defensive/specialized coach cannot flip overnight into {req_style} football without compromising structural integrity."
            )

    elif intent == "transfer_recruitment_target":
        pos = str(intent_data.get("detected_position") or "").upper()
        min_gsi = intent_data.get("min_gsi")
        max_gsi = intent_data.get("max_gsi")
        min_gsi = int(min_gsi) if min_gsi is not None else None
        max_gsi = int(max_gsi) if max_gsi is not None else None
        expensive = bool(intent_data.get("expensive_request", False))
        band = f" at GSI {min_gsi}–{max_gsi}" if min_gsi is not None and max_gsi is not None else ""
        if not pos:
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = "No position was named, so no recruitment search was opened."
        elif role_key == "chief_scout":
            philosophy = str(
                personality.get("philosophy")
                or personality.get("operating_philosophy")
                or personality.get("style")
                or "the filed scouting brief"
            )
            outcome = "accepted"
            state_effects["scout_shortlist"] = {
                "target_position": pos,
                "min_gsi": min_gsi,
                "max_gsi": max_gsi,
                "philosophy": philosophy,
            }
            reasoning_trace["verdict_reason"] = f"{staff_name} will shortlist {pos} targets{band} under {philosophy}."
        elif role_key == "head_of_youth_development":
            philosophy = str(
                personality.get("philosophy")
                or personality.get("operating_philosophy")
                or personality.get("style")
                or "the filed youth brief"
            )
            outcome = "accepted"
            state_effects["youth_recruitment_note"] = {
                "target_position": pos,
                "age_band": "16-21",
                "philosophy": philosophy,
            }
            reasoning_trace["verdict_reason"] = (
                f"{staff_name} will judge {pos} targets on the 16–21 age profile under {philosophy}. The general manager holds the fee."
            )
        elif role_key == "medical_director":
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                f"{staff_name} does not run recruitment. The general manager holds the fee."
            )
        else:
            treasury = _club_treasury_gtex(db, state)
            fin_disc = _optional_score(personality, "financial_discipline")
            risk_tol = _optional_score(personality, "transfer_risk_tolerance")
            reasoning_trace.update(
                {
                    "target_position": pos,
                    "min_gsi": min_gsi,
                    "max_gsi": max_gsi,
                    "expensive_request": expensive,
                    "treasury_balance": treasury,
                    "gm_financial_discipline": fin_disc,
                    "gm_transfer_risk_tolerance": risk_tol,
                }
            )
            conservative = (
                expensive and fin_disc is not None and fin_disc >= 68 and (risk_tol is None or risk_tol <= 60)
            )
            workflow = {
                "target_position": pos,
                "min_gsi": min_gsi,
                "max_gsi": max_gsi,
                "gm_verdict": "counterproposal_younger_value" if conservative else "shortlist_commissioned",
            }
            if conservative:
                outcome = "counterproposal"
                deltas["respect"] = 2
                deltas["tension"] = 4
                deltas["alignment"] = -2
                state_effects["recruitment_workflow"] = workflow
                reasoning_trace["verdict_reason"] = (
                    f"Financial discipline is {fin_disc}/100 and the request is a marquee {pos}. "
                    f"The fee will be the value already filed on each player, against treasury {treasury:,.0f} GTX. "
                    "A younger filed alternative is the counterproposal."
                )
            else:
                outcome = "accepted"
                deltas["trust"] = 3
                deltas["alignment"] = 4
                state_effects["recruitment_workflow"] = workflow
                reasoning_trace["verdict_reason"] = (
                    f"Recruitment assignment opened for {pos}{band}. "
                    f"Fees stay on the player records. Treasury on the day is {treasury:,.0f} GTX."
                )

    elif intent == "recruitment_spending_critique":
        if role_key not in ("general_manager", "finance_commercial_director"):
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = f"{staff_name} does not hold the wage book. The general manager does."
        else:
            fin_disc = _optional_score(personality, "financial_discipline")
            reasoning_trace["gm_financial_discipline"] = fin_disc
            if fin_disc is None:
                outcome = "deferred"
                reasoning_trace["verdict_reason"] = (
                    "Financial discipline is not filed, so the wage ceiling was left unchanged."
                )
            elif fin_disc >= 75:
                outcome = "accepted"
                deltas["alignment"] = 4
                deltas["trust"] = 2
                state_effects["wage_ceiling"] = {"mode": "catalog"}
                reasoning_trace["verdict_reason"] = (
                    "General Manager shares strict cost-control philosophy and tightens valuation ceilings on active targets."
                )
            else:
                outcome = "formal_disagreement"
                deltas["tension"] = 8
                deltas["alignment"] = -6
                deltas["autonomy"] = -5
                reasoning_trace["verdict_reason"] = (
                    "Ambitious recruitment lead defends squad investment levels as essential to compete at the club's target tier."
                )

    elif intent == "medical_clearance_pressure":
        if role_key != "medical_director":
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                f"{staff_name} does not clear players. The medical director holds return-to-play."
            )
        else:
            if personality.get("protocol_strictness") is not None:
                strictness = int(personality["protocol_strictness"])
            else:
                strictness = independence
            reasoning_trace["medical_protocol_strictness"] = strictness
            if strictness is None:
                outcome = "deferred"
                reasoning_trace["verdict_reason"] = "Medical strictness is not filed, so no clearance was changed."
            else:
                outcome = "declined" if strictness >= 70 else "conditional_acceptance"
                deltas["tension"] = 6
                deltas["autonomy"] = -4
                deltas["respect"] = 2
                reasoning_trace["verdict_reason"] = (
                    "Medical Director refuses to override return-to-play biometrics where reinjury risk exceeds clinical thresholds."
                )

    elif intent == "challenge_or_override_decision":
        reasoning_trace.update(
            {
                "interference_count": interference_count,
                "professional_independence": independence,
                "tolerance_for_owner_interference": interference_tolerance,
                "ego_reputation_sensitivity": ego_sensitivity,
            }
        )
        if independence is None or interference_tolerance is None:
            outcome = "deferred"
            reasoning_trace["verdict_reason"] = (
                "Independence and interference tolerance are not filed, so no override was judged."
            )
        elif interference_count >= 4 and independence >= 72 and interference_tolerance <= 45:
            outcome = "resignation_notice"
            deltas["tension"] = 22
            deltas["trust"] = -20
            deltas["autonomy"] = -25
            deltas["loyalty"] = -25
            reasoning_trace["verdict_reason"] = (
                f"Repeated owner interference (#{interference_count}) crossed the staff member's professional independence threshold ({independence}/100), triggering formal resignation."
            )
        elif interference_count >= 3 and independence >= 70 and interference_tolerance <= 50:
            outcome = "ultimatum"
            deltas["tension"] = 16
            deltas["trust"] = -12
            deltas["autonomy"] = -16
            deltas["loyalty"] = -12
            rel_meta["ultimatum_active"] = True
            reasoning_trace["verdict_reason"] = (
                f"Repeated owner interference (#{interference_count}) triggered a formal ultimatum protecting selection and coaching autonomy."
            )
        elif independence >= 60:
            outcome = "formal_disagreement"
            deltas["tension"] = 12
            deltas["trust"] = -8
            deltas["autonomy"] = -10
            deltas["alignment"] = -8
            reasoning_trace["verdict_reason"] = (
                "Staff member stands by his professional footballing judgement and logs a formal disagreement."
            )
        else:
            outcome = "conditional_acceptance"
            deltas["tension"] = 6
            deltas["autonomy"] = -8
            deltas["confidence"] = -6
            reasoning_trace["verdict_reason"] = (
                "Staff member reluctantly accommodates the owner's insistence under protest while noting the sporting risk."
            )

    else:
        outcome = "accepted"
        deltas["trust"] = 2
        deltas["respect"] = 2
        deltas["tension"] = -1
        reasoning_trace["verdict_reason"] = (
            "Constructive professional consultation grounded in current squad, tactical, and operational status."
        )

    relationship.trust = _clamp(relationship.trust + deltas["trust"])
    relationship.respect = _clamp(relationship.respect + deltas["respect"])
    relationship.alignment = _clamp(relationship.alignment + deltas["alignment"])
    relationship.tension = _clamp(relationship.tension + deltas["tension"])
    relationship.loyalty = _clamp(relationship.loyalty + deltas["loyalty"])

    rel_meta["ambition_compatibility"] = _clamp(
        int(rel_meta.get("ambition_compatibility", 74)) + deltas["ambition_compatibility"]
    )
    rel_meta["autonomy"] = _clamp(int(rel_meta.get("autonomy", 75)) + deltas["autonomy"])
    rel_meta["confidence"] = _clamp(int(rel_meta.get("confidence", 75)) + deltas["confidence"])
    rel_meta["culture_alignment"] = _clamp(int(rel_meta.get("culture_alignment", 72)) + deltas["culture_alignment"])

    if outcome in ("declined", "formal_disagreement", "ultimatum", "resignation_notice"):
        unresolved.append(
            {
                "id": str(uuid4())[:8],
                "intent": intent,
                "outcome": outcome,
                "summary": reasoning_trace.get("verdict_reason", ""),
                "recorded_at": _utcnow().isoformat(),
            }
        )
        rel_meta["unresolved_disagreements"] = unresolved[-10:]

    if outcome == "resignation_notice":
        rel_meta["resignation_notice_served"] = True
        relationship.status = "resigned"
        state_effects["staff_resigned"] = {
            "staff_id": staff_id,
            "staff_name": staff_name,
            "staff_role": role_key,
            "reason": "resigned_owner_interference",
        }
    elif outcome == "ultimatum" or relationship.tension >= 75:
        relationship.status = "volatile"
    elif relationship.tension >= 52 or relationship.trust <= 42:
        relationship.status = "strained"
    elif relationship.trust >= 70 and relationship.tension <= 28:
        relationship.status = "aligned"
    else:
        relationship.status = "watchful"

    relationship.metadata_json = rel_meta
    flag_modified(relationship, "metadata_json")
    relationship.updated_at = _utcnow()

    decision_rel_snapshot = serialize_relationship_health(relationship)
    db.add(
        OwnerClubRelationshipHistory(
            id=str(uuid4()),
            relationship_id=relationship.id,
            club_id=state.club_id,
            world_day=int(state.world_day or 1),
            reason=f"{staff_name} ({staff_title}) decision '{outcome}' on '{intent}': {reasoning_trace.get('verdict_reason', '')}"[
                :250
            ],
            delta_trust=deltas["trust"],
            delta_respect=deltas["respect"],
            delta_affinity=0,
            delta_tension=deltas["tension"],
            delta_alignment=deltas["alignment"],
            delta_influence=0,
            delta_loyalty=deltas["loyalty"],
            snapshot_json=decision_rel_snapshot,
            created_at=_utcnow(),
        )
    )

    _apply_layer_a_state_effects(
        db,
        state,
        role_key=role_key,
        staff_id=staff_id,
        staff_name=staff_name,
        staff_title=staff_title,
        personality=personality,
        outcome=outcome,
        state_effects=state_effects,
    )

    return {
        "decision_outcome": outcome,
        "intent": intent,
        "reasoning_trace": reasoning_trace,
        "relationship_deltas": deltas,
        "relationship_snapshot": decision_rel_snapshot,
        "state_effects": state_effects,
    }


def _apply_layer_a_state_effects(
    db: Session,
    state: OwnerClubState,
    *,
    role_key: str,
    staff_id: str,
    staff_name: str,
    staff_title: str,
    personality: dict[str, Any],
    outcome: str,
    state_effects: dict[str, Any],
) -> None:
    fac = dict(state.facilities_json or {})

    if "manager_matchday_commitment" in state_effects:
        commitments = dict(fac.get("_manager_matchday_commitments") or {})
        item = state_effects["manager_matchday_commitment"]
        commitments[str(item["player_id"])] = {
            **item,
            "approved_by_manager_id": staff_id,
            "approved_by_manager_name": staff_name,
            "updated_at": _utcnow().isoformat(),
        }
        fac["_manager_matchday_commitments"] = commitments

    if "manager_matchday_rejection" in state_effects:
        commitments = dict(fac.get("_manager_matchday_commitments") or {})
        item = state_effects["manager_matchday_rejection"]
        commitments.pop(str(item["player_id"]), None)
        rejections = dict(fac.get("_manager_matchday_rejections") or {})
        rejections[str(item["player_id"])] = {
            **item,
            "rejected_by_manager_id": staff_id,
            "rejected_by_manager_name": staff_name,
            "updated_at": _utcnow().isoformat(),
        }
        fac["_manager_matchday_commitments"] = commitments
        fac["_manager_matchday_rejections"] = rejections
        fac["_manager_youth_rejection_streak"] = int(fac.get("_manager_youth_rejection_streak") or 0) + 1

        # Private internal consequence only: elevate HOYD internal concern & record strictly confidential event.
        # Public supporters and media do NOT learn of private chats here; public consequences only follow observable
        # matchday lineups with zero youth appearances.
        hoyd = (fac.get("_executive_staff") or {}).get("head_of_youth_development") or {}
        hoyd_name = str(hoyd.get("name") or "").strip()
        if hoyd_name and not hoyd.get("is_vacant") and not hoyd.get("is_default"):
            hoyd_rel = ensure_staff_relationship(
                db,
                state,
                role_key="head_of_youth_development",
                staff_id=str(hoyd.get("id") or hoyd.get("staff_id") or "head_of_youth_development"),
                staff_name=hoyd_name,
                staff_title="Head of Youth Development",
                personality_profile=dict(hoyd.get("personality_profile") or {}),
            )
            hoyd_rel.tension = _clamp(int(hoyd_rel.tension) + 4)
            hoyd_rel.alignment = _clamp(int(hoyd_rel.alignment) - 4)
            hoyd_meta = dict(hoyd_rel.metadata_json or {})
            hoyd_meta["internal_academy_concern"] = {
                "player_id": str(item.get("player_id") or ""),
                "player_name": str(item.get("player_name") or ""),
                "rejected_by_manager": staff_name,
                "world_day": int(state.world_day or 1),
            }
            hoyd_rel.metadata_json = hoyd_meta
            flag_modified(hoyd_rel, "metadata_json")

        from app.owner_console import living_institution

        living_institution.emit_canonical_club_event(
            db,
            state,
            category="academy",
            event_type="internal_youth_pathway_disagreement",
            source_subsystem="autonomous_staff",
            title=f"Internal Selection Divergence: {staff_name} Declines Immediate Youth Commitment",
            description=(
                f"Private internal disagreement recorded between executive guidance and {staff_name} regarding "
                f"immediate matchday involvement for {item.get('player_name', 'academy prospect')}. Remains confidential."
            ),
            idempotency_key=(
                f"internal:youth_reject:{state.club_id}:{item.get('player_id')}:d{int(state.world_day or 1)}:{uuid4().hex[:6]}"
            ),
            visibility_classification=living_institution.VISIBILITY_PRIVATE_INTERNAL,
            severity="routine",
            source_type="staff_decision",
            source_id=staff_id,
            payload={
                "player_id": str(item.get("player_id") or ""),
                "manager_id": staff_id,
                "manager_name": staff_name,
                "hoyd_concern_raised": True,
            },
        )

    if "manager_disciplinary_exclusion" in state_effects:
        exclusions = dict(fac.get("_manager_disciplinary_exclusions") or {})
        item = state_effects["manager_disciplinary_exclusion"]
        exclusions[str(item["player_id"])] = {
            **item,
            "excluded_by_manager_id": staff_id,
            "updated_at": _utcnow().isoformat(),
        }
        fac["_manager_disciplinary_exclusions"] = exclusions

    if "culture_transition" in state_effects:
        ct = state_effects["culture_transition"]
        culture = dict(fac.get("_club_culture") or {})
        target = str(ct.get("target_identity") or "attacking")
        if culture.get("target_identity") != target:
            culture["target_identity"] = target
            culture["transition_progress_pct"] = min(100, int(ct.get("progress_delta", 15)))
        else:
            culture["transition_progress_pct"] = min(
                100, int(culture.get("transition_progress_pct", 20)) + int(ct.get("progress_delta", 15))
            )
        if culture["transition_progress_pct"] >= 100:
            culture["primary_identity"] = target
        culture["last_discussed_at"] = _utcnow().isoformat()
        fac["_club_culture"] = culture

    if "recruitment_workflow" in state_effects:
        rw = state_effects["recruitment_workflow"]
        assignment = execute_inter_staff_recruitment_workflow(
            db,
            state,
            initiated_by_role="owner" if role_key == "general_manager" else role_key,
            initiated_by_name=staff_name,
            target_position=str(rw.get("target_position") or ""),
            min_gsi=int(rw["min_gsi"]) if rw.get("min_gsi") is not None else None,
            max_gsi=int(rw["max_gsi"]) if rw.get("max_gsi") is not None else None,
            gm_verdict=str(rw.get("gm_verdict") or "shortlist_commissioned"),
            estimated_fee=float(rw["estimated_fee"]) if rw.get("estimated_fee") is not None else None,
            estimated_weekly_wage=(
                float(rw["estimated_weekly_wage"]) if rw.get("estimated_weekly_wage") is not None else None
            ),
        )
        state_effects["recruitment_assignment_id"] = assignment.id
        state_effects["candidate_shortlist"] = assignment.candidate_shortlist_json
        state_effects["recommended_candidate"] = assignment.recommended_candidate_json

    if "scout_shortlist" in state_effects:
        brief = dict(state_effects["scout_shortlist"])
        pos = str(brief.get("target_position") or "").upper()
        min_gsi = int(brief["min_gsi"]) if brief.get("min_gsi") is not None else None
        max_gsi = int(brief["max_gsi"]) if brief.get("max_gsi") is not None else None
        philosophy = str(brief.get("philosophy") or "")
        rows = list(
            db.scalars(
                select(OwnerSquadPlayer).where(
                    OwnerSquadPlayer.club_id != state.club_id,
                    OwnerSquadPlayer.status == "active",
                )
            ).all()
        )
        shortlist: list[dict[str, Any]] = []
        for row in rows:
            if row.rating is None:
                continue
            rating = int(row.rating)
            if min_gsi is not None and rating < min_gsi:
                continue
            if max_gsi is not None and rating > max_gsi:
                continue
            row_pos = str(row.position or "").upper()
            if pos and pos not in row_pos and row_pos not in pos:
                continue
            shortlist.append(
                {
                    "candidate_id": row.id,
                    "player_name": row.name,
                    "position": row.position,
                    "age": row.age,
                    "gsi": rating,
                    "potential": int(row.potential) if row.potential is not None else None,
                    "club_id": row.club_id,
                    "source": "filed_squad",
                }
            )
            if len(shortlist) >= 8:
                break
        assignment = OwnerRecruitmentAssignment(
            id=str(uuid4()),
            club_id=state.club_id,
            initiated_by_role="chief_scout",
            initiated_by_name=staff_name,
            target_position=pos or "ANY",
            min_gsi=min_gsi,
            max_gsi=max_gsi,
            tactical_profile=(philosophy or "filed")[:128],
            max_fee=0.0,
            max_weekly_wage=0.0,
            gm_evaluation_status="scout_shortlist",
            gm_notes="",
            scout_notes=(f"{staff_name} filed {pos or 'any position'} at GSI {min_gsi}–{max_gsi} under {philosophy}."),
            candidate_shortlist_json=shortlist,
            recommended_candidate_json=shortlist[0] if shortlist else {},
            metadata_json={"philosophy": philosophy, "filed_count": len(shortlist)},
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(assignment)
        db.flush()
        state_effects["recruitment_assignment_id"] = assignment.id
        state_effects["candidate_shortlist"] = shortlist

    if "youth_recruitment_note" in state_effects:
        fac["_youth_recruitment_brief"] = {
            **dict(state_effects["youth_recruitment_note"]),
            "filed_by": staff_name,
            "world_day": int(state.world_day or 1),
        }

    if "wage_ceiling" in state_effects and str(state_effects["wage_ceiling"].get("mode") or "") == "catalog":
        fac["_contract_wage_ceiling"] = "catalog"

    if role_key == "medical_director" and outcome == "declined":
        fac["_medical_protocol_hold"] = {
            "world_day": int(state.world_day or 1),
            "staff_name": staff_name,
            "reason": "return_to_play_refused",
        }

    if "staff_resigned" in state_effects:
        from app.owner_console import comms_persistence, living_club_world, living_institution

        history = list(fac.get("_staff_career_history") or [])
        history.append(
            {
                "staff_id": staff_id,
                "name": staff_name,
                "role": role_key,
                "title": staff_title,
                "action": "resigned",
                "reason": "resigned_owner_interference",
                "recorded_at": _utcnow().isoformat(),
            }
        )
        fac["_staff_career_history"] = history[-40:]
        prev_mgr_snapshot = dict(state.manager_json or {})
        if role_key in ("first_team_manager", "head_coach"):
            vacant_mgr = {"name": "", "is_vacant": True, "status": "vacant", "is_appointed": False}
            state.manager_json = vacant_mgr
            exec_staff = dict(fac.get("_executive_staff") or {})
            exec_staff.pop("first_team_manager", None)
            fac["_executive_staff"] = exec_staff
            setup = dict(fac.get("_tactical_setup") or {})
            setup.pop("ratified_manager_id", None)
            fac["_tactical_setup"] = setup
            flag_modified(state, "manager_json")
            state.facilities_json = fac
            flag_modified(state, "facilities_json")
            db.flush()

            resign_ev = living_institution.record_managerial_change(
                db,
                state,
                action="resigned",
                new_manager=vacant_mgr,
                previous_manager={**prev_mgr_snapshot, "id": staff_id, "name": staff_name},
                reason="resigned_owner_interference",
                severance_gtex=0,
                source_subsystem="autonomous_staff",
                idempotency_key=f"resign:{state.club_id}:{staff_id}:d{int(state.world_day or 1)}",
            )
            state_effects["canonical_event_id"] = resign_ev.id
            retire_staff_relationship_on_vacancy(db, state, role_key="first_team_manager")
            living_club_world.reconcile_staff_relationships(db, state)
            comms_persistence.rotate_staff_conversation_on_change(
                db,
                state,
                role_key="first_team_manager",
                previous_staff_name=staff_name,
                new_staff_name=None,
            )
        else:
            exec_staff = dict(fac.get("_executive_staff") or {})
            exec_staff.pop(role_key, None)
            fac["_executive_staff"] = exec_staff
            state.facilities_json = fac
            flag_modified(state, "facilities_json")
            db.flush()

            resign_ev = living_institution.record_executive_staff_change(
                db,
                state,
                action="dismissed",
                staff_role=role_key,
                staff_id=staff_id,
                staff_name=staff_name,
                fee_gtex=0,
                reason="resigned_owner_interference",
                idempotency_key=f"resign:{state.club_id}:{staff_id}:d{int(state.world_day or 1)}",
            )
            state_effects["canonical_event_id"] = resign_ev.id
            retire_staff_relationship_on_vacancy(db, state, role_key=role_key)
            living_club_world.reconcile_staff_relationships(db, state)
            comms_persistence.rotate_staff_conversation_on_change(
                db,
                state,
                role_key=role_key,
                previous_staff_name=staff_name,
                new_staff_name=None,
            )

        db.add(
            OwnerInboxItem(
                id=str(uuid4()),
                user_id=state.owner_user_id,
                club_id=state.club_id,
                kind="staff_resignation",
                priority="high",
                sender=staff_name,
                title=f"Formal Resignation Notice: {staff_name} ({staff_title})",
                what=f"{staff_name} has resigned as {staff_title}.",
                why="Repeated owner interference in professional sporting authority.",
                body=(
                    f"{staff_name} has tendered his resignation as {staff_title}, citing irreconcilable interference "
                    f"in professional sporting authority."
                ),
                category="requests",
                is_decision=False,
                status="open",
                created_at=_utcnow(),
            )
        )

    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    db.flush()


# ---------------------------------------------------------------------------
# SECTION 6 & 7: INTER-STAFF RECRUITMENT WORKFLOW (MANAGER <-> GM <-> CHIEF SCOUT)
# ---------------------------------------------------------------------------


def execute_inter_staff_recruitment_workflow(
    db: Session,
    state: OwnerClubState,
    *,
    initiated_by_role: str,
    initiated_by_name: str,
    target_position: str,
    min_gsi: int | None,
    max_gsi: int | None,
    gm_verdict: str = "shortlist_commissioned",
    estimated_fee: float | None = None,
    estimated_weekly_wage: float | None = None,
) -> OwnerRecruitmentAssignment:
    """Coordinate the First-Team Manager, General Manager, and Chief Scout on a recruitment requirement."""
    identities = ensure_club_staff_identities(db, state)
    gm = identities["general_manager"]
    scout = identities["chief_scout"]
    mgr = identities["first_team_manager"]
    mgr_profile = mgr["personality_profile"]
    treasury = _club_treasury_gtex(db, state)

    pos = target_position.upper()

    def _filed_targets(low: int | None, high: int | None, *, max_age: int | None = None) -> list[dict[str, Any]]:
        rows = list(
            db.scalars(
                select(OwnerSquadPlayer).where(
                    OwnerSquadPlayer.club_id != state.club_id,
                    OwnerSquadPlayer.status == "active",
                )
            ).all()
        )
        found: list[dict[str, Any]] = []
        for row in rows:
            if row.rating is None:
                continue
            rating = int(row.rating)
            age = int(row.age) if row.age is not None else None
            row_pos = str(row.position or "").upper()
            if low is not None and rating < low:
                continue
            if high is not None and rating > high:
                continue
            if pos and pos not in row_pos and row_pos not in pos:
                continue
            if max_age is not None and (age is None or age > max_age):
                continue
            fee = float(row.value_coin or 0)
            found.append(
                {
                    "candidate_id": row.id,
                    "player_name": row.name,
                    "position": row.position,
                    "age": age,
                    "gsi": rating,
                    "potential": int(row.potential) if row.potential is not None else None,
                    "estimated_fee": fee,
                    "weekly_wage_demand": 0,
                    "club_id": row.club_id,
                    "source": "filed_squad",
                    "tactical_fit": str(mgr_profile.get("preferred_tactical_philosophy") or ""),
                    "summary": f"{row.name} is already on another club's squad.",
                }
            )
        found.sort(key=lambda item: (item["age"] is None, item["age"] or 0, -int(item["gsi"])))
        return found

    prime = _filed_targets(min_gsi, max_gsi)
    younger_low = max(1, min_gsi - 8) if min_gsi is not None else None
    younger = _filed_targets(younger_low, max_gsi, max_age=21)
    if gm_verdict == "counterproposal_younger_value" and younger:
        shortlist = younger
        recommended = younger[0]
        gm_status = "counterproposal_younger_value"
    elif prime:
        shortlist = prime
        recommended = prime[0]
        gm_status = "awaiting_owner_approval"
    else:
        shortlist = []
        recommended = {
            "candidate_id": "",
            "player_name": "",
            "position": pos,
            "age": None,
            "gsi": None,
            "potential": None,
            "estimated_fee": 0,
            "weekly_wage_demand": 0,
            "source": "none_filed",
            "summary": "No player in this band is filed on another club's squad.",
        }
        gm_status = "no_filed_target"

    existing_watchlist_names = {
        str(w.player_name)
        for w in db.scalars(select(OwnerScoutingWatchlist).where(OwnerScoutingWatchlist.club_id == state.club_id)).all()
    }
    for cand in shortlist:
        if cand["player_name"] not in existing_watchlist_names:
            db.add(
                OwnerScoutingWatchlist(
                    id=str(uuid4()),
                    club_id=state.club_id,
                    save_context_id=f"save:{state.club_id}",
                    player_id=cand["candidate_id"],
                    player_name=cand["player_name"],
                    position=cand["position"],
                    age=cand["age"],
                    current_rating=cand["gsi"],
                    potential_rating=cand["potential"],
                    estimated_value_gtex=Decimal(str(cand["estimated_fee"])),
                    priority="high",
                    scout_notes=cand["summary"],
                    recommendation=cand.get("tactical_fit") or "",
                    created_at=_utcnow(),
                )
            )

    policy = db.scalar(select(ClubDelegationPolicy).where(ClubDelegationPolicy.club_id == state.club_id))
    operating_mode = str(policy.mode) if policy else "balanced"
    thresholds = dict((policy.financial_thresholds_json if policy else None) or {})
    if "max_single_transfer_auto_approve_gtex" in thresholds:
        max_auto_spend = float(thresholds["max_single_transfer_auto_approve_gtex"])
    elif "max_auto_spend_gtex" in thresholds:
        max_auto_spend = float(thresholds["max_auto_spend_gtex"])
    else:
        max_auto_spend = None
    delegated_decision_id: str | None = None

    if (
        recommended.get("player_name")
        and operating_mode in ("gm_led", "full_delegation")
        and max_auto_spend is not None
        and float(recommended["estimated_fee"]) <= max_auto_spend
        and gm_status != "counterproposal_younger_value"
    ):
        gm_status = "approved_within_authority"
        decision = ClubDelegatedDecision(
            id=str(uuid4()),
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            activity_key=f"recruitment_{pos.lower()}",
            domain="recruitment",
            proposed_by_role="general_manager",
            proposed_by_staff_name=str(gm["name"]),
            title=f"GM Authorised Recruitment: {recommended['player_name']} ({pos}, GSI {recommended['gsi']})",
            summary=(
                f"{gm['name']} (GM) approved the recruitment of {recommended['player_name']} within delegated spending limits ({max_auto_spend:,.0f} GTX)."
            ),
            financial_amount_gtex=Decimal(str(recommended["estimated_fee"])),
            requires_owner_approval=False,
            status="auto_executed",
            execution_status="executed",
            staff_competence_rating=int(gm["rating"]) if gm.get("rating") is not None else None,
            payload_json={
                "target_position": pos,
                "min_gsi": min_gsi,
                "max_gsi": max_gsi,
                "recommended_candidate": recommended,
                "candidate_shortlist": shortlist,
            },
            created_at=_utcnow(),
        )
        db.add(decision)
        db.flush()
        delegated_decision_id = decision.id
    elif recommended.get("player_name"):
        decision = ClubDelegatedDecision(
            id=str(uuid4()),
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            activity_key=f"recruitment_{pos.lower()}",
            domain="recruitment",
            proposed_by_role="general_manager",
            proposed_by_staff_name=str(gm["name"]),
            title=f"GM Recruitment Proposal: {recommended['player_name']} ({pos}, GSI {recommended['gsi']})",
            summary=(
                f"{gm['name']} (GM) and {scout['name']} (Chief Scout) evaluated the {pos} requirement (GSI {min_gsi}–{max_gsi}). "
                f"Recommended target: {recommended['player_name']} (age {recommended['age']}, GSI {recommended['gsi']}, potential {recommended['potential']}) "
                f"at est. fee {recommended['estimated_fee']:,.0f} GTX and weekly wage {recommended['weekly_wage_demand']:,.0f} GTX."
            ),
            financial_amount_gtex=Decimal(str(recommended["estimated_fee"])),
            requires_owner_approval=True,
            approval_reason="Transfer package requires owner sign-off under current delegation policy.",
            status="pending_approval",
            execution_status="pending_execution",
            staff_competence_rating=int(gm["rating"]) if gm.get("rating") is not None else None,
            payload_json={
                "target_position": pos,
                "min_gsi": min_gsi,
                "max_gsi": max_gsi,
                "recommended_candidate": recommended,
                "candidate_shortlist": shortlist,
            },
            created_at=_utcnow(),
        )
        db.add(decision)
        db.flush()
        delegated_decision_id = decision.id

    if recommended.get("player_name"):
        gm_notes = (
            f"{gm.get('name') or 'The general manager'} reviewed liquid treasury ({treasury:,.0f} GTX). "
            f"Recommended option: {recommended['player_name']} ({pos}, GSI {recommended['gsi']}) at {float(recommended['estimated_fee']):,.0f} GTX."
        )
        scout_notes = (
            f"Filed {len(shortlist)} {pos} player(s) already on other squads in the {min_gsi}–{max_gsi} window."
        )
    else:
        gm_notes = (
            f"No {pos} player between GSI {min_gsi} and {max_gsi} is filed on another club's squad. "
            f"Treasury on the day is {treasury:,.0f} GTX."
        )
        scout_notes = "No matching player is filed."

    assignment = OwnerRecruitmentAssignment(
        id=str(uuid4()),
        club_id=state.club_id,
        initiated_by_role=initiated_by_role,
        initiated_by_name=initiated_by_name,
        target_position=pos,
        min_gsi=min_gsi,
        max_gsi=max_gsi,
        tactical_profile=str(mgr_profile.get("preferred_tactical_philosophy") or ""),
        max_fee=float(recommended["estimated_fee"]),
        max_weekly_wage=float(recommended["weekly_wage_demand"]),
        gm_evaluation_status=gm_status,
        gm_notes=gm_notes,
        scout_notes=scout_notes,
        candidate_shortlist_json=shortlist,
        recommended_candidate_json=recommended,
        delegated_decision_id=delegated_decision_id,
        metadata_json={"operating_mode": operating_mode, "max_auto_spend": max_auto_spend},
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(assignment)
    db.flush()

    # If policy authorised automatic GM execution, attempt full transfer execution immediately
    if operating_mode in ("gm_led", "full_delegation") and gm_status == "approved_within_authority":
        execute_authorized_recruitment_signing(
            db,
            state,
            assignment_id=assignment.id,
            decision_id=delegated_decision_id,
            user_id=state.owner_user_id,
        )

    return assignment


def execute_authorized_recruitment_signing(
    db: Session,
    state: OwnerClubState,
    *,
    assignment_id: str | None = None,
    decision_id: str | None = None,
    user_id: str | None = None,
    chosen_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Execute an authorised GM/owner recruitment signing end-to-end:
    treasury check -> ledger debit -> OwnerSquadPlayer arrival -> permanent OwnerClubTransferRecord -> media/supporters.
    """
    from app.owner_console import living_institution

    assignment: OwnerRecruitmentAssignment | None = None
    decision: ClubDelegatedDecision | None = None

    if assignment_id:
        assignment = db.scalar(
            select(OwnerRecruitmentAssignment).where(
                OwnerRecruitmentAssignment.id == assignment_id,
                OwnerRecruitmentAssignment.club_id == state.club_id,
            )
        )
    if decision_id:
        decision = db.scalar(
            select(ClubDelegatedDecision).where(
                ClubDelegatedDecision.id == decision_id,
                ClubDelegatedDecision.club_id == state.club_id,
            )
        )
    if assignment is None and decision is not None:
        assignment = db.scalar(
            select(OwnerRecruitmentAssignment).where(
                OwnerRecruitmentAssignment.delegated_decision_id == decision.id,
                OwnerRecruitmentAssignment.club_id == state.club_id,
            )
        )
    if decision is None and assignment is not None and assignment.delegated_decision_id:
        decision = db.scalar(
            select(ClubDelegatedDecision).where(
                ClubDelegatedDecision.id == assignment.delegated_decision_id,
                ClubDelegatedDecision.club_id == state.club_id,
            )
        )

    if assignment is None and decision is None:
        raise ValueError("recruitment_assignment_not_found")

    a_meta = dict((assignment.metadata_json if assignment else None) or {})
    if assignment is not None and (
        assignment.gm_evaluation_status in ("completed", "signed_to_first_team") or a_meta.get("executed_player_id")
    ):
        return {
            "executed": True,
            "already_executed": True,
            "player_id": a_meta.get("executed_player_id"),
            "player_name": (assignment.recommended_candidate_json or {}).get("player_name"),
            "fee_gtex": float(a_meta.get("executed_fee_gtex") or assignment.max_fee or 0),
            "assignment_id": assignment.id,
        }

    shortlist = list(
        (assignment.candidate_shortlist_json if assignment else None)
        or ((decision.payload_json or {}).get("candidate_shortlist") if decision else [])
        or []
    )
    candidate: dict[str, Any] | None = None
    if chosen_candidate_id:
        candidate = next(
            (c for c in shortlist if str(c.get("candidate_id")) == str(chosen_candidate_id)),
            None,
        )
    if candidate is None:
        candidate = dict(
            (assignment.recommended_candidate_json if assignment else None)
            or ((decision.payload_json or {}).get("recommended_candidate") if decision else {})
            or (shortlist[0] if shortlist else {})
        )

    player_name = str(candidate.get("player_name") or "Recruited First-Team Target")
    pos = str(candidate.get("position") or (assignment.target_position if assignment else "CM"))
    age = int(candidate.get("age") or 23)
    gsi = int(candidate.get("gsi") or (assignment.min_gsi if assignment else 78))
    pot = int(candidate.get("potential") or max(gsi, gsi + 3))
    fee_dec = ledger.D(
        candidate.get("estimated_fee")
        or (decision.financial_amount_gtex if decision and decision.financial_amount_gtex else None)
        or (assignment.max_fee if assignment else 5000)
    )
    wage_dec = ledger.D(candidate.get("weekly_wage_demand") or (assignment.max_weekly_wage if assignment else 750))
    cand_id = str(candidate.get("candidate_id") or f"target_{uuid4().hex[:8]}")
    ref_key = assignment.id if assignment else str(decision.id)

    funding = ledger.get_club_funding(db, state.club_id)
    is_restricted_recruitment = (
        gsi >= 75 or bool(candidate.get("is_regen")) or bool(candidate.get("is_legend") or candidate.get("legend"))
    )
    # Autonomous recruitment never draws from the first-club squad grant.
    # Premium/restricted targets require deposited funds; other targets may
    # use ordinary promotional, earned, or deposited club balances.
    funding_pools = (
        (("deposited", funding["available_deposited"]),)
        if is_restricted_recruitment
        else (
            ("promotional", funding["available_promotional"]),
            ("earned", funding["available_earned"]),
            ("deposited", funding["available_deposited"]),
        )
    )
    available_for_route = sum((ledger.D(value) for _, value in funding_pools), ledger.D(0))
    if fee_dec > available_for_route:
        failure_reason = (
            "restricted_player_requires_deposited_funds"
            if is_restricted_recruitment and funding["total_cash"] >= fee_dec
            else "insufficient_funds"
        )
        if assignment is not None:
            assignment.gm_evaluation_status = "failed_insufficient_funds"
            assignment.metadata_json = {
                **a_meta,
                "execution_status": "failed_insufficient_funds",
                "failure_reason": failure_reason,
                "required_gtex": float(fee_dec),
                "available_gtex": float(available_for_route),
            }
            flag_modified(assignment, "metadata_json")
            assignment.updated_at = _utcnow()
        if decision is not None:
            decision.execution_status = "failed_insufficient_funds"
            decision.outcome_text = (
                f"Signing of {player_name} blocked: required {float(fee_dec):,.2f} GTX, "
                f"eligible recruitment funds available {float(available_for_route):,.2f} GTX."
            )
        living_institution.emit_canonical_club_event(
            db,
            state,
            category="recruitment",
            event_type="recruitment_execution_blocked",
            source_subsystem="recruitment",
            title=f"Recruitment Blocked: Eligible Funds Unavailable for {player_name}",
            description=(
                f"Authorised move for {player_name} ({pos}) halted because the eligible funding "
                f"pool holds {float(available_for_route):,.0f} GTX against a fee of {float(fee_dec):,.0f} GTX."
            ),
            idempotency_key=f"recruit_blocked:{ref_key}:{cand_id}:d{int(state.world_day or 1)}",
            visibility_classification=living_institution.VISIBILITY_RESTRICTED_EXECUTIVE,
            severity="high",
            source_type="recruitment_assignment",
            source_id=ref_key,
            payload={
                "player_name": player_name,
                "required_gtex": float(fee_dec),
                "available_gtex": float(available_for_route),
                "failure_reason": failure_reason,
            },
        )
        db.flush()
        return {
            "executed": False,
            "reason": failure_reason,
            "player_name": player_name,
            "required_gtex": float(fee_dec),
            "available_gtex": float(available_for_route),
            "assignment_id": assignment.id if assignment else None,
        }

    ledger_events = []
    remaining_fee = fee_dec
    try:
        with db.begin_nested():
            for balance_class, available_amount in funding_pools:
                if remaining_fee <= 0:
                    break
                portion = min(ledger.D(available_amount), remaining_fee)
                if portion <= 0:
                    continue
                selling_club_id = str(candidate.get("selling_club_id") or "")
                seller_account = (
                    ledger.club_account(selling_club_id)
                    if selling_club_id and selling_club_id != state.club_id
                    else ledger.WORLD_MARKET
                )
                ledger_events.append(
                    ledger.record(
                        db,
                        event_type="transfer_purchase",
                        source=ledger.club_account(state.club_id),
                        destination=seller_account,
                        currency=ledger.GTEX,
                        gross=portion,
                        fee_bps=ledger.TRANSFER_PLATFORM_FEE_BPS,
                        balance_class=balance_class,
                        club_id=state.club_id,
                        user_id=user_id or state.owner_user_id,
                        related_type="recruitment_assignment",
                        related_id=ref_key,
                        memo=f"Authorised recruitment signing: {player_name} ({pos}, GSI {gsi})",
                        check_funds=True,
                        wallet_idempotency_key=f"recruit_exec:{ref_key}:{cand_id}:{balance_class}",
                    )
                )
                remaining_fee -= portion
            if remaining_fee > 0:
                raise ledger.LedgerError("insufficient_eligible_recruitment_funds")
    except ledger.LedgerError as exc:
        if assignment is not None:
            assignment.gm_evaluation_status = "failed_insufficient_funds"
        if decision is not None:
            decision.execution_status = "failed_insufficient_funds"
            decision.outcome_text = str(exc)
        db.flush()
        return {
            "executed": False,
            "reason": str(exc),
            "player_name": player_name,
            "required_gtex": float(fee_dec),
            "available_gtex": float(available_for_route),
            "assignment_id": assignment.id if assignment else None,
        }

    ledger_ev = ledger_events[0]
    selling_club_id = str(candidate.get("selling_club_id") or "")
    source_player_id = str(candidate.get("source_player_id") or "")
    moved_player = None
    if selling_club_id and selling_club_id != state.club_id:
        if source_player_id:
            moved_player = db.get(OwnerSquadPlayer, source_player_id)
        if moved_player is None:
            moved_player = db.scalar(
                select(OwnerSquadPlayer).where(
                    OwnerSquadPlayer.club_id == selling_club_id,
                    OwnerSquadPlayer.name == player_name,
                    OwnerSquadPlayer.status == "active",
                )
            )
        if moved_player is not None and moved_player.club_id != selling_club_id:
            moved_player = None

    if moved_player is not None:
        moved_player.club_id = state.club_id
        moved_player.status = "active"
        moved_player.acquired_via = "staff_recruitment"
        moved_player.acquired_at = _utcnow()
        moved_player.value_coin = fee_dec
        pers = dict(moved_player.personality_json or {})
        pers.update(
            {
                "weekly_wage_gtex": float(wage_dec),
                "signed_world_day": int(state.world_day or 1),
                "assignment_id": assignment.id if assignment else None,
                "ledger_event_id": ledger_ev.id,
                "previous_club_id": selling_club_id,
            }
        )
        moved_player.personality_json = pers
        flag_modified(moved_player, "personality_json")
        sq_player = moved_player
        db.flush()
    else:
        sq_player = OwnerSquadPlayer(
            id=str(uuid4()),
            club_id=state.club_id,
            player_ref=cand_id,
            name=player_name,
            position=pos,
            age=age,
            rating=gsi,
            potential=pot,
            value_coin=fee_dec,
            morale=78,
            minutes=0,
            injured_days=0,
            is_regen=False,
            acquired_via="staff_recruitment",
            personality_json={
                "weekly_wage_gtex": float(wage_dec),
                "tactical_fit": candidate.get("tactical_fit") or "first_team_target",
                "signed_world_day": int(state.world_day or 1),
                "assignment_id": assignment.id if assignment else None,
                "ledger_event_id": ledger_ev.id,
                "ledger_event_ids": [event.id for event in ledger_events],
            },
            growth_log_json=[
                {
                    "world_day": int(state.world_day or 1),
                    "event": f"Signed via staff recruitment for {int(fee_dec):,} GTX.",
                }
            ],
            status="active",
            acquired_at=_utcnow(),
        )
        db.add(sq_player)
        db.flush()

    if assignment is not None:
        assignment.gm_evaluation_status = "signed_to_first_team"
        assignment.metadata_json = {
            **a_meta,
            "execution_status": "completed",
            "executed_player_id": sq_player.id,
            "executed_candidate_id": cand_id,
            "executed_fee_gtex": float(fee_dec),
            "executed_wage_gtex": float(wage_dec),
            "ledger_event_id": ledger_ev.id,
            "ledger_event_ids": [event.id for event in ledger_events],
            "executed_world_day": int(state.world_day or 1),
        }
        flag_modified(assignment, "metadata_json")
        assignment.updated_at = _utcnow()

    if decision is not None:
        decision.execution_status = "executed"
        if decision.status in ("pending_approval", "escalated"):
            decision.status = "approved"
        decision.resolved_at = decision.resolved_at or _utcnow()
        decision.outcome_text = f"Completed signing of {player_name} ({pos}, {gsi} OVR) for {int(fee_dec):,} GTX."

    transfer_rec = living_institution.record_transfer_movement(
        db,
        state,
        direction="arrival",
        transfer_type="permanent_signing",
        player_id=sq_player.id,
        player_name=player_name,
        position=pos,
        age=age,
        overall_rating=gsi,
        fee_gtex=fee_dec,
        wage_gtex=wage_dec,
        counterparty_club_name="GTEX International Scouting Market",
        idempotency_key=f"transfer:recruit:{ref_key}:{sq_player.id}",
    )

    db.flush()
    return {
        "executed": True,
        "player_id": sq_player.id,
        "player_name": player_name,
        "position": pos,
        "overall_rating": gsi,
        "fee_gtex": float(fee_dec),
        "wage_gtex": float(wage_dec),
        "ledger_event_id": ledger_ev.id,
        "transfer_record_id": transfer_rec.id,
        "assignment_id": assignment.id if assignment else None,
        "decision_id": decision.id if decision else None,
    }


# ---------------------------------------------------------------------------
# SECTION 4: LAYER B — DYNAMIC CONVERSATIONAL INTELLIGENCE (GROUNDED IN LAYER A)
# ---------------------------------------------------------------------------


def generate_layer_b_staff_response(
    *,
    state: OwnerClubState,
    staff_name: str,
    staff_title: str,
    role_key: str,
    personality: dict[str, Any],
    intent_data: dict[str, Any],
    layer_a_result: dict[str, Any],
    conversation_turn_count: int = 1,
    prior_messages: list[str] | None = None,
) -> tuple[str, str]:
    """Generate the staff member's natural-language reply grounded strictly in Layer A's outcome."""
    outcome = str(layer_a_result["decision_outcome"])
    intent = str(layer_a_result["intent"])
    trace = dict(layer_a_result.get("reasoning_trace") or {})
    effects = dict(layer_a_result.get("state_effects") or {})
    rel_snap = dict(layer_a_result.get("relationship_snapshot") or {})

    from app.ai_gateway.legacy_bridge import staff_dialogue_should_run

    if staff_dialogue_should_run():
        llm_reply = _try_grounded_external_ai(
            staff_name=staff_name,
            staff_title=staff_title,
            personality=personality,
            intent_data=intent_data,
            layer_a_result=layer_a_result,
            conversation_turn_count=conversation_turn_count,
        )
        if llm_reply:
            return llm_reply, "external_ai_validated"
        if os.getenv("GTEX_REQUIRE_EXTERNAL_AI", "0") == "1":
            return (
                f"[{staff_name} — {staff_title}] Decision recorded ({outcome}). Conversational synthesis is pending service recovery; authoritative decision state is preserved.",
                "pending_external_ai",
            )

    comm_style = str(personality.get("communication_style") or "measured_analytical")
    archetype_label = str(personality.get("archetype_label") or staff_title)
    tactical_phil = str(personality.get("preferred_tactical_philosophy") or "balanced_control").replace("_", " ")

    if conversation_turn_count <= 1:
        if comm_style == "blunt_candid":
            opener = "I will be direct with you."
        elif comm_style == "intense_demanding":
            opener = "Let us look at the competitive reality right now."
        elif comm_style == "diplomatic_warm":
            opener = "Thank you for raising this directly with me."
        else:
            opener = "I have reviewed your request against our current squad and operational data."
    elif conversation_turn_count == 2:
        opener = (
            f"Returning to this point for a second time in our discussion (trust {rel_snap.get('trust', 68)}/100, "
            f"tension {rel_snap.get('tension', 20)}/100):"
        )
    else:
        opener = (
            f"We have now revisited this issue {conversation_turn_count} times, and my position as {staff_title} "
            f"is shaped by our ongoing governance dynamic (autonomy {rel_snap.get('autonomy', 70)}/100, tension {rel_snap.get('tension', 25)}/100):"
        )

    player_name = str(trace.get("player_name") or intent_data.get("target_player_name") or "the player")
    player_age = trace.get("player_age") if trace.get("player_age") is not None else "not filed"
    player_rating = trace.get("player_rating") if trace.get("player_rating") is not None else "not filed"
    player_potential = trace.get("player_potential") if trace.get("player_potential") is not None else "not filed"

    if outcome == "resignation_notice":
        body = (
            f"{opener} Your repeated attempts to dictate sporting decisions have crossed a line I cannot accept "
            f"(professional independence {personality.get('professional_independence') if personality.get('professional_independence') is not None else 'not filed'}/100). A First-Team Manager "
            f"must own his dressing room and team sheet. Please accept this message as my formal resignation notice "
            f"effective immediately."
        )
    elif outcome == "ultimatum":
        body = (
            f"{opener} I have to draw a firm boundary here. This is intervention #{rel_snap.get('interference_count', 3)} "
            f"into my team selection authority. I was appointed to lead the sporting side with my {tactical_phil} methodology. "
            f"If my selection authority is overridden again, my position at {state.club_name} will become untenable. "
            f"I request a formal boardroom meeting if we are to resolve our working mandate."
        )
    elif intent in ("academy_player_opportunity", "player_selection_request"):
        if role_key == "head_of_youth_development":
            body = (
                f"{opener} From the academy department's perspective, {player_name} (age {player_age}, GSI {player_rating}, "
                f"potential {player_potential}) has earned senior pathway exposure. His technical metrics in U19 training are "
                f"outstanding, and I will formally recommend his inclusion to the First-Team Manager ahead of the next fixture."
            )
        elif outcome == "accepted":
            commitment = effects.get("manager_matchday_commitment") or {}
            role_label = "starting XI" if commitment.get("matchday_role") == "starting_xi" else "matchday squad"
            body = (
                f"{opener} I share your belief in developing our academy talent (youth commitment "
                f"{personality.get('youth_development_commitment') if personality.get('youth_development_commitment') is not None else 'not filed'}/100). I have evaluated {player_name} "
                f"(age {player_age}, GSI {player_rating}, potential {player_potential}, fitness {trace.get('player_fitness') if trace.get('player_fitness') is not None else 'not filed'}%) "
                f"in training this week, and his movement in our {tactical_phil} system justifies an opportunity. "
                f"I am including {player_name} in the {role_label} for the next match."
            )
        elif outcome == "partially_accepted":
            body = (
                f"{opener} I agree that {player_name} (age {player_age}, GSI {player_rating}, potential {player_potential}) "
                f"has encouraging upside, and I am happy to give him matchday exposure. However, starting him from the first whistle "
                f"carries unnecessary physical risk against senior centre-backs. I will name {player_name} on the substitutes' bench "
                f"with a plan to bring him on in the second half when spaces open up."
            )
        else:
            if trace.get("player_injured_days", 0) > 0 or trace.get("player_fitness", 90) < 58:
                body = (
                    f"{opener} Regardless of my view on his potential, {player_name} is not physically cleared for competitive "
                    f"action right now (fitness {trace.get('player_fitness')}%, injured days {trace.get('player_injured_days')}). "
                    f"I will not risk a long-term injury by selecting him."
                )
            else:
                body = (
                    f"{opener} I understand your interest in {player_name} (age {player_age}, GSI {player_rating}), "
                    f"but I do not believe he is ready for this level of competition. My threshold for senior selection is "
                    f"{trace.get('computed_readiness_threshold', 70)} (his current readiness index is {trace.get('player_effective_readiness', 64)}). "
                    f"He still needs to develop physically and improve his decision-making out of possession. "
                    f"I prefer to rely on our experienced senior options and continue his development in the academy before exposing him to first-team football."
                )
    elif intent == "drop_or_discipline_player":
        if outcome == "accepted":
            body = (
                f"{opener} Dressing-room discipline is non-negotiable for me (discipline standard "
                f"{personality.get('player_discipline_philosophy', 80)}/100). I have observed the same drop in focus from "
                f"{player_name}, and I have excluded him from the next matchday selection."
            )
        elif outcome == "counterproposal":
            body = (
                f"{opener} I note your concern regarding {player_name}'s attitude, but publicly dropping him before I have "
                f"conducted a private 1-on-1 review risks fracturing squad morale. My counterproposal is to issue a formal internal "
                f"warning today and assess his training intensity over the next 48 hours before finalizing my XI."
            )
        else:
            body = (
                f"{opener} Team selection and player discipline inside the dressing room fall under my remit as {staff_title}. "
                f"I cannot allow external directives to dictate who I drop when {player_name} remains tactically important to our setup. "
                f"I am recording a formal disagreement on this request."
            )
    elif intent in ("tactical_style_shift", "formation_request", "club_culture_direction"):
        req_style = str(trace.get("requested_style") or "not filed")
        if outcome == "deferred":
            body = f"{opener} {trace.get('verdict_reason') or 'The shape sits with the first-team manager.'}"
        elif outcome == "accepted":
            body = (
                f"{opener} Moving further toward {req_style} football aligns naturally with my {tactical_phil} identity "
                f"and preferred formations ({', '.join(personality.get('preferred_formations') or []) or 'not filed'}). "
                f"We are accelerating that transition on the training pitch immediately."
            )
        elif outcome == "conditional_acceptance":
            body = (
                f"{opener} I am open to evolving our identity toward {req_style} football, and my tactical flexibility "
                f"({personality.get('tactical_flexibility') if personality.get('tactical_flexibility') is not None else 'not filed'}/100) allows us to adapt. However, a stylistic shift cannot happen "
                f"overnight without exposing the squad. I will phase this transition across our microcycles provided recruitment "
                f"supports the profile we need."
            )
        else:
            body = (
                f"{opener} You hired me knowing my footballing identity is built on {tactical_phil} "
                f"(attacking/defensive index {personality.get('attacking_vs_defensive') if personality.get('attacking_vs_defensive') is not None else 'not filed'}/100). Asking me to abandon my core "
                f"principles for {req_style} football overnight is neither realistic nor suited to our current squad. "
                f"If you want to debate a fundamental change in club playing culture, we should convene a formal boardroom meeting."
            )
    elif intent == "transfer_recruitment_target":
        pos = str(trace.get("target_position") or "not filed")
        min_gsi = trace.get("min_gsi") if trace.get("min_gsi") is not None else "not filed"
        max_gsi = trace.get("max_gsi") if trace.get("max_gsi") is not None else "not filed"
        shortlist = list(effects.get("candidate_shortlist") or [])
        rec = dict(effects.get("recommended_candidate") or {})
        if outcome == "deferred" or effects.get("scout_shortlist") or effects.get("youth_recruitment_note"):
            body = f"{opener} {trace.get('verdict_reason') or 'That request sits with the general manager.'}"
        elif outcome == "counterproposal":
            fee_text = (
                f"{float(rec.get('estimated_fee')):,.0f} GTX already filed on the player record"
                if rec.get("estimated_fee") is not None
                else "no fee is filed"
            )
            body = (
                f"{opener} I have evaluated your request for a {pos} signing against our liquid treasury "
                f"({trace.get('treasury_balance', 0):,.0f} GTX). "
                f"My financial discipline is {personality.get('financial_discipline') if personality.get('financial_discipline') is not None else 'not filed'}/100. "
                f"I counterpropose {rec.get('player_name') or 'no filed alternative'} "
                f"(age {rec.get('age') if rec.get('age') is not None else 'not filed'}, "
                f"GSI {rec.get('gsi') if rec.get('gsi') is not None else 'not filed'}, "
                f"potential {rec.get('potential') if rec.get('potential') is not None else 'not filed'}) at {fee_text}."
            )
        elif outcome == "declined":
            body = (
                f"{opener} I cannot sanction this recruitment outlay for a {pos} right now. "
                f"Treasury on the day is {trace.get('treasury_balance', 0):,.0f} GTX. "
                f"The fee is the value already filed on the player, and it is not covered."
            )
        else:
            names_str = ", ".join(
                f"{c['player_name']} (GSI {c['gsi']}, {c['estimated_fee']:,.0f} GTX)" for c in shortlist[:3]
            )
            body = (
                f"{opener} I have coordinated with our Chief Scout and First-Team Manager on the {pos} requirement "
                f"(GSI {min_gsi}–{max_gsi}). Against our treasury of {trace.get('treasury_balance', 0):,.0f} GTX, we have shortlisted: "
                f"{names_str}. My primary recommendation is {rec.get('player_name', 'our top target')} "
                f"(est. fee {rec.get('estimated_fee', 0):,.0f} GTX, wage {rec.get('weekly_wage_demand', 0):,.0f} GTX/wk). "
                f"The proposal is ready for your executive review."
            )
    elif intent == "recruitment_spending_critique":
        if outcome == "deferred":
            body = f"{opener} {trace.get('verdict_reason') or 'The general manager holds the wage book.'}"
        elif outcome == "accepted":
            body = (
                f"{opener} We are completely aligned on capital efficiency. With a financial discipline index of "
                f"{personality.get('financial_discipline') if personality.get('financial_discipline') is not None else 'not filed'}/100, I am enforcing strict fee-to-GSI ceilings and rejecting "
                f"agent premiums that distort our {personality.get('wage_structure_philosophy', 'tiered')} wage structure."
            )
        else:
            body = (
                f"{opener} I have to push back on that assessment. Competing for honours requires calculated market ambition "
                f"(transfer risk tolerance {personality.get('transfer_risk_tolerance', 82)}/100). Cutting recruitment spend now "
                f"will leave the First-Team Manager short of elite quality in decisive fixtures."
            )
    elif intent == "medical_clearance_pressure":
        if outcome == "deferred":
            body = f"{opener} {trace.get('verdict_reason') or 'The medical director holds return-to-play.'}"
        else:
            body = (
                f"{opener} As Medical Director (protocol strictness {trace.get('medical_protocol_strictness', personality.get('protocol_strictness', '—'))}/100), "
                f"my clinical duty is to protect the club's playing assets from catastrophic soft-tissue relapse. "
                f"I will not sign off on premature matchday clearance when biometric load markers remain in the red zone."
            )
    elif intent == "challenge_or_override_decision":
        body = (
            f"{opener} You have made your displeasure clear, and as owner you always hold the right to dismiss me. "
            f"However, while I hold the role of {staff_title} ({archetype_label}), I will not rubber-stamp decisions "
            f"that contradict the footballing evidence in front of me. I have logged a formal disagreement in our record."
        )
    else:
        specialist_domain = personality.get("specialist_domain")
        domain_clause = (
            f"specialist focus on {str(specialist_domain).replace('_', ' ')}"
            if specialist_domain
            else f"{tactical_phil} framework"
        )
        body = (
            f"{opener} Speaking as your {staff_title} ({archetype_label}), our work remains anchored in our "
            f"{domain_clause} at {state.club_name} (World Day {int(state.world_day or 1)}). "
            f"Current relationship trust stands at {rel_snap.get('trust', 68)}/100 with operational alignment at "
            f"{rel_snap.get('alignment', 70)}/100."
        )

    return body, "grounded_deterministic"


def _try_grounded_external_ai(
    *,
    staff_name: str,
    staff_title: str,
    personality: dict[str, Any],
    intent_data: dict[str, Any],
    layer_a_result: dict[str, Any],
    conversation_turn_count: int,
) -> str | None:
    """Ask the central AI gateway for wording. Layer A remains the decision."""
    prompt_payload = {
        "staff_name": staff_name,
        "staff_title": staff_title,
        "communication_style": personality.get("communication_style"),
        "archetype": personality.get("archetype_label"),
        "owner_message": str(intent_data.get("raw_text") or "")[:500],
        "authoritative_decision_outcome": layer_a_result.get("decision_outcome"),
        "intent": layer_a_result.get("intent"),
        "reasoning_trace": _compact_staff_context(layer_a_result.get("reasoning_trace")),
        "state_effects": _compact_staff_context(layer_a_result.get("state_effects")),
        "turn": conversation_turn_count,
    }
    try:
        from app.ai_gateway.service import GtexAiService

        result = GtexAiService().generate_text(
            feature="staff_dialogue",
            user_content=json.dumps(prompt_payload, default=str),
            facts={"decision_outcome": layer_a_result.get("decision_outcome"), "intent": layer_a_result.get("intent")},
            extra_instructions=(
                "Write the staff member's reply in 2-4 sentences. "
                "Adhere to authoritative_decision_outcome. Do not invent players, fees, or agreements."
            ),
            max_output_tokens=220,
            temperature=0.4,
        )
    except Exception:
        return None
    if result.ok and result.text and len(result.text.strip()) >= 20:
        return result.text.strip()
    return None


def _compact_staff_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact: dict[str, Any] = {}
    for key, item in list(value.items())[:12]:
        if isinstance(item, (int, float, bool)) or item is None:
            compact[str(key)[:40]] = item
        elif isinstance(item, str):
            compact[str(key)[:40]] = item[:180]
    return compact


# ---------------------------------------------------------------------------
# SECTION 6 & 13: PROACTIVE STAFF-INITIATED CONVERSATIONS & INTER-STAFF ROOM
# ---------------------------------------------------------------------------


def generate_proactive_staff_initiatives(
    db: Session,
    state: OwnerClubState,
    *,
    owner_user_id: str,
    trigger_reason: str = "world_tick",
) -> list[dict[str, Any]]:
    """Evaluate real squad depth, academy readiness, injury load, budget, and tension
    so staff proactively initiate conversations and inter-staff recruitment workflows
    with deduplication and cooldowns.
    """
    identities = ensure_club_staff_identities(db, state)
    mgr = identities["first_team_manager"]
    mgr_profile = mgr["personality_profile"]
    gm = identities["general_manager"]
    hoyd = identities["head_of_youth_development"]
    med = identities["medical_director"]
    assistants = identities["assistant_coaches"]

    players = list(db.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    fac = dict(state.facilities_json or {})
    cooldowns = dict(fac.get("_proactive_comms_cooldowns") or {})
    world_day = int(state.world_day or 1)
    generated: list[dict[str, Any]] = []

    def _can_fire(key: str, min_days: int = 3) -> bool:
        last_day = cooldowns.get(key)
        if last_day is not None and (world_day - int(last_day)) < min_days and trigger_reason != "manual_audit":
            return False
        cooldowns[key] = world_day
        return True

    lw_players = [p for p in players if str(p.position or "").upper() in ("LW", "LM")]
    cb_players = [
        p for p in players if str(p.position or "").upper() in ("CB", "DEFENDER") and int(p.injured_days or 0) == 0
    ]

    open_lw_assignment = db.scalar(
        select(OwnerRecruitmentAssignment).where(
            OwnerRecruitmentAssignment.club_id == state.club_id,
            OwnerRecruitmentAssignment.target_position == "LW",
            OwnerRecruitmentAssignment.gm_evaluation_status.notin_(
                ("completed", "signed_to_first_team", "rejected_by_owner", "failed_insufficient_funds")
            ),
        )
    )
    mgr_name = str(mgr.get("name") or "").strip()
    mgr_seated = bool(
        mgr_name
        and not mgr.get("is_vacant")
        and not mgr.get("is_default")
        and mgr.get("manager_id") != "gtex-staff-coach"
        and "vacant" not in mgr_name.lower()
    )
    if (
        mgr_seated
        and not lw_players
        and open_lw_assignment is None
        and _can_fire("mgr_lw_recruitment_request", min_days=7)
    ):
        generated.append(
            {
                "sender_role": "first_team_manager",
                "sender_id": str(mgr.get("id") or "mgr"),
                "sender_name": mgr_name,
                "sender_title": "First-Team Manager",
                "topic": "Squad Depth: Left Wing",
                "priority": "normal",
                "event_key": f"proactive:mgr_lw_gap:w{(world_day - 1) // 7 + 1}",
                "body": (
                    f"No left winger is filed on the squad ({len(lw_players)} available). "
                    "I have not set a rating band or a fee."
                ),
                "action_payload": {"type": "squad_depth_warning", "position": "LW", "available_count": len(lw_players)},
            }
        )

    if len(cb_players) < 3 and _can_fire("mgr_cb_depth_concern", min_days=14):
        generated.append(
            {
                "sender_role": "first_team_manager",
                "sender_id": str(mgr.get("id") or "mgr"),
                "sender_name": str(mgr["name"]),
                "sender_title": "First-Team Manager",
                "topic": "Squad Depth Warning: Centre-Back Cover",
                "priority": "normal",
                "event_key": f"proactive:mgr_cb_depth:w{(world_day - 1) // 14 + 1}",
                "body": (
                    f"I am concerned about our defensive depth. We currently have only {len(cb_players)} healthy natural centre-backs available, "
                    f"and our {(list(mgr_profile.get('preferred_formations') or []) or ['not filed'])[0]} structure leaves us exposed if injuries or suspensions hit."
                ),
                "action_payload": {"type": "squad_depth_warning", "position": "CB", "available_count": len(cb_players)},
            }
        )

    academy_prospects = [
        p for p in players if _player_is_academy(p) and p.potential is not None and int(p.potential) >= 82
    ]
    if academy_prospects and _can_fire("hoyd_academy_promotion", min_days=14):
        top_prospect = sorted(academy_prospects, key=lambda p: -int(p.potential or 0))[0]
        rating_band = (int(top_prospect.rating or 0) // 5) * 5
        generated.append(
            {
                "sender_role": "head_of_youth_development",
                "sender_id": str(hoyd.get("id") or "hoyd"),
                "sender_name": str(hoyd["name"]),
                "sender_title": "Head of Youth Development",
                "topic": f"Academy Pathway Recommendation: {top_prospect.name} ({top_prospect.position})",
                "priority": "normal",
                "event_key": f"proactive:hoyd_prospect:{top_prospect.id}:band_{rating_band}",
                "body": (
                    f"I have been monitoring {top_prospect.name} (age {top_prospect.age}, {top_prospect.position}, GSI {top_prospect.rating}, "
                    f"potential {top_prospect.potential}). His technical development in academy fixtures has plateaued because he needs senior speed of play. "
                    f"I recommend integrating him into first-team training and matchday consideration."
                ),
                "action_payload": {
                    "type": "academy_promotion_recommendation",
                    "player_id": top_prospect.id,
                    "player_name": top_prospect.name,
                    "position": top_prospect.position,
                    "age": top_prospect.age,
                    "gsi": top_prospect.rating,
                    "potential": top_prospect.potential,
                },
            }
        )

    injured_or_fatigued = [
        p
        for p in players
        if int(p.injured_days or 0) > 0 or (_player_fitness(p) is not None and _player_fitness(p) < 72)
    ]
    if injured_or_fatigued and _can_fire("med_load_warning", min_days=7):
        names_list = ", ".join(p.name for p in injured_or_fatigued[:3])
        generated.append(
            {
                "sender_role": "medical_director",
                "sender_id": str(med.get("id") or "med"),
                "sender_name": str(med["name"]),
                "sender_title": "Medical Director",
                "topic": "Biometric Load & Injury Prevention Alert",
                "priority": "high" if len(injured_or_fatigued) >= 3 else "normal",
                "event_key": f"proactive:med_load:w{(world_day - 1) // 7 + 1}",
                "body": (
                    f"Our sports-science screening flagged elevated soft-tissue risk across {len(injured_or_fatigued)} squad members "
                    f"({names_list}). I have advised {mgr['name']} to rotate high-minute starters in the upcoming microcycle."
                ),
                "action_payload": {
                    "type": "medical_load_warning",
                    "affected_count": len(injured_or_fatigued),
                    "affected_players": [p.name for p in injured_or_fatigued[:4]],
                },
            }
        )

    if assistants and _can_fire("assistant_specialist_brief", min_days=14):
        def_coach = next((a for a in assistants if a.get("specialist_role") == "defensive_organisation"), assistants[0])
        generated.append(
            {
                "sender_role": "assistant_coach",
                "sender_id": str(def_coach.get("id") or "ac_def"),
                "sender_name": str(def_coach["name"]),
                "sender_title": str(def_coach["title"]),
                "topic": "Coaching Staff Specialist Note: Rest-Defence & Transition Spacing",
                "priority": "normal",
                "event_key": f"proactive:ac_def_note:w{(world_day - 1) // 14 + 1}",
                "body": (
                    f"In my video review with {mgr['name']}, I highlighted spacing between our pivot and centre-backs during high-pressing transitions. "
                    f"We are dedicating two tactical drills this week to rest-defence compactness."
                ),
                "action_payload": {
                    "type": "assistant_specialist_report",
                    "specialist_role": def_coach.get("specialist_role"),
                },
            }
        )

    # Institutional External Intelligence: Supporter Sentiment, Protest Escalation & Media Scrutiny
    from app.owner_console import living_institution
    from app.owner_console.institutional_models import OwnerMediaStory

    sup_profile, _ = living_institution.ensure_club_institutional_ecosystem(db, state)
    recent_stories = list(
        db.scalars(
            select(OwnerMediaStory)
            .where(OwnerMediaStory.club_id == state.club_id)
            .order_by(OwnerMediaStory.world_day.desc(), OwnerMediaStory.created_at.desc())
            .limit(5)
        ).all()
    )
    protest_stage = str(sup_profile.active_protest_stage or "none")
    overall_sent = int(sup_profile.overall_sentiment) if sup_profile.overall_sentiment is not None else None
    att_mod = int(sup_profile.attendance_modifier_pct or 0)
    ticket_tier = str(sup_profile.ticket_price_tier or "standard")

    if (
        protest_stage in ("petition", "banner_protest", "organised_boycott")
        or (ticket_tier in ("premium", "exploitative") and overall_sent is not None and overall_sent < 60)
        or att_mod <= -8
    ) and _can_fire("gm_supporter_commercial_alert", min_days=7):
        generated.append(
            {
                "sender_role": "general_manager",
                "sender_id": str(gm.get("id") or "gm"),
                "sender_name": str(gm["name"]),
                "sender_title": "General Manager",
                "topic": f"Supporter & Matchday Revenue Alert ({protest_stage.replace('_', ' ').title()})",
                "priority": "high" if protest_stage in ("banner_protest", "organised_boycott") else "normal",
                "event_key": f"proactive:gm_supporter_alert:{protest_stage}:w{(world_day - 1) // 7 + 1}",
                "body": (
                    f"From a commercial and governance perspective, our supporter sentiment sits at {overall_sent if overall_sent is not None else 'not filed'}/100 "
                    f"with active protest stage '{protest_stage.replace('_', ' ')}' under '{ticket_tier}' ticket pricing. "
                    f"Matchday attendance projection is shifted by {att_mod:+d}%. I advise scheduling a boardroom "
                    f"supporter-confidence review or easing matchday ticketing tiers immediately."
                ),
                "action_payload": {
                    "type": "supporter_commercial_intelligence",
                    "protest_stage": protest_stage,
                    "overall_sentiment": overall_sent,
                    "ticket_price_tier": ticket_tier,
                    "attendance_modifier_pct": att_mod,
                },
            }
        )

    high_media_pressure = any(int(st.leadership_pressure_delta or 0) >= 3 for st in recent_stories)
    if (
        (sup_profile.confidence_in_manager is not None and int(sup_profile.confidence_in_manager) <= 55)
        or protest_stage in ("banner_protest", "organised_boycott")
        or high_media_pressure
    ) and _can_fire("mgr_public_pressure_brief", min_days=7):
        headline_ref = recent_stories[0].headline if recent_stories else "recent public scrutiny"
        generated.append(
            {
                "sender_role": "first_team_manager",
                "sender_id": str(mgr.get("id") or "mgr"),
                "sender_name": str(mgr["name"]),
                "sender_title": "First-Team Manager",
                "topic": "Dressing-Room Focus Amid Media & Terrace Pressure",
                "priority": "high",
                "event_key": f"proactive:mgr_pressure_brief:{protest_stage}:w{(world_day - 1) // 7 + 1}",
                "body": (
                    f"The dressing room is aware of external noise surrounding '{headline_ref[:90]}' "
                    f"(supporter confidence in dugout: {sup_profile.confidence_in_manager}/100). "
                    f"We are tightening tactical organisation on the training pitch to win results back and steady terrace backing."
                ),
                "action_payload": {
                    "type": "manager_pressure_intelligence",
                    "confidence_in_manager": int(sup_profile.confidence_in_manager),
                    "protest_stage": protest_stage,
                },
            }
        )

    if (
        int(sup_profile.accumulated_frustration or 0) >= 20 or int(fac.get("_manager_youth_rejection_streak") or 0) >= 1
    ) and _can_fire("hoyd_supporter_youth_brief", min_days=10):
        generated.append(
            {
                "sender_role": "head_of_youth_development",
                "sender_id": str(hoyd.get("id") or "hoyd"),
                "sender_name": str(hoyd["name"]),
                "sender_title": "Head of Youth Development",
                "topic": "Supporter Appetite for Homegrown Pathway Visibility",
                "priority": "normal",
                "event_key": f"proactive:hoyd_youth_sentiment:w{(world_day - 1) // 10 + 1}",
                "body": (
                    f"Community and regular matchgoing segments closely track our homegrown pathway. "
                    f"With accumulated supporter frustration at {sup_profile.accumulated_frustration}/100, "
                    f"giving academy graduates controlled cup or substitute minutes would demonstrate authentic club identity."
                ),
                "action_payload": {
                    "type": "hoyd_youth_sentiment_brief",
                    "accumulated_frustration": int(sup_profile.accumulated_frustration),
                },
            }
        )

    fac["_proactive_comms_cooldowns"] = cooldowns
    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    db.flush()
    return generated


# ---------------------------------------------------------------------------
# SECTION 8: INTERACTIVE BOARDROOM NEGOTIATION ENGINE
# ---------------------------------------------------------------------------


def simulate_boardroom_meeting_negotiation(
    db: Session,
    state: OwnerClubState,
    *,
    title: str,
    agenda: str,
    meeting_type: str,
    requested_attendees: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a realistic, multi-participant boardroom negotiation where participants
    contribute according to their independent personalities, surface genuine disagreements
    (Manager vs GM, HOYD vs Manager, Chief Scout vs Manager), and table actionable resolutions.
    """
    identities = ensure_club_staff_identities(db, state)
    mgr = identities["first_team_manager"]
    mgr_profile = mgr["personality_profile"]
    gm = identities["general_manager"]
    gm_profile = gm["personality_profile"]
    hoyd = identities["head_of_youth_development"]
    scout = identities["chief_scout"]
    med = identities["medical_director"]
    culture = identities["club_culture"]

    from app.owner_console import living_institution

    sup_profile, _ = living_institution.ensure_club_institutional_ecosystem(db, state)
    protest_stage = str(sup_profile.active_protest_stage or "none")
    overall_sent = int(sup_profile.overall_sentiment) if sup_profile.overall_sentiment is not None else None
    ticket_tier = str(sup_profile.ticket_price_tier or "standard")
    att_mod = int(sup_profile.attendance_modifier_pct or 0)
    agenda_lower = f"{title} {agenda} {meeting_type}".lower()
    has_supporter_pressure = (
        protest_stage in ("petition", "banner_protest", "organised_boycott")
        or (ticket_tier in ("premium", "exploitative") and overall_sent is not None and overall_sent < 58)
        or any(k in agenda_lower for k in ("supporter", "protest", "ticket", "boycott", "public_trust"))
    )

    players = list(db.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    academy_striker = next((p for p in players if _player_is_academy(p)), players[0] if players else None)
    prospect_name = academy_striker.name if academy_striker else "an academy player"
    treasury = _club_treasury_gtex(db, state)

    contributions: list[dict[str, Any]] = [
        {
            "speaker_role": "first_team_manager",
            "speaker_id": str(mgr.get("id") or "mgr"),
            "speaker_name": str(mgr["name"]),
            "speaker_title": "First-Team Manager",
            "archetype": mgr_profile.get("archetype_label"),
            "stance": (
                "pro_youth_and_tactical_identity"
                if isinstance(mgr_profile.get("youth_development_commitment"), (int, float))
                and int(mgr_profile.get("youth_development_commitment")) >= 70
                else (
                    "win_now_senior_experience"
                    if isinstance(mgr_profile.get("preference_for_experienced_players"), (int, float))
                    else "profile_not_filed"
                )
            ),
            "statement": (
                f"From the touchline, my priority is executing our {(mgr_profile.get('preferred_tactical_philosophy') or 'not filed').replace('_', ' ')} "
                f"system ({', '.join(mgr_profile.get('preferred_formations') or []) or 'not filed'}). "
                + (
                    f"I am prepared to give academy talents like {prospect_name} structured minutes."
                    if isinstance(mgr_profile.get("youth_development_commitment"), (int, float))
                    and int(mgr_profile.get("youth_development_commitment")) >= 65
                    else (
                        f"Results come first; experience preference is {int(mgr_profile.get('preference_for_experienced_players'))}/100."
                        if isinstance(mgr_profile.get("preference_for_experienced_players"), (int, float))
                        else "Recruitment stays with players already filed on a squad."
                    )
                )
                + (
                    f" We also hear terrace frustration (manager confidence {int(sup_profile.confidence_in_manager) if sup_profile.confidence_in_manager is not None else 'not filed'}/100) and must respond on the pitch."
                    if has_supporter_pressure
                    else ""
                )
            ),
        },
        {
            "speaker_role": "general_manager",
            "speaker_id": str(gm.get("id") or "gm"),
            "speaker_name": str(gm["name"]),
            "speaker_title": "General Manager",
            "archetype": gm_profile.get("archetype_label"),
            "stance": (
                "strict_budget_and_resale_value"
                if isinstance(gm_profile.get("financial_discipline"), (int, float))
                and int(gm_profile.get("financial_discipline")) >= 70
                else (
                    "aggressive_market_ambition"
                    if isinstance(gm_profile.get("financial_discipline"), (int, float))
                    else "budget_not_filed"
                )
            ),
            "statement": (
                f"Looking at our liquid treasury of {treasury:,.0f} GTX and our {(gm_profile.get('wage_structure_philosophy') or 'not filed').replace('_', ' ')} wage model "
                + (
                    f"(financial discipline {int(gm_profile.get('financial_discipline'))}/100): "
                    if isinstance(gm_profile.get("financial_discipline"), (int, float))
                    else "(financial discipline not filed): "
                )
                + (
                    "I cannot rubber-stamp overpriced veteran signings that carry zero resale value. Any recruitment must stay within sustainable fee bands or target U23 profiles."
                    if isinstance(gm_profile.get("financial_discipline"), (int, float))
                    and int(gm_profile.get("financial_discipline")) >= 70
                    else (
                        "we have a window to push for silverware, and I believe we should back ambitious marquee targets even if it stretches our wage ceiling."
                        if isinstance(gm_profile.get("financial_discipline"), (int, float))
                        else "I will not set a wage band until a financial-discipline score is filed."
                    )
                )
                + (
                    f" Crucially, supporter sentiment is {overall_sent if overall_sent is not None else 'not filed'}/100 under '{ticket_tier}' ticketing ({protest_stage}), impacting matchday gate projections by {att_mod:+d}%."
                    if has_supporter_pressure
                    else ""
                )
            ),
        },
        {
            "speaker_role": "head_of_youth_development",
            "speaker_id": str(hoyd.get("id") or "hoyd"),
            "speaker_name": str(hoyd["name"]),
            "speaker_title": "Head of Youth Development",
            "archetype": (hoyd.get("personality_profile") or {}).get("archetype_label") or "Not filed",
            "stance": "protect_academy_pathway",
            "statement": (
                f"If we spend heavily on external squad fillers without guaranteeing a pathway for {prospect_name}, "
                f"our academy investment loses credibility. We need a clear commitment on U19-to-first-team minutes."
            ),
        },
        {
            "speaker_role": "chief_scout",
            "speaker_id": str(scout.get("id") or "scout"),
            "speaker_name": str(scout["name"]),
            "speaker_title": "Chief Scout",
            "archetype": (scout.get("personality_profile") or {}).get("archetype_label") or "Not filed",
            "stance": "data_driven_shortlist",
            "statement": (
                f"{scout.get('name')} will only name players already filed on a squad. "
                "If the board names a position and a rating band, that is the shortlist."
            ),
        },
        {
            "speaker_role": "medical_director",
            "speaker_id": str(med.get("id") or "med"),
            "speaker_name": str(med["name"]),
            "speaker_title": "Medical Director",
            "archetype": (med.get("personality_profile") or {}).get("archetype_label") or "Not filed",
            "stance": "biometric_load_protection",
            "statement": (
                "Whatever squad size we settle on, fixture congestion requires rotation. I will not clear fatigued starters "
                "for three 90-minute appearances in seven days."
            ),
        },
    ]
    seats = {
        "first_team_manager": mgr,
        "general_manager": gm,
        "head_of_youth_development": hoyd,
        "chief_scout": scout,
        "medical_director": med,
    }

    def _seat_speaks(person: dict[str, Any] | None) -> bool:
        if not isinstance(person, dict):
            return False
        name = str(person.get("name") or "").strip()
        return bool(
            name
            and not person.get("is_vacant")
            and not person.get("is_default")
            and person.get("manager_id") != "gtex-staff-coach"
            and "vacant" not in name.lower()
        )

    contributions = [item for item in contributions if _seat_speaks(seats.get(item["speaker_role"]))]

    disagreements: list[dict[str, Any]] = []
    veteran_pref = _optional_score(mgr_profile, "preference_for_experienced_players")
    gm_discipline = _optional_score(gm_profile, "financial_discipline")
    if veteran_pref is not None and veteran_pref >= 65 and gm_discipline is not None and gm_discipline >= 70:
        disagreements.append(
            {
                "axis": "Manager vs General Manager",
                "parties": [str(mgr["name"]), str(gm["name"])],
                "roles": ["first_team_manager", "general_manager"],
                "topic": "Senior Starters vs Wage & Resale Discipline",
                "summary": (
                    f"{mgr['name']} wants battle-tested senior signings for immediate results, while {gm['name']} "
                    f"insists on strict wage caps and younger resale assets."
                ),
            }
        )
    else:
        disagreements.append(
            {
                "axis": "Manager vs General Manager",
                "parties": [str(mgr["name"]), str(gm["name"])],
                "roles": ["first_team_manager", "general_manager"],
                "topic": "Transfer Fee Allocation vs Treasury Buffer",
                "summary": (
                    f"{mgr['name']} prioritises immediate tactical fit in the 80–85 GSI band, whereas {gm['name']} "
                    f"wants staggered add-ons to protect liquid reserves ({treasury:,.0f} GTX)."
                ),
            }
        )

    disagreements.append(
        {
            "axis": "Head of Youth Development vs First-Team Manager",
            "parties": [str(hoyd["name"]), str(mgr["name"])],
            "roles": ["head_of_youth_development", "first_team_manager"],
            "topic": f"First-Team Pathway for {prospect_name}",
            "summary": (
                f"{hoyd['name']} argues {prospect_name} is ready for guaranteed senior pathway minutes now, while {mgr['name']} "
                f"insists matchday selection must remain strictly subject to tactical and physical readiness."
            ),
        }
    )

    disagreements.append(
        {
            "axis": "Chief Scout vs First-Team Manager",
            "parties": [str(scout["name"]), str(mgr["name"])],
            "roles": ["chief_scout", "first_team_manager"],
            "topic": "Analytics Value Target vs Immediate Peak GSI",
            "summary": (
                f"{scout['name']} backs a 20-year-old high-upside profile based on underlying metrics, while {mgr['name']} "
                f"weighs immediate tactical execution for the next fixture block."
            ),
        }
    )

    proposed_resolutions: list[dict[str, Any]] = [
        {
            "resolution_id": "back_manager_sporting_plan",
            "title": f"Back {mgr['name']}'s Immediate Sporting Plan",
            "description": (
                "Authorise the filed recruitment target and reaffirm the First-Team Manager's full selection autonomy."
            ),
            "effects": {
                "manager_trust_delta": 6,
                "manager_autonomy_delta": 5,
                "gm_tension_delta": (
                    5 if gm_discipline is not None and gm_discipline >= 75 else (-2 if gm_discipline is not None else 0)
                ),
                "culture_shift": mgr_profile.get("preferred_tactical_philosophy"),
            },
        },
        {
            "resolution_id": "enforce_gm_sustainable_value",
            "title": f"Adopt {gm['name']}'s Sustainable Value & Youth Cap",
            "description": (
                f"Cap recruitment fees at sustainable analytics valuations and mandate a structured bench pathway for {prospect_name}."
            ),
            "effects": {
                "manager_trust_delta": (
                    -4 if veteran_pref is not None and veteran_pref >= 65 else (3 if veteran_pref is not None else 0)
                ),
                "manager_tension_delta": (
                    7
                    if _optional_score(mgr_profile, "professional_independence") is not None
                    and _optional_score(mgr_profile, "professional_independence") >= 75
                    else (2 if _optional_score(mgr_profile, "professional_independence") is not None else 0)
                ),
                "gm_trust_delta": 6,
                "hoyd_trust_delta": 6,
                "culture_shift": "youth_development",
            },
        },
        {
            "resolution_id": "balanced_boardroom_compromise",
            "title": "Ratify Conditional Compromise (Performance Clauses + Cup/Sub Pathway)",
            "description": (
                f"Pursue the 80–85 GSI target with incentive-based wage clauses while scheduling {prospect_name} for controlled substitute appearances."
            ),
            "effects": {
                "manager_trust_delta": 3,
                "gm_trust_delta": 4,
                "hoyd_trust_delta": 4,
                "manager_tension_delta": -2,
                "culture_shift": culture.get("primary_identity", "positional_play"),
            },
        },
    ]

    if has_supporter_pressure:
        disagreements.append(
            {
                "axis": "Supporters & Commercial Health vs Executive Pricing",
                "parties": [str(gm["name"]), "Supporters Trust Liaison"],
                "roles": ["general_manager", "supporter_liaison"],
                "topic": f"Active Protest Stage ({protest_stage}) & Matchday Access",
                "summary": (
                    f"Supporter sentiment sits at {overall_sent}/100 under '{ticket_tier}' tickets ({att_mod:+d}% attendance shift); "
                    f"executives debate ticket concessions versus preserving short-term gate pricing."
                ),
            }
        )
        proposed_resolutions.append(
            {
                "resolution_id": "supporter_trust_and_pricing_reset",
                "title": "Execute Supporter Trust & Affordable Ticketing Reset",
                "description": (
                    f"Reset matchday ticketing to 'standard' (or 'affordable') and issue a formal boardroom supporter "
                    f"engagement pact to cool '{protest_stage.replace('_', ' ')}' protests."
                ),
                "effects": {
                    "manager_trust_delta": 2,
                    "gm_trust_delta": 3,
                    "hoyd_trust_delta": 4,
                    "manager_tension_delta": -3,
                    "public_supporter_reset": True,
                    "target_ticket_tier": "affordable" if ticket_tier == "standard" else "standard",
                },
            }
        )

    disagreements = [
        item
        for item in disagreements
        if all(_seat_speaks(seats.get(role)) for role in item.get("roles") or [] if role in seats)
    ]
    minutes_lines = [
        f"Boardroom Session: {title} ({meeting_type.replace('_', ' ')})",
        f"Agenda: {agenda or 'Sporting direction, recruitment budget, and academy pathway alignment.'}",
        "Participant Positions:",
        *[f"- {c['speaker_name']} ({c['speaker_title']}): {c['statement']}" for c in contributions],
        "Recorded Inter-Staff Disagreements:",
        *[f"- {' vs '.join(d['parties'])} [{d['topic']}]: {d['summary']}" for d in disagreements],
        "Status: Open for Owner Executive Resolution or Compromise Ratification.",
    ]

    return {
        "contributions": contributions,
        "disagreements": disagreements,
        "proposed_resolutions": proposed_resolutions,
        "minutes_summary": "\n".join(minutes_lines),
        "attendees": [
            {"role": c["speaker_role"], "name": c["speaker_name"], "title": c["speaker_title"]} for c in contributions
        ],
    }


def resolve_boardroom_meeting_decision(
    db: Session,
    state: OwnerClubState,
    meeting: OwnerClubMeeting,
    *,
    resolution_id: str,
    owner_note: str = "",
) -> dict[str, Any]:
    """Apply the owner's executive decision on a boardroom meeting while preserving
    each staff member's independent perspective and updating relationships & directives.
    """
    identities = ensure_club_staff_identities(db, state)
    meta = dict(meeting.metadata_json or {})
    resolutions = list(meta.get("proposed_resolutions") or [])
    chosen = next((r for r in resolutions if r.get("resolution_id") == resolution_id), None)
    if chosen is None:
        chosen = (
            resolutions[0]
            if resolutions
            else {
                "resolution_id": resolution_id or "executive_directive",
                "title": "Owner Executive Decision",
                "description": owner_note or "Executive board resolution recorded.",
                "effects": {"manager_trust_delta": 2, "gm_trust_delta": 2},
            }
        )

    effects = dict(chosen.get("effects") or {})
    mgr = identities["first_team_manager"]
    gm = identities["general_manager"]

    mgr_rel = ensure_staff_relationship(
        db,
        state,
        role_key="first_team_manager",
        staff_id=str(mgr.get("id") or "mgr"),
        staff_name=str(mgr["name"]),
        staff_title="First-Team Manager",
        personality_profile=mgr["personality_profile"],
    )
    gm_rel = ensure_staff_relationship(
        db,
        state,
        role_key="general_manager",
        staff_id=str(gm.get("id") or "gm"),
        staff_name=str(gm["name"]),
        staff_title="General Manager",
        personality_profile=gm["personality_profile"],
    )

    mgr_rel.trust = _clamp(mgr_rel.trust + int(effects.get("manager_trust_delta", 0)))
    mgr_rel.tension = _clamp(mgr_rel.tension + int(effects.get("manager_tension_delta", 0)))
    mgr_meta = dict(mgr_rel.metadata_json or {})
    mgr_meta["autonomy"] = _clamp(int(mgr_meta.get("autonomy", 75)) + int(effects.get("manager_autonomy_delta", 0)))
    mgr_rel.metadata_json = mgr_meta
    flag_modified(mgr_rel, "metadata_json")

    gm_rel.trust = _clamp(gm_rel.trust + int(effects.get("gm_trust_delta", 0)))
    gm_rel.tension = _clamp(gm_rel.tension + int(effects.get("gm_tension_delta", 0)))

    decisions = list(meeting.decisions_json or [])
    decision_entry = {
        "resolution_id": chosen["resolution_id"],
        "title": chosen["title"],
        "description": chosen["description"],
        "owner_note": owner_note,
        "effects": effects,
        "resolved_at": _utcnow().isoformat(),
    }
    decisions.append(decision_entry)
    meeting.decisions_json = decisions
    flag_modified(meeting, "decisions_json")
    meeting.status = "completed"
    meeting.minutes_summary = (
        f"{meeting.minutes_summary or ''}\n\nExecutive Resolution Ratified: {chosen['title']} — {chosen['description']}"
        + (f" (Owner Note: {owner_note})" if owner_note else "")
    )
    meeting.updated_at = _utcnow()

    directive_key = f"boardroom_resolution:{meeting.id[:8]}"
    existing_dir = db.scalar(
        select(OwnerClubDirective).where(
            OwnerClubDirective.club_id == state.club_id,
            OwnerClubDirective.directive_key == directive_key,
        )
    )
    if existing_dir is None:
        db.add(
            OwnerClubDirective(
                id=str(uuid4()),
                club_id=state.club_id,
                department="boardroom",
                directive_key=directive_key,
                title=str(chosen["title"]),
                instruction=str(chosen["description"]),
                status="active",
                issued_day=int(state.world_day or 1),
                acknowledged_by=str(gm["name"]),
                acknowledgement_text=owner_note or "Ratified in boardroom session.",
                consequences_json=effects,
                updated_at=_utcnow(),
            )
        )

    from app.owner_console import living_institution

    world_day = int(state.world_day or 1)
    board_ev = living_institution.emit_canonical_club_event(
        db,
        state,
        category="governance",
        event_type="boardroom_resolution_ratified",
        source_subsystem="boardroom",
        title=f"Boardroom Resolution: {chosen['title']}",
        description=str(chosen["description"]),
        idempotency_key=f"board_res:{meeting.id}:{chosen['resolution_id']}:d{world_day}",
        visibility_classification=living_institution.VISIBILITY_RESTRICTED_EXECUTIVE,
        severity="notable",
        source_type="boardroom_meeting",
        source_id=meeting.id,
        payload={
            "meeting_id": meeting.id,
            "resolution_id": chosen["resolution_id"],
            "effects": effects,
        },
    )

    if effects.get("public_supporter_reset"):
        target_tier = str(effects.get("target_ticket_tier") or "standard")
        living_institution.engage_supporters(
            db,
            state,
            action_type="ticketing_decision",
            stance="collaborative",
            message=owner_note or f"Boardroom ratified supporter trust reset & '{target_tier}' matchday ticket tier.",
            ticket_price_tier=target_tier,
        )
        living_institution.publish_media_story(
            db,
            state,
            outlet_key="local_club_chronicle",
            story_type="supporter_reaction",
            classification="verified_event",
            headline=f"{state.club_name} Board Announces Supporter Trust & Ticketing Reset",
            subheadline=f"Official boardroom communiqué · Matchday tier adjusted to {target_tier}",
            body=(
                f"Following executive boardroom talks on World Day {world_day}, {state.club_name} confirmed an official "
                f"supporter outreach package setting ticket pricing to {target_tier}."
            ),
            source_type="boardroom_resolution",
            source_id=meeting.id,
            established_facts={
                "meeting_id": meeting.id,
                "ticket_price_tier": target_tier,
                "world_day": world_day,
            },
            idempotency_key=f"media:board_supporter_reset:{meeting.id}:d{world_day}",
            reputation_delta=1,
            supporter_sentiment_delta=4,
            leadership_pressure_delta=-3,
            visibility_classification=living_institution.VISIBILITY_OFFICIAL_ANNOUNCEMENT,
            has_public_signal=True,
            is_official_disclosure=True,
            canonical_event_id=board_ev.id,
        )

    living_institution.reconcile_club_reputation_and_identity(db, state)
    db.flush()
    return {
        "meeting_id": meeting.id,
        "status": meeting.status,
        "chosen_resolution": decision_entry,
        "canonical_event_id": board_ev.id,
        "manager_relationship": serialize_relationship_health(mgr_rel),
        "gm_relationship": serialize_relationship_health(gm_rel),
    }


# ---------------------------------------------------------------------------
# SECTION 11: MANAGER-DRIVEN MATCHDAY SELECTION AUTHORITY
# ---------------------------------------------------------------------------


VALID_TACTICAL_MENTALITIES = ("defensive", "balanced", "attacking")


def _normalize_tactical_mentality(value: Any, *, default: str = "balanced") -> str:
    clean = str(value or "").strip().lower()
    if clean in VALID_TACTICAL_MENTALITIES:
        return clean
    if any(k in clean for k in ("attack", "gegenpress", "high_press", "front_foot")):
        return "attacking"
    if any(k in clean for k in ("defens", "catenaccio", "pragmat", "low_block", "contain")):
        return "defensive"
    return default


def resolve_manager_mentality_decision(
    state_or_manager: OwnerClubState | dict[str, Any] | None,
    *,
    requested_mentality: str | None = None,
    facilities_json: dict[str, Any] | None = None,
    manager_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical First-Team Manager tactical mentality authority calculation.

    Used identically by owner tactical preference APIs, Operations Hub views,
    matchday selection, and competition simulation so tactical authority never
    disagrees across routes or simulation paths.
    """
    if isinstance(state_or_manager, dict):
        manager = dict(manager_override or state_or_manager or {})
        facs = dict(facilities_json or {})
        stored_req = requested_mentality
    elif state_or_manager is not None:
        manager = dict(manager_override or getattr(state_or_manager, "manager_json", None) or {})
        facs = dict(
            facilities_json
            if facilities_json is not None
            else (getattr(state_or_manager, "facilities_json", None) or {})
        )
        stored_req = (
            requested_mentality if requested_mentality is not None else getattr(state_or_manager, "mentality", None)
        )
    else:
        manager = dict(manager_override or {})
        facs = dict(facilities_json or {})
        stored_req = requested_mentality

    has_explicit_request = stored_req is not None and str(stored_req).strip().lower() in VALID_TACTICAL_MENTALITIES
    owner_requested = _normalize_tactical_mentality(stored_req, default="balanced")

    mgr_name = str(manager.get("name") or manager.get("display_name") or "").strip()
    is_vacant = bool(not manager or manager.get("is_vacant") or not mgr_name or "vacant" in mgr_name.lower())

    tactical_setup = {**dict(facs.get("_tactical_setup") or {}), **dict(facs.get("_tactical_config") or {})}

    if is_vacant:
        active_formation = str(tactical_setup.get("formation") or "4-3-3")
        active_pressing = str(tactical_setup.get("pressing") or "medium")
        effective_vacant = owner_requested if has_explicit_request else "balanced"
        return {
            "authority_model": "vacant_owner_provisional",
            "is_non_binding_preference": True,
            "manager_appointed": False,
            "manager_id": None,
            "manager_name": "First-Team Manager (Vacant)",
            "manager_archetype": None,
            "owner_requested_mentality": owner_requested,
            "manager_preferred_mentality": "balanced",
            "effective_mentality": effective_vacant,
            "decision_status": "owner_provisional",
            "implemented_as_requested": True,
            "reasoning": (
                "First-Team Manager seat is currently vacant. Provisional matchday preparation follows the "
                f"Owner's '{effective_vacant.upper()}' setup until a permanent manager is appointed."
            ),
            "factors": {
                "professional_independence": None,
                "tolerance_for_owner_interference": None,
                "tactical_flexibility": None,
                "attacking_vs_defensive": None,
                "active_formation": active_formation,
                "pressing": active_pressing,
                "preferred_tactical_philosophy": None,
                "tactical_distance": 0,
                "deference_score": None,
            },
        }

    profile = dict(manager.get("personality_profile") or {})
    if not profile or "professional_independence" not in profile or "tolerance_for_owner_interference" not in profile:
        derived = derive_manager_personality(manager)
        profile = {**derived, **profile}

    indep = _clamp(int(profile.get("professional_independence", 75)))
    tol = _clamp(int(profile.get("tolerance_for_owner_interference", 45)))
    flex = _clamp(int(profile.get("tactical_flexibility", 60)))
    loyalty = _clamp(int(profile.get("loyalty", 68)))
    atk_def = _clamp(int(profile.get("attacking_vs_defensive", 55)))
    philosophy = str(profile.get("preferred_tactical_philosophy") or manager.get("style") or "balanced_control")
    preferred_formations = list(profile.get("preferred_formations") or ["4-3-3"])
    active_formation = str(tactical_setup.get("formation") or preferred_formations[0])
    active_pressing = str(
        tactical_setup.get("pressing") or ("high" if int(profile.get("pressing_philosophy", 60)) >= 75 else "medium")
    )

    if atk_def >= 65:
        manager_preferred = "attacking"
    elif atk_def <= 38:
        manager_preferred = "defensive"
    else:
        manager_preferred = "balanced"

    if not has_explicit_request:
        owner_requested = manager_preferred

    mentality_order = {"defensive": 0, "balanced": 1, "attacking": 2}
    distance = abs(mentality_order[owner_requested] - mentality_order[manager_preferred])
    formation_mismatch = (owner_requested == "attacking" and active_formation.startswith("5-")) or (
        owner_requested == "defensive" and active_formation in ("3-4-3", "4-2-4")
    )

    deference_score = (
        (tol * 0.55)
        + ((100 - indep) * 0.45)
        + ((flex - 60) * 0.20)
        + ((loyalty - 65) * 0.10)
        - (distance * 8.0)
        - (8.0 if formation_mismatch else 0.0)
    )

    ratified_by_manager = bool(
        tactical_setup.get("ratified_by_manager") and tactical_setup.get("mentality") == owner_requested
    )

    if owner_requested == manager_preferred:
        effective = manager_preferred
        decision_status = "aligned"
        reasoning = (
            f"{mgr_name}'s tactical philosophy ({philosophy.replace('_', ' ')}, shape {active_formation}) "
            f"already aligns with a {effective.upper()} matchday plan."
        )
    elif ratified_by_manager:
        effective = owner_requested
        decision_status = "accepted"
        reasoning = (
            f"{mgr_name} ratified a tactical agreement with ownership for {effective.upper()} "
            f"under {active_formation} ({active_pressing} press)."
        )
    elif indep >= 75 or tol < 40:
        effective = manager_preferred
        decision_status = "rejected"
        reasoning = (
            f"{mgr_name} rejected the Owner's {owner_requested.upper()} request and retains matchday "
            f"{effective.upper()} under {active_formation} (Independence {indep}/100, Interference Tolerance {tol}/100)."
        )
    elif deference_score >= 48.0 and indep < 75 and tol >= 50:
        effective = owner_requested
        decision_status = "accepted"
        reasoning = (
            f"{mgr_name} accepted the Owner's non-binding {owner_requested.upper()} preference over their natural "
            f"{manager_preferred.upper()} inclination (Independence {indep}/100, Tolerance {tol}/100, Flexibility {flex}/100)."
        )
    elif 36.0 <= deference_score < 48.0:
        if distance == 2:
            effective = "balanced"
            decision_status = "modified"
            reasoning = (
                f"{mgr_name} refused to jump straight from {manager_preferred.upper()} to {owner_requested.upper()} in "
                f"{active_formation}, instead setting a BALANCED tactical compromise (Tolerance {tol}/100, Flexibility {flex}/100)."
            )
        elif distance == 1 and flex >= 70 and tol >= 55 and not formation_mismatch:
            effective = owner_requested
            decision_status = "accepted"
            reasoning = (
                f"{mgr_name} adapted their {active_formation} setup to accommodate the Owner's {owner_requested.upper()} "
                f"preference (Flexibility {flex}/100, Tolerance {tol}/100)."
            )
        else:
            effective = manager_preferred
            decision_status = "rejected"
            reasoning = (
                f"{mgr_name} declined the Owner's {owner_requested.upper()} shift and kept {effective.upper()} to preserve "
                f"{active_formation} shape integrity (Independence {indep}/100, Tolerance {tol}/100)."
            )
    else:
        effective = manager_preferred
        decision_status = "rejected"
        reasoning = (
            f"{mgr_name} upheld managerial authority and rejected {owner_requested.upper()}, maintaining "
            f"{effective.upper()} in {active_formation} (Independence {indep}/100, Tolerance {tol}/100)."
        )

    return {
        "authority_model": "first_team_manager_authoritative",
        "is_non_binding_preference": True,
        "manager_appointed": True,
        "manager_id": str(manager.get("id") or manager.get("manager_id") or profile.get("staff_id") or ""),
        "manager_name": mgr_name,
        "manager_archetype": profile.get("archetype_label") or profile.get("archetype_key"),
        "owner_requested_mentality": owner_requested,
        "manager_preferred_mentality": manager_preferred,
        "effective_mentality": effective,
        "decision_status": decision_status,
        "implemented_as_requested": effective == owner_requested,
        "reasoning": reasoning,
        "factors": {
            "professional_independence": indep,
            "tolerance_for_owner_interference": tol,
            "tactical_flexibility": flex,
            "attacking_vs_defensive": atk_def,
            "active_formation": active_formation,
            "pressing": active_pressing,
            "preferred_tactical_philosophy": philosophy,
            "tactical_distance": distance,
            "deference_score": round(deference_score, 2),
        },
    }


def evaluate_manager_mentality_authority(
    db: Session,
    state: OwnerClubState,
    *,
    requested_mentality: str | None = None,
) -> dict[str, Any]:
    ensure_club_staff_identities(db, state)
    return resolve_manager_mentality_decision(state, requested_mentality=requested_mentality)


def select_manager_matchday_lineup(
    db: Session,
    state: OwnerClubState,
) -> dict[str, Any]:
    """Authoritative First-Team Manager matchday selection engine."""
    identities = ensure_club_staff_identities(db, state)
    mgr = identities["first_team_manager"]
    mgr_profile = mgr["personality_profile"]
    fac = dict(state.facilities_json or {})

    commitments = dict(fac.get("_manager_matchday_commitments") or {})
    rejections = dict(fac.get("_manager_matchday_rejections") or {})
    exclusions = dict(fac.get("_manager_disciplinary_exclusions") or {})
    owner_pref = dict(fac.get("_owner_lineup_preference") or {})

    players = list(db.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    from app.models.player_injury_case import PlayerInjuryCase

    canonical_refs = [str(p.player_ref) for p in players if p.player_ref]
    active_injury_refs: set[str] = set()
    if canonical_refs:
        injury_rows = db.scalars(
            select(PlayerInjuryCase).where(
                PlayerInjuryCase.player_id.in_(canonical_refs),
                PlayerInjuryCase.recovered_on.is_(None),
            )
        ).all()
        active_injury_refs = {str(row.player_id) for row in injury_rows}
    eligible = [
        p
        for p in players
        if int(p.injured_days or 0) <= 0
        and str(p.id) not in exclusions
        and str(p.player_ref or "") not in active_injury_refs
    ]
    if len(eligible) < 11:
        eligible = [
            p for p in players if int(p.injured_days or 0) <= 0 and str(p.player_ref or "") not in active_injury_refs
        ]

    youth_commit = _optional_score(mgr_profile, "youth_development_commitment")
    veteran_pref = _optional_score(mgr_profile, "preference_for_experienced_players")
    from app.owner_console.engine import manager_tactics

    tactics = manager_tactics(dict(state.manager_json or {}), fac)
    tactical_setup = {**dict(fac.get("_tactical_setup") or {}), **dict(fac.get("_tactical_config") or {})}
    owner_formation = str(owner_pref.get("preferred_formation") or "")
    flexibility = int(tactics.get("tactical_flexibility") or 0)
    flexibility_pct = flexibility * 5 if flexibility <= 20 else flexibility
    manager_shapes = {str(item) for item in (tactics.get("formations") or [])}
    if owner_formation and (owner_formation in manager_shapes or flexibility_pct >= 70):
        chosen_formation = owner_formation
    else:
        chosen_formation = str(tactics.get("formation") or tactical_setup.get("formation") or "") or None

    mentality_authority = resolve_manager_mentality_decision(state)
    chosen_mentality = str(mentality_authority["effective_mentality"])

    def _manager_player_score(p: OwnerSquadPlayer) -> float:
        base = float(p.rating) if p.rating is not None else 0.0
        fitness_adj = (float(_player_fitness(p)) - 80.0) * 0.18 if "fitness" in dict(p.personality_json or {}) else 0.0
        morale_adj = ((float(p.morale) - 65.0) * 0.15) if p.morale is not None else 0.0
        age = int(p.age) if p.age is not None else None
        age_adj = 0.0
        if age is not None and youth_commit is not None and veteran_pref is not None:
            if age <= 19 or _player_is_academy(p):
                age_adj += ((youth_commit - 50) / 50.0) * 6.5
                age_adj -= ((veteran_pref - 50) / 50.0) * 6.0
            elif age >= 27:
                age_adj += ((veteran_pref - 50) / 50.0) * 4.5

        commitment = commitments.get(str(p.id))
        if commitment and commitment.get("matchday_role") == "starting_xi":
            age_adj += 30.0
        elif str(p.id) in rejections:
            age_adj -= 25.0
        return round(base + fitness_adj + morale_adj + age_adj, 2)

    def _sheet_name(p: OwnerSquadPlayer) -> str:
        pers = dict(p.personality_json or {})
        raw = str(pers.get("squad_status") or "").lower()
        if raw == "reserve":
            return "reserve"
        if pers.get("is_academy") or raw in {"academy", "u21"}:
            return "academy"
        if raw in {"first_team", "senior"}:
            return "first_team"
        if p.acquired_via == "academy" and p.is_regen and int(p.age or 99) <= 18:
            return "academy"
        return "first_team"

    def _is_gk(p: OwnerSquadPlayer) -> bool:
        pos = str(p.position or "")
        return pos.upper() in {"GK", "GOALKEEPER"} or pos.lower().startswith("goal")

    def _token_line(token: str) -> str | None:
        raw = token.strip().upper()
        if not raw:
            return None
        if raw in {"GK", "GOALKEEPER"} or raw.startswith("GOAL"):
            return "GK"
        if raw in {"CB", "LB", "RB", "LWB", "RWB", "DF", "DEF", "SW"} or raw.startswith("DEF") or "BACK" in raw:
            return "DEF"
        if raw in {"DM", "CDM", "CM", "AM", "CAM", "LM", "RM", "MF", "MID"} or raw.startswith("MID"):
            return "MID"
        if (
            raw in {"ST", "CF", "LW", "RW", "SS", "FW", "FWD", "ATT"}
            or raw.startswith("FORW")
            or raw.startswith("STRIK")
        ):
            return "FWD"
        return None

    def _player_line(p: OwnerSquadPlayer) -> str:
        first_token = str(p.position or "").strip().upper().split("/")[0].strip()
        return _token_line(first_token) or "MID"

    def _player_can_play_line(p: OwnerSquadPlayer, line: str) -> bool:
        pers = dict(p.personality_json or {})
        pos_str = f"{p.position or ''} / {pers.get('position_display') or ''}"
        tokens = [tok.strip() for tok in pos_str.replace(",", "/").split("/") if tok.strip()]
        matched = {_token_line(tok) for tok in tokens}
        matched.discard(None)
        if not matched:
            return line == "MID"
        return line in matched

    shape_parts = [int(x) for x in str(chosen_formation or "4-3-3").split("-") if x.isdigit()]
    if len(shape_parts) >= 3 and sum(shape_parts) == 10:
        def_target = shape_parts[0]
        fwd_target = shape_parts[-1]
        mid_target = sum(shape_parts[1:-1])
    else:
        def_target, mid_target, fwd_target = 4, 3, 3

    pref_ids = [
        str(pid) for pid in (owner_pref.get("preferred_player_ids") or owner_pref.get("preferred_starter_ids") or [])
    ]
    by_id = {str(p.id): p for p in eligible}
    first_team = [p for p in eligible if _sheet_name(p) == "first_team"]
    committed_xi = [
        p
        for p in eligible
        if (commitments.get(str(p.id)) or {}).get("matchday_role") == "starting_xi" and _sheet_name(p) != "first_team"
    ]
    committed_xi_ids = {str(p.id) for p in committed_xi}
    pref_first: list[OwnerSquadPlayer] = []
    pref_seen: set[str] = set()
    for pid in pref_ids:
        if pid in pref_seen or pid not in by_id:
            continue
        candidate = by_id[pid]
        if _sheet_name(candidate) == "first_team" or pid in committed_xi_ids:
            pref_first.append(candidate)
            pref_seen.add(pid)

    # If the owner submitted a complete 11-player lineup and the manager accepts all 11
    # (all 11 are eligible, on the first team or committed XI, not rejected, and include a GK),
    # keep the owner's exact 11 players in their exact chosen slot order without reshuffling.
    owner_full_xi_accepted = (
        len(pref_ids) == 11
        and len(pref_first) == 11
        and all(str(p.id) not in rejections for p in pref_first)
        and any(_is_gk(p) for p in pref_first)
    )

    if owner_full_xi_accepted:
        starters = list(pref_first[:11])
    else:
        ranked_first = sorted(first_team, key=_manager_player_score, reverse=True)
        ranked_non_academy = [
            p for p in sorted(eligible, key=_manager_player_score, reverse=True) if _sheet_name(p) != "academy"
        ]
        candidate_pool: list[OwnerSquadPlayer] = []
        pool_seen: set[str] = set()
        for player in pref_first + committed_xi + ranked_first + ranked_non_academy:
            pid = str(player.id)
            if pid not in pool_seen:
                candidate_pool.append(player)
                pool_seen.add(pid)

        used_ids: set[str] = set()

        def _take_line(line: str, count: int) -> list[OwnerSquadPlayer]:
            picked: list[OwnerSquadPlayer] = []
            # Pass 1: primary position matches line
            for player in candidate_pool:
                if len(picked) >= count:
                    break
                pid = str(player.id)
                if pid in used_ids:
                    continue
                if _player_line(player) == line:
                    picked.append(player)
                    used_ids.add(pid)
            # Pass 2: secondary position matches line
            if len(picked) < count:
                for player in candidate_pool:
                    if len(picked) >= count:
                        break
                    pid = str(player.id)
                    if pid in used_ids:
                        continue
                    if _player_can_play_line(player, line):
                        picked.append(player)
                        used_ids.add(pid)
            return picked

        gk_pick = _take_line("GK", 1)
        def_picks = _take_line("DEF", def_target)
        mid_picks = _take_line("MID", mid_target)
        fwd_picks = _take_line("FWD", fwd_target)

        def _top_up(bucket: list[OwnerSquadPlayer], target_count: int, *, allow_gk: bool = False) -> None:
            for player in candidate_pool:
                if len(bucket) >= target_count:
                    break
                pid = str(player.id)
                if pid in used_ids:
                    continue
                if not allow_gk and _is_gk(player):
                    continue
                bucket.append(player)
                used_ids.add(pid)

        _top_up(gk_pick, 1, allow_gk=True)
        _top_up(def_picks, def_target)
        _top_up(mid_picks, mid_target)
        _top_up(fwd_picks, fwd_target)

        starters = (gk_pick + def_picks + mid_picks + fwd_picks)[:11]
        if len(starters) < 11:
            for player in sorted(eligible, key=_manager_player_score, reverse=True):
                if len(starters) >= 11:
                    break
                if str(player.id) in used_ids or _sheet_name(player) == "academy":
                    continue
                starters.append(player)
                used_ids.add(str(player.id))
        starters = starters[:11]

    starter_ids = {p.id for p in starters}
    remaining = [p for p in sorted(eligible, key=_manager_player_score, reverse=True) if p.id not in starter_ids]

    bench: list[OwnerSquadPlayer] = []
    pref_bench_ids = [str(pid) for pid in (owner_pref.get("preferred_bench_ids") or [])]
    for pid in pref_bench_ids:
        player = by_id.get(pid)
        if (
            player is not None
            and player.id not in starter_ids
            and player not in bench
            and _sheet_name(player) != "academy"
            and len(bench) < 7
        ):
            bench.append(player)
    for p in remaining:
        commitment = commitments.get(str(p.id))
        if commitment and commitment.get("matchday_role") in ("matchday_squad_bench", "substitute_impact"):
            bench.append(p)
    for p in remaining:
        if p not in bench and _sheet_name(p) == "reserve" and len(bench) < 7:
            bench.append(p)
    for p in remaining:
        if p not in bench and _sheet_name(p) != "academy" and len(bench) < 7:
            bench.append(p)

    accepted_pref_ids = [pid for pid in pref_ids if pid in starter_ids]
    declined_pref_ids = [pid for pid in pref_ids if pid not in starter_ids]
    if declined_pref_ids:
        decision_outcome = "declined"
        verdict_reason = (
            f"{mgr['name']} declined owner-preferred players {', '.join(declined_pref_ids)} "
            f"and named the matchday XI ({chosen_formation}, {chosen_mentality})."
        )
    elif pref_ids:
        decision_outcome = "accepted"
        verdict_reason = (
            f"{mgr['name']} accepted the owner's preferred players into the matchday XI "
            f"({chosen_formation}, {chosen_mentality})."
        )
    else:
        decision_outcome = "manager_selection"
        verdict_reason = (
            f"{mgr['name']} selected the authoritative matchday XI ({chosen_formation}, {chosen_mentality}) "
            f"based on tactical philosophy, fitness, and readiness."
        )
    if owner_formation and owner_formation != chosen_formation:
        verdict_reason += (
            f" {mgr['name']} kept {chosen_formation}; tactical flexibility "
            f"{tactics.get('tactical_flexibility')} does not take {owner_formation}."
        )

    selection_payload = {
        "selected_by_manager_id": mgr.get("id"),
        "selected_by_manager_name": mgr.get("name"),
        "manager_archetype": mgr_profile.get("archetype_label"),
        "formation": chosen_formation,
        "tactical_flexibility": tactics.get("tactical_flexibility"),
        "tactical_match_bonus": tactics.get("tactical_match_bonus"),
        "owner_formation_accepted": not owner_formation or owner_formation == chosen_formation,
        "mentality": chosen_mentality,
        "mentality_authority": mentality_authority,
        "tactical_philosophy": mgr_profile.get("preferred_tactical_philosophy"),
        "owner_preferred_player_ids": pref_ids,
        "manager_starting_ids": [p.id for p in starters],
        "starting_xi_ids": [p.id for p in starters],
        "bench_ids": [p.id for p in bench],
        "decision_outcome": decision_outcome,
        "verdict_reason": verdict_reason,
        "starting_xi": [
            {
                "id": p.id,
                "name": p.name,
                "position": p.position,
                "age": p.age,
                "rating": p.rating,
                "fitness": _player_fitness(p),
                "is_academy": _player_is_academy(p),
                "manager_score": _manager_player_score(p),
            }
            for p in starters
        ],
        "bench": [
            {
                "id": p.id,
                "name": p.name,
                "position": p.position,
                "age": p.age,
                "rating": p.rating,
                "fitness": _player_fitness(p),
                "is_academy": _player_is_academy(p),
            }
            for p in bench
        ],
        "owner_preference_evaluation": {
            "is_non_binding": True,
            "accepted_starter_ids": accepted_pref_ids,
            "declined_starter_ids": declined_pref_ids,
            "manager_note": verdict_reason,
        },
        "selected_at": _utcnow().isoformat(),
    }
    fac["_last_manager_matchday_selection"] = selection_payload
    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    db.flush()
    return selection_payload
