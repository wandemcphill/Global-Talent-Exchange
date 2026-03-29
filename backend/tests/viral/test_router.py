from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import IdentityContext, get_current_user, get_optional_current_user, require_identity
from app.auth.security import create_access_token
from app.db import get_session
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.models.competition_match import CompetitionMatch
from app.models.creator_attention_earnings import ClipEarningsLog, CreatorWallet
from app.models.creator_profile import CreatorProfile
from app.models.event_backbone import EventOutbox
from app.models.follow import Follow
from app.models.user import User, UserRole
from app.models.user_affinity_profile import UserAffinityProfile
from app.viral.distribution import build_clip_distribution_manager
from app.viral.feed_contract import (
    PERSONALIZED_FEED_SOURCE_FOLLOWING,
    PERSONALIZED_FEED_SOURCE_FOR_YOU,
)
from app.viral.router import router as viral_router
from app.viral.schemas import (
    PersonalizedFeedAffinityView,
    PersonalizedFeedClipView,
    PersonalizedFeedRefreshResponse,
    PersonalizedFeedScoreBreakdownView,
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
)
from app.viral.service import ViralFeedService
from backend.tests.match_engine.helpers import build_request


class _ReusableFakeProducer:
    def __init__(self) -> None:
        self.received = []

    def enqueue_many(self, events):
        self.received.append(events)
        return len(events)


def _set_test_identity(
    app: FastAPI,
    *,
    current_user: User,
    session_id: str = "session-1",
    device_id: str = "device-test-1",
) -> None:
    app.state.test_identity = IdentityContext(
        user_id=current_user.id,
        session_id=session_id,
        device_id=device_id,
    )


def _identity_headers(*, user_id: str, session_id: str, device_id: str = "device-test-1") -> dict[str, str]:
    token = create_access_token(user_id, claims={"sid": session_id})
    return {
        "Authorization": f"Bearer {token}",
        "X-User-Id": user_id,
        "X-Session-Id": session_id,
        "X-Device-Id": device_id,
    }


def _build_app() -> tuple[FastAPI, sessionmaker[Session], User]:
    app = FastAPI()
    app.include_router(viral_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            AnalyticsEvent.__table__,
            CompetitionMatch.__table__,
            ClipVariant.__table__,
            CreatorWallet.__table__,
            ClipEarningsLog.__table__,
            CreatorProfile.__table__,
            EventOutbox.__table__,
            Follow.__table__,
            UserAffinityProfile.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        current_user = User(
            id="user-feed-1",
            email="feed@example.com",
            username="feed-user",
            password_hash="hashed",
            role=UserRole.USER,
        )
        session.add(current_user)
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    def override_identity() -> IdentityContext:
        return app.state.test_identity

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_optional_current_user] = lambda: current_user
    _set_test_identity(app, current_user=current_user)
    app.dependency_overrides[require_identity] = override_identity
    return app, session_factory, current_user


def _insert_match(session_factory: sessionmaker[Session], replay_payload) -> None:
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=replay_payload.match_id,
                competition_id=f"competition-{replay_payload.match_id}",
                round_id=f"round-{replay_payload.match_id}",
                round_number=1,
                home_club_id=replay_payload.summary.home_stats.team_id,
                away_club_id=replay_payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": replay_payload.model_dump(mode="json")},
            )
        )
        session.commit()


def test_viral_feed_router_returns_ranked_clips() -> None:
    app, session_factory, _current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=58, match_id="viral-router"))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/api/viral/matches/{replay_payload.match_id}/clips")

    assert response.status_code == 200
    body = response.json()
    assert body["clips"]
    assert body["clips"][0]["distribution_accounts"]
    assert len(body["clips"][0]["distribution_accounts"][0]["caption_tests"]) == 2
    assert body["clips"][0]["clip_id"] == f"{replay_payload.match_id}::{body['clips'][0]['highlight_id']}"
    assert body["clips"][0]["editor"]["aspect_ratio"] == "9:16"
    assert len(body["clips"][0]["formats"]) == 5
    assert body["clips"][0]["analytics"]["clip_id"] == body["clips"][0]["highlight_id"]
    assert body["clips"][0]["feedback"]["viral_analysis"]


