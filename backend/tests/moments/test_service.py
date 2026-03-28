from __future__ import annotations

from fastapi import FastAPI

from app.core.events import DomainEvent, InMemoryEventPublisher
from app.core.config import get_settings
from app.highlights.queue import FileHighlightRenderQueue
from app.highlights.service import HighlightGenerationService
from app.moments.service import MomentsEngine
from app.storage import LocalObjectStorage
from app.viral.ranking_service import InMemoryViralLeaderboardStore


def _build_engine(tmp_path) -> tuple[MomentsEngine, InMemoryEventPublisher, InMemoryViralLeaderboardStore]:
    app = FastAPI()
    queue = FileHighlightRenderQueue(tmp_path)
    storage = LocalObjectStorage(tmp_path)
    publisher = InMemoryEventPublisher()
    leaderboard = InMemoryViralLeaderboardStore()
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
    )
    return engine, publisher, leaderboard


def test_moments_engine_applies_goal_boost_and_hot_window(tmp_path) -> None:
    engine, publisher, leaderboard = _build_engine(tmp_path)

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
    assert moment.clip.queue_name == "clip_builder_queue"
    assert engine.highlight_generation_service.queue.get_by_storage_key(moment.clip.storage_key) is not None
    published_names = [event.name for event in publisher.published_events]
    assert published_names == [
        "viral.clip.dispatch.requested",
        "moments.live.created",
    ]
    top = leaderboard.top(1)
    assert len(top) == 1
    assert top[0].clip_id == moment.moment_id


def test_moments_engine_detects_last_minute_win(tmp_path) -> None:
    engine, _publisher, _leaderboard = _build_engine(tmp_path)

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
