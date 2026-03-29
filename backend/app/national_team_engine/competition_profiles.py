from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CompetitionLifecycleProfile:
    family: str
    age_band: str
    tournament_slots: int
    group_size: int
    advance_per_group: int
    best_third_slots: int
    qualifier_group_size: int
    eligible_confederations: tuple[str, ...]
    preferred_cycle_week: int
    schedule_label: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["eligible_confederations"] = list(self.eligible_confederations)
        return payload


COMPETITION_FAMILIES = ("world_cup", "afcon", "copa", "euros")
AGE_BANDS = ("senior", "u20", "u17")


PROFILE_MAP: dict[tuple[str, str], CompetitionLifecycleProfile] = {
    ("world_cup", "senior"): CompetitionLifecycleProfile(
        family="world_cup",
        age_band="senior",
        tournament_slots=48,
        group_size=4,
        advance_per_group=2,
        best_third_slots=8,
        qualifier_group_size=4,
        eligible_confederations=(),
        preferred_cycle_week=4,
        schedule_label="Week 4 -> World Cup Qualifiers",
    ),
    ("world_cup", "u20"): CompetitionLifecycleProfile(
        family="world_cup",
        age_band="u20",
        tournament_slots=24,
        group_size=4,
        advance_per_group=2,
        best_third_slots=4,
        qualifier_group_size=4,
        eligible_confederations=(),
        preferred_cycle_week=4,
        schedule_label="Week 4 -> U20 World Cup Qualifiers",
    ),
    ("world_cup", "u17"): CompetitionLifecycleProfile(
        family="world_cup",
        age_band="u17",
        tournament_slots=48,
        group_size=4,
        advance_per_group=2,
        best_third_slots=8,
        qualifier_group_size=4,
        eligible_confederations=(),
        preferred_cycle_week=4,
        schedule_label="Week 4 -> U17 World Cup Qualifiers",
    ),
    ("afcon", "senior"): CompetitionLifecycleProfile(
        family="afcon",
        age_band="senior",
        tournament_slots=24,
        group_size=4,
        advance_per_group=2,
        best_third_slots=4,
        qualifier_group_size=4,
        eligible_confederations=("CAF",),
        preferred_cycle_week=2,
        schedule_label="Week 2 -> Senior AFCON",
    ),
    ("afcon", "u20"): CompetitionLifecycleProfile(
        family="afcon",
        age_band="u20",
        tournament_slots=12,
        group_size=4,
        advance_per_group=2,
        best_third_slots=2,
        qualifier_group_size=4,
        eligible_confederations=("CAF",),
        preferred_cycle_week=2,
        schedule_label="Week 2 -> U20 AFCON",
    ),
    ("afcon", "u17"): CompetitionLifecycleProfile(
        family="afcon",
        age_band="u17",
        tournament_slots=16,
        group_size=4,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=4,
        eligible_confederations=("CAF",),
        preferred_cycle_week=1,
        schedule_label="Week 1 -> U17 AFCON",
    ),
    ("copa", "senior"): CompetitionLifecycleProfile(
        family="copa",
        age_band="senior",
        tournament_slots=16,
        group_size=4,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=5,
        eligible_confederations=("CONMEBOL",),
        preferred_cycle_week=3,
        schedule_label="Week 3 -> Senior Copa",
    ),
    ("copa", "u20"): CompetitionLifecycleProfile(
        family="copa",
        age_band="u20",
        tournament_slots=10,
        group_size=5,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=5,
        eligible_confederations=("CONMEBOL",),
        preferred_cycle_week=3,
        schedule_label="Week 3 -> U20 Copa",
    ),
    ("copa", "u17"): CompetitionLifecycleProfile(
        family="copa",
        age_band="u17",
        tournament_slots=10,
        group_size=5,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=5,
        eligible_confederations=("CONMEBOL",),
        preferred_cycle_week=3,
        schedule_label="Week 3 -> U17 Copa",
    ),
    ("euros", "senior"): CompetitionLifecycleProfile(
        family="euros",
        age_band="senior",
        tournament_slots=24,
        group_size=4,
        advance_per_group=2,
        best_third_slots=4,
        qualifier_group_size=4,
        eligible_confederations=("UEFA",),
        preferred_cycle_week=2,
        schedule_label="Week 2 -> Senior Euros",
    ),
    ("euros", "u20"): CompetitionLifecycleProfile(
        family="euros",
        age_band="u20",
        tournament_slots=16,
        group_size=4,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=4,
        eligible_confederations=("UEFA",),
        preferred_cycle_week=3,
        schedule_label="Week 3 -> U20 Euros",
    ),
    ("euros", "u17"): CompetitionLifecycleProfile(
        family="euros",
        age_band="u17",
        tournament_slots=16,
        group_size=4,
        advance_per_group=2,
        best_third_slots=0,
        qualifier_group_size=4,
        eligible_confederations=("UEFA",),
        preferred_cycle_week=1,
        schedule_label="Week 1 -> U17 Euros",
    ),
}