def test_viral_variant_router_returns_variants_and_winner() -> None:
    app, session_factory, _current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=58, match_id="viral-variants"))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        feed_response = client.get(f"/api/viral/matches/{replay_payload.match_id}/clips")
        clip_id = feed_response.json()["clips"][0]["clip_id"]

        variants_response = client.get(f"/api/viral/clips/{clip_id}/variants")

        assert variants_response.status_code == 200
        variants_body = variants_response.json()
        assert variants_body["resolved"] is False
        assert len(variants_body["variants"]) == 5
        leading_variant_id = variants_body["leading_variant_id"]

    with session_factory() as session:
        winner_candidate = session.get(ClipVariant, leading_variant_id)
        assert winner_candidate is not None
        winner_candidate.view_count = 1800
        winner_candidate.watch_time = 18.0
        winner_candidate.loop_rate = 0.55
        winner_candidate.shares = 260
        winner_candidate.comments = 140
        winner_candidate.completion_rate = 0.97
        winner_candidate.share_rate = 0.22
        winner_candidate.comment_rate = 0.11
        session.commit()

    with TestClient(app) as client:
        winner_response = client.get(f"/api/viral/clips/{clip_id}/winner")

    assert winner_response.status_code == 200
    winner_body = winner_response.json()
    assert winner_body["resolved"] is True
    assert winner_body["decision_reason"] == "view_threshold"
    assert winner_body["winner"]["variant_id"] == leading_variant_id
    assert winner_body["winner"]["pushed_to_trending"] is True


def test_viral_accounts_router_returns_persona_network() -> None:
    app, _session_factory, _current_user = _build_app()

    with TestClient(app) as client:
        response = client.get("/api/viral/accounts")

    assert response.status_code == 200
    body = response.json()
    handles = {item["handle"] for item in body["accounts"]}
    assert "@GTEXGoals" in handles
    assert "@TacticalBreakdown" in handles


def test_trending_router_returns_ranked_clips() -> None:
    app, session_factory, _current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=62, match_id="viral-trending"))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get("/viral/clips/trending", params={"limit": 5, "refresh": True})

    assert response.status_code == 200
    body = response.json()
    assert body["leaderboard_key"] == "leaderboard:clips"
    assert body["refreshed"] is True
    assert body["clips"]
    assert body["clips"][0]["trending_score"] >= body["clips"][-1]["trending_score"]
    assert body["clips"][0]["trending_metrics"]["views_last_60min"] >= body["clips"][0]["trending_metrics"]["views_last_10min"]
    assert "velocity" in body["clips"][0]["trending_metrics"]


