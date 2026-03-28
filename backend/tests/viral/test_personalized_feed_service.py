from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.moments.priority_cache import ensure_moment_priority_cache
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.follow import Follow
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.orchestrator.global_state import InMemoryGlobalFeedStateStore
from app.orchestrator.orchestrator_service import AttentionOrchestratorService
from app.orchestrator.schemas import AttentionOrchestratorConfigUpdateRequest
from app.users.follow_service import FollowGraphNotificationService, FollowGraphService, NullFollowGraphCache
from app.viral.ingestion_schemas import ClipEvent, ClipEventMetadata, ClipEventType
from app.viral.personalized_feed_service import (
    ClipAffinityCalculator,
    InMemoryPersonalizedFeedStore,
    PersonalizedFeedRankingService,
)
from app.viral.session_tracker import ViralSessionTracker
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedResponse,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
    ViralTrendingClipView,
    ViralTrendingMetricsView,
)


class _NoDbSession:
    def get_bind(self):
        return None


def test_clip_affinity_calculator_scores_creator_and_format_preferences() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AnalyticsEvent.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add(
            User(
                id="user-affinity-1",
                email="affinity@example.com",
                username="affinity-user",
                password_hash="hashed",
                role=UserRole.USER,
            )
        )
        session.add_all(
            [
                AnalyticsEvent(
                    name="clip.view",
                    user_id="user-affinity-1",
                    metadata_json={
                        "clip_id": "clip-1",
                        "creator_id": "@GTEXGoals",
                        "format_type": "instant_clip",
                    },
                ),
                AnalyticsEvent(
                    name="clip.like",
                    user_id="user-affinity-1",
                    metadata_json={
                        "clip_id": "clip-1",
                        "creator_id": "@GTEXGoals",
                        "format_type": "instant_clip",
                    },
                ),
                AnalyticsEvent(
                    name="clip.share",
                    user_id="user-affinity-1",
                    metadata_json={
                        "clip_id": "clip-1",
                        "creator_id": "@GTEXGoals",
                        "format_type": "instant_clip",
                    },
                ),
            ]
        )
        session.commit()

    with session_factory() as session:
        calculator = ClipAffinityCalculator(session=session)
        snapshot = calculator.build_snapshot("user-affinity-1")
        clip = SimpleNamespace(
            clip_id="clip-1",
            metadata={},
            distribution_accounts=[SimpleNamespace(handle="@GTEXGoals")],
            team_name=None,
            player_name=None,
            editor=SimpleNamespace(format_key="instant_clip"),
            formats=[],
            event_type="goal",
        )
        score = calculator.score_clip(snapshot=snapshot, clip=clip)

    assert score.view_signal > 0
    assert score.like_signal > 0
    assert score.share_signal > 0
    assert score.format_preference > 0
    assert score.creator_preference > 0
    assert score.total > 0


