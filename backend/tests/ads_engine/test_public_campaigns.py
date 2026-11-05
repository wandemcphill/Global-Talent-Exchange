from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.router import public_router
from app.auth.dependencies import get_session
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign


def _client() -> tuple[TestClient, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(public_router)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models.brand_advertising import BrandAdEvent

    Base.metadata.create_all(engine, tables=[BrandAdCampaign.__table__, BrandAdEvent.__table__])
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), factory


def _campaign(*, campaign_id: str, placement: str, now: datetime, **overrides) -> BrandAdCampaign:
    values = {
        "id": campaign_id,
        "brand_name": f"Brand {campaign_id}",
        "headline": "A real campaign headline",
        "description": "A public campaign description",
        "placement": placement,
        "destination_url": "https://example.com/campaign",
        "logo_url": "https://example.com/logo.png",
        "creative_url": None,
        "start_at": now - timedelta(hours=1),
        "end_at": now + timedelta(days=7),
        "priority": 100,
        "is_approved": True,
        "is_active": True,
        "campaign_type": "brand",
        "status": "approved",
    }
    values.update(overrides)
    return BrandAdCampaign(**values)


def test_public_feed_returns_only_approved_active_campaigns_in_window() -> None:
    client, factory = _client()
    now = datetime.now(UTC)

    with factory() as session:
        session.add_all(
            [
                _campaign(campaign_id="live-rail", placement="homepage_rail", now=now, priority=200),
                _campaign(campaign_id="live-auth", placement="auth_canvas", now=now),
                _campaign(campaign_id="unapproved", placement="homepage_rail", now=now, is_approved=False),
                _campaign(campaign_id="paused", placement="homepage_rail", now=now, is_active=False),
                _campaign(
                    campaign_id="scheduled",
                    placement="homepage_rail",
                    now=now,
                    start_at=now + timedelta(days=1),
                ),
                _campaign(
                    campaign_id="expired",
                    placement="homepage_rail",
                    now=now,
                    end_at=now - timedelta(seconds=1),
                ),
                _campaign(
                    campaign_id="unsafe-url",
                    placement="homepage_rail",
                    now=now,
                    destination_url="javascript:alert(1)",
                ),
            ]
        )
        session.commit()

    with client:
        response = client.get("/public/ads/campaigns")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert [item["id"] for item in payload["campaigns"]] == ["live-rail", "live-auth"]
        assert response.headers["cache-control"].startswith("public")

        rail_response = client.get("/public/ads/campaigns", params={"placement": "homepage_rail"})
        assert rail_response.status_code == 200
        assert [item["id"] for item in rail_response.json()["campaigns"]] == ["live-rail"]


def test_public_feed_rejects_unknown_placement() -> None:
    client, _factory = _client()
    with client:
        response = client.get("/public/ads/campaigns", params={"placement": "unknown-placement"})
        assert response.status_code == 422


def test_public_music_promotions_and_audio_telemetry_events() -> None:
    client, factory = _client()
    now = datetime.now(UTC)
    cid_verified = "11111111-2222-3333-4444-555555555555"
    cid_unverified = "99999999-8888-7777-6666-555555555555"

    # Add verified music campaign and unverified music campaign
    with factory() as session:
        session.add_all([
            _campaign(
                campaign_id=cid_verified,
                placement="music_track",
                campaign_type="music",
                now=now,
                music_target_type="track",
                music_target_id="track_101",
                music_title="Lagos Nights",
                music_artist_name="Kazeem",
                music_rights_verified=True,
                music_rights_holder="AfroBeats Universal",
                destination_url="https://open.spotify.com/track/101",
            ),
            _campaign(
                campaign_id=cid_unverified,
                placement="music_track",
                campaign_type="music",
                now=now,
                music_target_type="track",
                music_target_id="track_102",
                music_title="Bootleg Song",
                music_artist_name="Unknown Artist",
                music_rights_verified=False,
                destination_url="https://open.spotify.com/track/102",
            ),
        ])
        session.commit()

    with client:
        # 1. /public/ads/music/promotions only returns rights-verified campaigns
        res = client.get("/public/ads/music/promotions")
        assert res.status_code == 200
        data = res.json()
        assert len(data["promotions"]) == 1
        assert data["promotions"][0]["campaign_id"] == cid_verified
        assert data["promotions"][0]["track_title"] == "Lagos Nights"
        assert data["promotions"][0]["music_rights_verified"] is True

        # 2. Audio telemetry events accepted: play_requested, play_started, milestone_50, completed
        for event_type in ["play_requested", "play_started", "milestone_25", "milestone_50", "completed", "muted"]:
            ev_res = client.post(
                "/public/ads/events",
                json={
                    "campaign_id": cid_verified,
                    "event_type": event_type,
                    "idempotency_key": f"test-key-{event_type}-001",
                    "metadata_json": {"source": "gtex_audio_manager", "progress_ms": 50000},
                },
            )
            assert ev_res.status_code == 200, f"Failed for {event_type}: {ev_res.text}"
            assert ev_res.json()["accepted"] is True
