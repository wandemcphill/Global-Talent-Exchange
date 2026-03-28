from __future__ import annotations

import random

from app.simulation.content_agent import ContentAgent
from app.simulation.simulator import AttentionSimulationEngine, StrategyScenario
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
    assert comparison.baseline.total_impressions > 0
