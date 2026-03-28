from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI

from app.agents.agent_manager import AgentPerformanceRequest, AgentRuntimeConfig, CreatorAgentManager
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.viral.ranking_service import InMemoryViralLeaderboardStore


def _moment_payload(*, moment_id: str = "moment-1", event_type: str = "goal", final_score: float = 2.4) -> dict[str, object]:
    return {
        "moment_id": moment_id,
        "match_id": "match-1",
        "source_event_id": f"source-{moment_id}",
        "event_type": event_type,
        "detected_events": [event_type],
        "minute": 88,
        "team": "Home FC",
        "player": "Striker",
        "scoreline": "1-0",
        "created_at": datetime.now(UTC).isoformat(),
        "clip": {
            "storage_key": f"moments/live/match-1/{moment_id}.mp4",
            "cdn_path": f"https://cdn.test/{moment_id}.mp4",
            "render_status": "ready",
        },
        "boost": {"final_score": final_score},
        "metadata": {},
    }


def _build_manager(*, config: AgentRuntimeConfig) -> tuple[CreatorAgentManager, InMemoryEventPublisher, InMemoryViralLeaderboardStore]:
    app = FastAPI()
    publisher = InMemoryEventPublisher()
    leaderboard = InMemoryViralLeaderboardStore()
    app.state.event_publisher = publisher
    manager = CreatorAgentManager(
        app=app,
        event_publisher=publisher,
        leaderboard_store=leaderboard,
        config=config,
    )
    manager.bootstrap_population()
    manager.subscribe()
    return manager, publisher, leaderboard


def test_manager_auto_generates_agent_clip_from_live_moment() -> None:
    manager, publisher, leaderboard = _build_manager(
        config=AgentRuntimeConfig(
            initial_population=3,
            max_posts_per_cycle=2,
            auto_run_on_moment=True,
            moment_trigger_limit=1,
            ratio_warm_start_denominator=5,
        )
    )

    publisher.publish(DomainEvent(name="moments.live.created", payload=_moment_payload()))

    agent_events = [
        event
        for event in publisher.published_events
        if event.name == "viral.clip.dispatch.requested" and event.payload.get("agent_id")
    ]
    assert len(agent_events) == 1
    assert agent_events[0].payload["metadata"]["origin"] == "creator_agent"
    assert leaderboard.top(1)[0].payload["metadata"]["origin"] == "creator_agent"
    assert manager.summary().recent_agent_dispatches == 1


def test_manager_blocks_generation_when_agent_ratio_cap_would_be_exceeded() -> None:
    manager, publisher, _leaderboard = _build_manager(
        config=AgentRuntimeConfig(
            initial_population=2,
            max_agent_ratio=0.10,
            max_posts_per_cycle=1,
            auto_run_on_moment=True,
            moment_trigger_limit=1,
            ratio_warm_start_denominator=5,
        )
    )

    for index in range(4):
        publisher.publish(
            DomainEvent(
                name="viral.clip.dispatch.requested",
                payload={
                    "clip_id": f"human-{index}",
                    "metadata": {"origin": "human_creator"},
                },
            )
        )

    publisher.publish(DomainEvent(name="moments.live.created", payload=_moment_payload(moment_id="moment-2")))

    agent_events = [
        event
        for event in publisher.published_events
        if event.name == "viral.clip.dispatch.requested" and event.payload.get("agent_id")
    ]
    assert agent_events == []
    assert manager.summary().recent_agent_dispatches == 0


def test_manager_learning_updates_wallet_and_strategy_after_performance_feedback() -> None:
    manager, _publisher, _leaderboard = _build_manager(
        config=AgentRuntimeConfig(
            initial_population=1,
            max_posts_per_cycle=1,
            auto_run_on_moment=False,
            ratio_warm_start_denominator=5,
        )
    )

    manager.handle_event(DomainEvent(name="moments.live.created", payload=_moment_payload(moment_id="moment-3", final_score=2.8)))
    response = manager.run_cycle(max_agents=1, trigger="test")

    assert response.published_count == 1
    result = response.results[0]
    agent = manager._agents[result.agent_id]
    initial_duration = agent.profile.strategy.avg_duration

    receipt = manager.record_performance(
        AgentPerformanceRequest(
            clip_id=result.clip_id,
            watch_time=18.0,
            shares=14,
            comments=4,
            completion_rate=0.82,
            share_rate=0.07,
            comment_rate=0.02,
            velocity=1.40,
            earnings=3.5,
        )
    )

    assert receipt.reward > 0.0
    assert receipt.average_reward > 0.0
    assert receipt.balance > 0.0
    assert agent.profile.strategy.avg_duration <= initial_duration
    assert agent.learning_state.preferred_formats[result.primary_format] > 0.0
