from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.router import router as ads_router
from app.ads_engine.service import AudienceContext, OrganicCandidate, SponsoredClipService
from app.analytics.service import AnalyticsService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.infinite_league.router import router as infinite_league_router
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.creator_attention_earnings import ClipEarningsLog, CreatorWallet
from app.models.creator_profile import CreatorProfile
from app.models.event_backbone import EventOutbox
from app.models.highlight_event import HighlightEvent
from app.models.manager_duel import ManagerDuel
from app.models.spectator_session import SpectatorSession
from app.models.sponsored_clip import SponsoredClip
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.models.user_affinity_profile import UserAffinityProfile
from app.models.user_region import UserRegionProfile
from app.replay_archive.persistence import ReplayArchiveRecordRow
from app.services.creator_attention_earnings_service import CreatorAttentionEarningsService
from app.viral.schemas import ViralClipView
from app.viral.trust import InMemoryTrustStateStore, TrustFactorBreakdown, TrustScoreService, TrustState


def _build_app() -> tuple[TestClient, sessionmaker[Session], User, User]:
    app = FastAPI()
    app.include_router(ads_router)
    app.include_router(infinite_league_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            AnalyticsEvent.__table__,
            CompetitionMatch.__table__,
            CreatorWallet.__table__,
            ClipEarningsLog.__table__,
            CreatorProfile.__table__,
            EventOutbox.__table__,
            HighlightEvent.__table__,
            ManagerDuel.__table__,
            ReplayArchiveRecordRow.__table__,
            SpectatorSession.__table__,
            SponsoredClip.__table__,
            StoryFeedItem.__table__,
            User.__table__,
            UserAffinityProfile.__table__,
            UserRegionProfile.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    with session_factory() as session:
        admin = User(
            id="admin-1",
            email="admin@example.com",
            username="admin",
            password_hash="unused",
            role=UserRole.ADMIN,
            is_active=True,
        )
        viewer = User(
            id="viewer-1",
            email="viewer@example.com",
            username="viewer",
            password_hash="unused",
            role=UserRole.USER,
            is_active=True,
        )
        session.add_all(
            [
                admin,
                User(
                    id="advertiser-1",
                    email="advertiser@example.com",
                    username="advertiser",
                    password_hash="unused",
                    role=UserRole.USER,
                    is_active=True,
                ),
                viewer,
                UserAffinityProfile(
                    user_id=viewer.id,
                    favorite_formats_json={"instant_clip": 1.0},
                    favorite_creators_json={},
                    affinity_vector_json={"format:instant_clip": 1.0},
                    avg_watch_time=28.0,
                    skip_rate=0.1,
                    session_duration=120.0,
                    engagement_score=0.8,
                    state_json={},
                ),
                UserRegionProfile(
                    user_id=viewer.id,
                    region_code="NG",
                ),
            ]
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_current_user] = lambda: viewer
    return TestClient(app), session_factory, admin, viewer


def _seed_clip(client: TestClient) -> dict:
    tick_response = client.post("/infinite-league/tick", params={"count": 6})
    assert tick_response.status_code == 200, tick_response.text
    feed_response = client.get("/infinite-league/viral-feed", params={"limit": 12})
    assert feed_response.status_code == 200, feed_response.text
    clips = feed_response.json()["clips"]
    assert clips
    return clips[0]


def _create_ad(
    client: TestClient,
    *,
    clip_id: str,
    budget: str = "120.0000",
    metadata_json: dict | None = None,
) -> dict:
    now = datetime.now(UTC)
    response = client.post(
        "/ads/create",
        json={
            "advertiser_id": "advertiser-1",
            "clip_id": clip_id,
            "budget": budget,
            "bid_cpm": "12.0000",
            "target_audience": {
                "formats": ["instant_clip"],
                "creators": [],
                "regions": ["NG"],
            },
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "metadata_json": metadata_json or {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_ad_and_read_performance() -> None:
    with _build_app()[0] as client:
        clip = _seed_clip(client)
        created = _create_ad(client, clip_id=clip["clip_id"])
        performance = client.get("/ads/performance")

        assert performance.status_code == 200, performance.text
        payload = performance.json()
        assert payload["summary"]["ad_count"] == 1
        assert payload["ads"][0]["id"] == created["id"]
        assert payload["ads"][0]["clip_id"] == clip["clip_id"]
        assert payload["ads"][0]["max_impressions"] == 10000
        assert payload["ads"][0]["remaining_impressions"] == 10000


def test_sponsored_feed_injects_one_ad_without_duplicate_clip() -> None:
    with _build_app()[0] as client:
        clip = _seed_clip(client)
        _create_ad(client, clip_id=clip["clip_id"])

        response = client.get("/feed/sponsored", params={"limit": 12})
        assert response.status_code == 200, response.text
        payload = response.json()

        sponsored_items = [item for item in payload["items"] if item["item_type"] == "sponsored"]
        assert sponsored_items
        assert sponsored_items[0]["campaign"]["tracking"]["impression_event"] == "sponsored_clip.impression"
        served_clip_ids = [item["clip_id"] for item in payload["items"]]
        assert served_clip_ids.count(clip["clip_id"]) == 1

        performance = client.get("/ads/performance").json()
        assert performance["ads"][0]["impressions_served"] == 1


def test_sponsored_feed_credits_creator_wallet_on_delivery(monkeypatch) -> None:
    client, session_factory, _admin, viewer = _build_app()

    with client:
        clip = _seed_clip(client)

    with session_factory() as session:
        session.add(
            User(
                id="creator-sponsored-wallet-1",
                email="creator-sponsored-wallet@example.com",
                username="creator-sponsored-wallet",
                password_hash="unused",
                role=UserRole.USER,
                is_active=True,
            )
        )
        session.commit()

    with session_factory() as session:
        service = SponsoredClipService(
            session=session,
            creator_earnings_service=CreatorAttentionEarningsService(session=session),
        )
        feed_clip = ViralClipView.model_validate(
            {
                **clip,
                "metadata": {
                    **dict(clip.get("metadata") or {}),
                    "creator_user_id": "creator-sponsored-wallet-1",
                    "creator_id": "creator-sponsored-wallet-1",
                },
            }
        )

        monkeypatch.setattr(
            SponsoredClipService,
            "_build_organic_candidates",
            lambda self, *, user, limit, refresh: [
                OrganicCandidate(
                    clip=feed_clip,
                    organic_score=0.98,
                    organic_rank=1,
                )
            ],
        )
        monkeypatch.setattr(SponsoredClipService, "_recent_clip_lookup", lambda self, *, limit: {})
        monkeypatch.setattr(
            SponsoredClipService,
            "_audience_context",
            lambda self, *, user, region=None: AudienceContext(
                user_id=user.id,
                region=region or "NG",
                favorite_formats={},
                favorite_creators={},
                engagement_score=0.8,
                avg_watch_time=24.0,
                skip_rate=0.1,
            ),
        )
        monkeypatch.setattr(SponsoredClipService, "_rank_ads", lambda self, *, context, clip_lookup, now: [])

        response = service.build_sponsored_feed(user=viewer, limit=12)

        assert response.items
        assert response.items[0].clip_id == clip["clip_id"]

        session.commit()

    with session_factory() as session:
        wallet = session.query(CreatorWallet).filter(CreatorWallet.creator_user_id == "creator-sponsored-wallet-1").one_or_none()
        logs = session.query(ClipEarningsLog).filter(ClipEarningsLog.creator_user_id == "creator-sponsored-wallet-1").all()

        assert wallet is not None
        assert wallet.total_impressions == 1
        assert wallet.total_earnings_credit == Decimal("0.0020")
        assert len(logs) == 1
        assert logs[0].metadata_json["feed_source"] == "sponsored_feed"


def test_unified_feed_keeps_ads_spaced_to_one_per_five_clips() -> None:
    with _build_app()[0] as client:
        tick_response = client.post("/infinite-league/tick", params={"count": 8})
        assert tick_response.status_code == 200, tick_response.text
        feed_response = client.get("/infinite-league/viral-feed", params={"limit": 12})
        assert feed_response.status_code == 200, feed_response.text
        clips = feed_response.json()["clips"][:3]
        assert len(clips) == 3
        for clip in clips:
            _create_ad(client, clip_id=clip["clip_id"])

        response = client.get("/feed/sponsored", params={"limit": 15})
        assert response.status_code == 200, response.text
        payload = response.json()

        sponsored_positions = [
            item["slot_index"]
            for item in payload["items"]
            if item["item_type"] == "sponsored"
        ]
        assert sponsored_positions
        assert all(
            (right - left) >= 5
            for left, right in zip(sponsored_positions, sponsored_positions[1:], strict=False)
        )


def test_low_trust_advertiser_is_filtered_from_unified_feed() -> None:
    client, _session_factory, _admin, _viewer = _build_app()
    with client:
        trust_store = InMemoryTrustStateStore()
        trust_store.save_trust_state(
            TrustState(
                user_id="advertiser-1",
                trust_score=0.1,
                suspicious_event_count=5,
                healthy_event_count=0,
                shadow_banned=False,
                monetization_eligible=False,
                ranking_eligible=False,
                suspicious_flags=("low_trust_advertiser",),
                factors=TrustFactorBreakdown(
                    account_age=0.2,
                    session_consistency=0.2,
                    device_fingerprint_stability=0.2,
                    engagement_authenticity=0.2,
                    anomaly_detection=0.2,
                ),
                updated_at=datetime.now(UTC),
            )
        )
        client.app.state.trust_score_service = TrustScoreService(store=trust_store)
        clip = _seed_clip(client)
        _create_ad(client, clip_id=clip["clip_id"])

        response = client.get("/feed/sponsored", params={"limit": 12})
        assert response.status_code == 200, response.text
        assert not any(item["item_type"] == "sponsored" for item in response.json()["items"])

        performance = client.get("/ads/performance").json()["ads"][0]
        assert performance["eligible"] is False
        assert performance["revenue_attribution"]["creator_share"] == "0.0000"


def test_budget_cap_stops_serving_after_impression_limit() -> None:
    with _build_app()[0] as client:
        clip = _seed_clip(client)
        _create_ad(client, clip_id=clip["clip_id"], budget="0.0120")

        first_response = client.get("/feed/sponsored", params={"limit": 12})
        second_response = client.get("/feed/sponsored", params={"limit": 12})

        assert first_response.status_code == 200, first_response.text
        assert any(item["item_type"] == "sponsored" for item in first_response.json()["items"])
        assert second_response.status_code == 200, second_response.text
        assert not any(item["item_type"] == "sponsored" for item in second_response.json()["items"])


def test_clip_trust_weights_ad_billing() -> None:
    with _build_app()[0] as client:
        clip = _seed_clip(client)
        _create_ad(
            client,
            clip_id=clip["clip_id"],
            metadata_json={"avg_trust_score": 0.5, "clip_trust_score": 0.5},
        )

        response = client.get("/feed/sponsored", params={"limit": 12})
        assert response.status_code == 200, response.text
        assert any(item["item_type"] == "sponsored" for item in response.json()["items"])

        performance = client.get("/ads/performance").json()["ads"][0]
        assert performance["spend"] == "0.0060"
        assert performance["revenue_attribution"]["creator_share"] == "0.0030"


def test_analytics_events_update_click_watch_and_conversion_metrics() -> None:
    client, session_factory, _admin, viewer = _build_app()
    with client:
        clip = _seed_clip(client)
        created = _create_ad(client, clip_id=clip["clip_id"])
        client.get("/feed/sponsored", params={"limit": 12})

        with session_factory() as session:
            analytics = AnalyticsService()
            analytics.track_event(
                session,
                name="sponsored_clip.click",
                user_id=viewer.id,
                metadata={"ad_id": created["id"]},
            )
            analytics.track_event(
                session,
                name="sponsored_clip.watch",
                user_id=viewer.id,
                metadata={"ad_id": created["id"], "watch_time_seconds": 18},
            )
            analytics.track_event(
                session,
                name="sponsored_clip.conversion",
                user_id=viewer.id,
                metadata={"ad_id": created["id"]},
            )
            session.commit()

        performance = client.get("/ads/performance").json()["ads"][0]
        assert performance["impressions_served"] == 1
        assert performance["clicks"] == 1
        assert performance["conversions"] == 1
        assert performance["total_watch_time_seconds"] == 18.0
        assert performance["ctr"] == 1.0
        assert performance["revenue_attribution"]["creator_share"] == "0.0060"
