from __future__ import annotations


import hashlib

import json

import logging

import math

from pathlib import Path

import random

from typing import Any

logger = logging.getLogger(__name__)


FIRST_NAMES = [
    "Adewale",
    "Babatunde",
    "Damilola",
    "Oluwaseun",
    "Ayodeji",
    "Tunde",
    "Kehinde",
    "Taiwo",
    "Olamide",
    "Segun",
    "Femi",
    "Gbenga",
    "Tobi",
    "Dayo",
    "Bayo",
    "Ademola",
    "Kayode",
    "Wale",
    "Opeyemi",
    "Folarin",
]

LAST_NAMES = [
    "Adebayo",
    "Ogunleye",
    "Adeyemi",
    "Okunola",
    "Afolabi",
    "Balogun",
    "Ogundipe",
    "Adeniyi",
    "Oyelaran",
    "Akinola",
    "Olawale",
    "Ajayi",
    "Oladipo",
    "Adekunle",
    "Ogunbiyi",
    "Ojo",
    "Alabi",
    "Fashola",
]

POSITIONS = ["goalkeeper", "defender", "defender", "midfielder", "midfielder", "forward"]

AI_CLUBS = [
    "Ikorodu Royals",
    "Port Harcourt Tide",
    "Kano Pillars Academy",
    "Abuja Capital FC",
    "Enugu Coal City",
    "Ibadan Oluyole",
    "Benin Bronze",
    "Jos Plateau Stars",
    "Warri Delta Kings",
    "Calabar Carnival FC",
    "Owerri Heartland Youth",
    "Kaduna Northern Lights",
    "Lagos Island Mariners",
    "Abeokuta Rock FC",
    "Uyo Akwa Stars",
]

SPONSORS = [
    "Lekki Logistics",
    "Eko Telecom",
    "Harbour Trust Bank",
    "Naija Kicks",
    "Sahel Energy",
    "Okada Express",
    "Jollof Republic Foods",
]

SPONSOR_SLOTS = ["Front of shirt", "Stadium naming", "Training kit", "Sleeve patch"]

ROLE_REQUESTS = {
    "defender": "a commanding centre-back who can lead the line",
    "midfielder": "a ball-winning midfielder to protect the back four",
    "forward": "a clinical striker who can finish half-chances",
    "goalkeeper": "a reliable goalkeeper with big-game composure",
}


TEMPERAMENTS = ["calm", "demanding", "fiery", "volatile", "pragmatic"]

DISCIPLINE = ["strict", "balanced", "player-friendly"]

MEDIA = ["guarded", "charismatic", "combative", "diplomatic"]

TRANSFER_PREFS = ["youth-first", "proven-veterans", "bargain-hunter", "marquee-signings", "system-fits"]

FACILITY_KINDS = ("training", "academy", "medical", "stadium", "commercial")


def seeded(*parts: object) -> random.Random:

    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()

    return random.Random(int(digest[:12], 16))


def clamp(value: float, low: float, high: float) -> float:

    return max(low, min(high, value))


def apply_mood_delta(record: dict[str, Any] | None, delta: int, *, key: str = "mood") -> int | None:
    """Move a mood that is already on the record. An unfiled mood stays unfiled."""
    if not isinstance(record, dict):
        return None
    raw = record.get(key)
    if raw is None:
        return None
    try:
        current = int(raw)
    except (TypeError, ValueError):
        return None
    updated = int(clamp(current + int(delta), 0, 100))
    record[key] = updated
    return updated


def prestige_tier_label(prestige: int) -> str:

    p = int(prestige or 0)

    if p >= 85:

        return "Tier 1: Global Superclub"

    if p >= 70:

        return "Tier 2: Continental Elite"

    if p >= 50:

        return "Tier 3: Established Challenger"

    if p >= 35:

        return "Tier 4: Rising Contender"

    return "Tier 5: Grassroots Foundation"


EXECUTIVE_STAFF_ROLES = (
    "general_manager",
    "first_team_manager",
    "head_of_youth_development",
    "chief_scout",
    "medical_director",
)