def test_personalized_feed_blends_following_feed_and_emits_new_clip_notification() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Follow.__table__,
            NotificationRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                User(id="viewer-1", email="viewer@example.com", username="viewer", password_hash="hashed", role=UserRole.USER),
                User(id="creator-followed", email="followed@example.com", username="followed", password_hash="hashed", role=UserRole.USER),
                User(id="creator-other", email="other@example.com", username="other", password_hash="hashed", role=UserRole.USER),
                User(id="fan-a", email="fan-a@example.com", username="fana", password_hash="hashed", role=UserRole.USER),
                User(id="fan-b", email="fan-b@example.com", username="fanb", password_hash="hashed", role=UserRole.USER),
            ]
        )
        session.add_all(
            [
                Follow(follower_id="viewer-1", following_id="creator-followed"),
                Follow(follower_id="fan-a", following_id="creator-followed"),
                Follow(follower_id="fan-b", following_id="creator-followed"),
            ]
        )
        session.commit()

    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = True):
            clips = [
                _build_clip(
                    clip_id="clip-viral",
                    creator_id="creator-other",
                    viral_score=92,
                    ranking_score=75.0,
                ),
                _build_clip(
                    clip_id="clip-followed",
                    creator_id="creator-followed",
                    viral_score=55,
                    ranking_score=48.0,
                ),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    with session_factory() as session:
        follow_graph = FollowGraphService(session=session, cache=NullFollowGraphCache())
        service = PersonalizedFeedRankingService(
            session=session,
            feed_store=InMemoryPersonalizedFeedStore(),
            feed_service=_FeedService(),
            follow_graph_service=follow_graph,
            notification_service=FollowGraphNotificationService(
                session=session,
                follow_graph_service=follow_graph,
            ),
            feedback_engine=_FeedbackEngine(),
            cold_start_manager=_ColdStartManager(),
        )

        following_response = service.get_following(user_id="viewer-1", limit=2, refresh=True)
        hybrid_response = service.get_for_you(user_id="viewer-1", limit=2, refresh=True)

        assert following_response.feed_type == "following"
        assert following_response.feed_key == "user:viewer-1:following_feed"
        assert following_response.clips[0].clip_id == "clip-followed"
        assert following_response.clips[0].score_breakdown.following_boost > 0.0
        assert following_response.clips[0].score_breakdown.social_boost > 0.0

        assert hybrid_response.feed_type == "for_you"
        assert hybrid_response.mix == {"for_you": 0.6, "following": 0.4}
        assert {clip.feed_source for clip in hybrid_response.clips} == {"for_you", "following"}

        notifications = list(session.scalars(select(NotificationRecord)).all())
        assert len(notifications) == 3
        assert {item.user_id for item in notifications} == {"viewer-1", "fan-a", "fan-b"}
        assert {item.template_key for item in notifications} == {"FOLLOWED_CREATOR_NEW_CLIP"}
        assert {item.resource_id for item in notifications} == {"clip-followed"}


def test_personalized_feed_boosts_creators_trending_inside_follow_network() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Follow.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                User(id="viewer-network", email="viewer-network@example.com", username="viewer-network", password_hash="hashed", role=UserRole.USER),
                User(id="friend-a", email="friend-a@example.com", username="friend-a", password_hash="hashed", role=UserRole.USER),
                User(id="friend-b", email="friend-b@example.com", username="friend-b", password_hash="hashed", role=UserRole.USER),
                User(id="creator-network", email="creator-network@example.com", username="creator-network", password_hash="hashed", role=UserRole.USER),
                User(id="creator-other", email="creator-other@example.com", username="creator-other", password_hash="hashed", role=UserRole.USER),
            ]
        )
        session.add_all(
            [
                Follow(follower_id="viewer-network", following_id="friend-a"),
                Follow(follower_id="viewer-network", following_id="friend-b"),
                Follow(follower_id="friend-a", following_id="creator-network"),
                Follow(follower_id="friend-b", following_id="creator-network"),
            ]
        )
        session.commit()

    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            clips = [
                _build_clip(
                    clip_id="clip-other",
                    creator_id="creator-other",
                    viral_score=75,
                    ranking_score=48.0,
                ),
                _build_clip(
                    clip_id="clip-network",
                    creator_id="creator-network",
                    viral_score=70,
                    ranking_score=45.0,
                ),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    with session_factory() as session:
        follow_graph = FollowGraphService(session=session, cache=NullFollowGraphCache())
        service = PersonalizedFeedRankingService(
            session=session,
            feed_store=InMemoryPersonalizedFeedStore(),
            feed_service=_FeedService(),
            follow_graph_service=follow_graph,
            feedback_engine=_FeedbackEngine(),
            cold_start_manager=_ColdStartManager(),
        )

        response = service.get_for_you(user_id="viewer-network", limit=2, refresh=True)

        assert response.clips[0].clip_id == "clip-network"
        assert response.clips[0].score_breakdown.following_boost == 0.0
        assert response.clips[0].score_breakdown.social_boost >= 0.2


def test_personalized_feed_reranks_after_two_session_interactions() -> None:
    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            clips = [
                _build_clip(
                    clip_id="clip-global",
                    creator_id="creator-global",
                    viral_score=92,
                    ranking_score=92.0,
                    event_type="goal",
                    tags=["goal"],
                    metadata={"creator_id": "creator-global", "content_type": "highlight", "format_key": "instant_clip"},
                ),
                _build_clip(
                    clip_id="clip-session",
                    creator_id="creator-session",
                    viral_score=70,
                    ranking_score=70.0,
                    event_type="tactical_swing",
                    tags=["tactical"],
                    metadata={"creator_id": "creator-session", "content_type": "tactical", "format_key": "breakdown"},
                ),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    tracker = ViralSessionTracker()
    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
        cold_start_manager=_ColdStartManager(),
        session_tracker=tracker,
    )

    baseline = service.get_for_you(user_id="viewer-live", limit=2, refresh=True, session_id="session-live")
    assert baseline.clips[0].clip_id == "clip-global"

    tracker.observe_many(
        [
            _build_session_event(
                clip_id="clip-session",
                session_id="session-live",
                event_type=ClipEventType.COMPLETE,
                watch_time_ms=12_000,
                video_length_ms=12_000,
                content_type="tactical",
                format_key="breakdown",
                clip_event_type="tactical_swing",
                tags=["tactical"],
            ),
            _build_session_event(
                clip_id="clip-session",
                session_id="session-live",
                event_type=ClipEventType.LIKE,
                watch_time_ms=12_000,
                video_length_ms=12_000,
                content_type="tactical",
                format_key="breakdown",
                clip_event_type="tactical_swing",
                tags=["tactical"],
            ),
            _build_session_event(
                clip_id="clip-global",
                session_id="session-live",
                event_type=ClipEventType.SCROLL,
                watch_time_ms=400,
                video_length_ms=12_000,
                content_type="highlight",
                format_key="instant_clip",
                clip_event_type="goal",
                tags=["goal"],
            ),
        ]
    )

    refreshed = service.get_for_you(user_id="viewer-live", limit=2, refresh=True, session_id="session-live")

    assert refreshed.clips[0].clip_id == "clip-session"
    assert refreshed.clips[0].score_breakdown.session_boost > refreshed.clips[1].score_breakdown.session_boost


def test_personalized_feed_filters_seen_clips_from_future_results() -> None:
    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            clips = [
                _build_clip(clip_id="clip-1", creator_id="creator-1", viral_score=95, ranking_score=95.0),
                _build_clip(clip_id="clip-2", creator_id="creator-2", viral_score=90, ranking_score=90.0),
                _build_clip(clip_id="clip-3", creator_id="creator-3", viral_score=80, ranking_score=80.0),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
        cold_start_manager=_ColdStartManager(),
    )

    first_response = service.get_for_you(user_id="viewer-seen", limit=2, refresh=True)
    service.record_delivery(first_response)

    refreshed = service.get_for_you(user_id="viewer-seen", limit=3, refresh=True)

    assert {clip.clip_id for clip in refreshed.clips}.isdisjoint({clip.clip_id for clip in first_response.clips})
    assert refreshed.clips[0].clip_id == "clip-3"


def test_personalized_feed_refresh_returns_replacements_after_cursor() -> None:
    class _FeedService:
        def __init__(self) -> None:
            self.variant = "initial"

        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            initial = [
                _build_clip(clip_id="clip-1", creator_id="creator-1", viral_score=95, ranking_score=95.0),
                _build_clip(clip_id="clip-2", creator_id="creator-2", viral_score=90, ranking_score=90.0),
                _build_clip(clip_id="clip-3", creator_id="creator-3", viral_score=85, ranking_score=85.0),
            ]
            refreshed = [
                _build_clip(clip_id="clip-1", creator_id="creator-1", viral_score=95, ranking_score=95.0),
                _build_clip(clip_id="clip-9", creator_id="creator-9", viral_score=94, ranking_score=94.0),
                _build_clip(clip_id="clip-8", creator_id="creator-8", viral_score=93, ranking_score=93.0),
            ]
            clips = initial if self.variant == "initial" else refreshed
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    feed_service = _FeedService()
    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        feed_service=feed_service,
        feedback_engine=_FeedbackEngine(),
        cold_start_manager=_ColdStartManager(),
    )

    initial = service.get_for_you(user_id="viewer-refresh", limit=3, refresh=True)
    assert [clip.clip_id for clip in initial.clips] == ["clip-1", "clip-2", "clip-3"]

    feed_service.variant = "refreshed"
    refresh_payload = service.refresh_for_you(user_id="viewer-refresh", cursor=0, limit=3)

    assert refresh_payload.replace_indices == [1, 2]
    assert [clip.clip_id for clip in refresh_payload.new_items] == ["clip-9", "clip-8"]


