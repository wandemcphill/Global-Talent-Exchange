from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.brand_campaigns import public_router, router
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.user import User, UserRole


def _client() -> tuple[TestClient, sessionmaker[Session], User, User]:
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_router, prefix="/public/ads")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            BrandAdCampaign.__table__,
            BrandAdvertiserProfile.__table__,
            BrandAdEvent.__table__,
            BrandAdReviewEvent.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    advertiser = User(
        id="00000000-0000-4000-8000-000000000001",
        email="advertiser@example.com",
        username="advertiser",
        password_hash="x",
        role=UserRole.USER,
    )
    admin = User(
        id="00000000-0000-4000-8000-000000000002",
        email="admin@example.com",
        username="admin",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    with factory() as session:
        session.add_all([advertiser, admin])
        session.commit()

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: advertiser
    app.dependency_overrides[get_optional_current_user] = lambda: advertiser
    app.dependency_overrides[get_current_admin] = lambda: admin
    return TestClient(app), factory, advertiser, admin


def _yield_session(factory):
    with factory() as session:
        yield session


def _payload(**updates):
    now = datetime.now(UTC)
    value = {
        "campaign_type": "brand",
        "brand_name": "GTEX Partner",
        "headline": "Reach the GTEX audience",
        "description": "A public partner campaign",
        "placement": "homepage_rail",
        "destination_url": "https://example.com/campaign",
        "logo_url": "https://example.com/logo.png",
        "creative_url": None,
        "start_at": (now - timedelta(minutes=1)).isoformat(),
        "end_at": (now + timedelta(days=10)).isoformat(),
        "budget_amount": "250.00",
        "currency": "USD",
        "pricing_model": "CPM",
        "unit_price": "4.5000",
    }
    value.update(updates)
    return value


def test_advertiser_profile_campaign_ownership_and_review_flow():
    client, factory, advertiser, _admin = _client()
    with client:
        response = client.put(
            "/ads/brand/profile",
            json={
                "company_name": "Partner Ltd",
                "contact_name": "Campaign Owner",
                "website_url": "https://example.com",
                "billing_email": "billing@example.com",
            },
        )
        assert response.status_code == 200, response.text

        created = client.post("/ads/brand/campaigns", json=_payload())
        assert created.status_code == 201, created.text
        campaign_id = created.json()["id"]
        assert created.json()["status"] == "draft"

        submitted = client.post(f"/ads/brand/campaigns/{campaign_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "pending"

        admin_review = client.post(
            f"/ads/brand/admin/campaigns/{campaign_id}/review",
            json={"action": "approve", "note": "Creative checked"},
        )
        assert admin_review.status_code == 200, admin_review.text
        assert admin_review.json()["status"] == "approved"

        history = client.get(f"/ads/brand/campaigns/{campaign_id}/history")
        assert history.status_code == 200, history.text
        assert {event["action"] for event in history.json()} == {"submitted", "approve"}
        with factory() as session:
            campaign = session.get(BrandAdCampaign, campaign_id)
            assert campaign is not None
            assert campaign.advertiser_id == advertiser.id
            assert session.query(BrandAdReviewEvent).filter_by(campaign_id=campaign_id).count() == 2


def test_idempotent_events_and_music_promotion_disclosure_fields():
    client, factory, advertiser, _admin = _client()
    now = datetime.now(UTC)
    with factory() as session:
        profile = BrandAdvertiserProfile(
            user_id=advertiser.id,
            company_name="Music Label",
            contact_name="Artist Manager",
            billing_email="billing@example.com",
        )
        campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="GTEX TRAX Artist",
            headline="Listen to the new single",
            description="Official artist promotion",
            placement="music_track",
            destination_url="https://example.com/listen",
            start_at=now - timedelta(minutes=1),
            end_at=now + timedelta(days=1),
            budget_amount=Decimal("50.00"),
            currency="USD",
            pricing_model="CPC",
            unit_price=Decimal("0.25"),
            status="approved",
            is_approved=True,
            is_active=True,
            music_target_type="track",
            music_target_id="gtex-trax-afro-01",
            music_title="Lagos Nightlights",
            music_artist_name="Kazeem",
        )
        session.add_all([profile, campaign])
        session.commit()
        campaign_id = campaign.id

    payload = {
        "campaign_id": campaign_id,
        "event_type": "impression",
        "idempotency_key": "music-impression-0001",
        "metadata_json": {},
    }
    with client:
        first = client.post("/public/ads/events", json=payload)
        second = client.post("/public/ads/events", json=payload)
        promotions = client.get("/public/ads/music/promotions")
        assert first.status_code == 200, first.text
        assert first.json()["duplicate"] is False
        assert second.status_code == 200, second.text
        assert second.json()["duplicate"] is True
        assert promotions.status_code == 200
        assert promotions.json()["promotions"][0]["target_id"] == "gtex-trax-afro-01"