EXECUTIVE_STAFF_CATALOG: list[dict[str, Any]] = [
    # --- General Managers ---
    {
        "id": "gm_grassroots_dayo",
        "staff_id": "gm_grassroots_dayo",
        "role": "general_manager",
        "role_label": "General Manager",
        "name": "Dayo Adeleke",
        "style": "Grassroots Operator",
        "temperament": "pragmatic",
        "ambition": 10,
        "loyalty": 16,
        "youth_development": 12,
        "tactical_flexibility": 10,
        "negotiation": 11,
        "commercial_acumen": 11,
        "scouting_accuracy": 10,
        "medical_expertise": 8,
        "min_prestige": 15,
        "salary": 600,
        "salary_gtex": 600,
        "signing_fee_gtex": 1200,
        "bio": "A well-connected community operator with decades of grassroots Nigerian football administration experience.",
        "specialty": "Grassroots Local Sourcing",
    },
    {
        "id": "gm_paul_mitchell",
        "staff_id": "gm_paul_mitchell",
        "role": "general_manager",
        "role_label": "General Manager",
        "name": "Paul Mitchell",
        "style": "Modern Sporting Director",
        "temperament": "demanding",
        "ambition": 16,
        "loyalty": 12,
        "youth_development": 15,
        "tactical_flexibility": 14,
        "negotiation": 16,
        "commercial_acumen": 15,
        "scouting_accuracy": 16,
        "medical_expertise": 12,
        "min_prestige": 45,
        "salary": 2500,
        "salary_gtex": 2500,
        "signing_fee_gtex": 5000,
        "bio": "Renowned recruitment director who built modern title-challenging squads across England and France.",
        "specialty": "Squad Rebuilding & Value Arbitrage",
    },
    {
        "id": "gm_michael_edwards",
        "staff_id": "gm_michael_edwards",
        "role": "general_manager",
        "role_label": "General Manager",
        "name": "Michael Edwards",
        "style": "Data & High-Performance Architect",
        "temperament": "calm",
        "ambition": 18,
        "loyalty": 14,
        "youth_development": 17,
        "tactical_flexibility": 17,
        "negotiation": 19,
        "commercial_acumen": 18,
        "scouting_accuracy": 19,
        "medical_expertise": 15,
        "min_prestige": 75,
        "salary": 8000,
        "salary_gtex": 8000,
        "signing_fee_gtex": 16000,
        "bio": "Legendary sporting executive who engineered Liverpool's domestic and European resurgence through data-driven mastery.",
        "specialty": "Elite Negotiation & Analytics Architecture",
    },
    # --- First-Team Managers ---
    {
        "id": "gtex-staff-coach",
        "staff_id": "gtex-staff-coach",
        "role": "first_team_manager",
        "role_label": "First-Team Manager",
        "name": "Tunde Bakare",
        "style": "Balanced Staff Coach",
        "temperament": "calm",
        "ambition": 9,
        "loyalty": 18,
        "youth_development": 12,
        "tactical_flexibility": 11,
        "negotiation": 8,
        "commercial_acumen": 9,
        "scouting_accuracy": 10,
        "medical_expertise": 9,
        "min_prestige": 15,
        "salary": 500,
        "salary_gtex": 500,
        "signing_fee_gtex": 1000,
        "bio": "A dependable, pragmatic staff manager assigned by GTEX until the board appoints a marquee tactician.",
        "specialty": "Squad Stabilization",
    },
    {
        "id": "mgr_tunde_mcphill",
        "staff_id": "mgr_tunde_mcphill",
        "role": "first_team_manager",
        "role_label": "First-Team Manager",
        "name": "Tunde Mc'Phill",
        "nation": "Nigeria",
        "nationality": "Nigeria",
        "country_code": "NG",
        "age": 37,
        "gender": "male",
        "style": "Gegenpressing Counter-Attack",
        "mentality": "pressing",
        "pressing": "gegenpress",
        "temperament": "pragmatic",
        "ambition": 15,
        "loyalty": 16,
        "youth_development": 16,
        "tactical_flexibility": 16,
        "tactical_quality": 16,
        "influence": 16,
        "negotiation": 12,
        "commercial_acumen": 10,
        "scouting_accuracy": 14,
        "medical_expertise": 10,
        "min_prestige": 32,
        "salary": 1600,
        "salary_fancoin": 1600,
        "salary_fan_coin": 1600,
        "salary_gtex": 160,
        "signing_fee_gtex": 4800,
        "rating": 76,
        "gsi": 76,
        "potential": 88,
        "rarity": "established",
        "profile_locked": True,
        "portrait_url": "/staff-portraits/mature_m_west_african_41.jpg",
        "preferred_formation": "3-4-3",
        "preferred_formations": ["3-4-3", "3-4-1-2", "3-4-2-1", "4-1-2-1-2", "4-4-2"],
        "fallback_formation": "4-4-2",
        "tactics": ["3-4-3", "3-4-1-2", "3-4-2-1", "4-1-2-1-2", "4-4-2", "gegenpress", "counter_attack"],
        "traits": ["develops_young_players", "academy_promotion_bias", "tactical_flexibility", "balanced_substitution"],
        "youth_age_max": 26,
        "uses_academy_players": True,
        "son_player_id": "0ad4570a-0c6c-448b-ae08-3584be3d1ef0",
        "son_player_name": "Folarin Mc'Phill",
        "family_relationship": "Father of academy striker Folarin Mc'Phill (Nigeria)",
        "bio": (
            "Tunde Mc'Phill, 37, Nigerian tactician who coaches high-voltage gegenpressing and counter-attacking football. "
            "He rotates 3-4-3, 3-4-1-2, 3-4-2-1, and a 4-1-2-1-2 diamond (4-4-2 diamond), with 4-4-2 as his fallback: "
            "aggressive counter-pressing traps, rapid vertical transitions, and relentless front-three movement. "
            "Father of academy striker Folarin Mc'Phill. He selects players under 26 and builds the side from academy graduates. "
            "Youth rating & tactical influence 16. GSI 76, potential 88."
        ),
        "philosophy_summary": (
            "Gegenpressing counter-attacking football across 3-4-3, 3-4-1-2, 3-4-2-1, and 4-1-2-1-2 diamond (4-4-2 fallback). "
            "Father of academy striker Folarin Mc'Phill. Players under 26, academy graduates first."
        ),
        "personal_agenda": (
            "Gegenpressing counter-attacking football across 3-4-3, 3-4-1-2, 3-4-2-1, and 4-1-2-1-2 diamond (4-4-2 fallback). "
            "Promote academy graduates and players under 26."
        ),
        "specialty": "Gegenpressing Counter-Attack & Youth Pathway",
    },
    {
        "id": "mgr_marcelo_vance",
        "staff_id": "mgr_marcelo_vance",
        "role": "first_team_manager",
        "role_label": "First-Team Manager",
        "name": "Marcelo Vance",
        "style": "High-Intensity Pressing",
        "temperament": "fiery",
        "ambition": 15,
        "loyalty": 11,
        "youth_development": 16,
        "tactical_flexibility": 15,
        "negotiation": 10,
        "commercial_acumen": 11,
        "scouting_accuracy": 13,
        "medical_expertise": 11,
        "min_prestige": 40,
        "salary": 2200,
        "salary_gtex": 2200,
        "signing_fee_gtex": 4400,
        "bio": "Obsessive tactician known for relentless Gegenpressing, fitness conditioning, and promoting fearless youth.",
        "specialty": "Pressing & Match Intensity",
    },
    {
        "id": "mgr_carlo_castiglione",
        "staff_id": "mgr_carlo_castiglione",
        "role": "first_team_manager",
        "role_label": "First-Team Manager",
        "name": "Carlo Castiglione",
        "style": "Galactico Man-Manager",
        "temperament": "calm",
        "ambition": 19,
        "loyalty": 13,
        "youth_development": 14,
        "tactical_flexibility": 19,
        "negotiation": 15,
        "commercial_acumen": 17,
        "scouting_accuracy": 16,
        "medical_expertise": 14,
        "min_prestige": 75,
        "salary": 2000,
        "salary_gtex": 2000,
        "signing_fee_gtex": 4000,
        "bio": "Multi-time European champion with an eyebrow of steel, master of dressing-room harmony and tactical adjustments in big finals.",
        "specialty": "Champions League Pedigree & Star Management",
    },
    # --- Head of Youth Development ---
    {
        "id": "hoyd_femi_ogunleye",
        "staff_id": "hoyd_femi_ogunleye",
        "role": "head_of_youth_development",
        "role_label": "Head of Youth Development",
        "name": "Femi Ogunleye",
        "style": "Diamond-in-the-Rough Mentor",
        "temperament": "demanding",
        "ambition": 11,
        "loyalty": 17,
        "youth_development": 14,
        "tactical_flexibility": 10,
        "negotiation": 10,
        "commercial_acumen": 8,
        "scouting_accuracy": 13,
        "medical_expertise": 10,
        "min_prestige": 15,
        "salary": 500,
        "salary_gtex": 500,
        "signing_fee_gtex": 1000,
        "bio": "Pivotal figure in Lagos youth academies who has uncovered dozens of raw teenagers and shaped them into pros.",
        "specialty": "Grassroots Academy Pipeline",
    },
    {
        "id": "hoyd_piet_devisser",
        "staff_id": "hoyd_piet_devisser",
        "role": "head_of_youth_development",
        "role_label": "Head of Youth Development",
        "name": "Piet de Visser Jr",
        "style": "Total Football Pedagogy",
        "temperament": "calm",
        "ambition": 14,
        "loyalty": 15,
        "youth_development": 17,
        "tactical_flexibility": 15,
        "negotiation": 12,
        "commercial_acumen": 11,
        "scouting_accuracy": 16,
        "medical_expertise": 12,
        "min_prestige": 45,
        "salary": 2200,
        "salary_gtex": 2200,
        "signing_fee_gtex": 4500,
        "bio": "Dutch academy guru emphasizing positional versatility, technical elegance, and fast first-touch progression.",
        "specialty": "Technical Fundamentals & High Ceilings",
    },
    {
        "id": "hoyd_carles_font",
        "staff_id": "hoyd_carles_font",
        "role": "head_of_youth_development",
        "role_label": "Head of Youth Development",
        "name": "Carles Font",
        "style": "La Masia DNA Mastermind",
        "temperament": "diplomatic",
        "ambition": 17,
        "loyalty": 14,
        "youth_development": 20,
        "tactical_flexibility": 18,
        "negotiation": 14,
        "commercial_acumen": 14,
        "scouting_accuracy": 18,
        "medical_expertise": 14,
        "min_prestige": 70,
        "salary": 6000,
        "salary_gtex": 6000,
        "signing_fee_gtex": 12000,
        "bio": "Architect of golden generations who instills elite tactical maturity into prospects before their 18th birthday.",
        "specialty": "Generational Wonderkid Incubation",
    },
    # --- Chief Scout ---
    {
        "id": "scout_kelechi_nwosu",
        "staff_id": "scout_kelechi_nwosu",
        "role": "chief_scout",
        "role_label": "Chief Scout",
        "name": "Kelechi Nwosu",
        "style": "Eye-Test Traditionalist",
        "temperament": "pragmatic",
        "ambition": 10,
        "loyalty": 16,
        "youth_development": 11,
        "tactical_flexibility": 11,
        "negotiation": 10,
        "commercial_acumen": 8,
        "scouting_accuracy": 13,
        "medical_expertise": 8,
        "min_prestige": 15,
        "salary": 450,
        "salary_gtex": 450,
        "signing_fee_gtex": 900,
        "bio": "Has travelled across 30 African states unearthing hidden raw speed and natural athletic prodigies.",
        "specialty": "Regional Athletic Profiling",
    },
    {
        "id": "scout_sven_mislintat",
        "staff_id": "scout_sven_mislintat",
        "role": "chief_scout",
        "role_label": "Chief Scout",
        "name": "Sven Mislintat",
        "style": "Diamond Eye Analytics",
        "temperament": "demanding",
        "ambition": 15,
        "loyalty": 12,
        "youth_development": 14,
        "tactical_flexibility": 15,
        "negotiation": 13,
        "commercial_acumen": 13,
        "scouting_accuracy": 17,
        "medical_expertise": 10,
        "min_prestige": 50,
        "salary": 2400,
        "salary_gtex": 2400,
        "signing_fee_gtex": 4800,
        "bio": "Pioneer of metrics-blended video scouting with an unmatched track record in discovering European breakout stars.",
        "specialty": "Value Discovery & Statistical Outliers",
    },
    {
        "id": "scout_luis_campos",
        "staff_id": "scout_luis_campos",
        "role": "chief_scout",
        "role_label": "Chief Scout",
        "name": "Luis Campos",
        "style": "Global Network Sovereign",
        "temperament": "pragmatic",
        "ambition": 19,
        "loyalty": 11,
        "youth_development": 16,
        "tactical_flexibility": 17,
        "negotiation": 18,
        "commercial_acumen": 19,
        "scouting_accuracy": 20,
        "medical_expertise": 13,
        "min_prestige": 72,
        "salary": 6500,
        "salary_gtex": 6500,
        "signing_fee_gtex": 13000,
        "bio": "Built Monaco and Lille championship squads; holds an unmatched global scouting network spanning South America to Asia.",
        "specialty": "Billion-Dollar Scouting Pipeline",
    },
    # --- Medical Director ---
    {
        "id": "med_dr_amaka_eze",
        "staff_id": "med_dr_amaka_eze",
        "role": "medical_director",
        "role_label": "Medical Director",
        "name": "Dr. Amaka Eze",
        "style": "Holistic Physio Care",
        "temperament": "calm",
        "ambition": 11,
        "loyalty": 18,
        "youth_development": 10,
        "tactical_flexibility": 9,
        "negotiation": 9,
        "commercial_acumen": 8,
        "scouting_accuracy": 9,
        "medical_expertise": 13,
        "min_prestige": 15,
        "salary": 400,
        "salary_gtex": 400,
        "signing_fee_gtex": 800,
        "bio": "Dedicated sports medicine specialist focused on workload management, muscle fatigue prevention, and fast rehabilitation.",
        "specialty": "Preventive Care & Rapid Recovery",
    },
    {
        "id": "med_dr_lieven",
        "staff_id": "med_dr_lieven",
        "role": "medical_director",
        "role_label": "Medical Director",
        "name": "Dr. Lieven Maesschalck",
        "style": "High-Performance Biomechanics",
        "temperament": "demanding",
        "ambition": 15,
        "loyalty": 14,
        "youth_development": 11,
        "tactical_flexibility": 11,
        "negotiation": 12,
        "commercial_acumen": 12,
        "scouting_accuracy": 11,
        "medical_expertise": 17,
        "min_prestige": 45,
        "salary": 1800,
        "salary_gtex": 1800,
        "signing_fee_gtex": 3600,
        "bio": "World-renowned Belgian physiotherapist trusted by Premier League stars for complex ligament and muscular reconstructions.",
        "specialty": "Advanced Biomechanics & Ligament Recovery",
    },
    {
        "id": "med_dr_ramon_cugat",
        "staff_id": "med_dr_ramon_cugat",
        "role": "medical_director",
        "role_label": "Medical Director",
        "name": "Dr. Ramon Cugat",
        "style": "Regenerative Cellular Therapy",
        "temperament": "calm",
        "ambition": 18,
        "loyalty": 15,
        "youth_development": 12,
        "tactical_flexibility": 12,
        "negotiation": 14,
        "commercial_acumen": 15,
        "scouting_accuracy": 13,
        "medical_expertise": 20,
        "min_prestige": 70,
        "salary": 5500,
        "salary_gtex": 5500,
        "signing_fee_gtex": 11000,
        "bio": "World-leading orthopedic surgeon and PRP therapy pioneer who has saved the careers of hundreds of world-class athletes.",
        "specialty": "Regenerative Medicine & Halved Injury Downtime",
    },
]


# Dynamically load full executive staff catalog from exported JSON if present

_catalog_file = Path(__file__).resolve().parent / "executive_staff_catalog.json"
_seen_ids = {s.get("id") for s in EXECUTIVE_STAFF_CATALOG}

if _catalog_file.is_file():

    try:

        with open(_catalog_file, "r", encoding="utf-8") as _f:

            _loaded_staff = json.load(_f)

            if isinstance(_loaded_staff, list) and _loaded_staff:

                _seen_ids.update(s.get("id") for s in EXECUTIVE_STAFF_CATALOG)

                for _s in _loaded_staff:

                    if _s.get("id") and _s["id"] not in _seen_ids:

                        EXECUTIVE_STAFF_CATALOG.append(_s)

                        _seen_ids.add(_s["id"])

    except Exception as _e:

        logger.warning("Could not load executive_staff_catalog.json: %s", _e)

from app.owner_console.real_first_team_managers import apply_real_first_team_managers

apply_real_first_team_managers(EXECUTIVE_STAFF_CATALOG)
_seen_ids.update(item.get("id") for item in EXECUTIVE_STAFF_CATALOG)

from app.owner_console.regen_staff_catalog import build_regen_staff_catalog

for _regen in build_regen_staff_catalog():
    if _regen.get("id") and _regen["id"] not in _seen_ids:
        EXECUTIVE_STAFF_CATALOG.append(_regen)
        _seen_ids.add(_regen["id"])
build_regen_staff_catalog.cache_clear()


MANAGER_CATALOG: list[dict[str, Any]] = [
    item for item in EXECUTIVE_STAFF_CATALOG if item["role"] == "first_team_manager"
]


def calculate_staff_effects(appointed_staff: dict[str, Any]) -> dict[str, Any]:

    gm = appointed_staff.get("general_manager") or {}

    mgr = appointed_staff.get("first_team_manager") or {}

    hoyd = appointed_staff.get("head_of_youth_development") or {}

    scout = appointed_staff.get("chief_scout") or {}

    med = appointed_staff.get("medical_director") or {}

    return {
        "transfer_fee_discount_pct": (
            round(float(gm["negotiation"]) * 0.5, 1) if gm.get("negotiation") is not None else 0.0
        ),
        "sponsor_revenue_bonus_pct": (
            round(float(gm["commercial_acumen"]) * 0.6, 1) if gm.get("commercial_acumen") is not None else 0.0
        ),
        "academy_potential_bonus": (
            int(hoyd["youth_development"]) // 3 if hoyd.get("youth_development") is not None else 0
        ),
        "tactical_match_bonus": (
            round(
                float(
                    mgr["tactical_flexibility"]
                    if mgr.get("tactical_flexibility") is not None
                    else mgr.get("tactical_quality")
                )
                * 0.4,
                1,
            )
            if mgr.get("tactical_flexibility") is not None or mgr.get("tactical_quality") is not None
            else 0.0
        ),
        "scouting_precision_bonus": (
            round(float(scout["scouting_accuracy"]) * 0.5, 1) if scout.get("scouting_accuracy") is not None else 0.0
        ),
        "injury_recovery_bonus": int(med["medical_expertise"]) // 3 if med.get("medical_expertise") is not None else 0,
    }


