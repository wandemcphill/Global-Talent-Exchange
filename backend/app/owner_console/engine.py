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
    club_id: str, world_day: int, academy_level: int, youth_skill: int, count: int
) -> list[dict[str, Any]]:
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
            events.append({
                "minute": ev.minute,
                "type": "goal",
                "team": side_key,
                "scorer": scorer,
                "score": f"{score['home']}-{score['away']}",
                "text": ev.commentary or f"{scorer} scores for {team_name}!",
            })
        elif ev_type in {"shot_missed", "shot_saved", "shot_blocked"}:
            events.append({
                "minute": ev.minute,
                "type": "chance",
                "team": side_key,
                "text": ev.commentary or f"Chance for {team_name}.",
            })
        elif ev_type in {"yellow_card", "red_card"}:
            events.append({
                "minute": ev.minute,
                "type": "flavour",
                "team": side_key,
                "text": ev.commentary or f"Card shown for {team_name}.",
            })

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
            + sum((8 if e.get("team") == "home" else -8) for e in events if start <= e.get("minute", 0) < end and e.get("team"))
        )
        momentum.append(int(clamp(weight, 5, 95)))

    result = {
        "home_goals": hg,
        "away_goals": ag,
        "events": events,
        "momentum": momentum,
        "lambda": [round(replay.summary.home_stats.shots * 0.15 + 0.5, 2), round(replay.summary.away_stats.shots * 0.15 + 0.5, 2)],
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
