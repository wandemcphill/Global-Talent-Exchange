from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Any


DNA_ARCHETYPES = ("playmaker", "poacher", "engine", "destroyer")

_ARCHETYPE_TEMPLATES: dict[str, dict[str, float]] = {
    "playmaker": {"tempo": 0.63, "risk_taking": 0.69, "creativity": 0.86, "discipline": 0.52},
    "poacher": {"tempo": 0.71, "risk_taking": 0.58, "creativity": 0.46, "discipline": 0.56},
    "engine": {"tempo": 0.68, "risk_taking": 0.43, "creativity": 0.59, "discipline": 0.74},
    "destroyer": {"tempo": 0.52, "risk_taking": 0.34, "creativity": 0.33, "discipline": 0.82},
}

_COUNTRY_BIASES: dict[str, dict[str, float]] = {
    "BR": {"tempo": 0.02, "risk_taking": 0.08, "creativity": 0.09, "discipline": -0.03},
    "ES": {"tempo": 0.03, "risk_taking": 0.01, "creativity": 0.06, "discipline": 0.06},
    "JP": {"tempo": 0.03, "risk_taking": -0.02, "creativity": 0.01, "discipline": 0.10},
    "NG": {"tempo": 0.07, "risk_taking": 0.05, "creativity": 0.03, "discipline": -0.02},
    "GH": {"tempo": 0.06, "risk_taking": 0.04, "creativity": 0.03, "discipline": -0.01},
    "MA": {"tempo": 0.01, "risk_taking": 0.00, "creativity": 0.02, "discipline": 0.07},
}

_ARCHETYPE_BY_POSITION: dict[str, tuple[str, ...]] = {
    "gk": ("engine", "destroyer"),
    "goalkeeper": ("engine", "destroyer"),
    "cb": ("destroyer", "engine"),
    "rb": ("engine", "destroyer"),
    "lb": ("engine", "destroyer"),
    "defender": ("destroyer", "engine"),
    "dm": ("engine", "destroyer"),
    "cm": ("engine", "playmaker"),
    "am": ("playmaker", "engine"),
    "midfielder": ("playmaker", "engine"),
    "rw": ("playmaker", "poacher"),
    "lw": ("playmaker", "poacher"),
    "winger": ("playmaker", "poacher"),
    "st": ("poacher", "playmaker"),
    "cf": ("poacher", "playmaker"),
    "forward": ("poacher", "playmaker"),
}