def test_personalized_feed_rejects_missing_identity_context() -> None:
    app, session_factory, current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=64, match_id="viral-missing-identity"))
    _insert_match(session_factory, replay_payload)
    del app.dependency_overrides[require_identity]

    with TestClient(app) as client:
        response = client.get(
            "/feed/for-you",
            headers={"Authorization": f"Bearer {create_access_token(current_user.id, claims={'sid': 'session-missing'})}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing identity context"


def test_clip_events_reject_mismatched_identity_context() -> None:
    app, _session_factory, current_user = _build_app()
    del app.dependency_overrides[require_identity]
    payload = {
        "event_id": "1c9d0d3e-19ec-4c46-98fe-66584dba5f1d",
        "clip_id": "match-1::clip-001",
        "user_id": current_user.id,
        "session_id": "session-body",
        "timestamp": "2026-03-28T12:00:00Z",
        "event_type": "view",
        "watch_time_ms": 1900,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "viral_feed",
        },
    }

    with TestClient(app) as client:
        response = client.post(
            "/events/clip",
            json=payload,
            headers=_identity_headers(
                user_id=current_user.id,
                session_id="session-header",
            ),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Event identity does not match authenticated identity."


def test_personalized_feed_router_ranks_and_caches_per_user_feed() -> None:
    app, session_factory, current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=66, match_id="viral-personalized"))
    _insert_match(session_factory, replay_payload)

    with session_factory() as session:
        feed = ViralFeedService(session).build_match_feed(replay_payload.match_id)
        preferred_clip = feed.clips[0]
        session.add_all(
            [
                AnalyticsEvent(
                    name="clip.view",
                    user_id=current_user.id,
                    metadata_json={
                        "clip_id": preferred_clip.clip_id,
                        "creator_id": preferred_clip.distribution_accounts[0].handle,
                        "format_type": preferred_clip.editor.format_key,
                    },
                ),
                AnalyticsEvent(
                    name="clip.like",
                    user_id=current_user.id,
                    metadata_json={
                        "clip_id": preferred_clip.clip_id,
                        "creator_id": preferred_clip.distribution_accounts[0].handle,
                        "format_type": preferred_clip.editor.format_key,
                    },
                ),
                AnalyticsEvent(
                    name="clip.share",
                    user_id=current_user.id,
                    metadata_json={
                        "clip_id": preferred_clip.clip_id,
                        "creator_id": preferred_clip.distribution_accounts[0].handle,
                        "format_type": preferred_clip.editor.format_key,
                    },
                ),
            ]
        )
        session.commit()

    with TestClient(app) as client:
        first_response = client.get("/feed/for-you", params={"limit": 5, "refresh": True})
        second_response = client.get("/feed/for-you", params={"limit": 5})

    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["user_id"] == current_user.id
    assert first_body["feed_key"] == f"user:{current_user.id}:feed"
    assert first_body["feed_source"] == PERSONALIZED_FEED_SOURCE_FOR_YOU
    assert "feed_type" not in first_body
    assert "clips" not in first_body
    assert first_body["cache_hit"] is False
    assert first_body["items"]
    assert first_body["items"][0]["score"] >= first_body["items"][-1]["score"]
    assert any(item["clip_id"] == preferred_clip.clip_id for item in first_body["items"][:3])
    assert first_body["items"][0]["score_breakdown"]["user_affinity"] >= 0.2
    assert "diversity_penalty" in first_body["items"][0]["score_breakdown"]
    assert first_body["items"][0]["score_breakdown"]["orchestrator_weight"] >= 0.0
    assert first_body["items"][0]["score_breakdown"]["session_boost"] >= 1.0
    assert first_body["items"][0]["orchestrator"]["allocated_impressions"] >= first_body["items"][0]["orchestrator"]["consumed_impressions"]
    assert {
        item["feed_source"] for item in first_body["items"]
    } <= {
        PERSONALIZED_FEED_SOURCE_FOR_YOU,
        PERSONALIZED_FEED_SOURCE_FOLLOWING,
    }

    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["cache_hit"] is False
    assert second_body["items"]


def test_personalized_feed_refresh_router_returns_replace_contract(monkeypatch) -> None:
    app, _session_factory, current_user = _build_app()
    _set_test_identity(app, current_user=current_user, session_id="session-refresh")

    class _FakeFeedService:
        def __init__(self) -> None:
            self.recorded = None

        def refresh_for_you(self, *, user_id: str, cursor: int, limit: int, session_id: str | None = None):
            assert user_id == current_user.id
            assert cursor == 1
            assert limit == 5
            assert session_id == "session-refresh"
            return PersonalizedFeedRefreshResponse(
                new_items=[
                    PersonalizedFeedClipView(
                        clip_id="clip-refresh-1",
                        match_id="match-refresh-1",
                        highlight_id="highlight-refresh-1",
                        title="clip-refresh-1",
                        event_type="goal",
                        minute=87,
                        viral_score=88,
                        engagement=80.0,
                        freshness=75.0,
                        ranking_score=70.0,
                        tags=["goal"],
                        breakdown=ViralScoreBreakdownView(total=88),
                        caption=ViralCaptionView(hook="Hook", caption="Caption"),
                        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text="Hook"),
                        formats=[],
                        analytics=ViralClipAnalyticsView(clip_id="clip-refresh-1"),
                        feedback=ViralFeedbackLoopView(
                            performance_tier="high_retention",
                            recommendation="increase",
                            viral_analysis="strong retention",
                        ),
                        metadata={},
                        rank=2,
                        score=1.23,
                        feed_source=PERSONALIZED_FEED_SOURCE_FOR_YOU,
                        score_breakdown=PersonalizedFeedScoreBreakdownView(
                            affinity=PersonalizedFeedAffinityView(),
                            final_score=1.23,
                        ),
                    )
                ],
                replace_indices=[2],
            )

        def record_refresh_delivery(self, *, user_id: str, clips):
            self.recorded = (user_id, [clip.clip_id for clip in clips])

    fake_service = _FakeFeedService()
    monkeypatch.setattr("app.viral.router.build_personalized_feed_service", lambda app, session: fake_service)

    with TestClient(app) as client:
        response = client.get(
            "/feed/for-you/refresh",
            params={"cursor": 1, "limit": 5},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["replace_indices"] == [2]
    assert body["new_items"][0]["clip_id"] == "clip-refresh-1"
    assert fake_service.recorded == (current_user.id, ["clip-refresh-1"])


def test_following_feed_router_returns_a_feed_contract() -> None:
    app, session_factory, current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=68, match_id="viral-following"))
    _insert_match(session_factory, replay_payload)

    with session_factory() as session:
        session.add(
            User(
                id="creator-following-1",
                email="creator-following@example.com",
                username="creator-following",
                password_hash="hashed",
                role=UserRole.USER,
            )
        )
        session.add(Follow(follower_id=current_user.id, following_id="creator-following-1"))
        session.commit()

    with TestClient(app) as client:
        response = client.get("/feed/following", params={"limit": 5, "refresh": True})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == current_user.id
    assert body["feed_source"] == PERSONALIZED_FEED_SOURCE_FOLLOWING
    assert "feed_type" not in body
    assert "clips" not in body
    assert body["feed_key"] == f"user:{current_user.id}:following_feed"
    assert body["items"]


