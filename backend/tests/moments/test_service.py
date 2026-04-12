from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import DomainEvent, InMemoryEventPublisher
from app.core.config import get_settings
from app.highlights.queue import FileHighlightRenderQueue
from app.highlights.service import HighlightGenerationService
from app.moments.priority_cache import ensure_moment_priority_cache
from app.moments.service import MomentsEngine
from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.storage import LocalObjectStorage
from app.viral.distribution import InMemoryViralDispatchPoolStore
from app.viral.ingestion_runtime import ViralDispatchRuntime
from app.viral.promotion import ViralClipPromotionService
from app.viral.ranking_service import InMemoryViralLeaderboardStore


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ClipVariant.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def _build_engine(
    tmp_path,
) -> tuple[MomentsEngine, InMemoryEventPublisher, InMemoryViralLeaderboardStore, sessionmaker[Session]]:
    app = FastAPI()
    queue = FileHighlightRenderQueue(tmp_path)
    storage = LocalObjectStorage(tmp_path)
    publisher = InMemoryEventPublisher()
    leaderboard = InMemoryViralLeaderboardStore()
    session_factory = _session_factory()
    highlight_service = HighlightGenerationService(
        settings=get_settings(),
        queue=queue,
        storage=storage,
    )
    engine = MomentsEngine(
        app=app,
        highlight_generation_service=highlight_service,
        event_publisher=publisher,
        viral_leaderboard_store=leaderboard,
        session_factory=session_factory,
    )
    return engine, publisher, leaderboard, session_factory


def test_moments_engine_applies_goal_boost_and_hot_window(tmp_path) -> None:
    engine, publisher, leaderboard, _session_factory = _build_engine(tmp_path)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-1",
                "event_id": "evt-1",
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 4,
                "clock": "4'",
                "team_id": "club-home",
                "team": "Home FC",
                "player_id": "player-9",
                "player": "Striker",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )

    response = engine.live(limit=5)

    assert response.total == 1
    moment = response.moments[0]
    assert moment.detected_events == ["goal"]
    assert moment.boost.initial_score == 1.0
    assert moment.boost.priority_boost == 0.3
    assert moment.boost.hot_window_multiplier == 2.0
    assert moment.boost.final_score == 2.6
    assert moment.clip.storage_key is not None
    assert moment.clip.queue_name is None
    assert moment.clip.render_status == "unavailable"
    assert engine.highlight_generation_service.queue.get_by_storage_key(moment.clip.storage_key) is None
    published_names = [event.name for event in publisher.published_events]
    assert published_names == [
        "viral.clip.dispatch.requested",
        "moments.live.created",
    ]
    top = leaderboard.top(1)
    assert len(top) == 1
    assert top[0].clip_id == moment.moment_id


def test_moments_engine_dispatch_events_seed_the_viral_pool_runtime(tmp_path) -> None:
    engine, publisher, _leaderboard, _session_factory = _build_engine(tmp_path)
    pool_store = InMemoryViralDispatchPoolStore()
    runtime = ViralDispatchRuntime(pool_store=pool_store)
    runtime.ensure_event_subscription(publisher)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-runtime",
                "event_id": "evt-runtime",
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 9,
                "clock": "9'",
                "team": "Runtime FC",
                "player": "Seeder",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )

    moment = engine.live(limit=1, match_id="match-runtime").moments[0]
    pool_entries = pool_store.top(limit=1)

    assert len(pool_entries) == 1
    assert pool_entries[0].clip_id == moment.moment_id
    assert pool_entries[0].payload["metadata"]["dispatch_event_name"] == "viral.clip.dispatch.requested"


def test_moments_engine_detects_last_minute_win(tmp_path) -> None:
    engine, _publisher, _leaderboard, _session_factory = _build_engine(tmp_path)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-2",
                "event_id": "evt-88",
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 89,
                "clock": "89'",
                "team": "Away FC",
                "player": "Closer",
                "home_score": 0,
                "away_score": 1,
                "metadata": {},
            },
        )
    )

    moment = engine.live(limit=5, match_id="match-2").moments[0]

    assert moment.event_type == "goal"
    assert moment.detected_events == ["goal", "last_minute_win"]
    assert moment.boost.priority_boost == 0.8
    assert moment.boost.final_score == 1.8


def test_moments_engine_dedupes_by_source_event_id_and_sequence_id(tmp_path) -> None:
    engine, _publisher, _leaderboard, _session_factory = _build_engine(tmp_path)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-dedupe",
                "event_id": "evt-a",
                "source_event_id": "evt-source",
                "sequence_id": 4,
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 12,
                "team": "Dedupe FC",
                "player": "Finisher",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )
    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-dedupe",
                "event_id": "evt-b",
                "source_event_id": "evt-source",
                "sequence_id": 4,
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 12,
                "team": "Dedupe FC",
                "player": "Finisher",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )

    response = engine.live(limit=5, match_id="match-dedupe")

    assert response.total == 1


def test_moments_engine_seeds_priority_cache_for_live_feed_injection(tmp_path) -> None:
    engine, _publisher, _leaderboard, _session_factory = _build_engine(tmp_path)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-priority",
                "event_id": "evt-priority",
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 11,
                "team": "Priority FC",
                "player": "Closer",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )

    moment = engine.live(limit=1, match_id="match-priority").moments[0]
    cached = ensure_moment_priority_cache(engine.app).top(limit=1)

    assert len(cached) == 1
    assert cached[0]["clip_id"] == moment.moment_id
    assert cached[0]["metadata"]["is_moment"] is True


def test_moments_engine_creates_goal_variant_burst_and_fast_tracks_winner(tmp_path) -> None:
    engine, _publisher, _leaderboard, session_factory = _build_engine(tmp_path)

    engine.handle_event(
        DomainEvent(
            name="match.events",
            payload={
                "match_id": "match-viral",
                "event_id": "evt-goal",
                "event_type": "goal",
                "source_event_type": "goal",
                "minute": 12,
                "clock": "12'",
                "team": "Burst FC",
                "player": "Finisher",
                "home_score": 1,
                "away_score": 0,
                "metadata": {},
            },
        )
    )

    moment = engine.live(limit=1, match_id="match-viral").moments[0]

    assert moment.metadata["variant_count"] == 5

    with session_factory() as session:
        variants = list(
            session.scalars(
                select(ClipVariant)
                .where(ClipVariant.base_clip_id == moment.moment_id)
                .order_by(ClipVariant.format_type.asc())
            ).all()
        )

        assert len(variants) == 5
        assert {variant.format_type for variant in variants} == {
            "instant",
            "cinematic",
            "debate",
            "tactical",
            "meme",
        }

        expired_created_at = datetime.now(UTC) - timedelta(minutes=3, seconds=5)
        for variant in variants:
            variant.created_at = expired_created_at
        session.commit()

        decision = ViralClipPromotionService(session=session).refresh(moment.moment_id)

        assert decision.resolved is True
        assert decision.decision_reason == "time_threshold"
        assert decision.winner_variant_id is not None