def test_personalized_feed_prioritizes_live_moment_cache_candidates() -> None:
    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            clips = [
                _build_clip(clip_id="clip-feed", creator_id="creator-feed", viral_score=88, ranking_score=88.0),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    app = FastAPI()
    priority_cache = ensure_moment_priority_cache(app)
    priority_clip = ViralTrendingClipView(
        **_build_clip(
            clip_id="clip-moment",
            creator_id="creator-moment",
            viral_score=99,
            ranking_score=99.0,
            metadata={"source": "moments_engine", "is_moment": True},
        ).model_dump(mode="json"),
        rank=1,
        trending_score=99.0,
        age_hours=0.0,
        recompute_bucket="hot",
        last_ranked_at=datetime.now(UTC),
        trending_metrics=ViralTrendingMetricsView(
            completion_rate=0.0,
            avg_watch_time=0.0,
            avg_watch_time_normalized=0.0,
            loop_rate=0.0,
            share_rate=0.0,
            comment_rate=0.0,
            skip_rate=0.0,
            velocity=2.6,
            views_last_10min=300,
            views_last_60min=500,
            velocity_boost_applied=True,
            decay_multiplier=1.0,
        ),
    )
    priority_cache.put(
        clip_id=priority_clip.clip_id,
        score=priority_clip.trending_score,
        payload=priority_clip.model_dump(mode="json"),
    )

    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
        cold_start_manager=_ColdStartManager(),
        moment_priority_cache=priority_cache,
    )

    response = service.get_for_you(user_id="viewer-priority", limit=2, refresh=True)

    assert response.clips[0].clip_id == "clip-moment"
    assert {clip.clip_id for clip in response.clips} == {"clip-moment", "clip-feed"}