def test_trending_router_filters_capped_clip_on_second_delivery() -> None:
    app, session_factory, _current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=72, match_id="viral-trending-cap"))
    _insert_match(session_factory, replay_payload)

    with session_factory() as session:
        clip = ViralFeedService(session).build_match_feed(
            replay_payload.match_id,
            allocate_impressions=False,
        ).clips[0]
        manager = build_clip_distribution_manager()
        seeded = manager.refresh_distribution(
            clip_id=clip.clip_id,
            viral_score=clip.viral_score,
            analytics=clip.analytics.model_dump(mode="python"),
            performance_tier=clip.feedback.performance_tier,
        )
        seeded.impressions_cap = 1
        seeded.impressions_served = 0
        manager.store.save(seeded)

    with TestClient(app) as client:
        first_response = client.get("/viral/clips/trending", params={"limit": 5, "refresh": True})
        second_response = client.get("/viral/clips/trending", params={"limit": 5})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_ids = [item["clip_id"] for item in first_response.json()["clips"]]
    second_ids = [item["clip_id"] for item in second_response.json()["clips"]]
    assert clip.clip_id in first_ids
    assert clip.clip_id not in second_ids


def test_personalized_feed_router_filters_capped_cached_clip_on_delivery() -> None:
    app, session_factory, current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=74, match_id="viral-personalized-cap"))
    _insert_match(session_factory, replay_payload)

    with session_factory() as session:
        feed = ViralFeedService(session).build_match_feed(replay_payload.match_id, allocate_impressions=False)
        preferred_clip = feed.clips[0]
        manager = build_clip_distribution_manager()
        seeded = manager.refresh_distribution(
            clip_id=preferred_clip.clip_id,
            viral_score=preferred_clip.viral_score,
            analytics=preferred_clip.analytics.model_dump(mode="python"),
            performance_tier=preferred_clip.feedback.performance_tier,
        )
        seeded.impressions_cap = 1
        seeded.impressions_served = 0
        manager.store.save(seeded)
        session.add_all(
            [
                AnalyticsEvent(
                    name="clip.view",
                    user_id=current_user.id,
                    metadata_json={
                        "clip_id": preferred_clip.clip_id,
                        "creator_id": preferred_clip.distribution_accounts[0].handle,
                        "format_type": preferred_clip.editor.format_key,
                    },
                ),
                AnalyticsEvent(
                    name="clip.like",
                    user_id=current_user.id,
                    metadata_json={
                        "clip_id": preferred_clip.clip_id,
                        "creator_id": preferred_clip.distribution_accounts[0].handle,
                        "format_type": preferred_clip.editor.format_key,
                    },
                ),
            ]
        )
        session.commit()

    with TestClient(app) as client:
        first_response = client.get("/feed/for-you", params={"limit": 5, "refresh": True})
        second_response = client.get("/feed/for-you", params={"limit": 5})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_ids = [item["clip_id"] for item in first_response.json()["items"]]
    second_ids = [item["clip_id"] for item in second_response.json()["items"]]
    assert preferred_clip.clip_id in first_ids
    assert preferred_clip.clip_id not in second_ids


