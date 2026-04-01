from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.agent_manager import AgentPerformanceRequest, AgentRuntimeConfig, CreatorAgentManager
from app.agents.models import (
    AgentLearningStateRecord,
    AgentPerformanceLogRecord,
    AgentRecord,
    AgentStrategyRecord,
    AgentWalletRecord,
)
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.models.base import Base
from app.models.event_backbone import EventOutbox
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
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            AgentRecord.__table__,
            AgentStrategyRecord.__table__,
            AgentLearningStateRecord.__table__,
            AgentWalletRecord.__table__,
            AgentPerformanceLogRecord.__table__,
            EventOutbox.__table__,
        ],
    )
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
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


def test_manager_bootstrap_persists_parent_and_dependent_agent_rows() -> None:
    manager, _publisher, _leaderboard = _build_manager(
        config=AgentRuntimeConfig(
            initial_population=1,
            max_posts_per_cycle=1,
            auto_run_on_moment=False,
            ratio_warm_start_denominator=5,
        )
    )

    agent_id = next(iter(manager._agents))

    with manager.app.state.session_factory() as session:
        assert session.get(AgentRecord, agent_id) is not None
        assert session.get(AgentStrategyRecord, agent_id) is not None
        assert session.get(AgentLearningStateRecord, agent_id) is not None
        assert session.get(AgentWalletRecord, agent_id) is not None


def test_manager_persists_agent_state_and_performance_logs_across_restart() -> None:
    manager, _publisher, _leaderboard = _build_manager(
        config=AgentRuntimeConfig(
            initial_population=1,
            max_posts_per_cycle=1,
            auto_run_on_moment=False,
            ratio_warm_start_denominator=5,
        )
    )

    manager.handle_event(DomainEvent(name="moments.live.created", payload=_moment_payload(moment_id="moment-persist", final_score=2.9)))
    response = manager.run_cycle(max_agents=1, trigger="persist")

    assert response.published_count == 1
    result = response.results[0]

    receipt = manager.record_performance(
        AgentPerformanceRequest(
            clip_id=result.clip_id,
            watch_time=16.0,
            shares=6,
            comments=2,
            completion_rate=0.78,
            share_rate=0.05,
            comment_rate=0.015,
            velocity=1.1,
            impressions=400,
            earnings=2.25,
        )
    )

    agent_id = result.agent_id
    manager.close()

    app = manager.app
    restored = CreatorAgentManager(
        app=app,
        event_publisher=app.state.event_publisher,
        leaderboard_store=InMemoryViralLeaderboardStore(),
        config=AgentRuntimeConfig(initial_population=1, max_posts_per_cycle=1, auto_run_on_moment=False),
    )
    restored.bootstrap_population()

    restored_agent = restored._agents[agent_id]
    assert restored_agent.last_generated_clip_id == result.clip_id
    assert restored_agent.learning_state.total_posts == 1
    assert restored_agent.learning_state.average_reward == receipt.average_reward
    assert restored_agent.wallet.last_earnings > 0.0
    assert restored_agent.profile.strategy.shared_brain == "copilot"

    with app.state.session_factory() as session:
        logs = list(
            session.scalars(
                select(AgentPerformanceLogRecord)
                .where(AgentPerformanceLogRecord.agent_id == agent_id)
                .order_by(AgentPerformanceLogRecord.created_at.asc())
            ).all()
        )

    assert len(logs) == 1
    assert logs[0].clip_id == result.clip_id
    assert logs[0].payout_eligible is True
    assert logs[0].quality_score > 0.0
