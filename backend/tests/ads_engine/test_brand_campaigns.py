from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.brand_campaigns import record_server_brand_delivery, router
from app.ads_engine.router import public_router as delivery_router
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.user import User, UserRole


def _client() -> tuple[TestClient, sessionmaker[Session], User, User]:
    app = FastAPI()
    app.include_router(router)
    app.include_router(delivery_router)
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
        with factory() as session:
            draft = session.get(BrandAdCampaign, campaign_id)
            assert draft is not None
            assert draft.payment_status == "unpaid"

        forged = client.post("/ads/brand/campaigns", json={**_payload(), "payment_status": "paid"})
        assert forged.status_code == 422

        submitted = client.post(f"/ads/brand/campaigns/{campaign_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "pending"

        unpaid_review = client.post(
            f"/ads/brand/admin/campaigns/{campaign_id}/review",
            json={"action": "approve", "note": "Creative checked"},
        )
        assert unpaid_review.status_code == 409, unpaid_review.text

        hidden = client.get("/public/ads/campaigns")
        assert hidden.status_code == 200, hidden.text
        assert campaign_id not in {item["id"] for item in hidden.json()["campaigns"]}
        with factory() as session:
            campaign = session.get(BrandAdCampaign, campaign_id)
            assert campaign is not None
            assert campaign.status == "pending"
            assert campaign.is_approved is False
            assert campaign.is_active is False
            assert campaign.advertiser_id == advertiser.id
            campaign.payment_status = "paid"
            session.commit()

        admin_review = client.post(
            f"/ads/brand/admin/campaigns/{campaign_id}/review",
            json={"action": "approve", "note": "Creative checked"},
        )
        assert admin_review.status_code == 200, admin_review.text
        assert admin_review.json()["status"] == "approved"

        live = client.get("/public/ads/campaigns")
        assert live.status_code == 200, live.text
        assert campaign_id in {item["id"] for item in live.json()["campaigns"]}

        history = client.get(f"/ads/brand/campaigns/{campaign_id}/history")
        assert history.status_code == 200, history.text
        assert {event["action"] for event in history.json()} == {"submitted", "approve"}
        with factory() as session:
            campaign = session.get(BrandAdCampaign, campaign_id)
            assert campaign is not None
            assert campaign.advertiser_id == advertiser.id
            assert campaign.payment_status == "paid"
            assert session.query(BrandAdReviewEvent).filter_by(campaign_id=campaign_id).count() == 2


def test_unpaid_approved_campaign_is_absent_from_public_feed():
    client, factory, advertiser, _admin = _client()
    now = datetime.now(UTC)
    with factory() as session:
        unpaid = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="brand",
            brand_name="Unpaid Partner",
            headline="Should stay off the feed",
            description="Approved on paper, never paid",
            placement="homepage_rail",
            destination_url="https://example.com/unpaid",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=3),
            budget_amount=Decimal("100.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("5.0000"),
            status="approved",
            is_approved=True,
            is_active=True,
            payment_status="unpaid",
        )
        paid = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="brand",
            brand_name="Paid Partner",
            headline="Cleared for the homepage",
            description="Approved and paid",
            placement="homepage_rail",
            destination_url="https://example.com/paid",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=3),
            budget_amount=Decimal("100.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("5.0000"),
            status="approved",
            is_approved=True,
            is_active=True,
            payment_status="paid",
        )
        unpaid_music = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Unpaid Label",
            headline="Unpaid rotation",
            description="Rights cleared, invoice open",
            placement="music_track",
            destination_url="https://example.com/unpaid-track",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=3),
            budget_amount=Decimal("40.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("2.0000"),
            status="approved",
            is_approved=True,
            is_active=True,
            payment_status="unpaid",
            music_target_type="track",
            music_target_id="trax-unpaid",
            music_title="Unpaid Single",
            music_artist_name="Open Invoice",
            music_rights_verified=True,
        )
        paid_music = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Paid Label",
            headline="Paid rotation",
            description="Rights cleared and settled",
            placement="music_track",
            destination_url="https://example.com/paid-track",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=3),
            budget_amount=Decimal("40.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("2.0000"),
            status="approved",
            is_approved=True,
            is_active=True,
            payment_status="paid",
            music_target_type="track",
            music_target_id="trax-paid",
            music_title="Paid Single",
            music_artist_name="Settled Invoice",
            music_rights_verified=True,
        )
        session.add_all([unpaid, paid, unpaid_music, paid_music])
        session.commit()
        unpaid_id = unpaid.id
        paid_id = paid.id

    with client:
        feed = client.get("/public/ads/campaigns")
        assert feed.status_code == 200, feed.text
        ids = [item["id"] for item in feed.json()["campaigns"]]
        assert paid_id in ids
        assert unpaid_id not in ids

        music = client.get("/public/ads/music/promotions")
        assert music.status_code == 200, music.text
        targets = [item["target_id"] for item in music.json()["promotions"]]
        assert "trax-paid" in targets
        assert "trax-unpaid" not in targets


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
            music_rights_verified=True,
            music_rights_holder="Afrobeat Collective",
            payment_status="paid",
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
        assert promotions.json()["promotions"][0]["music_rights_verified"] is True
        assert promotions.json()["promotions"][0]["music_rights_holder"] == "Afrobeat Collective"