def _filled_skill(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    skill = int(value)
    if skill <= 0:
        return None
    return max(1, min(20, skill))


def _locked_catalog_staff(record: dict[str, Any], role_key: str) -> dict[str, Any] | None:
    rec_ids = {
        str(record.get(k) or "").strip().lower()
        for k in ("id", "staff_id", "manager_id")
        if str(record.get(k) or "").strip()
    }
    rec_name = str(record.get("name") or record.get("display_name") or "").strip().lower()
    for item in EXECUTIVE_STAFF_CATALOG:
        if not item.get("profile_locked") or item.get("role") != role_key:
            continue
        item_id = str(item.get("id") or "").strip().lower()
        item_name = str(item.get("name") or "").strip().lower()
        if (item_id and item_id in rec_ids) or (rec_name and rec_name == item_name):
            return item
    return None


def apply_staff_influence(record: dict[str, Any] | None, role_key: str) -> dict[str, Any]:
    """Attach a hired person's strength to the skill that role actually changes.

    A named hire with only a rating still moves youth intake, negotiation,
    or tactics. A vacant or default seat is left untouched, so the game keeps
    using the default development rating of 10.
    """
    if not isinstance(record, dict):
        return {}
    if record.get("use_default") or record.get("is_default") or record.get("is_vacant"):
        return record
    name = str(record.get("name") or record.get("display_name") or "").strip()
    if not name or name.lower() == "default":
        return record
    locked = _locked_catalog_staff(record, role_key)
    if locked:
        for key in (
            "preferred_formation",
            "preferred_formations",
            "tactics",
            "traits",
            "style",
            "mentality",
            "pressing",
            "philosophy_summary",
            "bio",
            "specialty",
            "nation",
            "nationality",
            "country_code",
            "youth_development",
            "tactical_flexibility",
            "tactical_quality",
            "influence",
            "uses_academy_players",
            "youth_age_max",
            "son_player_id",
            "son_player_name",
            "family_relationship",
            "profile_locked",
            "fallback_formation",
            "personal_agenda",
            "portrait_url",
        ):
            if locked.get(key) is not None:
                record[key] = list(locked[key]) if isinstance(locked[key], list) else locked[key]
        if not record.get("manager_id") and locked.get("id"):
            record["manager_id"] = locked["id"]
    if not record.get("personal_agenda"):
        agenda = (
            record.get("philosophy_summary")
            or record.get("philosophy")
            or record.get("specialty")
            or record.get("style")
            or record.get("bio")
        )
        if agenda:
            record["personal_agenda"] = str(agenda)
    if not record.get("portrait_url"):
        import zlib
        from app.owner_console.regen_staff_catalog import PORTRAIT_PUBLIC_PREFIX, portrait_filename
        from app.owner_console.staff_supply import _FEMALE_GIVEN_NAMES, _face_group_for_nation

        staff_name = str(record.get("name") or record.get("display_name") or "").strip()
        first_name = staff_name.split(" ", 1)[0] if staff_name else ""
        raw_gender = str(record.get("gender") or "").strip().lower()
        if raw_gender in {"female", "male"}:
            gender = raw_gender
        elif first_name in _FEMALE_GIVEN_NAMES or staff_name.lower().startswith("dr. amaka"):
            gender = "female"
        else:
            gender = "male"
        nation_str = str(record.get("nation") or record.get("nationality") or "")
        seed_idx = zlib.crc32(f"{staff_name}:{nation_str}:{gender}".encode("utf-8")) & 0xFFFFFFFF
        face_group = str(record.get("face_group") or "") or _face_group_for_nation(nation_str, seed_idx)
        record["portrait_url"] = f"{PORTRAIT_PUBLIC_PREFIX}/{portrait_filename(face_group, gender, seed_idx)}"
    rating_raw = record.get("rating")
    if rating_raw is None:
        rating_raw = record.get("gsi")
    rating = int(rating_raw) if isinstance(rating_raw, (int, float)) and not isinstance(rating_raw, bool) else None
    if rating is None:
        rarity = str(record.get("rarity") or "").strip().lower()
        derived = {"legendary": 18, "elite_active": 16, "rare": 13, "popular": 11}.get(rarity, 10)
    else:
        derived = max(8, min(20, int(round(rating / 5))))
    if rating is not None:
        record["rating"] = rating
    if role_key == "head_of_youth_development":
        record["youth_development"] = _filled_skill(record.get("youth_development")) or derived
    elif role_key == "general_manager":
        record["negotiation"] = _filled_skill(record.get("negotiation")) or derived
        record["commercial_acumen"] = _filled_skill(record.get("commercial_acumen")) or derived
    elif role_key == "first_team_manager":
        tactical = (
            _filled_skill(record.get("tactical_flexibility"))
            or _filled_skill(record.get("tactical_quality"))
            or _filled_skill(record.get("influence"))
            or derived
        )
        record["tactical_flexibility"] = tactical
        record["tactical_quality"] = _filled_skill(record.get("tactical_quality")) or tactical
        record["influence"] = _filled_skill(record.get("influence")) or tactical
        traits = record.get("traits") or record.get("catalog_traits") or []
        trait_names = {str(item).strip().lower() for item in traits} if isinstance(traits, list) else set()
        record["youth_development"] = _filled_skill(record.get("youth_development")) or (
            16 if "develops_young_players" in trait_names else max(8, derived - 2)
        )
    elif role_key == "chief_scout":
        record["scouting_accuracy"] = _filled_skill(record.get("scouting_accuracy")) or derived
    elif role_key == "medical_director":
        record["medical_expertise"] = _filled_skill(record.get("medical_expertise")) or derived
    return record


def squad_sheet(
    *,
    squad_status: Any = None,
    is_regen: bool = False,
    age: Any = None,
    minutes: Any = None,
    acquired_via: Any = None,
) -> str:
    """The sheet a player is on. A missing sheet is the first team.

    Academy is an explicit academy sheet, or a youth regen who arrived through
    the academy. A bought regen with no minutes is not on the academy list.
    """
    raw = str(squad_status or "").strip().lower()
    if raw == "reserve":
        return "reserve"
    if raw in {"academy", "u21"}:
        return "academy"
    if raw in {"first_team", "senior"}:
        return "first_team"
    if acquired_via == "academy" and is_regen:
        try:
            years = int(age)
        except (TypeError, ValueError):
            years = 99
        if years <= 18:
            return "academy"
    return "first_team"


def player_mood_profile(
    morale: Any,
    *,
    rating: Any = None,
    potential: Any = None,
    age: Any = None,
    minutes: Any = 0,
    loyalty: Any = None,
    ambition: Any = None,
    contract_tier: str | None = None,
    promised_minutes: bool = False,
    promoted: bool = False,
) -> dict[str, Any]:
    """Translate a player's morale into on-pitch performance and contract decisions."""
    base_rating = int(rating) if isinstance(rating, (int, float)) else None
    tier = str(contract_tier or "scholar").strip().lower()
    assured = bool(promised_minutes or promoted or (isinstance(loyalty, (int, float)) and int(loyalty) >= 16))
    if morale is None or isinstance(morale, bool):
        return {
            "mood_state": "Not filed",
            "performance_shift": 0.0,
            "effective_match_rating": base_rating,
            "performance_summary": "Mood not filed",
            "contract_stance": "signed_improved_youth" if tier == "improved_youth" else "open_to_terms",
            "contract_willing": True,
            "contract_cost_fan_coin": 1_000,
            "contract_morale_boost": 12,
            "contract_loyalty_boost": 2,
            "contract_pressure_drop": 25,
            "contract_summary": (
                "Improved youth contract active."
                if tier == "improved_youth"
                else "Standard 1,000 FAN youth contract terms."
            ),
        }

    m = int(clamp(int(round(float(morale))), 0, 100))
    if m >= 75:
        mood_state = "Thriving"
    elif m >= 55:
        mood_state = "Content"
    elif m >= 40:
        mood_state = "Restless"
    else:
        mood_state = "Unsettled"

    performance_shift = round((m - 60) * 0.12, 1)
    effective_match_rating = (
        int(clamp(int(round(base_rating + performance_shift)), 40, 99)) if base_rating is not None else None
    )
    sign = "+" if performance_shift > 0 else ""
    if mood_state == "Thriving":
        performance_summary = f"Thriving ({m}/100) · {sign}{performance_shift} match rating"
    elif mood_state == "Content":
        performance_summary = f"Content ({m}/100) · {sign}{performance_shift} match rating"
    elif mood_state == "Restless":
        performance_summary = f"Restless ({m}/100) · {performance_shift} match focus"
    else:
        performance_summary = f"Unsettled ({m}/100) · {performance_shift} match form"

    if tier == "improved_youth":
        contract_stance = "signed_improved_youth"
        contract_willing = True
        contract_cost_fan_coin = 1_000
        contract_morale_boost = 10
        contract_loyalty_boost = 2
        contract_pressure_drop = 20
        contract_summary = "Improved youth contract active · committed to the club."
    elif mood_state == "Thriving":
        contract_stance = "ready_to_commit"
        contract_willing = True
        contract_cost_fan_coin = 1_000
        contract_morale_boost = 12
        contract_loyalty_boost = 3
        contract_pressure_drop = 30
        contract_summary = "Thriving — eager to commit on a 1,000 FAN contract (+3 loyalty, +12 morale)."
    elif mood_state == "Content":
        contract_stance = "open_to_terms"
        contract_willing = True
        contract_cost_fan_coin = 1_000
        contract_morale_boost = 12
        contract_loyalty_boost = 2
        contract_pressure_drop = 25
        contract_summary = "Content — accepts standard 1,000 FAN contract terms (+2 loyalty, +12 morale)."
    elif mood_state == "Restless":
        contract_stance = "demands_reassurance"
        contract_willing = True
        contract_cost_fan_coin = 1_000 if assured else 1_250
        contract_morale_boost = 14
        contract_loyalty_boost = 1
        contract_pressure_drop = 20
        contract_summary = (
            "Restless — accepts 1,000 FAN because a first-team pathway is promised."
            if assured
            else "Restless — demands a 1,250 FAN reassurance package to commit (+14 morale)."
        )
    else:
        if assured:
            contract_stance = "conditional_retention"
            contract_willing = True
            contract_cost_fan_coin = 1_250
            contract_morale_boost = 15
            contract_loyalty_boost = 1
            contract_pressure_drop = 20
            contract_summary = (
                "Unsettled — signs a 1,250 FAN retention deal only because pathway assurances are in place."
            )
        else:
            contract_stance = "refuses_while_unsettled"
            contract_willing = False
            contract_cost_fan_coin = 1_500
            contract_morale_boost = 0
            contract_loyalty_boost = 0
            contract_pressure_drop = 0
            contract_summary = (
                "Unsettled — refuses a new contract until morale lifts or first-team minutes are promised."
            )

    return {
        "mood_state": mood_state,
        "performance_shift": performance_shift,
        "effective_match_rating": effective_match_rating,
        "performance_summary": performance_summary,
        "contract_stance": contract_stance,
        "contract_willing": contract_willing,
        "contract_cost_fan_coin": contract_cost_fan_coin,
        "contract_morale_boost": contract_morale_boost,
        "contract_loyalty_boost": contract_loyalty_boost,
        "contract_pressure_drop": contract_pressure_drop,
        "contract_summary": contract_summary,
    }


def manager_tactics(manager: dict[str, Any] | None, facilities: dict[str, Any] | None = None) -> dict[str, Any]:
    """The shape and match bonus the appointed manager plays.

    A tactical setup this manager has ratified wins. Otherwise their own
    formations win. A manager with no filed shape still has one, taken from
    their mentality, so the tactics screen and the match use the same plan.
    """
    record = apply_staff_influence(dict(manager or {}), "first_team_manager")
    setup = dict((facilities or {}).get("_tactical_setup") or {})
    named = str(record.get("name") or record.get("display_name") or "").strip()
    if not named or record.get("is_default") or record.get("is_vacant") or named.lower() == "default":
        return {
            "manager_name": "",
            "formation": str(setup.get("formation") or "4-3-3"),
            "formations": ["4-3-3"],
            "mentality": str(setup.get("mentality") or ""),
            "tactical_flexibility": None,
            "tactical_quality": None,
            "tactical_match_bonus": 0,
            "pressing": setup.get("pressing"),
        }
    profile = dict(record.get("personality_profile") or {})
    formations = [
        str(item) for item in (record.get("preferred_formations") or profile.get("preferred_formations") or []) if item
    ]
    if not formations and record.get("preferred_formation"):
        formations = [str(record["preferred_formation"])]
    mentality = str(
        record.get("tactical_preference")
        or record.get("mentality")
        or profile.get("preferred_tactical_philosophy")
        or ""
    )
    if not formations:
        text = mentality.lower()
        if any(word in text for word in ("defend", "low_block", "compact", "cautious")):
            formations = ["5-4-1", "5-3-2", "4-4-2"]
        elif any(word in text for word in ("attack", "press", "gegen", "wing")):
            formations = ["3-4-3", "4-3-3", "4-2-3-1"]
        else:
            formations = ["4-2-3-1", "4-3-3", "4-4-2"]
    manager_id = str(record.get("manager_id") or record.get("id") or "")
    stored = str(setup.get("formation") or "")
    ratified = (
        bool(manager_id)
        and str(setup.get("ratified_manager_id") or "") == manager_id
        and bool(stored)
        and (stored in formations or bool(setup.get("owner_override")))
    )
    effects = calculate_staff_effects({"first_team_manager": record})
    return {
        "manager_name": str(record.get("name") or record.get("display_name") or ""),
        "formation": stored if ratified else formations[0],
        "formations": formations,
        "fallback_formation": record.get("fallback_formation") or (formations[-1] if len(formations) > 1 else None),
        "mentality": mentality or str(setup.get("mentality") or ""),
        "style": record.get("style"),
        "philosophy_summary": record.get("philosophy_summary") or record.get("philosophy"),
        "tactical_flexibility": record.get("tactical_flexibility"),
        "tactical_quality": record.get("tactical_quality"),
        "youth_development": record.get("youth_development"),
        "influence": record.get("influence") or record.get("tactical_flexibility"),
        "tactical_match_bonus": effects["tactical_match_bonus"],
        "pressing": setup.get("pressing") or record.get("pressing"),
        "nation": record.get("nation") or record.get("nationality"),
        "son_player_id": record.get("son_player_id"),
        "son_player_name": record.get("son_player_name"),
        "family_relationship": record.get("family_relationship"),
    }


def manager_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = apply_staff_influence(dict(snapshot or {}), "first_team_manager")
    manager_id = str(snapshot.get("manager_id") or snapshot.get("id") or "")
    name = str(snapshot.get("display_name") or snapshot.get("name") or "").strip()
    profile: dict[str, Any] = {
        "manager_id": manager_id or None,
        "name": name,
        "is_default": manager_id == "gtex-staff-coach" or bool(snapshot.get("is_default")),
        "is_vacant": (not name) or manager_id == "gtex-staff-coach" or bool(snapshot.get("is_vacant")),
    }
    if snapshot.get("rarity") is not None:
        profile["rarity"] = snapshot["rarity"]
    if snapshot.get("mentality") is not None:
        profile["tactical_preference"] = snapshot["mentality"]
    elif snapshot.get("tactical_preference") is not None:
        profile["tactical_preference"] = snapshot["tactical_preference"]
    if snapshot.get("tactics"):
        profile["tactics"] = list(snapshot["tactics"])
    if snapshot.get("traits"):
        profile["catalog_traits"] = list(snapshot["traits"])
    if snapshot.get("philosophy_summary"):
        profile["philosophy"] = snapshot["philosophy_summary"]
    elif snapshot.get("philosophy"):
        profile["philosophy"] = snapshot["philosophy"]
    for key in (
        "temperament",
        "ambition",
        "loyalty",
        "discipline_style",
        "youth_development",
        "media_style",
        "transfer_preference",
        "tactical_quality",
        "tactical_flexibility",
        "influence",
        "pressing",
        "mood",
        "rating",
        "age",
        "gsi",
        "potential",
        "preferred_formation",
        "fallback_formation",
        "personal_agenda",
        "youth_age_max",
        "nation",
        "nationality",
        "country_code",
        "style",
        "son_player_id",
        "son_player_name",
        "family_relationship",
    ):
        if snapshot.get(key) is not None:
            profile[key] = snapshot[key]
    if snapshot.get("profile_locked"):
        profile["profile_locked"] = True
        if snapshot.get("tactical_flexibility") is not None and profile.get("tactical_quality") is None:
            profile["tactical_quality"] = int(snapshot["tactical_flexibility"])
        if snapshot.get("uses_academy_players"):
            profile["uses_academy_players"] = True
            profile["transfer_preference"] = "youth-first"
        if snapshot.get("preferred_formations"):
            profile["preferred_formations"] = list(snapshot["preferred_formations"])
    elif snapshot.get("preferred_formations"):
        profile["preferred_formations"] = list(snapshot["preferred_formations"])
    if snapshot.get("portrait_url"):
        profile["portrait_url"] = snapshot["portrait_url"]
    return profile


DEFAULT_MANAGER = {
    "manager_id": "gtex-staff-coach",
    "display_name": "Tunde Bakare (GTEX staff coach)",
    "rarity": "staff",
}


def regen_personality(rng: random.Random) -> dict[str, Any]:

    keys = (
        "ambition",
        "loyalty",
        "marketability",
        "professionalism",
        "adaptability",
        "growth_responsiveness",
        "environment_sensitivity",
    )

    personality = {key: rng.randint(4, 20) for key in keys}

    personality["transfer_pressure"] = 10

    personality["growth_buffer"] = 0.0

    return personality


def generate_regens(
    club_id: str,
    generation_key: int | str,
    academy_level: int,
    youth_skill: int,
    count: int,
    club_prestige: int = 45,
    hoyd_youth: int = 10,
    campus_intake_quality_pct: int = 0,
    campus_ceiling_bonus: int = 0,
    country_code: str | None = None,
) -> list[dict[str, Any]]:
    from app.services.regen_culture_name_pools import coherent_person_name

    rng = seeded("intake", club_id, generation_key)
    out = []
    quality_rating_boost = int(round(max(0, int(campus_intake_quality_pct)) / 5.0))
    ceiling_boost = max(0, int(campus_ceiling_bonus))
    max_pot_cap = min(98, 95 + min(3, ceiling_boost // 2))
    for index in range(count):
        prestige_boost = (int(club_prestige) - 40) // 10
        hoyd_boost = int(hoyd_youth) // 4
        base_pot = (
            58
            + academy_level * 4
            + youth_skill // 2
            + prestige_boost
            + hoyd_boost
            + ceiling_boost
            + rng.randint(-6, 10)
        )
        potential = int(clamp(base_pot, 55, max_pot_cap))
        name, culture = coherent_person_name(rng, country_code)
        position = rng.choice(POSITIONS[1:] if index else POSITIONS)
        age = rng.randint(16, 18)
        base_rating = rng.randint(44, 56) + quality_rating_boost
        rating = int(clamp(base_rating, 44, min(72, potential - 4)))
        personality = regen_personality(rng)
        personality["fitness"] = 96
        personality["campus_intake_quality_pct"] = int(campus_intake_quality_pct)
        personality["campus_ceiling_bonus"] = ceiling_boost
        personality["naming_culture"] = culture
        out.append(
            {
                "name": name,
                "position": position,
                "age": age,
                "rating": rating,
                "potential": potential,
                "personality": personality,
            }
        )
    return out


def rating_from_value(value_eur: float | None) -> int:

    value = max(float(value_eur or 0), 100_000.0)

    return int(clamp(20 + 7.5 * math.log10(value), 50, 88))


def price_from_value(value_eur: float | None) -> int:

    return int(clamp(float(value_eur or 0) / 10_000, 800, 25_000))


def calculate_gsi_price(
    current_gsi: int,
    potential_gsi: int,
    *,
    is_real: bool = True,
    is_legend: bool = False,
) -> float:
    """Official GTEX GSI pricing curve (250 GTX @ 90 Real, 500 @ 90 Regen, 900 @ 90 Legend, 60% discount <=70 GSI)."""

    cur = max(40, min(99, int(current_gsi)))

    pot = max(cur, min(99, int(potential_gsi)))

    eval_gsi = float(pot) if is_legend else (0.40 * cur + 0.60 * pot)

    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)

    if eval_gsi <= 70.0:

        base_price *= 0.40

    elif eval_gsi < 75.0:

        base_price *= 0.40 + 0.60 * ((eval_gsi - 70.0) / 5.0)

    if is_legend:

        return round(base_price * 3.6, 2)

    if not is_real:

        return round(base_price * 2.0, 2)

    return round(base_price, 2)


def market_quote(value_eur: float | None, value_credits: float | None) -> tuple[int, int]:
    """Fallback (price, rating) when explicit GSI / share_price_coin is absent."""

    if value_eur:

        rating = rating_from_value(value_eur)

        return max(15, int(round(calculate_gsi_price(rating, rating)))), rating

    credits = max(float(value_credits or 0), 0.0)

    rating = int(clamp(45 + 8.5 * math.log(credits + 1), 50, 92))

    price = int(round(credits)) if credits >= 15 else int(round(calculate_gsi_price(rating, rating)))

    return max(15, price), rating


def normalize_position(raw: str | None) -> str:
    from app.players.position_roles import position_family

    return position_family(raw)


def regen_value(rating: int, potential: int, age: int) -> int:

    return int(max(300, (rating - 40) * 60 + (potential - rating) * 45 + (19 - min(age, 19)) * 120))


def regen_growth(player: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Apply one world-day of growth. ctx: training, manager_youth, competition_quality, prestige, plus campus bonuses."""
    p = player["personality"]
    injured_days = max(0, int(player.get("injured_days", 0) or 0))
    minutes_factor = clamp(player["minutes"] / 540, 0, 1)
    morale_factor = 0.6 + player["morale"] / 125
    env = p.get("environment_sensitivity", 12) / 20
    facility_term = ctx["training"] / 5
    campus_train_pct = float(ctx.get("campus_training_efficiency_pct", 0))
    campus_dev_pct = float(ctx.get("campus_regen_dev_speed_pct", 0))
    campus_boost_term = clamp((campus_train_pct * 0.6 + campus_dev_pct * 1.0) / 100.0, 0.0, 0.85)
    drivers = {
        "facilities": round(0.35 * (facility_term + campus_boost_term * 0.5) * (0.6 + env), 3),
        "manager_quality": round(0.25 * ctx["manager_youth"] / 20, 3),
        "playing_time": round(0.2 * minutes_factor, 3),
        "competition_quality": round(0.1 * ctx["competition_quality"], 3),
        "club_prestige": round(0.1 * clamp(ctx["prestige"] / 60, 0, 1), 3),
    }
    if campus_boost_term > 0:
        drivers["campus_infrastructure"] = round(0.22 * campus_boost_term * (0.7 + env * 0.5), 3)
    responsiveness = p.get("growth_responsiveness", 12) / 12 * (0.7 + p.get("professionalism", 14) / 40)
    raw_gain = sum(drivers.values()) * responsiveness * morale_factor * 1.6
    if injured_days >= 7:
        rehab_growth_multiplier = 0.15
    elif injured_days > 0:
        rehab_growth_multiplier = 0.35
    else:
        rehab_growth_multiplier = 1.0
    if injured_days > 0:
        drivers = {k: round(v * rehab_growth_multiplier, 3) for k, v in drivers.items()}
    gain = raw_gain * rehab_growth_multiplier
    buffer = p.get("growth_buffer", 0.0) + gain
    points = 0 if injured_days > 0 else int(buffer)
    ceiling_bonus = int(ctx.get("campus_academy_ceiling_bonus", 0))
    effective_potential = min(
        98,
        int(player["potential"]) + max(0, ceiling_bonus - int(p.get("campus_ceiling_bonus", 0))),
    )
    headroom = effective_potential - player["rating"]
    points = max(0, min(points, headroom))
    if injured_days > 0:
        p["growth_buffer"] = round(min(0.95, buffer), 3)
    else:
        p["growth_buffer"] = round(buffer - int(buffer), 3)
    pressure = p.get("transfer_pressure", 10)
    pressure += (p.get("ambition", 14) - 10) * 0.8 * (1 - minutes_factor)
    if ctx["prestige"] < p.get("ambition", 14) * 3:
        pressure += 2
    if ctx["training"] <= 1 and p.get("environment_sensitivity", 12) >= 14:
        pressure += 3
    if campus_train_pct >= 25:
        pressure -= 1.5
    pressure -= p.get("loyalty", 12) * 0.25
    p["transfer_pressure"] = int(clamp(pressure, 0, 100))
    top_driver = max(drivers, key=drivers.get)
    weakest = min(drivers, key=drivers.get)
    explanation = (
        f"Growth restricted by injury rehabilitation ({injured_days}d remaining); light tactical study only."
        if injured_days > 0
        else f"Growth driven mostly by {top_driver.replace('_', ' ')}; held back by {weakest.replace('_', ' ')}."
    )
    return {
        "points": points,
        "effective_potential": effective_potential,
        "drivers": drivers,
        "top_driver": top_driver,
        "weakest_driver": weakest,
        "injury_rehab_restriction": injured_days > 0,
        "injured_days": injured_days,
        "rehab_growth_multiplier": rehab_growth_multiplier,
        "explanation": explanation,
    }


def club_strength(
    players: list[dict[str, Any]],
    manager: dict[str, Any],
    facilities: dict[str, Any],
    *,
    campus_effects: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.owner_console.autonomous_staff_engine import derive_manager_personality

    mgr_profile = derive_manager_personality(manager or {})
    commitments = dict((facilities or {}).get("_manager_matchday_commitments") or {})
    rejections = dict((facilities or {}).get("_manager_matchday_rejections") or {})
    exclusions = dict((facilities or {}).get("_manager_disciplinary_exclusions") or {})

    youth_commit = mgr_profile.get("youth_development_commitment")
    veteran_pref = mgr_profile.get("preference_for_experienced_players")
    youth_commit = int(youth_commit) if youth_commit is not None else None
    veteran_pref = int(veteran_pref) if veteran_pref is not None else None

    def _manager_selection_score(p: dict[str, Any]) -> float:
        pid = str(p.get("id") or "")
        base = float(p["rating"]) if p.get("rating") is not None else 0.0
        fitness_adj = (float(p["fitness"]) - 80.0) * 0.15 if p.get("fitness") is not None else 0.0
        morale_adj = (float(p["morale"]) - 65.0) * 0.15 if p.get("morale") is not None else 0.0
        age = int(p["age"]) if p.get("age") is not None else None
        age_adj = 0.0
        if age is not None and youth_commit is not None and veteran_pref is not None:
            if age <= 19 or p.get("is_academy"):
                age_adj += ((youth_commit - 50) / 50.0) * 6.5
                age_adj -= ((veteran_pref - 50) / 50.0) * 6.0
            elif age >= 27:
                age_adj += ((veteran_pref - 50) / 50.0) * 4.5
        comm = commitments.get(pid)
        if comm and comm.get("matchday_role") == "starting_xi":
            age_adj += 30.0
        elif pid in rejections:
            age_adj -= 25.0
        return base + fitness_adj + morale_adj + age_adj

    healthy = [
        p for p in players if int(p.get("injured_days", 0) or 0) <= 0 and str(p.get("id") or "") not in exclusions
    ]
    if len(healthy) < 11:
        healthy = [p for p in players if int(p.get("injured_days", 0) or 0) <= 0] or list(players)

    def _sheet(p: dict[str, Any]) -> str:
        return squad_sheet(
            squad_status=p.get("squad_status"),
            is_regen=bool(p.get("is_regen")),
            age=p.get("age"),
            minutes=p.get("minutes"),
            acquired_via=p.get("acquired_via"),
        )

    def _is_gk(p: dict[str, Any]) -> bool:
        pos = str(p.get("position") or "").lower()
        return pos in {"gk", "goalkeeper"} or pos.startswith("goal")

    by_id = {str(p.get("id") or ""): p for p in healthy}
    filed_ids = [
        str(pid)
        for pid in (((facilities or {}).get("_last_manager_matchday_selection") or {}).get("starting_xi_ids") or [])
    ]
    committed_starters = {
        pid
        for pid, comm in commitments.items()
        if isinstance(comm, dict) and comm.get("matchday_role") == "starting_xi"
    }
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _take(player: dict[str, Any]) -> None:
        pid = str(player.get("id") or "")
        if not pid or pid in seen or len(chosen) >= 11:
            return
        chosen.append(player)
        seen.add(pid)

    for pid in filed_ids:
        player = by_id.get(pid)
        if player is None:
            continue
        if _sheet(player) == "academy" and pid not in committed_starters:
            continue
        _take(player)
    pool = [p for p in healthy if _sheet(p) == "first_team"] or [p for p in healthy if _sheet(p) != "academy"]
    ranked = sorted(pool, key=_manager_selection_score, reverse=True)
    if not any(_is_gk(player) for player in chosen):
        keeper = next((player for player in ranked if _is_gk(player)), None)
        if keeper is not None:
            chosen.insert(0, keeper)
            seen.add(str(keeper.get("id") or ""))
            if len(chosen) > 11:
                dropped = chosen.pop()
                seen.discard(str(dropped.get("id") or ""))
    for player in ranked:
        _take(player)
    if len(chosen) < 11:
        for player in sorted(healthy, key=_manager_selection_score, reverse=True):
            if _sheet(player) == "academy":
                continue
            _take(player)
    fit = chosen[:11]
    if not fit:
        return {
            "strength": None,
            "xi": [],
            "bench": [],
            "promised_sub_ids": [],
            "formation": None,
            "pressing": None,
            "tempo": None,
            "width": None,
            "defensive_line": None,
            "tactical_quality": None,
            "avg_rating": None,
            "avg_morale": None,
            "avg_fitness": None,
        }
    starter_ids = {p["id"] for p in fit}

    def _promised_bench(player: dict[str, Any]) -> bool:
        comm = commitments.get(str(player.get("id") or ""))
        return bool(comm and comm.get("matchday_role") in ("matchday_squad_bench", "substitute_impact"))

    remaining = [
        p
        for p in sorted(healthy, key=_manager_selection_score, reverse=True)
        if p["id"] not in starter_ids and (_sheet(p) != "academy" or _promised_bench(p))
    ]
    bench: list[dict[str, Any]] = []
    promised_sub_ids: list[str] = []
    for p in remaining:
        comm = commitments.get(str(p.get("id") or ""))
        if comm and comm.get("matchday_role") in ("matchday_squad_bench", "substitute_impact"):
            bench.append(p)
            promised_sub_ids.append(p["id"])
    for p in remaining:
        if p not in bench and _sheet(p) == "reserve" and len(bench) < 7:
            bench.append(p)
    for p in remaining:
        if p not in bench and len(bench) < 7:
            bench.append(p)

    ratings = [float(p["rating"]) for p in fit if p.get("rating") is not None]
    morales = [float(p["morale"]) for p in fit if p.get("morale") is not None]
    fitnesses = [float(p["fitness"]) for p in fit if p.get("fitness") is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    avg_morale = sum(morales) / len(morales) if morales else None
    avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else None
    depth_penalty = (11 - len(fit)) * 2.5
    strength = avg_rating
    tactics = manager_tactics(manager, facilities)
    if strength is not None:
        bonus = tactics.get("tactical_match_bonus")
        if bonus is not None:
            strength += float(bonus)
        elif manager.get("tactical_quality") is not None:
            strength += float(manager["tactical_quality"]) * 0.35
        if avg_morale is not None:
            strength += (avg_morale - 60) * 0.12
        if facilities.get("medical") is not None:
            strength += int(facilities["medical"]) * 0.4
        cohesion = (campus_effects or {}).get("tactical_cohesion_pct")
        if cohesion is not None:
            strength += float(cohesion) * 0.08
        if avg_fitness is not None:
            strength += (avg_fitness - 85.0) * 0.06
        strength -= depth_penalty
    from app.owner_console import autonomous_staff_engine

    mentality_authority = autonomous_staff_engine.resolve_manager_mentality_decision(
        manager,
        facilities_json=facilities,
    )
    formation = tactics.get("formation")
    pressing = int(mgr_profile["pressing_philosophy"]) if mgr_profile.get("pressing_philosophy") is not None else None
    attack = (
        int(mgr_profile["attacking_vs_defensive"]) if mgr_profile.get("attacking_vs_defensive") is not None else None
    )
    possession = (
        int(mgr_profile["possession_vs_direct"]) if mgr_profile.get("possession_vs_direct") is not None else None
    )
    raw_quality = manager.get("tactical_quality")
    if raw_quality is None:
        tactical_quality = None
    else:
        raw_quality_int = int(raw_quality)
        tactical_quality = int(clamp(raw_quality_int * 5 if raw_quality_int <= 20 else raw_quality_int, 1, 100))
    width = None
    if possession is not None:
        width = 68 if possession <= 40 else 46 if possession >= 70 else 55
    return {
        "strength": round(strength, 2) if strength is not None else None,
        "xi": [p["id"] for p in fit],
        "bench": [p["id"] for p in bench],
        "promised_sub_ids": promised_sub_ids,
        "formation": formation,
        "pressing": pressing,
        "tempo": attack,
        "width": width,
        "defensive_line": attack,
        "philosophy": str(mgr_profile.get("preferred_tactical_philosophy") or manager.get("philosophy") or ""),
        "tactical_quality": tactical_quality,
        "tactical_match_bonus": tactics.get("tactical_match_bonus"),
        "tactics": tactics,
        "manager_mentality": mentality_authority["manager_preferred_mentality"],
        "mentality_authority": mentality_authority,
        "avg_rating": round(avg_rating, 1) if avg_rating is not None else None,
        "avg_morale": round(avg_morale, 1) if avg_morale is not None else None,
        "avg_fitness": round(avg_fitness, 1) if avg_fitness is not None else None,
    }


def calculate_match_attendance(
    *,
    fans: int,
    prestige: int,
    stadium_level: int = 1,
    campus_effects: dict[str, Any] | None = None,
    gf: int = 0,
    ga: int = 0,
) -> dict[str, Any]:
    """Calculate authoritative home match attendance (hard-capped by operational stadium capacity) and gate receipts."""
    eff = dict(campus_effects or {})
    raw_capacity = eff.get("stadium_capacity")
    if raw_capacity is None:
        return {
            "attendance": 0,
            "stadium_capacity": None,
            "raw_demand": 0,
            "capacity_utilization_pct": None,
            "sold_out": False,
            "gate_receipts_gtex": 0,
        }
    stadium_capacity = max(1_000, int(raw_capacity))
    matchday_rev_pct = (
        int(eff["matchday_revenue_bonus_pct"]) if eff.get("matchday_revenue_bonus_pct") is not None else 0
    )
    vip_hospitality_gtex = int(eff.get("vip_hospitality_flat_gtex", 0))
    commercial_growth_pct = int(eff.get("commercial_growth_bonus_pct", 0))
    home_advantage_bonus = int(eff.get("home_advantage_bonus", 0))
    stad_lvl = max(1, int(stadium_level))

    core_supporter_turnout = int(round(max(200, int(fans)) * (2.2 + stad_lvl * 0.25)))
    prestige_draw = int(max(10, int(prestige)) * 110)
    infra_draw = (
        int(round(stadium_capacity * 0.25))
        + int(matchday_rev_pct * 85)
        + int(home_advantage_bonus * 180)
        + (450 if vip_hospitality_gtex > 0 else 0)
    )
    match_spectacle = max(0, (int(gf) + int(ga)) * 90 + (200 if int(gf) > int(ga) else 0))

    raw_demand = max(200, core_supporter_turnout + prestige_draw + infra_draw + match_spectacle)
    attendance = min(stadium_capacity, raw_demand)
    capacity_utilization_pct = round((attendance / stadium_capacity) * 100.0, 1)

    ticket_yield_per_fan = 0.055 * (1.0 + (stad_lvl - 1) * 0.15)
    revenue_multiplier = 1.0 + (matchday_rev_pct + commercial_growth_pct * 0.5) / 100.0
    raw_gate = attendance * ticket_yield_per_fan * revenue_multiplier + vip_hospitality_gtex
    gate_receipts_gtex = max(50, int(round(raw_gate)))

    return {
        "attendance": attendance,
        "stadium_capacity": stadium_capacity,
        "raw_demand": raw_demand,
        "capacity_utilization_pct": capacity_utilization_pct,
        "sold_out": attendance >= stadium_capacity,
        "gate_receipts_gtex": gate_receipts_gtex,
    }


def calculate_daily_training_workload_minutes(
    player: dict[str, Any],
    *,
    is_starter: bool,
    mentality: str = "balanced",
    training_level: int = 1,
) -> dict[str, Any]:
    """Deterministic daily training workload model based on squad role, cumulative match minutes, fitness, and mentality."""
    minutes_played = max(0, int(player.get("minutes", 0) or 0))
    pers = dict(player.get("personality") or {})
    fitness = int(clamp(int(pers.get("fitness", player.get("fitness", 95))), 0, 100))
    professionalism = int(pers.get("professionalism", 12))
    age = int(player.get("age", 24) or 24)

    if is_starter and minutes_played >= 180:
        base_minutes = 55
    elif is_starter or minutes_played >= 90:
        base_minutes = 45
    elif minutes_played > 0:
        base_minutes = 35
    else:
        base_minutes = 25

    mentality_delta = 8 if mentality == "attacking" else (-5 if mentality == "defensive" else 0)
    fatigue_delta = 6 if (fitness < 60 and mentality == "attacking") else (-6 if fitness < 60 else 0)
    prof_delta = -3 if professionalism >= 16 else (2 if professionalism <= 7 else 0)
    age_delta = 4 if age >= 31 else 0
    facility_delta = 2 if int(training_level) >= 3 else 0

    minutes_load = int(
        clamp(base_minutes + mentality_delta + fatigue_delta + prof_delta + age_delta + facility_delta, 15, 85)
    )
    workload_tier = "high_intensity" if minutes_load >= 55 else "standard" if minutes_load >= 40 else "light_recovery"
    return {
        "minutes_load": minutes_load,
        "workload_tier": workload_tier,
        "is_starter": bool(is_starter),
    }


def evaluate_player_injury_risk(
    *,
    club_id: str,
    player_id: str,
    context_key: str | int,
    fitness: int,
    minutes_load: int = 90,
    mentality: str = "balanced",
    medical_level: int = 1,
    med_director_expertise: int = 10,
    campus_injury_reduction_pct: int = 0,
) -> dict[str, Any]:
    """Authoritative injury-incidence and severity model consumed by matchday and world-clock simulation."""
    fit_val = int(clamp(int(fitness), 0, 100))
    load_clamped = int(clamp(int(minutes_load), 10, 120))
    base_hazard = round(0.0025 + (load_clamped / 90.0) * 0.0425, 4)
    fatigue_overload = max(0, 75 - fit_val) * 0.011
    mentality_hazard = 0.025 if mentality == "attacking" else 0.0
    staff_facility_mitigation = (max(1, int(medical_level)) - 1) * 0.015 + max(
        0, int(med_director_expertise) - 10
    ) * 0.004
    unmitigated_risk = clamp(
        base_hazard + fatigue_overload + mentality_hazard - staff_facility_mitigation,
        0.01,
        0.85,
    )
    reduction_pct = int(clamp(int(campus_injury_reduction_pct), 0, 65))
    reduction_factor = 1.0 - (reduction_pct / 100.0)
    effective_risk = round(unmitigated_risk * reduction_factor, 4)

    rng = seeded("injury_incidence", club_id, player_id, str(context_key))
    roll = round(rng.random(), 4)
    injured = bool(fit_val < 70 and roll < effective_risk)
    injured_days = 0
    injury_type = None
    if injured:
        raw_days = 5 + max(0, (70 - fit_val) // 5) + rng.randint(0, 4)
        injured_days = max(1, int(round(raw_days * reduction_factor)))
        if injured_days >= 10:
            injury_type = "Severe Ankle Ligament Sprain"
        elif injured_days >= 7:
            injury_type = "Hamstring Grade-2 Tear"
        elif injured_days >= 4:
            injury_type = "Quadriceps Strain"
        else:
            injury_type = "Calf Contusion / Dead Leg"

    return {
        "minutes_load": load_clamped,
        "unmitigated_risk": round(unmitigated_risk, 4),
        "injury_reduction_pct": reduction_pct,
        "effective_risk": effective_risk,
        "roll": roll,
        "injured": injured,
        "injured_days": injured_days,
        "injury_type": injury_type,
    }


MENTALITY = {"defensive": (0.78, 0.7), "balanced": (1.0, 1.0), "attacking": (1.25, 1.22)}


GOAL_LINES = [
    "{team} break at pace and {scorer} finishes low into the corner!",
    "{scorer} rises highest from the corner. {team} score!",
    "A sweeping move from {team} ends with {scorer} tapping in.",
    "{scorer} curls one from the edge of the box. What a strike for {team}!",
]

CHANCE_LINES = [
    "{team} carve an opening but the shot flashes wide.",
    "Big save! {team} denied from close range.",
    "{team} hit the woodwork. The home end holds its breath.",
    "{team} press high and win it back in a dangerous area.",
]

FLAVOUR_LINES = [
    "The stadium roar builds as {team} push forward.",
    "Yellow card for a cynical challenge. {team} lose their cool.",
    "{team} slow the tempo and keep the ball.",
    "Tactical switch on the touchline; {team} change shape.",
]


def _poisson(rng: random.Random, lam: float) -> int:

    limit, k, p = math.exp(-lam), 0, 1.0

    while True:

        p *= rng.random()

        if p <= limit:

            return k

        k += 1


def _playable_formation(formation: str) -> str:
    parts = [part for part in str(formation or "").split("-") if part.isdigit()]
    if len(parts) >= 2 and sum(int(part) for part in parts) == 10:
        return "-".join(parts)
    return "4-3-3"


def _roles_for_formation(formation: str) -> list[Any]:
    from app.match_engine.simulation.models import PlayerRole

    parts = [int(part) for part in _playable_formation(formation).split("-")]
    defenders, forwards = parts[0], parts[-1]
    midfielders = sum(parts[1:-1])
    return (
        [PlayerRole.GOALKEEPER]
        + ([PlayerRole.DEFENDER] * defenders)
        + ([PlayerRole.MIDFIELDER] * midfielders)
        + ([PlayerRole.FORWARD] * forwards)
    )


def simulate_match(seed: str, home: dict[str, Any], away: dict[str, Any]) -> dict[str, Any]:
    """Simulate a match using the canonical MatchSimulationService exclusively.



    home/away: name, strength, mentality, scorers(list[str]), manager(dict|None).

    """

    from app.match_engine.schemas import (
        MatchCompetitionContextInput,
        MatchPlayerInput,
        MatchSimulationRequest,
        MatchTeamInput,
        TeamTacticalPlanInput,
    )

    from app.match_engine.services.match_simulation_service import MatchSimulationService

    from app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle

    seed_int = int(hashlib.sha256(str(seed).encode()).hexdigest()[:8], 16)

    def _build_side_input(side_id: str, side_data: dict[str, Any]) -> MatchTeamInput:

        mentality = side_data.get("mentality", "balanced")

        style = {
            "attacking": TacticalStyle.ATTACKING,
            "defensive": TacticalStyle.DEFENSIVE,
        }.get(mentality, TacticalStyle.BALANCED)

        raw_strength = side_data.get("strength")
        if raw_strength is None:
            raise ValueError("match strength was not filed")
        base_rating = int(clamp(float(raw_strength), 40, 95))
        formation = _playable_formation(str(side_data.get("formation") or "4-3-3"))
        roles = _roles_for_formation(formation)

        scorers = list(side_data.get("scorers") or [])
        xi_players = [p for p in (side_data.get("xi_players") or []) if isinstance(p, dict)]
        avg_side_morale = (
            int(clamp(int(round(float(side_data["avg_morale"]))), 1, 100))
            if side_data.get("avg_morale") is not None
            else None
        )

        def _player_for_slot(idx: int, slot_role: Any) -> dict[str, Any] | None:
            if idx < len(xi_players):
                return xi_players[idx]
            return None

        starters = []

        for i, role in enumerate(roles):
            slot_player = _player_for_slot(i, role)
            p_name = (
                str(slot_player.get("name") or "")
                if slot_player and slot_player.get("name")
                else (scorers[i % len(scorers)] if scorers else f"{side_data.get('name', 'Team')} Player {i+1}")
            )
            p_id = str(slot_player.get("id") or f"{side_id}-player-{i+1}") if slot_player else f"{side_id}-player-{i+1}"
            p_morale = (
                int(clamp(int(round(float(slot_player["morale"]))), 1, 100))
                if slot_player and slot_player.get("morale") is not None
                else avg_side_morale
            )
            p_fitness = (
                int(clamp(int(round(float(slot_player["fitness"]))), 1, 100))
                if slot_player and slot_player.get("fitness") is not None
                else None
            )
            raw_player_rating = (
                int(slot_player["rating"])
                if slot_player and isinstance(slot_player.get("rating"), (int, float))
                else base_rating
            )
            mood_eval = player_mood_profile(p_morale, rating=raw_player_rating)
            p_overall = int(clamp(int(mood_eval["effective_match_rating"] or base_rating), 40, 99))

            starters.append(
                MatchPlayerInput(
                    player_id=p_id,
                    player_name=p_name,
                    role=role,
                    overall=p_overall,
                    morale=p_morale,
                    motivation=p_morale,
                    fitness=p_fitness,
                    goalkeeping=p_overall if role == PlayerRole.GOALKEEPER else None,
                )
            )

        bench = [
            MatchPlayerInput(
                player_id=f"{side_id}-sub-1",
                player_name=f"{side_data.get('name', 'Team')} Sub 1",
                role=PlayerRole.MIDFIELDER,
                overall=max(40, base_rating - 2),
            )
        ]

        return MatchTeamInput(
            team_id=side_id,
            team_name=str(side_data.get("name", side_id)),
            formation=formation,
            tactics=TeamTacticalPlanInput(
                style=style,
                mentality=style,
                **{
                    key: int(clamp(int(side_data[key]), 0 if key != "tactical_quality" else 1, 100))
                    for key in ("pressing", "tempo", "width", "defensive_line", "tactical_quality")
                    if side_data.get(key) is not None
                },
            ),
            starters=starters,
            bench=bench,
        )

    req = MatchSimulationRequest(
        match_id=str(seed),
        seed=seed_int,
        competition=MatchCompetitionContextInput(
            competition_type=MatchCompetitionType.LEAGUE,
            stage="Round",
        ),
        home_team=_build_side_input("home", home),
        away_team=_build_side_input("away", away),
    )

    service = MatchSimulationService()

    replay = service.build_replay_payload(req)

    hg = replay.summary.home_score

    ag = replay.summary.away_score

    events = [
        {"minute": 0, "type": "kickoff", "team": None, "text": f"Kick-off between {home['name']} and {away['name']}."}
    ]

    score = {"home": 0, "away": 0}

    for ev in replay.timeline.events:

        ev_type = getattr(ev.event_type, "value", str(ev.event_type))

        side_key = "home" if ev.team_id == "home" else ("away" if ev.team_id == "away" else None)

        team_name = home["name"] if side_key == "home" else away["name"]

        if ev_type in {"goal", "penalty_goal", "penalty_scored"}:

            if side_key:

                score[side_key] += 1

            scorer = ev.primary_player.player_name if ev.primary_player else f"{team_name} Scorer"

            events.append(
                {
                    "minute": ev.minute,
                    "type": "goal",
                    "team": side_key,
                    "scorer": scorer,
                    "score": f"{score['home']}-{score['away']}",
                    "text": ev.commentary or f"{scorer} scores for {team_name}!",
                }
            )

        elif ev_type in {"shot_missed", "shot_saved", "shot_blocked"}:

            events.append(
                {
                    "minute": ev.minute,
                    "type": "chance",
                    "team": side_key,
                    "text": ev.commentary or f"Chance for {team_name}.",
                }
            )

        elif ev_type in {"yellow_card", "red_card"}:

            events.append(
                {
                    "minute": ev.minute,
                    "type": "flavour",
                    "team": side_key,
                    "text": ev.commentary or f"Card shown for {team_name}.",
                }
            )

    events.append({"minute": 45, "type": "half", "team": None, "text": "Half-time whistle."})

    events.append(
        {"minute": 90, "type": "full", "team": None, "text": f"Full-time: {home['name']} {hg}-{ag} {away['name']}."}
    )

    events.sort(key=lambda e: (e["minute"], e["type"] == "full"))

    gap = (home["strength"] + 2.5 - away["strength"]) / 11

    momentum = []

    for block in range(18):

        start, end = block * 5, block * 5 + 5

        weight = (
            50
            + (gap * 10)
            + sum(
                (8 if e.get("team") == "home" else -8)
                for e in events
                if start <= e.get("minute", 0) < end and e.get("team")
            )
        )

        momentum.append(int(clamp(weight, 5, 95)))

    result = {
        "home_goals": hg,
        "away_goals": ag,
        "events": events,
        "momentum": momentum,
        "lambda": [
            round(replay.summary.home_stats.shots * 0.15 + 0.5, 2),
            round(replay.summary.away_stats.shots * 0.15 + 0.5, 2),
        ],
        "gap": round(gap, 3),
    }

    if replay.summary.decided_by_penalties:

        result["penalty_winner"] = "home" if replay.summary.winner_team_id == "home" else "away"

    return result


def manager_reaction(manager: dict[str, Any], result: str) -> str:

    temperament = manager.get("temperament", "calm")

    name = manager.get("name", "The manager")

    lines = {
        ("win", "fiery"): "punches the air and sprints down the touchline.",
        ("win", "calm"): "applauds the fans and heads straight for the tunnel.",
        ("loss", "fiery"): "kicks a water bottle and refuses the post-match handshake.",
        ("loss", "volatile"): "storms into the dressing room. Expect a tense week.",
        ("loss", "calm"): "is measured in defeat: 'We learn and we go again.'",
        ("draw", "demanding"): "says a point is not good enough for this club.",
    }

    return f"{name} " + lines.get(
        (result, temperament),
        {
            "win": "is pleased with the response.",
            "loss": "wants answers from the board and the squad.",
            "draw": "calls it a fair result.",
        }[result],
    )


def explain_match(
    sim: dict[str, Any], club_side: str, home: dict[str, Any], away: dict[str, Any], extras: dict[str, Any]
) -> dict[str, Any]:

    mine, theirs = (home, away) if club_side == "home" else (away, home)

    my_goals = sim["home_goals"] if club_side == "home" else sim["away_goals"]

    their_goals = sim["away_goals"] if club_side == "home" else sim["home_goals"]

    result = "win" if my_goals > their_goals else "loss" if my_goals < their_goals else "draw"

    diff = round(mine["strength"] - theirs["strength"], 1)

    factors = [
        {
            "factor": "Squad strength gap",
            "value": f"{'+' if diff >= 0 else ''}{diff}",
            "impact": "positive" if diff > 0 else "negative" if diff < 0 else "neutral",
        },
        {
            "factor": "Mentality",
            "value": mine["mentality"],
            "impact": "risk" if mine["mentality"] == "attacking" else "neutral",
        },
        {
            "factor": "Home advantage",
            "value": "Yes" if club_side == "home" else "No",
            "impact": "positive" if club_side == "home" else "neutral",
        },
        {
            "factor": "Average morale",
            "value": str(extras.get("avg_morale", "-")),
            "impact": "positive" if float(extras.get("avg_morale", 60)) >= 65 else "negative",
        },
    ]

    next_actions = []

    if result != "win" and diff < 0:

        next_actions.append("Strengthen the starting XI in Market & Transfers")

    if float(extras.get("avg_morale", 60)) < 60:

        next_actions.append("Resolve morale issues in the Owner Inbox")

    if extras.get("training", 1) <= 2:

        next_actions.append("Upgrade the training ground to accelerate player growth")

    if not next_actions:

        next_actions.append("Keep the squad settled and enter a higher-tier competition")

    headline = {
        "win": f"{mine['name']} beat {theirs['name']} {my_goals}-{their_goals}",
        "loss": f"{mine['name']} fall {my_goals}-{their_goals} to {theirs['name']}",
        "draw": f"{mine['name']} and {theirs['name']} share the points",
    }[result]

    return {"result": result, "headline": headline, "why": factors, "next_actions": next_actions}


def generate_sponsor_offers(
    club_id: str,
    prestige: int = 35,
    gm_negotiation: int = 12,
    commercial_level: int = 1,
    campus_sponsor_bonus_pct: int = 0,
) -> list[dict[str, Any]]:
    """Generate 3 competing seasonal sponsor offers presented by the General Manager, gated by club prestige."""
    base_nego_mult = 1.0 + max(0, int(gm_negotiation) - 10) * 0.04 + max(0, int(commercial_level) - 1) * 0.08
    campus_payout_mult = 1.0 + max(0, int(campus_sponsor_bonus_pct)) / 200.0
    # The displayed per-match offer includes the current campus uplift, but the
    # stored deal keeps its negotiated base. Match settlement applies the live
    # campus uplift exactly once, so the same benefit is not compounded.
    nego_mult = base_nego_mult + max(0, int(campus_sponsor_bonus_pct)) / 100.0

    prestige_val = int(prestige)

    base_offers = [
        {
            "offer_id": "sponsor_guaranteed_airways",
            "sponsor_name": "Aether Global Airways",
            "slot": "Front of Shirt",
            "strategy_profile": "guaranteed_heavy",
            "upfront_signing_bonus_gtex": int(round(1_200 * nego_mult, -1)),
            "per_match_gross_gtex": int(round(int(round(280 * base_nego_mult, -1)) * campus_payout_mult)),
            "base_per_match_gross_gtex": int(round(280 * base_nego_mult, -1)),
            "win_bonus_clause_gtex": int(round(80 * nego_mult, -1)),
            "matches_duration": 10,
            "min_prestige_required": 20,
            "gm_recommendation": "High guaranteed upfront liquidity with reliable per-match baseline; ideal for stabilizing club cash flow.",
        },
        {
            "offer_id": "sponsor_balanced_chronos",
            "sponsor_name": "Chronos Precision Labs",
            "slot": "Stadium Naming & Kit Sleeve",
            "strategy_profile": "balanced",
            "upfront_signing_bonus_gtex": int(round(900 * nego_mult, -1)),
            "per_match_gross_gtex": int(round(int(round(360 * base_nego_mult, -1)) * campus_payout_mult)),
            "base_per_match_gross_gtex": int(round(360 * base_nego_mult, -1)),
            "win_bonus_clause_gtex": int(round(220 * nego_mult, -1)),
            "matches_duration": 10,
            "min_prestige_required": 40,
            "gm_recommendation": "Balanced structure pairing a solid signing bonus with strong matchday and victory incentives.",
        },
        {
            "offer_id": "sponsor_superclub_sovereign",
            "sponsor_name": "Sovereign Quantum Group",
            "slot": "Global Principal Partner",
            "strategy_profile": "trophy_incentive_heavy",
            "upfront_signing_bonus_gtex": int(round(1_800 * nego_mult, -1)),
            "per_match_gross_gtex": int(round(int(round(520 * base_nego_mult, -1)) * campus_payout_mult)),
            "base_per_match_gross_gtex": int(round(520 * base_nego_mult, -1)),
            "win_bonus_clause_gtex": int(round(480 * nego_mult, -1)),
            "matches_duration": 10,
            "min_prestige_required": 65,
            "gm_recommendation": "Marquee superclub contract with massive victory bonus clauses. Requires Tier 2+ Prestige or elite GM negotiation.",
        },
    ]

    out: list[dict[str, Any]] = []

    for offer in base_offers:

        min_p = int(offer["min_prestige_required"])

        effective_min_p = max(15, min_p - (10 if int(gm_negotiation) >= 17 else 0))

        locked = prestige_val < effective_min_p

        out.append(
            {
                **offer,
                "min_prestige_required": effective_min_p,
                "locked": locked,
            }
        )

    return out


def generate_boardroom_dilemma(
    club_id: str,
    world_day: int,
    gm_name: str = "General Manager",
    manager_name: str = "First-Team Manager",
    hoyd_name: str = "Head of Youth Development",
) -> dict[str, Any]:
    """Generate an interactive multi-choice boardroom dilemma for the Daily AI Owner Briefing."""

    templates = [
        {
            "key": "wage_cap_vs_target",
            "title": "Executive Clash: Wage Cap Discipline vs. Marquee Reinforcements",
            "conflict_summary": (
                f"{manager_name} (First-Team Manager) is demanding immediate wage-structure flexibility to keep senior stars motivated, "
                f"while {gm_name} (General Manager) insists on enforcing strict commercial cost controls to protect the club treasury."
            ),
            "role_a": f"General Manager ({gm_name})",
            "role_b": f"First-Team Manager ({manager_name})",
            "choices": [
                {
                    "choice_id": "enforce_gm_wage_cap",
                    "label": "Enforce GM's Wage Cap",
                    "summary": f"Back {gm_name}'s financial discipline and rebate commercial overhead into the club treasury.",
                    "backed_role": "general_manager",
                    "effects_preview": "+500 GTEX Treasury Efficiency · +8 GM Mood · -4 First-Team Manager Mood",
                },
                {
                    "choice_id": "back_manager_target",
                    "label": "Back Manager's Squad Priority",
                    "summary": f"Authorize {manager_name}'s dressing-room incentives to energize the senior squad.",
                    "backed_role": "first_team_manager",
                    "effects_preview": "+6 Squad Morale · +10 First-Team Manager Mood · -4 GM Mood",
                },
                {
                    "choice_id": "owner_performance_compromise",
                    "label": "Fund Performance-Linked Clause",
                    "summary": "Inject 400 GTEX into a performance bonus pool that satisfies both executives and boosts club prestige.",
                    "backed_role": "compromise",
                    "effects_preview": "-400 GTEX Club Cash · +5 GM & Manager Mood · +4 Squad Morale · +1 Prestige",
                },
            ],
        },
        {
            "key": "academy_pathway_vs_veterans",
            "title": "Boardroom Debate: Academy Regen Pathway vs. Veteran Certainty",
            "conflict_summary": (
                f"{hoyd_name} (Head of Youth Development) argues our top academy prospects need guaranteed match minutes now, "
                f"whereas {manager_name} (First-Team Manager) wants to rely on seasoned starters for immediate results."
            ),
            "role_a": f"Head of Youth Development ({hoyd_name})",
            "role_b": f"First-Team Manager ({manager_name})",
            "choices": [
                {
                    "choice_id": "mandate_youth_minutes",
                    "label": "Mandate Youth Pathway Minutes",
                    "summary": f"Back {hoyd_name} and fast-track academy regens into senior matchday contention.",
                    "backed_role": "head_of_youth_development",
                    "effects_preview": "+10 HOYD Mood · +8 Regen Morale & Loyalty · +1 Prestige · -3 Manager Mood",
                },
                {
                    "choice_id": "prioritize_senior_results",
                    "label": "Prioritize Immediate Senior Results",
                    "summary": f"Give {manager_name} full autonomy to field the strongest veteran XI without youth quotas.",
                    "backed_role": "first_team_manager",
                    "effects_preview": "+8 First-Team Manager Mood · +5 Senior Squad Morale · -4 HOYD Mood",
                },
                {
                    "choice_id": "hybrid_cup_rotation",
                    "label": "Establish Cup & Showcase Rotation",
                    "summary": "Create a structured rotation policy aligning the HOYD and First-Team Manager.",
                    "backed_role": "compromise",
                    "effects_preview": "+5 HOYD & Manager Mood · +4 Squad Morale · +1 Prestige",
                },
            ],
        },
    ]

    templates.extend(
        [
            {
                "key": "super_agent_ultimatum",
                "title": "Midnight Ultimatum: Super-Agent Threatens Rival Transfer Leak",
                "conflict_summary": (
                    f"An aggressive Mino-style Super-Agent representing your top regen prospect has leaked interest from a bitter rival club. "
                    f"{gm_name} wants to call the agent's bluff and ban him from the training ground, while {manager_name} begs you to keep the player happy before matchday."
                ),
                "role_a": f"General Manager ({gm_name})",
                "role_b": f"First-Team Manager ({manager_name})",
                "choices": [
                    {
                        "choice_id": "enforce_gm_wage_cap",
                        "label": "Call the Agent's Bluff & Hold the Line",
                        "summary": f"Back {gm_name}: refuse agent blackmail and reinforce club authority.",
                        "backed_role": "general_manager",
                        "effects_preview": "+500 GTEX Treasury · +8 GM Mood · +1 Prestige · -4 Manager Mood",
                    },
                    {
                        "choice_id": "back_manager_target",
                        "label": "Appease the Star & Promise Spotlight",
                        "summary": f"Side with {manager_name} and guarantee key matchday status to calm the dressing room.",
                        "backed_role": "first_team_manager",
                        "effects_preview": "+6 Squad Morale · +10 Manager Mood · -4 GM Mood",
                    },
                    {
                        "choice_id": "owner_performance_compromise",
                        "label": "Restructure Deal with Loyalty Bonus",
                        "summary": "Tie the agent's demands strictly to on-pitch trophy and goal milestones (-400 GTEX).",
                        "backed_role": "compromise",
                        "effects_preview": "-400 GTEX Club Cash · +5 GM & Manager Mood · +4 Squad Morale · +1 Prestige",
                    },
                ],
            },
            {
                "key": "regen_nightlife_tabloid",
                "title": "Sim-Life Tabloid Scandal: Wonderkid Spotted at VIP Supercar Lounge",
                "conflict_summary": (
                    f"Photos surfaced in the GTEX Newsroom of your breakout academy regen at a late-night VIP supercar lounge 48 hours before kickoff. "
                    f"{manager_name} demands an immediate fine and benching, while {hoyd_name} warns harsh public punishment will shatter the youngster's confidence."
                ),
                "role_a": f"Head of Youth Development ({hoyd_name})",
                "role_b": f"First-Team Manager ({manager_name})",
                "choices": [
                    {
                        "choice_id": "mandate_youth_minutes",
                        "label": "Protect the Wonderkid & Shield from Media",
                        "summary": f"Back {hoyd_name}: handle it internally and turn the media noise into 'Us Against the World' motivation.",
                        "backed_role": "head_of_youth_development",
                        "effects_preview": "+10 HOYD Mood · +8 Regen Morale & Loyalty · +1 Prestige · -3 Manager Mood",
                    },
                    {
                        "choice_id": "prioritize_senior_results",
                        "label": "Drop & Fine — Enforce Iron Dressing-Room Code",
                        "summary": f"Back {manager_name}: send a ruthless message that no player is bigger than the badge.",
                        "backed_role": "first_team_manager",
                        "effects_preview": "+8 First-Team Manager Mood · +5 Senior Squad Morale · -4 HOYD Mood",
                    },
                    {
                        "choice_id": "hybrid_cup_rotation",
                        "label": "Assign Senior Captain Mentorship & PR Charity Duty",
                        "summary": "Pair the regen with a veteran leader and deflect tabloid pressure constructively.",
                        "backed_role": "compromise",
                        "effects_preview": "+5 HOYD & Manager Mood · +4 Squad Morale · +1 Prestige",
                    },
                ],
            },
            {
                "key": "rival_owner_mind_games",
                "title": "Rivalry Grudge Saga: Rival Owner Mocks Your Club on Live Broadcast",
                "conflict_summary": (
                    f"A rival club owner went on live GTEX broadcast claiming your club 'buys Showroom glamour instead of real football heritage'. "
                    f"{manager_name} wants to fire back in the press and pledge a derby bonus, while {gm_name} advises a cold, corporate focus."
                ),
                "role_a": f"General Manager ({gm_name})",
                "role_b": f"First-Team Manager ({manager_name})",
                "choices": [
                    {
                        "choice_id": "enforce_gm_wage_cap",
                        "label": "Take the High Road & Monetize the Hype",
                        "summary": f"Let {gm_name} turn the media attention into a commercial broadcast sponsor activation (+500 GTEX).",
                        "backed_role": "general_manager",
                        "effects_preview": "+500 GTEX Commercial Windfall · +8 GM Mood · -4 Manager Mood",
                    },
                    {
                        "choice_id": "back_manager_target",
                        "label": "Clap Back Publicly & Fire Up the Dressing Room",
                        "summary": f"Unleash {manager_name} in the press conference and turn the next fixture into a blood-and-thunder grudge match.",
                        "backed_role": "first_team_manager",
                        "effects_preview": "+6 Squad Morale · +10 Manager Mood · -4 GM Mood",
                    },
                    {
                        "choice_id": "owner_performance_compromise",
                        "label": "Pledge Double Grudge-Match Win Bonus",
                        "summary": "Let your treasury and scoreboard do the talking with a 400 GTEX victory pot.",
                        "backed_role": "compromise",
                        "effects_preview": "-400 GTEX Club Cash · +5 GM & Manager Mood · +4 Squad Morale · +1 Prestige",
                    },
                ],
            },
            {
                "key": "executive_poaching_raid",
                "title": "Boardroom Poaching Raid: Tier-1 Superclub Approaches Your Executive",
                "conflict_summary": (
                    f"Rumors are swirling that a Tier-1 Continental Superclub has privately sounded out {gm_name} with a lucrative contract to defect and bring your scouting dossier along."
                ),
                "role_a": f"General Manager ({gm_name})",
                "role_b": f"First-Team Manager ({manager_name})",
                "choices": [
                    {
                        "choice_id": "enforce_gm_wage_cap",
                        "label": "Expand GM Authority & Commercial Autonomy",
                        "summary": f"Publicly affirm {gm_name} as the architect of your project and lock in his commercial vision.",
                        "backed_role": "general_manager",
                        "effects_preview": "+500 GTEX Commercial Rebate · +8 GM Mood · -4 Manager Mood",
                    },
                    {
                        "choice_id": "back_manager_target",
                        "label": "Shift Power to First-Team Manager",
                        "summary": f"Make clear that {manager_name} runs football decisions if the GM's head is turned.",
                        "backed_role": "first_team_manager",
                        "effects_preview": "+6 Squad Morale · +10 Manager Mood · -4 GM Mood",
                    },
                    {
                        "choice_id": "owner_performance_compromise",
                        "label": "Host Executive Unity Summit & Retention Bonus",
                        "summary": "Reward the entire executive suite with a 400 GTEX retention bonus to cement boardroom loyalty.",
                        "backed_role": "compromise",
                        "effects_preview": "-400 GTEX Club Cash · +5 GM & Manager Mood · +4 Squad Morale · +1 Prestige",
                    },
                ],
            },
        ]
    )

    chosen = templates[int(world_day) % len(templates)]

    return {
        "dilemma_id": f"dilemma:{club_id}:{world_day}:{chosen['key']}",
        "title": chosen["title"],
        "conflict_summary": chosen["conflict_summary"],
        "role_a": chosen["role_a"],
        "role_b": chosen["role_b"],
        "status": "open",
        "selected_choice_id": None,
        "resolution_outcome": None,
        "choices": chosen["choices"],
    }
