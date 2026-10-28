from __future__ import annotations

import hashlib
import math
import random
from typing import Any

FIRST_NAMES = [
    "Chidi",
    "Tunde",
    "Emeka",
    "Ayo",
    "Ifeanyi",
    "Segun",
    "Kelechi",
    "Musa",
    "Bayo",
    "Obinna",
    "Femi",
    "Uche",
    "Dayo",
    "Sani",
    "Kunle",
    "Nnamdi",
    "Tobi",
    "Yusuf",
    "Ade",
    "Ikenna",
]
LAST_NAMES = [
    "Okafor",
    "Adeyemi",
    "Balogun",
    "Eze",
    "Ibrahim",
    "Okonkwo",
    "Adebayo",
    "Nwosu",
    "Lawal",
    "Obi",
    "Akinola",
    "Uzor",
    "Bello",
    "Chukwu",
    "Afolabi",
    "Danjuma",
    "Oyelaran",
    "Ogunleye",
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
        "salary": 9000,
        "salary_gtex": 9000,
        "signing_fee_gtex": 18000,
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
        "transfer_fee_discount_pct": round(float(gm.get("negotiation", 10)) * 0.5, 1),
        "sponsor_revenue_bonus_pct": round(float(gm.get("commercial_acumen", 10)) * 0.6, 1),
        "academy_potential_bonus": max(1, int(hoyd.get("youth_development", 10)) // 3),
        "tactical_match_bonus": round(float(mgr.get("tactical_flexibility", mgr.get("tactical_quality", 10))) * 0.4, 1),
        "scouting_precision_bonus": round(float(scout.get("scouting_accuracy", 10)) * 0.5, 1),
        "injury_recovery_bonus": max(1, int(med.get("medical_expertise", 10)) // 3),
    }


def manager_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    manager_id = str(snapshot.get("manager_id") or "gtex-staff-coach")
    rng = seeded("manager", manager_id)
    traits = list(snapshot.get("traits") or [])
    rarity = str(snapshot.get("rarity") or "staff")
    rarity_bonus = {"legendary": 5, "elite": 4, "popular": 2, "rising": 1}.get(rarity, 0)
    youth = int(clamp(rng.randint(7, 16) + (3 if "academy_promotion_bias" in traits else 0) + rarity_bonus // 2, 1, 20))
    return {
        "manager_id": manager_id,
        "name": snapshot.get("display_name") or snapshot.get("name") or "Tunde Bakare",
        "rarity": rarity,
        "tactical_preference": snapshot.get("mentality")
        or rng.choice(["technical", "pressing", "counter", "balanced"]),
        "tactics": list(snapshot.get("tactics") or ["balanced_shape"]),
        "catalog_traits": traits,
        "philosophy": snapshot.get("philosophy_summary")
        or "A pragmatic staff coach assigned by GTEX until the board appoints its own manager.",
        "temperament": rng.choice(TEMPERAMENTS),
        "ambition": rng.randint(6, 15) + rarity_bonus,
        "loyalty": rng.randint(5, 18),
        "discipline_style": rng.choice(DISCIPLINE),
        "youth_development": youth,
        "media_style": rng.choice(MEDIA),
        "transfer_preference": "youth-first" if youth >= 15 else rng.choice(TRANSFER_PREFS),
        "tactical_quality": int(clamp(rng.randint(8, 14) + rarity_bonus, 1, 20)),
        "mood": 70,
        "is_default": manager_id == "gtex-staff-coach",
    }


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
) -> list[dict[str, Any]]:
    rng = seeded("intake", club_id, generation_key)
    out = []
    for index in range(count):
        prestige_boost = (int(club_prestige) - 40) // 10
        hoyd_boost = int(hoyd_youth) // 4
        base_pot = 58 + academy_level * 4 + youth_skill // 2 + prestige_boost + hoyd_boost + rng.randint(-6, 10)
        potential = int(clamp(base_pot, 55, 95))
        out.append(
            {
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "position": rng.choice(POSITIONS[1:] if index else POSITIONS),
                "age": rng.randint(16, 18),
                "rating": rng.randint(44, 56),
                "potential": potential,
                "personality": regen_personality(rng),
            }
        )
    return out


def rating_from_value(value_eur: float | None) -> int:
    value = max(float(value_eur or 0), 100_000.0)
    return int(clamp(20 + 7.5 * math.log10(value), 50, 88))


def price_from_value(value_eur: float | None) -> int:
    return int(clamp(float(value_eur or 0) / 10_000, 800, 25_000))


def market_quote(value_eur: float | None, value_credits: float | None) -> tuple[int, int]:
    """(price, rating) from EUR value, else from the repo's GTEX credit valuation."""
    if value_eur:
        return price_from_value(value_eur), rating_from_value(value_eur)
    credits = max(float(value_credits or 0), 0.0)
    return int(clamp(credits * 120, 800, 25_000)), int(clamp(45 + 8.5 * math.log(credits + 1), 50, 88))


def normalize_position(raw: str | None) -> str:
    text = (raw or "").strip().lower()
    if text in {"gk", "goalkeeper", "keeper"} or text.startswith("goal"):
        return "goalkeeper"
    if text in {"df", "def", "cb", "lb", "rb"} or any(k in text for k in ("back", "defend")):
        return "defender"
    if text in {"fw", "st", "cf", "lw", "rw"} or any(k in text for k in ("striker", "forward", "wing", "attack")):
        return "forward"
    return "midfielder"


def regen_value(rating: int, potential: int, age: int) -> int:
    return int(max(300, (rating - 40) * 60 + (potential - rating) * 45 + (19 - min(age, 19)) * 120))


def regen_growth(player: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Apply one world-day of growth. ctx: training, manager_youth, competition_quality, prestige."""
    p = player["personality"]
    minutes_factor = clamp(player["minutes"] / 540, 0, 1)
    morale_factor = 0.6 + player["morale"] / 125
    env = p["environment_sensitivity"] / 20
    facility_term = ctx["training"] / 5
    drivers = {
        "facilities": round(0.35 * facility_term * (0.6 + env), 3),
        "manager_quality": round(0.25 * ctx["manager_youth"] / 20, 3),
        "playing_time": round(0.2 * minutes_factor, 3),
        "competition_quality": round(0.1 * ctx["competition_quality"], 3),
        "club_prestige": round(0.1 * clamp(ctx["prestige"] / 60, 0, 1), 3),
    }
    responsiveness = p["growth_responsiveness"] / 12 * (0.7 + p["professionalism"] / 40)
    gain = sum(drivers.values()) * responsiveness * morale_factor * 1.6
    buffer = p.get("growth_buffer", 0.0) + gain
    points = int(buffer)
    headroom = player["potential"] - player["rating"]
    points = max(0, min(points, headroom))
    p["growth_buffer"] = round(buffer - int(buffer), 3)
    pressure = p.get("transfer_pressure", 10)
    pressure += (p["ambition"] - 10) * 0.8 * (1 - minutes_factor)
    if ctx["prestige"] < p["ambition"] * 3:
        pressure += 2
    if ctx["training"] <= 1 and p["environment_sensitivity"] >= 14:
        pressure += 3
    pressure -= p["loyalty"] * 0.25
    p["transfer_pressure"] = int(clamp(pressure, 0, 100))
    top_driver = max(drivers, key=drivers.get)
    weakest = min(drivers, key=drivers.get)
    return {
        "points": points,
        "drivers": drivers,
        "top_driver": top_driver,
        "weakest_driver": weakest,
        "explanation": f"Growth driven mostly by {top_driver.replace('_', ' ')}; held back by {weakest.replace('_', ' ')}.",
    }


def club_strength(players: list[dict[str, Any]], manager: dict[str, Any], facilities: dict[str, int]) -> dict[str, Any]:
    fit = sorted((p for p in players if p["injured_days"] <= 0), key=lambda p: p["rating"], reverse=True)[:11]
    if not fit:
        return {"strength": 40.0, "xi": [], "avg_rating": 40, "avg_morale": 50}
    avg_rating = sum(p["rating"] for p in fit) / len(fit)
    avg_morale = sum(p["morale"] for p in fit) / len(fit)
    depth_penalty = (11 - len(fit)) * 2.5
    strength = (
        avg_rating
        + manager.get("tactical_quality", 10) * 0.35
        + (avg_morale - 60) * 0.08
        + facilities.get("medical", 1) * 0.4
        - depth_penalty
    )
    return {
        "strength": round(strength, 2),
        "xi": [p["id"] for p in fit],
        "avg_rating": round(avg_rating, 1),
        "avg_morale": round(avg_morale, 1),
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
        base_rating = int(clamp(float(side_data.get("strength", 70)), 40, 95))
        roles = [
            PlayerRole.GOALKEEPER,
            PlayerRole.DEFENDER,
            PlayerRole.DEFENDER,
            PlayerRole.DEFENDER,
            PlayerRole.DEFENDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.FORWARD,
            PlayerRole.FORWARD,
            PlayerRole.FORWARD,
        ]
        scorers = list(side_data.get("scorers") or [])
        starters = []
        for i, role in enumerate(roles):
            p_name = scorers[i % len(scorers)] if scorers else f"{side_data.get('name', 'Team')} Player {i+1}"
            starters.append(
                MatchPlayerInput(
                    player_id=f"{side_id}-player-{i+1}",
                    player_name=p_name,
                    role=role,
                    overall=base_rating,
                    finishing=base_rating if role == PlayerRole.FORWARD else 50,
                    defending=base_rating if role in (PlayerRole.DEFENDER, PlayerRole.GOALKEEPER) else 50,
                    goalkeeping=base_rating if role == PlayerRole.GOALKEEPER else 1,
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
            tactics=TeamTacticalPlanInput(style=style, mentality=style),
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
) -> list[dict[str, Any]]:
    """Generate 3 competing seasonal sponsor offers presented by the General Manager, gated by club prestige."""
    nego_mult = 1.0 + max(0, int(gm_negotiation) - 10) * 0.04 + max(0, int(commercial_level) - 1) * 0.08
    prestige_val = int(prestige)

    base_offers = [
        {
            "offer_id": "sponsor_guaranteed_airways",
            "sponsor_name": "Aether Global Airways",
            "slot": "Front of Shirt",
            "strategy_profile": "guaranteed_heavy",
            "upfront_signing_bonus_gtex": int(round(1_200 * nego_mult, -1)),
            "per_match_gross_gtex": int(round(280 * nego_mult, -1)),
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
            "per_match_gross_gtex": int(round(360 * nego_mult, -1)),
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
            "per_match_gross_gtex": int(round(520 * nego_mult, -1)),
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