_COMPLEMENTARY_ARCHETYPES: dict[frozenset[str], float] = {
    frozenset({"playmaker", "poacher"}): 0.22,
    frozenset({"engine", "playmaker"}): 0.18,
    frozenset({"engine", "destroyer"}): 0.16,
    frozenset({"poacher", "engine"}): 0.08,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _round_trait(value: float) -> float:
    return round(_clamp_unit(value), 4)


def _position_key(position: str | None) -> str:
    return (position or "").strip().lower()


def archetype_candidates(position: str | None) -> tuple[str, ...]:
    key = _position_key(position)
    if key in _ARCHETYPE_BY_POSITION:
        return _ARCHETYPE_BY_POSITION[key]
    if "goal" in key:
        return _ARCHETYPE_BY_POSITION["goalkeeper"]
    if any(token in key for token in ("back", "def", "cb", "rb", "lb", "wb")):
        return _ARCHETYPE_BY_POSITION["defender"]
    if any(token in key for token in ("mid", "cm", "dm", "am")):
        return _ARCHETYPE_BY_POSITION["midfielder"]
    if any(token in key for token in ("wing", "st", "cf", "fw", "forw")):
        return _ARCHETYPE_BY_POSITION["forward"]
    return ("engine", "playmaker")


def normalize_dna_profile(
    raw: dict[str, Any] | None,
    *,
    position: str | None = None,
) -> dict[str, Any]:
    baseline_archetype = archetype_candidates(position)[0]
    payload = dict(raw or {})
    archetype = str(payload.get("archetype") or baseline_archetype).strip().lower()
    if archetype not in DNA_ARCHETYPES:
        archetype = baseline_archetype
    template = _ARCHETYPE_TEMPLATES[archetype]
    evolution = payload.get("evolution")
    return {
        "archetype": archetype,
        "tempo": _round_trait(float(payload.get("tempo", template["tempo"]))),
        "risk_taking": _round_trait(float(payload.get("risk_taking", template["risk_taking"]))),
        "creativity": _round_trait(float(payload.get("creativity", template["creativity"]))),
        "discipline": _round_trait(float(payload.get("discipline", template["discipline"]))),
        "evolution": list(evolution) if isinstance(evolution, list) else [],
        "morale_boost": round(max(-0.25, min(0.25, float(payload.get("morale_boost", 0.0)))), 4),
    }


def generate_dna_profile(
    *,
    position: str | None,
    country_code: str | None,
    lineage_metadata: dict[str, Any] | None = None,
    inherited_profile: dict[str, Any] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    randomizer = rng or random.Random()
    candidates = archetype_candidates(position)
    archetype = candidates[0] if randomizer.random() < 0.68 else candidates[min(1, len(candidates) - 1)]
    template = dict(_ARCHETYPE_TEMPLATES[archetype])
    bias = _COUNTRY_BIASES.get((country_code or "").upper(), {})
    generated = {
        key: _round_trait(template[key] + bias.get(key, 0.0) + randomizer.uniform(-0.09, 0.09))
        for key in ("tempo", "risk_taking", "creativity", "discipline")
    }
    if inherited_profile:
        inherited = normalize_dna_profile(inherited_profile, position=position)
        for key in ("tempo", "risk_taking", "creativity", "discipline"):
            generated[key] = _round_trait((generated[key] * 0.62) + (float(inherited[key]) * 0.38))
        if randomizer.random() < 0.45:
            archetype = inherited["archetype"]
    elif lineage_metadata:
        for key in ("tempo", "risk_taking", "creativity", "discipline"):
            generated[key] = _round_trait((generated[key] * 0.72) + (template[key] * 0.28))
    return {
        "archetype": archetype,
        **generated,
        "evolution": [
            {
                "at": _utcnow().isoformat(),
                "reason": "generated",
                "archetype": archetype,
            }
        ],
        "morale_boost": 0.0,
    }


def evolve_dna_profile(
    raw: dict[str, Any] | None,
    *,
    position: str | None,
    reason: str,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    profile = normalize_dna_profile(raw, position=position)
    target_archetype = archetype_candidates(position)[0]
    target = _ARCHETYPE_TEMPLATES[target_archetype]
    evolved = dict(profile)
    for key in ("tempo", "risk_taking", "creativity", "discipline"):
        evolved[key] = _round_trait((float(profile[key]) * 0.82) + (target[key] * 0.18))
    if target_archetype != profile["archetype"]:
        current_distance = sum(abs(float(profile[key]) - _ARCHETYPE_TEMPLATES[profile["archetype"]][key]) for key in ("tempo", "risk_taking", "creativity", "discipline"))
        target_distance = sum(abs(float(evolved[key]) - target[key]) for key in ("tempo", "risk_taking", "creativity", "discipline"))
        if target_distance + 0.04 < current_distance:
            evolved["archetype"] = target_archetype
    history = list(profile.get("evolution", []))
    history.append(
        {
            "at": (occurred_at or _utcnow()).isoformat(),
            "reason": reason,
            "archetype": evolved["archetype"],
            "position": position,
        }
    )
    evolved["evolution"] = history[-8:]
    return evolved


def chemistry_fit_score(left: dict[str, Any] | None, right: dict[str, Any] | None) -> float:
    left_dna = normalize_dna_profile(left)
    right_dna = normalize_dna_profile(right)
    trait_distance = sum(abs(float(left_dna[key]) - float(right_dna[key])) for key in ("tempo", "risk_taking", "creativity", "discipline")) / 4.0
    complement = _COMPLEMENTARY_ARCHETYPES.get(frozenset({left_dna["archetype"], right_dna["archetype"]}), 0.0)
    same_archetype_bonus = 0.10 if left_dna["archetype"] == right_dna["archetype"] and left_dna["archetype"] != "poacher" else 0.0
    discipline_alignment = 0.06 if abs(float(left_dna["discipline"]) - float(right_dna["discipline"])) <= 0.12 else 0.0
    return max(0.0, min(1.0, 0.44 + complement + same_archetype_bonus + discipline_alignment - (trait_distance * 0.58)))


def match_attribute_adjustments(raw: dict[str, Any] | None) -> dict[str, int]:
    profile = normalize_dna_profile(raw)
    tempo = float(profile["tempo"]) - 0.5
    risk = float(profile["risk_taking"]) - 0.5
    creativity = float(profile["creativity"]) - 0.5
    discipline = float(profile["discipline"]) - 0.5
    archetype = profile["archetype"]
    adjustments = {
        "pace": round(tempo * 16),
        "off_ball_movement": round((tempo * 10) + (creativity * 8)),
        "creativity": round((creativity * 18) + (risk * 6)),
        "decision_making": round((creativity * 8) + (discipline * 8) - (risk * 5)),
        "discipline": round(discipline * 18),
        "consistency": round((discipline * 10) - (risk * 8)),
        "technique": round((creativity * 12) + (tempo * 5)),
        "clutch_factor": round((risk * 8) + (tempo * 6)),
        "big_match_temperament": round((discipline * 7) + (risk * 5)),
        "motivation": round((tempo * 4) + (discipline * 4)),
        "morale": round(float(profile.get("morale_boost", 0.0)) * 28),
    }
    if archetype == "playmaker":
        adjustments["creativity"] += 5
        adjustments["technique"] += 4
    elif archetype == "poacher":
        adjustments["clutch_factor"] += 5
        adjustments["off_ball_movement"] += 4
    elif archetype == "engine":
        adjustments["decision_making"] += 4
        adjustments["consistency"] += 4
    elif archetype == "destroyer":
        adjustments["discipline"] += 5
        adjustments["decision_making"] += 2
    return adjustments


def growth_bias_multiplier(raw: dict[str, Any] | None, *, category: str) -> float:
    profile = normalize_dna_profile(raw)
    creativity = float(profile["creativity"])
    discipline = float(profile["discipline"])
    tempo = float(profile["tempo"])
    risk = float(profile["risk_taking"])
    if category == "potential":
        return round(1.0 + (creativity * 0.10) + (tempo * 0.05), 4)
    if category == "market_value":
        return round(1.0 + (risk * 0.08) + (creativity * 0.06) + (tempo * 0.04), 4)
    if category == "morale":
        return round(1.0 + (discipline * 0.08) + (tempo * 0.04), 4)
    return 1.0


__all__ = [
    "DNA_ARCHETYPES",
    "archetype_candidates",
    "chemistry_fit_score",
    "evolve_dna_profile",
    "generate_dna_profile",
    "growth_bias_multiplier",
    "match_attribute_adjustments",
    "normalize_dna_profile",
]
