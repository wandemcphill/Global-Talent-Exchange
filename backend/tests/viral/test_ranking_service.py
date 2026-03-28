from __future__ import annotations

from math import exp
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.trust_middleware import SharedTrustMiddleware
from app.models.base import Base
from app.models.follow import Follow
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.users.follow_service import FollowGraphNotificationService, FollowGraphService, NullFollowGraphCache
from app.viral.cascade import InMemoryViralCascadeStore, ViralCascadeEngine
from app.viral.ranking_service import ClipLiveMetricsSnapshot, InMemoryViralLeaderboardStore, ViralRankingService
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedResponse,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
)
from app.viral.scorer import ViralRankingInput, score_trending_clip
from app.viral.trust import InMemoryTrustStateStore, TrustFactorBreakdown, TrustScoreService, TrustState


class _FeedbackEngine:
    def viral_weight_adjustments(self) -> dict[str, float]:
        return {}

    def record_viral_success(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None


class _CampaignIntegrationHook:
    def list_campaign_clips(self, *, limit: int = 20) -> list[ViralClipView]:
        return []


def test_score_trending_clip_applies_weighting_velocity_and_decay() -> None:
    result = score_trending_clip(
        ViralRankingInput(
            clip_id="clip-1",
            views=1000,
            completions=800,
            total_watch_time=12_000,
            loops=220,
            shares=70,
            comments=30,
            skips=120,
            views_last_10min=250,
            views_last_60min=600,
            age_hours=6,
            duration_seconds=15,
        ),
        velocity_threshold=0.3,
    )

    expected_decay = round(exp(-6 / 24), 6)
    expected_score = round(
        (
            (0.35 * 0.8)
            + (0.20 * 0.22)
            + (0.20 * 0.07)
            + (0.10 * 0.03)
            + (0.10 * 0.8)
            - (0.15 * 0.12)
        )
        * 1.2
        * expected_decay,
        6,
    )

    assert result.clip_id == "clip-1"
    assert result.metrics.completion_rate == 0.8
    assert result.metrics.avg_watch_time == 12.0
    assert result.metrics.avg_watch_time_normalized == 0.8
    assert result.metrics.loop_rate == 0.22
    assert result.metrics.share_rate == 0.07
    assert result.metrics.comment_rate == 0.03
    assert result.metrics.skip_rate == 0.12
    assert result.metrics.velocity == 0.4167
    assert result.metrics.velocity_boost_applied is True
    assert result.metrics.decay_multiplier == expected_decay
    assert result.score == expected_score


def _build_clip(
    *,
    clip_id: str,
    completion_rate: float,
    share_rate: float,
    views_last_10min: int,
    views_last_60min: int,
    loops: float,
    comments: int,
) -> ViralClipView:
    view_count = 1000
    completions = int(round(view_count * completion_rate))
    shares = int(round(view_count * share_rate))
    return ViralClipView(
        clip_id=clip_id,
        match_id="match-1",
        highlight_id=f"{clip_id}-highlight",
        title=clip_id,
        event_type="goal",
        minute=88,
        viral_score=92,
        engagement=80.0,
        freshness=90.0,
        ranking_score=55.0,
        tags=["goal"],
        breakdown=ViralScoreBreakdownView(total=92, base_event=50, late_drama_bonus=30),
        caption=ViralCaptionView(hook=clip_id, caption="late drama"),
        distribution_accounts=[],
        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text=clip_id),
        formats=[],
        analytics=ViralClipAnalyticsView(
            clip_id=clip_id,
            view_count=view_count,
            completions=completions,
            watch_time=12.0,
            total_watch_time=12_000.0,
            loops=loops,
            loop_rate=loops / view_count,
            shares=shares,
            comments=comments,
            skips=view_count - completions,
            completion_rate=completion_rate,
            share_rate=share_rate,
            comment_rate=comments / view_count,
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
        ),
        feedback=ViralFeedbackLoopView(
            performance_tier="high_retention",
            recommendation="increase",
            increase_similar_clips=True,
            actions=["boost"],
            viral_analysis="strong retention",
        ),
        metadata={},
    )