def test_music_rights_verification_admin_endpoint():
    client, factory, advertiser, admin = _client()
    now = datetime.now(UTC)
    with factory() as session:
        profile = BrandAdvertiserProfile(
            user_id=advertiser.id,
            company_name="Major Trax Records",
            contact_name="A&R Lead",
            billing_email="ar@traxrecords.com",
        )
        music_campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Major Trax",
            headline="Promote Afrobeats Anthem",
            description="Clearance pending campaign",
            placement="music_track",
            destination_url="https://example.com/track",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=7),
            budget_amount=Decimal("100.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("5.0000"),
            status="pending",
            is_approved=False,
            is_active=False,
            music_target_type="track",
            music_target_id="trax-anthem-42",
            music_title="Vibes from Lagos",
            music_artist_name="Tunde & The Crew",
            music_rights_verified=False,
        )
        brand_campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="brand",
            brand_name="Tech Brand",
            headline="Global Cloud Services",
            description="Non-music campaign",
            placement="homepage_rail",
            destination_url="https://example.com/cloud",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=7),
            budget_amount=Decimal("100.00"),
            currency="USD",
            pricing_model="CPM",
            unit_price=Decimal("5.0000"),
            status="pending",
            is_approved=False,
            is_active=False,
        )
        session.add_all([profile, music_campaign, brand_campaign])
        session.commit()
        music_campaign_id = music_campaign.id
        brand_campaign_id = brand_campaign.id

    with client:
        # Non-music campaign cannot be verified for music rights
        invalid_type_res = client.put(
            f"/ads/brand/admin/campaigns/{brand_campaign_id}/music-rights",
            json={
                "music_rights_verified": True,
                "music_rights_holder": "Some Publisher",
                "music_license_doc_url": "https://example.com/license.pdf",
                "note": "Invalid attempt",
            },
        )
        assert invalid_type_res.status_code == 400
        assert "only applies to music campaigns" in invalid_type_res.text

        # Verify music rights on valid music campaign
        verify_res = client.put(
            f"/ads/brand/admin/campaigns/{music_campaign_id}/music-rights",
            json={
                "music_rights_verified": True,
                "music_rights_holder": "Afrobeats Global Publishing Ltd",
                "music_license_doc_url": "https://example.com/cleared-license.pdf",
                "note": "Master recording and publishing agreement verified",
            },
        )
        assert verify_res.status_code == 200, verify_res.text
        data = verify_res.json()
        assert data["music_rights_verified"] is True
        assert data["music_rights_holder"] == "Afrobeats Global Publishing Ltd"
        assert data["music_license_doc_url"] == "https://example.com/cleared-license.pdf"

        # Verify review event history
        history = client.get(f"/ads/brand/campaigns/{music_campaign_id}/history")
        assert history.status_code == 200
        events = history.json()
        assert any(e["action"] == "verify_music_rights" for e in events)


