from __future__ import annotations

import hashlib
import math
import random
from typing import Any

FIRST_NAMES = ["Chidi", "Tunde", "Emeka", "Ayo", "Ifeanyi", "Segun", "Kelechi", "Musa", "Bayo", "Obinna", "Femi", "Uche", "Dayo", "Sani", "Kunle", "Nnamdi", "Tobi", "Yusuf", "Ade", "Ikenna"]
LAST_NAMES = ["Okafor", "Adeyemi", "Balogun", "Eze", "Ibrahim", "Okonkwo", "Adebayo", "Nwosu", "Lawal", "Obi", "Akinola", "Uzor", "Bello", "Chukwu", "Afolabi", "Danjuma", "Oyelaran", "Ogunleye"]
POSITIONS = ["goalkeeper", "defender", "defender", "midfielder", "midfielder", "forward"]
AI_CLUBS = ["Ikorodu Royals", "Port Harcourt Tide", "Kano Pillars Academy", "Abuja Capital FC", "Enugu Coal City", "Ibadan Oluyole", "Benin Bronze", "Jos Plateau Stars", "Warri Delta Kings", "Calabar Carnival FC", "Owerri Heartland Youth", "Kaduna Northern Lights", "Lagos Island Mariners", "Abeokuta Rock FC", "Uyo Akwa Stars"]
SPONSORS = ["Lekki Logistics", "Eko Telecom", "Harbour Trust Bank", "Naija Kicks", "Sahel Energy", "Okada Express", "Jollof Republic Foods"]
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


