from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Any, Callable

from app.models.regen import RegenProfile
from app.regen_career.policy_service import RegenCareerPolicyService
from app.regen_career.retirement_academy_bridge import RegenRetirementAcademyBridge
from app.regen_career.retirement_legacy_plan import build_retirement_legacy_plan
from app.services.player_lifecycle_service import PlayerLifecycleService

_POLICY_INSTALLED = False
_ORIGINAL_SYNC: Callable[..., dict[str, Any]] | None = None


def _subtract_months(value: date, months: int) -> date:
    """Return a calendar date `months` before `value` without external dependencies."""
    total = value.year * 12 + (value.month - 1) - int(months)
    year, month_index = divmod(total, 12)
    month = month_index + 1
    month_lengths = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    day = min(value.day, month_lengths[month - 1])
    return date(year, month, day)


def _assessment_payload(context: Any) -> dict[str, Any]:
    assessment = context.assessment
    return {
        "retirement_policy": "phase6_dynamic",
        "retirement_policy_status": "assessed",
        "virtual_age_months": assessment.virtual_age_months,
        "career_stage": assessment.career_stage,
        "retirement_pressure": assessment.retirement_pressure,
        "retirement_pressure_band": assessment.pressure_band.value,
        "expected_longevity_months": assessment.expected_longevity_months,
        "retirement_watch": assessment.should_enter_retirement_watch,
        "retirement_decision_eligible": assessment.eligible_for_retirement_decision,
        "retirement_drivers": list(assessment.drivers),
        "generation_season_number": context.generation_season_number,
        "current_season_number": context.current_season_number,
    }


def _retirement_legacy_plan(regen: RegenProfile, player_id: str, state: dict[str, Any]) -> dict[str, Any] | None:
    club_id = state.get("previous_club_id")
    if not state.get("retired") or not club_id or state.get("retired_on") is None:
        return None
    potential_range = dict(regen.potential_range_json or {})
    potential_floor = potential_range.get("minimum")
    plan = build_retirement_legacy_plan(
        retiring_regen_id=regen.regen_id,
        retiring_player_id=player_id,
        club_id=club_id,
        current_gsi=regen.current_gsi,
        potential_floor_gsi=potential_floor,
    )
    return {
        "status": "planned",
        "trigger_key": plan.trigger_key,
        "retiring_regen_id": plan.retiring_regen_id,
        "retiring_player_id": plan.retiring_player_id,
        "club_id": plan.club_id,
        "successor_count": plan.successor_count,
        "successor_quality_floor_gsi": plan.successor_quality_floor_gsi,
        "exceptional_successor_candidate": plan.exceptional_successor_candidate,
        "generation_owner": "existing_academy_pipeline",
        "generation_status": "pending",
    }


def _policy_sync(
    self: PlayerLifecycleService,
    player,
    regen: RegenProfile,
    *,
    reference_on: date,
    contract_summary,
    bids,
) -> dict[str, Any]:
    global _ORIGINAL_SYNC
    if _ORIGINAL_SYNC is None:
        raise RuntimeError("Phase 6C lifecycle policy adapter is not installed")

    policy_context = None
    try:
        policy_context = RegenCareerPolicyService(self.session).assess(
            player.id,
            reference_on=reference_on,
        )
    except (ValueError, KeyError):
        policy_context = None

    original_settings = self.settings
    original_generated_at = regen.generated_at
    try:
        if policy_context is None:
            regen_config = replace(self.settings.regen_generation, regen_lifecycle_retirement_months=10**9)
            self.settings = replace(self.settings, regen_generation=regen_config)
        else:
            age_months = policy_context.assessment.virtual_age_months
            if age_months is None:
                regen_config = replace(self.settings.regen_generation, regen_lifecycle_retirement_months=10**9)
                self.settings = replace(self.settings, regen_generation=regen_config)
            else:
                regen_date = _subtract_months(reference_on, age_months)
                regen.generated_at = datetime.combine(regen_date, original_generated_at.timetz())
                regen_config = replace(
                    self.settings.regen_generation,
                    regen_lifecycle_retirement_months=(
                        0 if policy_context.assessment.eligible_for_retirement_decision else 10**9
                    ),
                )
                self.settings = replace(self.settings, regen_generation=regen_config)

        state = _ORIGINAL_SYNC(
            self,
            player,
            regen,
            reference_on=reference_on,
            contract_summary=contract_summary,
            bids=bids,
        )
    finally:
        regen.generated_at = original_generated_at
        self.settings = original_settings

    already_retired = bool(state.get("retired", False))

    if policy_context is None or policy_context.assessment.virtual_age_months is None:
        state["virtual_age_months"] = None
        state.pop("lifecycle_age_months", None)
        state["career_stage"] = "age_unknown"
        state["retirement_pressure"] = False
        state["retirement_pressure_band"] = "unknown"
        state["expected_longevity_months"] = None
        state["retirement_watch"] = False
        state["retirement_decision_eligible"] = False
        state["eligible_for_retirement_decision"] = False
        state["policy_drivers"] = []
        state["retirement_drivers"] = []
        state["retirement_policy_status"] = "age_unknown"
        state["retirement_policy"] = "phase6_dynamic"
        if already_retired:
            state["retired"] = True
            state["lifecycle_phase"] = "retired"
        else:
            state["retired"] = False
            state["lifecycle_phase"] = "age_unknown"
    else:
        state.update(_assessment_payload(policy_context))
        state["policy_drivers"] = list(policy_context.assessment.drivers)
        state["eligible_for_retirement_decision"] = policy_context.assessment.eligible_for_retirement_decision
        if policy_context.assessment.eligible_for_retirement_decision:
            state["lifecycle_phase"] = "retired"
            state["retired"] = True
        else:
            state["retired"] = False

    legacy_plan = _retirement_legacy_plan(regen, player.id, state)
    if legacy_plan is not None:
        state["legacy_intake_plan"] = legacy_plan
        bridge_result = RegenRetirementAcademyBridge(self.session).consume(state=state)
        if bridge_result is not None:
            state["legacy_intake_plan"] = {
                **legacy_plan,
                "generation_status": bridge_result.status,
                "prospect_ids": list(bridge_result.prospect_ids),
            }

    self._set_regen_career_state(regen, state)
    self.session.flush()
    return state


def install() -> None:
    global _POLICY_INSTALLED, _ORIGINAL_SYNC
    if _POLICY_INSTALLED:
        return
    _ORIGINAL_SYNC = PlayerLifecycleService._sync_regen_state
    PlayerLifecycleService._sync_regen_state = _policy_sync  # type: ignore[method-assign]
    _POLICY_INSTALLED = True


install()


__all__ = ["install"]
