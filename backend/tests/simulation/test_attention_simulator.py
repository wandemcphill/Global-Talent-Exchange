from __future__ import annotations

from datetime import UTC, datetime
import random

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.user import User
from app.orchestrator.global_state import InMemoryGlobalFeedStateStore
from app.runtime_config.service import RuntimeConfigService, default_runtime_config_snapshot
from app.simulation.metrics_collector import SimulationReport
from app.simulation.content_agent import ContentAgent
from app.simulation.simulator import AttentionSimulationEngine, StrategyComparisonReport, StrategyScenario
from app.simulation.user_agent import UserAgent


def test_attention_simulation_engine_produces_report() -> None:
    rng = random.Random(42)
    users = [
        UserAgent.randomized(
            user_id=f"user-{index}",
            formats=["instant_clip", "cinematic_replay"],
            creators=["creator-a", "creator-b", "creator-c"],
            rng=rng,
        )
        for index in range(4)
    ]
    content = [
        ContentAgent(
            clip_id="sim::clip-a",
            creator_id="creator-a",
            quality=0.82,
            format="instant_clip",
            trust=0.93,
            velocity=1.4,
            is_moment=True,
        ),
        ContentAgent(
            clip_id="sim::clip-b",
            creator_id="creator-b",
            quality=0.64,
            format="cinematic_replay",
            trust=0.9,
            velocity=0.75,
        ),
        ContentAgent(
            clip_id="sim::clip-c",
            creator_id="creator-c",
            quality=0.55,
            format="instant_clip",
            trust=0.88,
            velocity=0.4,
            is_ad=True,
            bid_weight=1.3,
        ),
    ]

    report = AttentionSimulationEngine(random_seed=7).run(users=users, content=content, ticks=40, feed_size=3)

    assert report.ticks == 40
    assert report.sessions == 40
    assert report.total_impressions > 0
    assert report.avg_watch_time > 0
    assert 0.0 <= report.fairness_index <= 1.0
    assert "position_1" in report.retention_curve
    assert report.creator_distribution


def test_attention_simulation_engine_compares_strategy_scenarios() -> None:
    users = [
        UserAgent(
            user_id="user-main",
            preferences={"formats": {"instant_clip": 0.2}, "creators": {"creator-a": 0.25}},
            attention_span=0.7,
            engagement_bias=0.8,
            share_bias=0.3,
        )
    ]
    content = [
        ContentAgent(
            clip_id="sim::clip-main",
            creator_id="creator-a",
            quality=0.78,
            format="instant_clip",
            trust=0.95,
            velocity=1.2,
            is_moment=True,
        ),
        ContentAgent(
            clip_id="sim::clip-side",
            creator_id="creator-b",
            quality=0.58,
            format="cinematic_replay",
            trust=0.89,
            velocity=0.5,
        ),
    ]

    comparison = AttentionSimulationEngine(random_seed=11).compare_strategies(
        users=users,
        content=content,
        ticks=25,
        feed_size=2,
        scenarios=[
            StrategyScenario(name="more_moment_boost", config_overrides={"moment_boost": 2.1}),
            StrategyScenario(name="higher_velocity_budget", config_overrides={"viral_velocity_cap_multiplier": 9000.0}),
        ],
    )

    assert "more_moment_boost" in comparison.scenarios
    assert "higher_velocity_budget" in comparison.scenarios
    assert "avg_session_time" in comparison.deltas["more_moment_boost"]
    assert comparison.scenario_overrides["more_moment_boost"]["moment_boost"] == 2.1
    assert comparison.baseline.total_impressions > 0


def test_attention_simulation_engine_auto_tunes_runtime_and_orchestrator() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AnalyticsEvent.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.state.session_factory = session_factory
    app.state.attention_orchestrator_store = InMemoryGlobalFeedStateStore()

    comparison = StrategyComparisonReport(
        baseline=SimulationReport(
            generated_at=datetime.now(UTC),
            ticks=100,
            sessions=100,
            avg_session_time=10.0,
            avg_watch_time=6.0,
            retention_curve={"position_1": 6.0},
            fairness_index=0.7,
            creator_distribution={"creator-a": 60, "creator-b": 40},
            ad_performance={"ctr": 0.05},
            viral_detection_speed=30.0,
            total_impressions=100,
        ),
        scenarios={
            "velocity_up": SimulationReport(
                generated_at=datetime.now(UTC),
                ticks=100,
                sessions=100,
                avg_session_time=12.0,
                avg_watch_time=7.0,
                retention_curve={"position_1": 7.0},
                fairness_index=0.74,
                creator_distribution={"creator-a": 55, "creator-b": 45},
                ad_performance={"ctr": 0.07},
                viral_detection_speed=22.0,
                total_impressions=110,
            )
        },
        deltas={"velocity_up": {"avg_session_time": 2.0}},
        scenario_overrides={"velocity_up": {"viral_velocity_cap_multiplier": 9000.0, "moment_boost": 2.1}},
    )

    with session_factory() as session:
        result = AttentionSimulationEngine(random_seed=11).auto_tune(
            app=app,
            session=session,
            comparison=comparison,
        )
        runtime_snapshot = RuntimeConfigService(session=session).load_current()

    orchestrator_config = app.state.attention_orchestrator_store.load_config()
    defaults = default_runtime_config_snapshot()

    assert result.selected_scenario == "velocity_up"
    assert orchestrator_config.viral_velocity_cap_multiplier == 9000.0
    assert orchestrator_config.moment_boost == 2.1
    assert runtime_snapshot.viral_weights.velocity_multiplier > defaults.viral_weights.velocity_multiplier
    assert runtime_snapshot.feed_weights.viral_score > defaults.feed_weights.viral_score