def infer_competition_family(*, key: str, title: str, metadata_json: dict[str, Any] | None = None) -> str:
    metadata = metadata_json or {}
    explicit = str(metadata.get("competition_family") or "").strip().lower()
    if explicit in COMPETITION_FAMILIES:
        return explicit

    haystack = f"{key} {title}".lower()
    if "afcon" in haystack:
        return "afcon"
    if "copa" in haystack:
        return "copa"
    if "euro" in haystack:
        return "euros"
    return "world_cup"


def profile_for(*, family: str, age_band: str, metadata_json: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = PROFILE_MAP[(family, age_band if age_band in AGE_BANDS else "senior")]
    payload = profile.as_dict()
    overrides = dict((metadata_json or {}).get("competition_engine") or {})
    if "eligible_confederations" in overrides:
        overrides["eligible_confederations"] = list(overrides["eligible_confederations"])
    payload.update(overrides)
    payload["family"] = family
    payload["age_band"] = age_band
    payload["tournament_slots"] = max(2, int(payload["tournament_slots"]))
    payload["group_size"] = max(2, int(payload["group_size"]))
    payload["advance_per_group"] = max(1, int(payload["advance_per_group"]))
    payload["best_third_slots"] = max(0, int(payload["best_third_slots"]))
    payload["qualifier_group_size"] = max(2, int(payload["qualifier_group_size"]))
    payload["preferred_cycle_week"] = max(1, int(payload["preferred_cycle_week"]))
    payload["schedule_label"] = str(payload["schedule_label"]).strip() or profile.schedule_label
    payload["eligible_confederations"] = list(payload.get("eligible_confederations") or [])
    return payload


def seeded_competition_definitions(*, season_label: str) -> list[dict[str, Any]]:
    definitions = [
        ("gtex-world-cup", "GTEX World Cup", "world_cup", "senior"),
        ("gtex-u20-world-cup", "U20 World Cup", "world_cup", "u20"),
        ("gtex-u17-world-cup", "U17 World Cup", "world_cup", "u17"),
        ("gtex-afcon", "GTEX AFCON", "afcon", "senior"),
        ("gtex-u20-afcon", "U20 AFCON", "afcon", "u20"),
        ("gtex-u17-afcon", "U17 AFCON", "afcon", "u17"),
        ("gtex-copa", "GTEX Copa", "copa", "senior"),
        ("gtex-u20-copa", "U20 Copa", "copa", "u20"),
        ("gtex-u17-copa", "U17 Copa", "copa", "u17"),
        ("gtex-euros", "GTEX Euros", "euros", "senior"),
        ("gtex-u20-euros", "U20 Euros", "euros", "u20"),
        ("gtex-u17-euros", "U17 Euros", "euros", "u17"),
    ]
    seeded: list[dict[str, Any]] = []
    for key, title, family, age_band in definitions:
        profile = profile_for(family=family, age_band=age_band, metadata_json={"competition_engine": {}})
        seeded.append(
            {
                "key": key,
                "title": title,
                "season_label": season_label,
                "region_type": "global" if family == "world_cup" else family,
                "age_band": age_band,
                "format_type": "cup",
                "status": "draft",
                "competition_family": family,
                "metadata_json": {
                    "competition_family": family,
                    "entry_mode": "rental_only",
                    "minimum_squad_size": 18,
                    "maximum_squad_size": 30,
                    "free_player_quota": 5,
                    "free_player_distribution": {"high": 1, "mid": 2, "low": 2},
                    "competition_engine": profile,
                    "schedule_profile": {
                        "preferred_cycle_week": profile["preferred_cycle_week"],
                        "label": profile["schedule_label"],
                    },
                },
            }
        )
    return seeded