def test_ranking_service_pins_active_cascade_above_higher_scoring_noncascade_clip() -> None:
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    cascade_engine = ViralCascadeEngine(store=InMemoryViralCascadeStore())
    cascade_clip = cascade_engine.apply_to_clip(
        _build_clip(
            clip_id="clip-cascade",
            completion_rate=0.83,
            share_rate=0.16,
            views_last_10min=360,
            views_last_60min=120,
            loops=220,
            comments=18,
        ),
        now=now,
    )
    non_cascade_clip = _build_clip(
        clip_id="clip-normal",
        completion_rate=0.94,
        share_rate=0.08,
        views_last_10min=260,
        views_last_60min=520,
        loops=260,
        comments=45,
    )

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(
                clips=[non_cascade_clip, cascade_clip],
                generated_at=now,
                personalization={},
            )

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-1", updated_at=now)]

    service = _RankingService(
        session=MagicMock(),
        leaderboard_store=InMemoryViralLeaderboardStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
    )

    response = service.recompute(scope="all")

    assert response.clips[0].clip_id == "clip-cascade"
    assert response.clips[0].metadata["cascade"]["trending_pinned"] is True
    assert response.clips[0].trending_score < response.clips[1].trending_score


def test_ranking_service_uses_sanitized_live_velocity_metrics() -> None:
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    clip = _build_clip(
        clip_id="clip-sanitized",
        completion_rate=0.90,
        share_rate=0.12,
        views_last_10min=380,
        views_last_60min=420,
        loops=180,
        comments=20,
    )

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(clips=[clip], generated_at=now, personalization={})

    class _MetricsStore:
        def get_snapshot(self, clip_id: str, *, now: datetime) -> ClipLiveMetricsSnapshot | None:
            assert clip_id == "clip-sanitized"
            return ClipLiveMetricsSnapshot(
                views=30.0,
                completions=20.0,
                total_watch_time=210.0,
                loops=4.0,
                shares=2.0,
                comments=1.0,
                skips=10.0,
                views_last_10min=6,
                views_last_60min=60,
                low_trust_views_last_10min=20,
                low_trust_views_last_60min=40,
            )

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-1", updated_at=now)]

    service = _RankingService(
        session=MagicMock(),
        leaderboard_store=InMemoryViralLeaderboardStore(),
        feed_service=_FeedService(),
        metrics_store=_MetricsStore(),
        feedback_engine=_FeedbackEngine(),
    )

    response = service.recompute(scope="all")

    assert response.clips
    metrics = response.clips[0].trending_metrics
    assert metrics.views_last_10min == 6
    assert metrics.views_last_60min == 60
    assert metrics.velocity_boost_applied is False


def test_ranking_service_weights_trending_score_by_clip_trust() -> None:
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    clip = _build_clip(
        clip_id="clip-trust-weighted",
        completion_rate=0.90,
        share_rate=0.12,
        views_last_10min=320,
        views_last_60min=500,
        loops=180,
        comments=24,
    ).model_copy(update={"metadata": {"avg_trust_score": 0.5, "clip_trust_score": 0.5}})

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(clips=[clip], generated_at=now, personalization={})

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-1", updated_at=now)]

    service = _RankingService(
        session=MagicMock(),
        leaderboard_store=InMemoryViralLeaderboardStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
    )

    response = service.recompute(scope="all")

    assert response.clips
    trending_clip = response.clips[0]
    assert trending_clip.metadata["raw_trending_score"] > trending_clip.trending_score
    assert trending_clip.trending_score == round(trending_clip.metadata["raw_trending_score"] * 0.5, 6)


def test_ranking_service_skips_low_clip_trust_clips() -> None:
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    clip = _build_clip(
        clip_id="clip-low-trust",
        completion_rate=0.88,
        share_rate=0.10,
        views_last_10min=280,
        views_last_60min=420,
        loops=140,
        comments=12,
    ).model_copy(update={"metadata": {"avg_trust_score": 0.25, "clip_trust_score": 0.25}})

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(clips=[clip], generated_at=now, personalization={})

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-1", updated_at=now)]

    service = _RankingService(
        session=MagicMock(),
        leaderboard_store=InMemoryViralLeaderboardStore(),
        feed_service=_FeedService(),
        feedback_engine=_FeedbackEngine(),
    )

    response = service.recompute(scope="all")

    assert response.clips == []


