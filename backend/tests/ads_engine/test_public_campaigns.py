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