def test_unverified_music_campaign_excluded_from_public_promotions():
    client, factory, advertiser, _admin = _client()
    now = datetime.now(UTC)
    with factory() as session:
        profile = BrandAdvertiserProfile(
            user_id=advertiser.id,
            company_name="Indie Label",
            contact_name="Indie Producer",
            billing_email="indie@example.com",
        )
        # Approved and active, BUT music_rights_verified is False
        unverified_campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Unverified Artist",
            headline="Check out my demo",
            description="Unverified track",
            placement="music_track",
            destination_url="https://example.com/demo",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=7),
            budget_amount=Decimal("50.00"),
            currency="USD",
            pricing_model="CPC",
            unit_price=Decimal("0.5000"),
            status="approved",
            is_approved=True,
            is_active=True,
            music_target_type="track",
            music_target_id="trax-demo-unverified",
            music_title="Demo Track 1",
            music_artist_name="Unknown Artist",
            music_rights_verified=False,
            payment_status="paid",
        )
        # Approved, active, AND music_rights_verified is True
        verified_campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Verified Artist",
            headline="Official Single",
            description="Verified track",
            placement="music_track",
            destination_url="https://example.com/official",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=7),
            budget_amount=Decimal("50.00"),
            currency="USD",
            pricing_model="CPC",
            unit_price=Decimal("0.5000"),
            status="approved",
            is_approved=True,
            is_active=True,
            music_target_type="track",
            music_target_id="trax-official-verified",
            music_title="Official Anthem",
            music_artist_name="Verified Star",
            music_rights_verified=True,
            music_rights_holder="Star Records Ltd",
            payment_status="paid",
        )
        session.add_all([profile, unverified_campaign, verified_campaign])
        session.commit()

    with client:
        res = client.get("/public/ads/music/promotions")
        assert res.status_code == 200, res.text
        promotions = res.json()["promotions"]
        target_ids = [p["target_id"] for p in promotions]
        assert "trax-official-verified" in target_ids
        assert "trax-demo-unverified" not in target_ids


def test_budget_exhaustion_delivery_throttling():
    client, factory, advertiser, _admin = _client()
    now = datetime.now(UTC)
    with factory() as session:
        profile = BrandAdvertiserProfile(
            user_id=advertiser.id,
            company_name="Budgeted Brand",
            contact_name="Budget Manager",
            billing_email="budget@example.com",
        )
        # Budget = $10.00, CPC = $2.00. Exhausts at 5 clicks.
        campaign = BrandAdCampaign(
            advertiser_id=advertiser.id,
            campaign_type="music",
            brand_name="Budgeted Trax",
            headline="Limited Budget Track",
            description="Track with small budget",
            placement="music_track",
            destination_url="https://example.com/track",
            start_at=now - timedelta(minutes=5),
            end_at=now + timedelta(days=7),
            budget_amount=Decimal("10.00"),
            currency="USD",
            pricing_model="CPC",
            unit_price=Decimal("2.0000"),
            status="approved",
            is_approved=True,
            is_active=True,
            music_target_type="track",
            music_target_id="trax-budget-exhaustion",
            music_title="Budget Hit",
            music_artist_name="Budget Artist",
            music_rights_verified=True,
            music_rights_holder="Budget Label",
            payment_status="paid",
        )
        session.add_all([profile, campaign])
        session.commit()
        campaign_id = campaign.id

    client.app.dependency_overrides[get_optional_current_user] = lambda: None
    with client:
        # Initially delivered
        res1 = client.get("/public/ads/music/promotions")
        assert res1.status_code == 200
        assert any(p["target_id"] == "trax-budget-exhaustion" for p in res1.json()["promotions"])

        # Five unauthenticated clicks are analytics only and must not exhaust the budget.
        for i in range(5):
            click_res = client.post(
                "/public/ads/events",
                json={
                    "campaign_id": campaign_id,
                    "event_type": "click",
                    "idempotency_key": f"exhaust-click-{i}",
                    "metadata_json": {},
                },
            )
            assert click_res.status_code == 200, click_res.text

        still_live = client.get("/public/ads/music/promotions")
        assert still_live.status_code == 200
        assert any(p["target_id"] == "trax-budget-exhaustion" for p in still_live.json()["promotions"])
        with factory() as session:
            stored = session.query(BrandAdEvent).filter_by(campaign_id=campaign_id, event_source="client").count()
            assert stored == 5
            campaign = session.get(BrandAdCampaign, campaign_id)
            assert campaign is not None
            for i in range(5):
                assert record_server_brand_delivery(
                    session,
                    campaign,
                    event_type="click",
                    idempotency_key=f"server-delivery-click-{i}",
                )
            assert (
                record_server_brand_delivery(
                    session,
                    campaign,
                    event_type="click",
                    idempotency_key="server-delivery-click-0",
                )
                is False
            )
            session.commit()

        # A server-recorded delivery can still exhaust a paid CPC budget.
        exhausted = client.get("/public/ads/music/promotions")
        assert exhausted.status_code == 200
        assert not any(p["target_id"] == "trax-budget-exhaustion" for p in exhausted.json()["promotions"])

        blocked_event = client.post(
            "/public/ads/events",
            json={
                "campaign_id": campaign_id,
                "event_type": "click",
                "idempotency_key": "exhaust-click-blocked",
                "metadata_json": {},
            },
        )
        assert blocked_event.status_code == 404
