from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.follow import Follow
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.users.follow_service import FollowGraphNotificationService, FollowGraphService, NullFollowGraphCache
from app.viral.personalized_feed_service import (
    ClipAffinityCalculator,
    InMemoryPersonalizedFeedStore,
    PersonalizedFeedRankingService,
)
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedResponse,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
)


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


def _build_clip(*, clip_id: str, creator_id: str, viral_score: int, ranking_score: float) -> ViralClipView:
    return ViralClipView(
        clip_id=clip_id,
        match_id=f"match-{clip_id}",
        highlight_id=f"highlight-{clip_id}",
        title=clip_id,
        event_type="goal",
        minute=88,
        viral_score=viral_score,
        engagement=80.0,
        freshness=90.0,
        ranking_score=ranking_score,
        tags=["goal"],
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
        metadata={"creator_id": creator_id},
    )