def test_clip_event_ingestion_accepts_single_event_payload() -> None:
    class _FakeProducer:
        def __init__(self) -> None:
            self.received = []

        def enqueue_many(self, events):
            self.received.append(events)
            return len(events)

    app, _session_factory, _current_user = _build_app()
    producer = _FakeProducer()
    app.state.clip_event_ingestion_service = producer
    payload = {
        "event_id": "a243d5ca-5363-49cb-96f1-562c708db907",
        "clip_id": "clip-123",
        "user_id": "user-1",
        "session_id": "session-1",
        "timestamp": "2026-03-28T12:00:00Z",
        "event_type": "view",
        "watch_time_ms": 1900,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "feed",
        },
    }

    with TestClient(app) as client:
        response = client.post("/events/clip", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["accepted_events"] == 1
    assert "clip.view" in body["topics"]
    assert producer.received
    assert producer.received[0][0].clip_id == "clip-123"
    assert producer.received[0][0].event_type.value == "view"


def test_clip_event_ingestion_mirrors_live_personalization_state() -> None:
    class _FakeProducer:
        def __init__(self) -> None:
            self.received = []

        def enqueue_many(self, events):
            self.received.append(events)
            return len(events)

    app, session_factory, current_user = _build_app()
    producer = _FakeProducer()
    app.state.clip_event_ingestion_service = producer
    app.dependency_overrides[get_optional_current_user] = lambda: current_user
    _set_test_identity(app, current_user=current_user, session_id="session-live-affinity")
    payload = {
        "event_id": "aa3f63ff-9b9b-4a7e-a73c-6a5d72f3f101",
        "clip_id": "clip-live-affinity",
        "user_id": current_user.id,
        "session_id": "session-live-affinity",
        "timestamp": "2026-03-28T12:00:00Z",
        "event_type": "like",
        "watch_time_ms": 12000,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "feed",
            "creator_id": "creator-live",
            "format_key": "match_recap",
            "clip_event_type": "goal",
        },
    }

    with TestClient(app) as client:
        response = client.post("/events/clip", json=payload)
        session_state = client.get("/api/viral/sessions/session-live-affinity")

    assert response.status_code == 202
    assert session_state.status_code == 200
    assert producer.received
    assert producer.received[0][0].user_id == current_user.id

    with session_factory() as session:
        analytics_events = session.query(AnalyticsEvent).all()
        assert len(analytics_events) == 1
        analytics_event = analytics_events[0]
        assert analytics_event.name == "clip.like"
        assert analytics_event.user_id == current_user.id
        assert analytics_event.metadata_json["clip_id"] == "clip-live-affinity"
        assert analytics_event.metadata_json["session_id"] == "session-live-affinity"
        assert analytics_event.metadata_json["creator_id"] == "creator-live"
        assert analytics_event.metadata_json["format_key"] == "match_recap"
        assert analytics_event.metadata_json["watch_time_seconds"] == 12.0

        affinity_profile = session.get(UserAffinityProfile, current_user.id)
        assert affinity_profile is not None
        assert affinity_profile.favorite_creators_json["creator_live"] > 0.0
        assert affinity_profile.favorite_formats_json["match_recap"] > 0.0
        assert affinity_profile.state_json["event_counts"]["like"] == 1


