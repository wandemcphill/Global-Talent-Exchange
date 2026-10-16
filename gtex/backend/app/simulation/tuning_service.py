from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.orchestrator.orchestrator_service import build_attention_orchestrator_service
from app.orchestrator.schemas import AttentionOrchestratorConfigUpdateRequest
from app.runtime_config.schemas import FeedWeightsUpdate, RuntimeConfigUpdateRequest, ViralWeightsUpdate
from app.runtime_config.service import RuntimeConfigService
from app.simulation.simulator import StrategyComparisonReport


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(frozen=True, slots=True)
class SimulationAutoTuneResult:
    selected_scenario: str | None
    objective_score: float
    orchestrator_adjustments: dict[str, Any]
    runtime_adjustments: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_scenario": self.selected_scenario,
            "objective_score": round(self.objective_score, 6),
            "orchestrator_adjustments": dict(self.orchestrator_adjustments),
            "runtime_adjustments": dict(self.runtime_adjustments),
        }


@dataclass(slots=True)
class SimulationTuningService:
    app: FastAPI
    session: Session

    def apply(self, comparison: StrategyComparisonReport, *, actor_id: str | None = "simulation.auto_tuner") -> SimulationAutoTuneResult:
        baseline = comparison.baseline
        selected_name: str | None = None
        selected_score = 0.0
        for name, report in comparison.scenarios.items():
            objective = self._objective_score(report=report, baseline=baseline)
            if objective > selected_score:
                selected_name = name
                selected_score = objective
        if selected_name is None or selected_score <= 0.0:
            return SimulationAutoTuneResult(
                selected_scenario=None,
                objective_score=0.0,
                orchestrator_adjustments={},
                runtime_adjustments={},
            )

        selected_report = comparison.scenarios[selected_name]
        overrides = dict(comparison.scenario_overrides.get(selected_name, {}))
        orchestrator_updates = self._orchestrator_updates(overrides=overrides)
        runtime_updates = self._runtime_updates(
            baseline=baseline,
            scenario=selected_report,
            overrides=overrides,
        )

        if orchestrator_updates:
            build_attention_orchestrator_service(app=self.app, session=self.session).update_config(
                AttentionOrchestratorConfigUpdateRequest(**orchestrator_updates)
            )
        if runtime_updates:
            RuntimeConfigService(
                session=self.session,
                settings=getattr(self.app.state, "settings", None),
            ).update(actor_id=actor_id, payload=RuntimeConfigUpdateRequest(**runtime_updates))
        self.session.commit()
        return SimulationAutoTuneResult(
            selected_scenario=selected_name,
            objective_score=selected_score,
            orchestrator_adjustments=orchestrator_updates,
            runtime_adjustments=runtime_updates,
        )

    @staticmethod
    def _objective_score(*, report, baseline) -> float:  # noqa: ANN001
        session_gain = report.avg_session_time - baseline.avg_session_time
        watch_gain = report.avg_watch_time - baseline.avg_watch_time
        fairness_gain = report.fairness_index - baseline.fairness_index
        ad_gain = report.ad_performance.get("ctr", 0.0) - baseline.ad_performance.get("ctr", 0.0)
        viral_speed_gain = baseline.viral_detection_speed - report.viral_detection_speed
        return round(
            (session_gain * 0.45)
            + (watch_gain * 0.35)
            + (fairness_gain * 0.15)
            + (ad_gain * 0.05)
            + (viral_speed_gain * 0.01),
            6,
        )

    @staticmethod
    def _orchestrator_updates(*, overrides: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "test_impressions_cap",
            "expand_multiplier",
            "viral_base_cap",
            "viral_velocity_cap_multiplier",
            "new_clip_minimum_impressions",
            "new_clip_age_hours",
            "moment_boost",
            "expand_threshold",
            "viral_threshold",
            "decay_threshold",
            "winner_share",
            "exploration_share",
            "max_agent_feed_ratio",
            "min_human_exposure_guarantee",
        }
        return {key: value for key, value in overrides.items() if key in allowed}

    def _runtime_updates(self, *, baseline, scenario, overrides: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
        current = RuntimeConfigService(
            session=self.session,
            settings=getattr(self.app.state, "settings", None),
        ).load_current()
        viral_weights: dict[str, float] = {}
        feed_weights: dict[str, float] = {}

        if "viral_velocity_cap_multiplier" in overrides and scenario.avg_watch_time > baseline.avg_watch_time:
            viral_weights["velocity_multiplier"] = round(
                _clamp(current.viral_weights.velocity_multiplier + 0.08, 1.0, 3.0),
                4,
            )
        if "moment_boost" in overrides and scenario.avg_session_time > baseline.avg_session_time:
            feed_weights["viral_score"] = round(
                _clamp(current.feed_weights.viral_score + 0.03, 0.0, 2.0),
                4,
            )
        if scenario.fairness_index < baseline.fairness_index:
            feed_weights["repetition_penalty"] = round(
                _clamp(current.feed_weights.repetition_penalty + 0.04, 0.0, 2.0),
                4,
            )
        if scenario.ad_performance.get("ctr", 0.0) > baseline.ad_performance.get("ctr", 0.0):
            feed_weights["following_boost"] = round(
                _clamp(current.feed_weights.following_boost + 0.02, 0.0, 2.0),
                4,
            )
        runtime_updates: dict[str, Any] = {}
        if viral_weights:
            runtime_updates["viral_weights"] = ViralWeightsUpdate(**viral_weights)
        if feed_weights:
            runtime_updates["feed_weights"] = FeedWeightsUpdate(**feed_weights)
        return runtime_updates


__all__ = [
    "SimulationAutoTuneResult",
    "SimulationTuningService",
]