def test_ranking_service_emits_creator_viral_notifications() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Follow.__table__, NotificationRecord.__table__],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                User(id="viewer-1", email="viewer@example.com", username="viewer", password_hash="hashed", role=UserRole.USER),
                User(id="creator-1", email="creator@example.com", username="creator", password_hash="hashed", role=UserRole.USER),
            ]
        )
        session.add(Follow(follower_id="viewer-1", following_id="creator-1"))
        session.commit()

    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(
                clips=[
                    _build_clip(
                        clip_id="clip-creator-viral",
                        completion_rate=0.92,
                        share_rate=0.18,
                        views_last_10min=340,
                        views_last_60min=880,
                        loops=300,
                        comments=60,
                    ).model_copy(update={"metadata": {"creator_id": "creator-1"}})
                ],
                generated_at=now,
                personalization={},
            )

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-viral", updated_at=now)]

    with session_factory() as session:
        follow_graph = FollowGraphService(session=session, cache=NullFollowGraphCache())
        service = _RankingService(
            session=session,
            leaderboard_store=InMemoryViralLeaderboardStore(),
            feed_service=_FeedService(),
            notification_service=FollowGraphNotificationService(
                session=session,
                follow_graph_service=follow_graph,
            ),
            feedback_engine=_FeedbackEngine(),
            campaign_integration_hook=_CampaignIntegrationHook(),
        )

        response = service.recompute(scope="all")

        assert response.clips[0].clip_id == "clip-creator-viral"
        notifications = list(session.scalars(select(NotificationRecord)).all())
        assert len(notifications) == 1
        assert notifications[0].user_id == "viewer-1"
        assert notifications[0].template_key == "FOLLOWED_CREATOR_VIRAL"


def test_ranking_service_filters_low_trust_creators_from_trending_results() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    clip = _build_clip(
        clip_id="clip-low-trust",
        completion_rate=0.92,
        share_rate=0.18,
        views_last_10min=340,
        views_last_60min=880,
        loops=300,
        comments=60,
    ).model_copy(update={"metadata": {"creator_id": "creator-low-trust"}})

    class _FeedService:
        def build_match_feed(self, _match_id: str, *, allocate_impressions: bool = False) -> ViralFeedResponse:
            return ViralFeedResponse(clips=[clip], generated_at=now, personalization={})

    class _RankingService(ViralRankingService):
        def _recent_replay_candidates(self):
            return [MagicMock(match_id="match-viral", updated_at=now)]

    with session_factory() as session:
        session.add(
            User(
                id="creator-low-trust",
                email="creator-low-trust@example.com",
                username="creator-low-trust",
                password_hash="hashed",
                role=UserRole.USER,
            )
        )
        session.commit()

        trust_store = InMemoryTrustStateStore()
        trust_store.save_trust_state(
            TrustState(
                user_id="creator-low-trust",
                trust_score=0.1,
                suspicious_event_count=5,
                healthy_event_count=0,
                shadow_banned=False,
                monetization_eligible=False,
                ranking_eligible=False,
                suspicious_flags=("viral_gate",),
                factors=TrustFactorBreakdown(
                    account_age=0.2,
                    session_consistency=0.2,
                    device_fingerprint_stability=0.2,
                    engagement_authenticity=0.2,
                    anomaly_detection=0.2,
                ),
                updated_at=now,
            )
        )
        service = _RankingService(
            session=session,
            leaderboard_store=InMemoryViralLeaderboardStore(),
            feed_service=_FeedService(),
            trust_middleware=SharedTrustMiddleware(
                session=session,
                trust_service=TrustScoreService(store=trust_store),
            ),
            feedback_engine=_FeedbackEngine(),
            campaign_integration_hook=_CampaignIntegrationHook(),
        )

        response = service.recompute(scope="all")

        assert response.clips == []