def test_clip_like_event_credits_creator_wallet_automatically() -> None:
    app, session_factory, current_user = _build_app()
    producer = _ReusableFakeProducer()
    app.state.clip_event_ingestion_service = producer
    creator = User(
        id="creator-wallet-router-1",
        email="creator-wallet-router@example.com",
        username="creator-wallet-router",
        password_hash="hashed",
        role=UserRole.USER,
    )

    with session_factory() as session:
        session.add(creator)
        session.commit()

    payload = {
        "event_id": "4f70dbb1-5379-4279-a9af-084340d0d871",
        "clip_id": "clip-wallet-router-1",
        "user_id": current_user.id,
        "session_id": "session-1",
        "timestamp": "2026-03-29T12:00:00Z",
        "event_type": "like",
        "watch_time_ms": 3200,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "feed",
            "creator_id": creator.id,
        },
    }

    with TestClient(app) as client:
        response = client.post("/events/clip", json=payload)

    assert response.status_code == 202
    assert producer.received

    with session_factory() as session:
        wallet = session.query(CreatorWallet).filter(CreatorWallet.creator_user_id == creator.id).one_or_none()
        logs = session.query(ClipEarningsLog).all()

        assert wallet is not None
        assert wallet.total_impressions == 0
        assert wallet.total_likes == 1
        assert wallet.total_shares == 0
        assert str(wallet.total_earnings_credit) == "0.0100"
        assert len(logs) == 1
        assert logs[0].clip_id == "clip-wallet-router-1"
        assert logs[0].reference_key == "clip-event:4f70dbb1-5379-4279-a9af-084340d0d871"
        assert logs[0].metadata_json["creator_id"] == creator.id

def test_clip_event_ingestion_accepts_batched_events() -> None:
    class _FakeProducer:
        def __init__(self) -> None:
            self.received = []

        def enqueue_many(self, events):
            self.received.append(events)
            return len(events)

    app, _session_factory, _current_user = _build_app()
    producer = _FakeProducer()
    app.state.clip_event_ingestion_service = producer
    payload = {
        "events": [
            {
                "event_id": "3b77b090-abd6-45a4-9046-036f2f1f3d8f",
                "clip_id": "clip-1",
                "user_id": None,
                "session_id": "session-1",
                "timestamp": "2026-03-28T12:00:00Z",
                "event_type": "watch_time",
                "watch_time_ms": 3500,
                "video_length_ms": 10000,
                "metadata": {
                    "device": "android",
                    "country": "US",
                    "referrer": "reel",
                },
            },
            {
                "event_id": "6a0ef78a-ca7f-4e8c-b991-7b1bfbdf2e0c",
                "clip_id": "clip-1",
                "user_id": None,
                "session_id": "session-1",
                "timestamp": "2026-03-28T12:00:01Z",
                "event_type": "scroll",
                "watch_time_ms": 400,
                "video_length_ms": 10000,
                "metadata": {
                    "device": "android",
                    "country": "US",
                    "referrer": "reel",
                },
            },
        ]
    }

    with TestClient(app) as client:
        response = client.post("/events/clip", json=payload)

    assert response.status_code == 202
    assert response.json()["accepted_events"] == 2
    assert len(producer.received[0]) == 2


def test_live_clip_events_personalize_for_you_feed_within_session() -> None:
    app, session_factory, current_user = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(
        build_request(seed=86, match_id="viral-live-personalization")
    )
    _insert_match(session_factory, replay_payload)
    app.state.clip_event_ingestion_service = _ReusableFakeProducer()
    app.dependency_overrides[get_optional_current_user] = lambda: current_user
    _set_test_identity(app, current_user=current_user, session_id="session-live-feedback")

    with session_factory() as session:
        target_clip = ViralFeedService(session).build_match_feed(replay_payload.match_id).clips[0]

    event_payload = {
        "events": [
            {
                "event_id": f"b84286bf-5f3d-48b9-a52d-{index:012d}",
                "clip_id": target_clip.clip_id,
                "user_id": None,
                "session_id": "session-live-feedback",
                "timestamp": f"2026-03-28T12:00:{index:02d}Z",
                "event_type": event_type,
                "watch_time_ms": 12000,
                "video_length_ms": 12000,
                "metadata": {
                    "device": "android",
                    "country": "NG",
                    "referrer": "feed",
                    "creator_id": target_clip.distribution_accounts[0].handle,
                    "format_key": target_clip.editor.format_key,
                    "clip_event_type": target_clip.event_type,
                    "team_name": target_clip.team_name,
                },
            }
            for index, event_type in enumerate(("view", "complete", "like"), start=1)
        ]
    }

    with TestClient(app) as client:
        ingest_response = client.post("/events/clip", json=event_payload)
        feed_response = client.get(
            "/feed/for-you",
            params={"limit": 12, "refresh": True},
        )

    assert ingest_response.status_code == 202
    assert feed_response.status_code == 200
    body = feed_response.json()
    assert body["cache_hit"] is False
    assert body["items"]
    assert all(item["score_breakdown"]["cold_start_exploration"] is False for item in body["items"])
    target_item = next(item for item in body["items"] if item["clip_id"] == target_clip.clip_id)
    assert target_item["score_breakdown"]["user_affinity"] > 0.0
    assert target_item["score_breakdown"]["affinity"]["creator_preference"] > 0.0
    assert target_item["score_breakdown"]["affinity"]["format_preference"] > 0.0