def test_personalized_feed_applies_agent_fairness_cap_when_humans_exist() -> None:
    class _FeedService:
        def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
            clips = [
                _build_clip(
                    clip_id="agent-1",
                    creator_id="agent-1",
                    viral_score=99,
                    ranking_score=99.0,
                    metadata={"origin": "creator_agent", "is_agent_generated": True, "agent_id": "agent-1"},
                ),
                _build_clip(
                    clip_id="agent-2",
                    creator_id="agent-2",
                    viral_score=97,
                    ranking_score=97.0,
                    metadata={"origin": "creator_agent", "is_agent_generated": True, "agent_id": "agent-2"},
                ),
                _build_clip(
                    clip_id="human-1",
                    creator_id="creator-human-1",
                    viral_score=90,
                    ranking_score=90.0,
                    metadata={"origin": "human_creator"},
                ),
                _build_clip(
                    clip_id="human-2",
                    creator_id="creator-human-2",
                    viral_score=89,
                    ranking_score=89.0,
                    metadata={"origin": "human_creator"},
                ),
                _build_clip(
                    clip_id="human-3",
                    creator_id="creator-human-3",
                    viral_score=88,
                    ranking_score=88.0,
                    metadata={"origin": "human_creator"},
                ),
            ]
            return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})

    class _FeedbackEngine:
        def creator_recommendation_boost(self, _creator_id: str) -> float:
            return 0.0

    class _ColdStartManager:
        def is_new_user(self, _user_id: str) -> bool:
            return False

        def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
            return 0.0

        def creator_boost(self, _creator_id: str) -> float:
            return 0.0

    orchestrator = AttentionOrchestratorService(state_store=InMemoryGlobalFeedStateStore())
    orchestrator.update_config(
        AttentionOrchestratorConfigUpdateRequest(
            max_agent_feed_ratio=0.25,
            min_human_exposure_guarantee=0.75,
        )
    )

    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
        cold_start_manager=_ColdStartManager(),
        attention_orchestrator=orchestrator,
    )

    response = service.get_for_you(user_id="viewer-fair", limit=4, refresh=True)

    agent_count = sum(1 for clip in response.clips if clip.metadata.get("origin") == "creator_agent")
    human_count = sum(1 for clip in response.clips if clip.metadata.get("origin") == "human_creator")

    assert len(response.clips) == 4
    assert agent_count <= 1
    assert human_count >= 3


def _build_clip(
    *,
    clip_id: str,
    creator_id: str,
    viral_score: int,
    ranking_score: float,
    event_type: str = "goal",
    tags: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> ViralClipView:
    return ViralClipView(
        clip_id=clip_id,
        match_id=f"match-{clip_id}",
        highlight_id=f"highlight-{clip_id}",
        title=clip_id,
        event_type=event_type,
        minute=88,
        viral_score=viral_score,
        engagement=80.0,
        freshness=90.0,
        ranking_score=ranking_score,
        tags=tags or ["goal"],
        breakdown=ViralScoreBreakdownView(total=viral_score, base_event=50),
        caption=ViralCaptionView(hook=clip_id, caption=clip_id),
        distribution_accounts=[],
        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text=clip_id),
        formats=[],
        analytics=ViralClipAnalyticsView(
            clip_id=clip_id,
            view_count=1000,
            completions=800,
            watch_time=12.0,
            total_watch_time=12000.0,
            loops=220.0,
            loop_rate=0.22,
            shares=90,
            comments=24,
            skips=200,
            completion_rate=0.8,
            share_rate=0.09,
            comment_rate=0.024,
            views_last_10min=240,
            views_last_60min=640,
        ),
        feedback=ViralFeedbackLoopView(
            performance_tier="high_retention",
            recommendation="increase",
            increase_similar_clips=True,
            actions=["boost"],
            viral_analysis="strong retention",
        ),
        metadata={"creator_id": creator_id, **(metadata or {})},
    )


def _build_session_event(
    *,
    clip_id: str,
    session_id: str,
    event_type: ClipEventType,
    watch_time_ms: int,
    video_length_ms: int,
    content_type: str,
    format_key: str,
    clip_event_type: str,
    tags: list[str],
) -> ClipEvent:
    return ClipEvent(
        event_id="00000000-0000-0000-0000-000000000001",
        clip_id=clip_id,
        user_id=None,
        session_id=session_id,
        timestamp=datetime.now(UTC),
        event_type=event_type,
        watch_time_ms=watch_time_ms,
        video_length_ms=video_length_ms,
        metadata=ClipEventMetadata(
            device="ios",
            country="NG",
            referrer="feed",
            content_type=content_type,
            format_key=format_key,
            clip_event_type=clip_event_type,
            tags=tags,
        ),
    )
