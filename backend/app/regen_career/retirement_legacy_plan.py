from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegenRetirementLegacyPlan:
    """Deterministic hand-off from a retired regen to the academy pipeline.

    This is deliberately a plan, not a second academy generator. The existing
    academy generation service remains the only owner of actual successor
    creation and persistence.
    """

    trigger_key: str
    retiring_regen_id: str
    retiring_player_id: str
    club_id: str
    successor_count: int
    successor_quality_floor_gsi: int
    exceptional_successor_candidate: bool


def build_retirement_legacy_plan(
    *,
    retiring_regen_id: str,
    retiring_player_id: str,
    club_id: str,
    current_gsi: int,
    potential_floor_gsi: int | None = None,
) -> RegenRetirementLegacyPlan:
    current = max(0, min(99, int(current_gsi)))
    potential = current if potential_floor_gsi is None else max(0, min(99, int(potential_floor_gsi)))
    exceptional = max(current, potential) >= 90
    successor_count = 2 if exceptional else 1
    quality_floor = max(current, potential) if exceptional else current
    return RegenRetirementLegacyPlan(
        trigger_key=f"regen-retirement:{retiring_regen_id}:{club_id}",
        retiring_regen_id=retiring_regen_id,
        retiring_player_id=retiring_player_id,
        club_id=club_id,
        successor_count=successor_count,
        successor_quality_floor_gsi=quality_floor,
        exceptional_successor_candidate=exceptional,
    )


__all__ = ["RegenRetirementLegacyPlan", "build_retirement_legacy_plan"]