def test_clip_event_ingestion_rejects_invalid_event_type() -> None:
    class _FakeProducer:
        def enqueue_many(self, events):
            return len(events)

    app, _session_factory, _current_user = _build_app()
    app.state.clip_event_ingestion_service = _FakeProducer()
    payload = {
        "event_id": "f0ad85a5-df95-44e0-b3ef-44210fe5ab1a",
        "clip_id": "clip-123",
        "user_id": None,
        "session_id": "session-1",
        "timestamp": "2026-03-28T12:00:00Z",
        "event_type": "replay",
        "watch_time_ms": 1900,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "feed",
        },
    }

    with TestClient(app) as client:
        response = client.post("/events/clip", json=payload)

    assert response.status_code == 422


def test_session_state_router_tracks_events_and_refresh_window() -> None:
    app, session_factory, _current_user = _build_app()
    app.state.clip_event_ingestion_service = _ReusableFakeProducer()
    match_ids: list[str] = []
    for seed in (58, 62, 64):
        replay_payload = MatchSimulationService().build_replay_payload(
            build_request(seed=seed, match_id=f"viral-session-{seed}")
        )
        _insert_match(session_factory, replay_payload)
        match_ids.append(replay_payload.match_id)

    with TestClient(app) as client:
        feed_response = client.get(
            "/api/viral/feed/for-you",
            params={
                "session_id": "session-refresh",
                "limit": 12,
                "match_ids": ",".join(match_ids),
            },
        )

        assert feed_response.status_code == 200
        feed_body = feed_response.json()
        refresh_after = feed_body["session"]["refresh_after_clips"]
        assert 5 <= refresh_after <= 10
        assert len(feed_body["clips"]) >= refresh_after

        event_payload = {
            "events": [
                {
                    "event_id": f"5f89ccf6-8bdf-4ebf-9fe2-{index:012d}",
                    "clip_id": clip["clip_id"],
                    "user_id": None,
                    "session_id": "session-refresh",
                    "timestamp": f"2026-03-28T12:00:{index:02d}Z",
                    "event_type": "view",
                    "watch_time_ms": 1200,
                    "video_length_ms": 10000,
                    "metadata": {
                        "device": "ios",
                        "country": "NG",
                        "referrer": "feed",
                    },
                }
                for index, clip in enumerate(feed_body["clips"][:refresh_after], start=1)
            ]
        }
        ingest_response = client.post("/events/clip", json=event_payload)

        assert ingest_response.status_code == 202

        session_state_response = client.get("/api/viral/sessions/session-refresh")

        assert session_state_response.status_code == 200
        session_state_body = session_state_response.json()
        assert session_state_body["clips_seen"] == refresh_after
        assert session_state_body["watch_time_ms"] == refresh_after * 1200
        assert session_state_body["pending_refresh"] is True
        assert session_state_body["clips_until_refresh"] == 0

        refreshed_response = client.get(
            "/api/viral/feed/for-you",
            params={
                "session_id": "session-refresh",
                "limit": 12,
                "match_ids": ",".join(match_ids),
            },
        )

    assert refreshed_response.status_code == 200
    refreshed_body = refreshed_response.json()
    assert refreshed_body["session"]["refreshed"] is True
    assert refreshed_body["session"]["pending_refresh"] is False
    assert 5 <= refreshed_body["session"]["refresh_after_clips"] <= 10


