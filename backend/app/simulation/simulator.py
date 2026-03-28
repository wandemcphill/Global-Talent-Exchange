from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import random
from typing import Any

from app.orchestrator.global_state import AttentionOrchestratorConfig, InMemoryGlobalFeedStateStore
from app.orchestrator.orchestrator_service import AttentionOrchestratorService
from app.simulation.content_agent import ContentAgent
from app.simulation.metrics_collector import SimulationMetricsCollector, SimulationReport
from app.simulation.user_agent import UserAgent


@dataclass(frozen=True, slots=True)
class StrategyScenario:
    name: str
    config_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyComparisonReport:
    baseline: SimulationReport
    scenarios: dict[str, SimulationReport]
    deltas: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.as_dict(),
            "scenarios": {name: report.as_dict() for name, report in self.scenarios.items()},
            "deltas": deepcopy(self.deltas),
        }


@dataclass(slots=True)
class AttentionSimulationEngine:
    orchestrator: AttentionOrchestratorService | None = None
    random_seed: int = 20260328
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.random_seed)
        if self.orchestrator is None:
            self.orchestrator = AttentionOrchestratorService(state_store=InMemoryGlobalFeedStateStore())

    def run(
        self,
        *,
        users: list[UserAgent],
        content: list[ContentAgent],
        ticks: int = 10_000,
        feed_size: int = 5,
    ) -> SimulationReport:
        if not users:
            raise ValueError("Simulation requires at least one user.")
        if not content:
            raise ValueError("Simulation requires at least one content agent.")
        metrics = SimulationMetricsCollector()
        for tick in range(max(int(ticks), 1)):
            user = self._rng.choice(users)
            metrics.begin_session()
            clip_candidates = [agent.as_clip() for agent in content]
            feed = self.orchestrator.generate_feed(user=user, clips=clip_candidates, limit=max(int(feed_size), 1))
            clip_agent_by_id = {agent.clip_id: agent for agent in content}
            for position, clip in enumerate(feed):
                metrics.record_delivery(tick=tick, position=position, clip=clip)
                reaction = user.react(clip, rng=self._rng)
                metrics.record_reaction(clip=clip, position=position, reaction=reaction)
                content_agent = clip_agent_by_id.get(str(getattr(clip, "clip_id", "")))
                if content_agent is not None:
                    content_agent.apply_reaction(reaction)
        return metrics.report(ticks=max(int(ticks), 1))

    def compare_strategies(
        self,
        *,
        users: list[UserAgent],
        content: list[ContentAgent],
        ticks: int = 2_000,
        feed_size: int = 5,
        scenarios: list[StrategyScenario],
    ) -> StrategyComparisonReport:
        baseline_engine = self._engine_for_overrides({})
        baseline = baseline_engine.run(
            users=deepcopy(users),
            content=deepcopy(content),
            ticks=ticks,
            feed_size=feed_size,
        )
        scenario_reports: dict[str, SimulationReport] = {}
        deltas: dict[str, dict[str, Any]] = {}
        for scenario in scenarios:
            scenario_engine = self._engine_for_overrides(scenario.config_overrides)
            report = scenario_engine.run(
                users=deepcopy(users),
                content=deepcopy(content),
                ticks=ticks,
                feed_size=feed_size,
            )
            scenario_reports[scenario.name] = report
            deltas[scenario.name] = {
                "avg_session_time": round(report.avg_session_time - baseline.avg_session_time, 4),
                "avg_watch_time": round(report.avg_watch_time - baseline.avg_watch_time, 4),
                "fairness_index": round(report.fairness_index - baseline.fairness_index, 4),
                "ad_ctr": round(report.ad_performance.get("ctr", 0.0) - baseline.ad_performance.get("ctr", 0.0), 4),
                "viral_detection_speed": round(baseline.viral_detection_speed - report.viral_detection_speed, 4),
            }
        return StrategyComparisonReport(
            baseline=baseline,
            scenarios=scenario_reports,
            deltas=deltas,
        )

    def _engine_for_overrides(self, overrides: dict[str, Any]) -> "AttentionSimulationEngine":
        store = InMemoryGlobalFeedStateStore()
        config = AttentionOrchestratorConfig.from_payload(overrides)
        store.save_config(config)
        return AttentionSimulationEngine(
            orchestrator=AttentionOrchestratorService(state_store=store),
            random_seed=self.random_seed,
        )