def manager_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    manager_id = str(snapshot.get("manager_id") or "gtex-staff-coach")
    rng = seeded("manager", manager_id)
    traits = list(snapshot.get("traits") or [])
    rarity = str(snapshot.get("rarity") or "staff")
    rarity_bonus = {"legendary": 5, "elite": 4, "popular": 2, "rising": 1}.get(rarity, 0)
    youth = int(clamp(rng.randint(7, 16) + (3 if "academy_promotion_bias" in traits else 0) + rarity_bonus // 2, 1, 20))
    return {
        "manager_id": manager_id,
        "name": snapshot.get("display_name") or "Tunde Bakare",
        "rarity": rarity,
        "tactical_preference": snapshot.get("mentality") or rng.choice(["technical", "pressing", "counter", "balanced"]),
        "tactics": list(snapshot.get("tactics") or ["balanced_shape"]),
        "catalog_traits": traits,
        "philosophy": snapshot.get("philosophy_summary") or "A pragmatic staff coach assigned by GTEX until the board appoints its own manager.",
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


DEFAULT_MANAGER = {"manager_id": "gtex-staff-coach", "display_name": "Tunde Bakare (GTEX staff coach)", "rarity": "staff"}


def regen_personality(rng: random.Random) -> dict[str, Any]:
    keys = ("ambition", "loyalty", "marketability", "professionalism", "adaptability", "growth_responsiveness", "environment_sensitivity")
    personality = {key: rng.randint(4, 20) for key in keys}
    personality["transfer_pressure"] = 10
    personality["growth_buffer"] = 0.0
    return personality


def generate_regens(club_id: str, world_day: int, academy_level: int, youth_skill: int, count: int) -> list[dict[str, Any]]:
    rng = seeded("intake", club_id, world_day)
    out = []
    for index in range(count):
        potential = int(clamp(58 + academy_level * 4 + youth_skill // 2 + rng.randint(-6, 10), 55, 94))
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
    strength = avg_rating + manager.get("tactical_quality", 10) * 0.35 + (avg_morale - 60) * 0.08 + facilities.get("medical", 1) * 0.4 - depth_penalty
    return {"strength": round(strength, 2), "xi": [p["id"] for p in fit], "avg_rating": round(avg_rating, 1), "avg_morale": round(avg_morale, 1)}


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
    """home/away: name, strength, mentality, scorers(list[str]), manager(dict|None)."""
    rng = seeded("match", seed)
    h_att, h_def = MENTALITY.get(home["mentality"], (1.0, 1.0))
    a_att, a_def = MENTALITY.get(away["mentality"], (1.0, 1.0))
    gap = (home["strength"] + 2.5 - away["strength"]) / 11
    lam_home = clamp(1.35 * math.exp(gap) * h_att * a_def, 0.15, 4.5)
    lam_away = clamp(1.1 * math.exp(-gap) * a_att * h_def, 0.15, 4.5)
    hg, ag = _poisson(rng, lam_home), _poisson(rng, lam_away)
    events: list[dict[str, Any]] = [{"minute": 0, "type": "kickoff", "team": None, "text": f"Kick-off between {home['name']} and {away['name']}."}]
    goal_minutes = sorted([("home", rng.randint(2, 90)) for _ in range(hg)] + [("away", rng.randint(2, 90)) for _ in range(ag)], key=lambda x: x[1])
    for _ in range(rng.randint(6, 9)):
        side = "home" if rng.random() < lam_home / (lam_home + lam_away) else "away"
        team = home if side == "home" else away
        pool = CHANCE_LINES if rng.random() < 0.65 else FLAVOUR_LINES
        events.append({"minute": rng.randint(3, 89), "type": "chance" if pool is CHANCE_LINES else "flavour", "team": side, "text": rng.choice(pool).format(team=team["name"])})
    score = {"home": 0, "away": 0}
    for side, minute in goal_minutes:
        team = home if side == "home" else away
        score[side] += 1
        scorer = rng.choice(team["scorers"]) if team["scorers"] else f"{team['name']} No. {rng.randint(7, 11)}"
        events.append({"minute": minute, "type": "goal", "team": side, "scorer": scorer, "score": f"{score['home']}-{score['away']}", "text": rng.choice(GOAL_LINES).format(team=team["name"], scorer=scorer)})
    events.append({"minute": 45, "type": "half", "team": None, "text": "Half-time whistle."})
    events.append({"minute": 90, "type": "full", "team": None, "text": f"Full-time: {home['name']} {hg}-{ag} {away['name']}."})
    events.sort(key=lambda e: (e["minute"], e["type"] == "full"))
    momentum = []
    for block in range(18):
        start, end = block * 5, block * 5 + 5
        weight = 50 + (gap * 10) + sum((8 if e["team"] == "home" else -8) for e in events if start <= e["minute"] < end and e["team"])
        momentum.append(int(clamp(weight + rng.randint(-6, 6), 5, 95)))
    return {"home_goals": hg, "away_goals": ag, "events": events, "momentum": momentum, "lambda": [round(lam_home, 2), round(lam_away, 2)], "gap": round(gap, 3)}


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
    return f"{name} " + lines.get((result, temperament), {"win": "is pleased with the response.", "loss": "wants answers from the board and the squad.", "draw": "calls it a fair result."}[result])


def explain_match(sim: dict[str, Any], club_side: str, home: dict[str, Any], away: dict[str, Any], extras: dict[str, Any]) -> dict[str, Any]:
    mine, theirs = (home, away) if club_side == "home" else (away, home)
    my_goals = sim["home_goals"] if club_side == "home" else sim["away_goals"]
    their_goals = sim["away_goals"] if club_side == "home" else sim["home_goals"]
    result = "win" if my_goals > their_goals else "loss" if my_goals < their_goals else "draw"
    diff = round(mine["strength"] - theirs["strength"], 1)
    factors = [
        {"factor": "Squad strength gap", "value": f"{'+' if diff >= 0 else ''}{diff}", "impact": "positive" if diff > 0 else "negative" if diff < 0 else "neutral"},
        {"factor": "Mentality", "value": mine["mentality"], "impact": "risk" if mine["mentality"] == "attacking" else "neutral"},
        {"factor": "Home advantage", "value": "Yes" if club_side == "home" else "No", "impact": "positive" if club_side == "home" else "neutral"},
        {"factor": "Average morale", "value": str(extras.get("avg_morale", "-")), "impact": "positive" if float(extras.get("avg_morale", 60)) >= 65 else "negative"},
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
    headline = {"win": f"{mine['name']} beat {theirs['name']} {my_goals}-{their_goals}", "loss": f"{mine['name']} fall {my_goals}-{their_goals} to {theirs['name']}", "draw": f"{mine['name']} and {theirs['name']} share the points"}[result]
    return {"result": result, "headline": headline, "why": factors, "next_actions": next_actions}