def test_session_aware_feed_router_applies_session_affinity() -> None:
    app, session_factory, _current_user = _build_app()
    app.state.clip_event_ingestion_service = _ReusableFakeProducer()
    replay_payload = MatchSimulationService().build_replay_payload(
        build_request(seed=58, match_id="viral-session-affinity")
    )
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        discovery_response = client.get(
            "/api/viral/feed/for-you",
            params={"session_id": "session-affinity", "match_ids": replay_payload.match_id, "limit": 12},
        )

        assert discovery_response.status_code == 200
        discovery_body = discovery_response.json()
        assert discovery_body["clips"]

        favorite_clip = discovery_body["clips"][0]
        target_clip = next(
            clip
            for clip in discovery_body["clips"]
            if clip["clip_id"] != favorite_clip["clip_id"]
            and (
                clip.get("team_name") != favorite_clip.get("team_name")
                or clip["event_type"] != favorite_clip["event_type"]
            )
        )

        baseline_response = client.get(
            "/api/viral/feed/for-you",
            params={
                "session_id": "session-affinity",
                "match_ids": replay_payload.match_id,
                "limit": 12,
                "favorite_team": favorite_clip.get("team_name"),
                "favorite_event_types": favorite_clip["event_type"],
            },
        )

        assert baseline_response.status_code == 200
        baseline_body = baseline_response.json()
        baseline_target = next(clip for clip in baseline_body["clips"] if clip["clip_id"] == target_clip["clip_id"])

        event_payload = {
            "event_id": "5931f050-84d8-4b4e-a1ef-9a00c0f4e101",
            "clip_id": target_clip["clip_id"],
            "user_id": None,
            "session_id": "session-affinity",
            "timestamp": "2026-03-28T12:05:00Z",
            "event_type": "complete",
            "watch_time_ms": 12000,
            "video_length_ms": 12000,
            "metadata": {
                "device": "android",
                "country": "NG",
                "referrer": "feed",
            },
        }
        ingest_response = client.post("/events/clip", json=event_payload)

        assert ingest_response.status_code == 202

        personalized_response = client.get(
            "/api/viral/feed/for-you",
            params={
                "session_id": "session-affinity",
                "match_ids": replay_payload.match_id,
                "limit": 12,
                "favorite_team": favorite_clip.get("team_name"),
                "favorite_event_types": favorite_clip["event_type"],
            },
        )

    assert personalized_response.status_code == 200
    personalized_body = personalized_response.json()
    personalized_target = next(clip for clip in personalized_body["clips"] if clip["clip_id"] == target_clip["clip_id"])
    assert personalized_body["session"]["override_global_affinity"] is True
    assert personalized_target["ranking_score"] > baseline_target["ranking_score"]
    assert personalized_target["metadata"]["session_score_adjustment"] > 0


def test_trust_routes_return_weighted_profile_state() -> None:
    app, _session_factory, current_user = _build_app()
    app.state.clip_event_ingestion_service = _ReusableFakeProducer()
    payload = {
        "events": [
            {
                "event_id": f"3c9f33ff-bf79-4baf-84c7-{index:012d}",
                "clip_id": "clip-trust",
                "user_id": current_user.id,
                "session_id": "session-trust",
                "timestamp": f"2026-03-28T12:00:{index:02d}Z",
                "event_type": "loop",
                "watch_time_ms": 12000,
                "video_length_ms": 12000,
                "metadata": {
                    "device": "ios",
                    "country": "NG",
                    "referrer": "feed",
                },
            }
            for index in range(1, 6)
        ]
    }

    with TestClient(app) as client:
        ingest_response = client.post("/events/clip", json=payload, headers={"x-device-id": "device-trust-1"})
        me_response = client.get("/trust/me")
        user_response = client.get(f"/trust/{current_user.id}")

    assert ingest_response.status_code == 202
    assert me_response.status_code == 200
    assert user_response.status_code == 200
    me_body = me_response.json()
    assert me_body["user_id"] == current_user.id
    assert me_body["trust_score"] < 0.55
    assert "repeated_loop_session" in me_body["suspicious_flags"]
    assert me_body["factors"]["device_fingerprint_stability"] >= 0.75
    assert user_response.json()["trust_score"] == me_body["trust_score"]
