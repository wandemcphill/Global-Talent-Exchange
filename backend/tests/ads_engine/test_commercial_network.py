from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.router import public_router as ads_public_router, router as ads_router
from app.auth.dependencies import get_session
from app.auth.router import router as auth_router
from app.auth.security import hash_password
from app.auth.service import AuthError, AuthService
from app.models.access_control import Organization, OrganizationMembership
from app.models.auth_session import AuthSession
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.club_profile import ClubProfile
from app.models.commercial_network import (
    AdPlacementSpec,
    AdPricingPackage,
    AdvertiserClientBrand,
    AdvertiserInvoice,
    AdvertiserMediaAsset,
    AdvertiserPaymentRecord,
    AdvertiserRefundRecord,
    AdvertiserSubscription,
    AdvertiserWebhookEvent,
    AdvertiserWorkspace,
    AdvertiserWorkspaceMember,
    CommercialAuditLog,
)
from app.models.user import PublicAccountType, User, UserRole
from app.models.user_region import UserRegionProfile


def _build_commercial_test_app(tmp_path: Path, monkeypatch) -> tuple[TestClient, sessionmaker[Session]]:
    monkeypatch.setenv("GTE_MEDIA_STORAGE_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_paystack_commercial_secret")
    monkeypatch.setenv("KORAPAY_SECRET_KEY", "korapay_test_secret_key")
    monkeypatch.setenv("KORAPAY_WEBHOOK_SECRET", "korapay_test_webhook_secret")

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(ads_router, prefix="/api/v2")
    app.include_router(ads_public_router, prefix="/api/v2")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            UserRegionProfile.__table__,
            ClubProfile.__table__,
            Organization.__table__,
            OrganizationMembership.__table__,
            AuthSession.__table__,
            BrandAdvertiserProfile.__table__,
            BrandAdCampaign.__table__,
            BrandAdEvent.__table__,
            BrandAdReviewEvent.__table__,
            AdvertiserWorkspace.__table__,
            AdvertiserWorkspaceMember.__table__,
            AdvertiserClientBrand.__table__,
            AdPlacementSpec.__table__,
            AdPricingPackage.__table__,
            AdvertiserMediaAsset.__table__,
            AdvertiserPaymentRecord.__table__,
            AdvertiserInvoice.__table__,
            AdvertiserSubscription.__table__,
            AdvertiserRefundRecord.__table__,
            AdvertiserWebhookEvent.__table__,
            CommercialAuditLog.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_advertiser_registration_login_and_isolation_from_normal_users(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_commercial_test_app(tmp_path, monkeypatch)

    # 1. Register a Business Advertiser through the dedicated commercial network endpoint
    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Zenith Bank PLC",
            "contact_name": "Adaobi Nwosu",
            "email": "marketing@zenithbank.example.com",
            "phone_number": "+2348012345678",
            "website_url": "https://zenithbank.example.com",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    payload = reg_res.json()
    assert payload["user"]["role"] == "advertiser"
    assert payload["user"]["account_type"] == "advertiser"
    assert payload["landing_route"] == "/advertiser/dashboard"
    adv_token = payload["access_token"]

    # 2. Verify advertiser workspace is created and accessible
    ws_res = client.get("/api/v2/advertiser/workspace", headers=_auth_header(adv_token))
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert ws_data["workspace"]["company_name"] == "Zenith Bank PLC"
    assert ws_data["workspace"]["account_type"] == "business"
    assert ws_data["workspace"]["default_currency"] == "NGN"

    # 3. Verify advertiser is strictly blocked from football club provisioning
    with session_factory() as session:
        adv_user = session.get(User, payload["user"]["id"])
        assert adv_user is not None
        with pytest.raises(AuthError):
            AuthService().ensure_user_club_context(session, adv_user)

    # 4. Verify normal GTEX player user cannot access advertiser workspace endpoints
    with session_factory() as session:
        normal_user = User(
            id="normal-player-1",
            email="player@gtex.example.com",
            username="normalplayer",
            full_name="Normal Player",
            phone_number="+2348099999999",
            password_hash=hash_password("PlayerPassword!123"),
            role=UserRole.USER,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add(normal_user)
        session.flush()
        normal_token = AuthService().issue_session_tokens(normal_user, session=session).access_token
        session.commit()

    forbidden_res = client.get("/api/v2/advertiser/workspace", headers=_auth_header(normal_token))
    assert forbidden_res.status_code == 403


def test_agency_multi_brand_and_team_member_workspace(tmp_path: Path, monkeypatch) -> None:
    client, _ = _build_commercial_test_app(tmp_path, monkeypatch)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "agency",
            "company_name": "Lagos Media House Agency",
            "contact_name": "Tunde Bakare",
            "email": "agency@lagosmedia.example.com",
            "phone_number": "+2348022223333",
            "password": "AgencyPassword!123",  # pragma: allowlist secret
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]

    # Create two client brands
    b1 = client.post(
        "/api/v2/advertiser/brands",
        headers=_auth_header(token),
        json={"brand_name": "MTN Nigeria", "website_url": "https://mtn.ng", "industry": "Telecoms"},
    )
    assert b1.status_code == 201
    b2 = client.post(
        "/api/v2/advertiser/brands",
        headers=_auth_header(token),
        json={"brand_name": "Flutterwave", "website_url": "https://flutterwave.com", "industry": "Fintech"},
    )
    assert b2.status_code == 201

    # Invite a campaign manager team member
    member_res = client.post(
        "/api/v2/advertiser/members",
        headers=_auth_header(token),
        json={"email": "buyer@lagosmedia.example.com", "role": "campaign_manager"},
    )
    assert member_res.status_code == 201

    ws = client.get("/api/v2/advertiser/workspace", headers=_auth_header(token)).json()
    assert len(ws["client_brands"]) == 2
    assert len(ws["members"]) == 2  # owner + invited campaign_manager


def test_direct_media_upload_magic_bytes_and_silent_video_enforcement(tmp_path: Path, monkeypatch) -> None:
    client, _ = _build_commercial_test_app(tmp_path, monkeypatch)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "FirstBrand NG",
            "email": "ads@firstbrand.example.com",
            "phone_number": "+2348033334444",
            "password": "BrandPassword!123",  # pragma: allowlist secret
        },
    )
    token = reg_res.json()["access_token"]

    # 1. Valid PNG Logo Upload
    valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
    logo_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "logo"},
        files={"file": ("brand-logo.png", valid_png, "image/png")},
    )
    assert logo_res.status_code == 201, logo_res.text
    assert logo_res.json()["asset_kind"] == "logo"
    assert logo_res.json()["delivery_url"].startswith("/api/v2/public/ads/media/")

    # 2. Silent MP4 Video Upload (ftyp header without audio track atoms)
    silent_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 256
    silent_vid_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "brand_video"},
        files={"file": ("silent-spot.mp4", silent_mp4, "video/mp4")},
    )
    assert silent_vid_res.status_code == 201, silent_vid_res.text
    assert silent_vid_res.json()["is_silent_verified"] is True

    # 3. Non-Silent MP4 Video Upload (contains 'soun' / 'mp4a' audio stream atom) MUST be rejected
    noisy_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"trakmdiahdlrsounmp4a" + b"\x00" * 128
    noisy_vid_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "brand_video"},
        files={"file": ("noisy-spot.mp4", noisy_mp4, "video/mp4")},
    )
    assert noisy_vid_res.status_code == 422
    assert "silent" in noisy_vid_res.json()["detail"].lower()

    # 4. Spoofed file header rejected
    spoof_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "brand_image"},
        files={"file": ("fake.png", b"not-a-real-png-header", "image/png")},
    )
    assert spoof_res.status_code == 422


def test_full_brand_and_music_campaigns_ngn_billing_and_rbac(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_commercial_test_app(tmp_path, monkeypatch)

    # Create a content admin (no finance refund permission) and a super_admin (finance permission)
    with session_factory() as session:
        content_admin = User(
            id="content-admin-1",
            email="content.admin@gtex.test",
            username="contentadmin",
            password_hash=hash_password("AdminPass!123"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        super_admin = User(
            id="super-admin-1",
            email="finance.admin@gtex.test",
            username="financeadmin",
            password_hash=hash_password("SuperPass!123"),
            role=UserRole.SUPER_ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add_all([content_admin, super_admin])
        session.flush()
        content_admin_token = AuthService().issue_session_tokens(content_admin, session=session).access_token
        super_admin_token = AuthService().issue_session_tokens(super_admin, session=session).access_token
        session.commit()

    # 1. Verify public placements start with explicit "unconfigured" NGN pricing
    pl_res = client.get("/api/v2/public/ads/placements")
    assert pl_res.status_code == 200
    placements = pl_res.json()
    hero_spec = next(p for p in placements if p["placement_key"] == "public_homepage")
    assert hero_spec["pricing_configured"] is False
    assert hero_spec["weekly_rate_minor_ngn"] is None

    # 2. Register Brand Advertiser & Upload Creative
    brand_reg = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Paystack Brand Corp",
            "email": "brand@paystack.example.com",
            "phone_number": "+2348055556666",
            "password": "BrandPassword!123",  # pragma: allowlist secret
        },
    )
    brand_token = brand_reg.json()["access_token"]

    valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
    creative_asset = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(brand_token),
        data={"asset_kind": "brand_image"},
        files={"file": ("hero-banner.png", valid_png, "image/png")},
    ).json()

    # 3. Minimum 7-day rule: duration_days < 7 must fail with 422
    short_res = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(brand_token),
        json={
            "company_name": "Paystack Brand Corp",
            "contact_email": "brand@paystack.example.com",
            "contact_phone": "+2348055556666",
            "placements": ["public_homepage"],
            "headline": "Powering African Commerce",
            "description": "Seamless payments across Africa.",
            "website_url": "https://paystack.com",
            "creative_asset_id": creative_asset["id"],
            "duration_days": 5,
        },
    )
    assert short_res.status_code == 422

    # 4. Create 14-day Brand Campaign while placement NGN price is still unconfigured
    unconf_camp = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(brand_token),
        json={
            "company_name": "Paystack Brand Corp",
            "contact_email": "brand@paystack.example.com",
            "contact_phone": "+2348055556666",
            "placements": ["public_homepage"],
            "headline": "Powering African Commerce",
            "description": "Seamless payments across Africa.",
            "website_url": "https://paystack.com",
            "creative_asset_id": creative_asset["id"],
            "duration_days": 14,
        },
    )
    assert unconf_camp.status_code == 201, unconf_camp.text
    unconf_id = unconf_camp.json()["id"]
    assert unconf_camp.json()["payment_status"] == "unpaid"
    assert unconf_camp.json()["price_minor_ngn"] == 0

    # Attempting to initiate NGN payment when pricing is unconfigured must fail with 422
    pay_unconf = client.post(
        "/api/v2/advertiser/payments/initiate",
        headers=_auth_header(brand_token),
        json={"campaign_id": unconf_id, "provider": "paystack"},
    )
    assert pay_unconf.status_code == 422

    # 5. Admin configures NGN weekly rate on public_homepage (₦250,000/week = 25,000,000 kobo)
    cfg_res = client.patch(
        "/api/v2/admin/advertising/placements/public_homepage",
        headers=_auth_header(content_admin_token),
        json={"weekly_rate_minor_ngn": 25_000_000, "is_enabled": True},
    )
    assert cfg_res.status_code == 200
    assert cfg_res.json()["pricing_configured"] is True
    assert cfg_res.json()["weekly_rate_formatted_ngn"] == "₦250,000.00"

    # 6. Create 14-day Brand Campaign now that NGN pricing is configured (2 weeks = ₦500,000.00 = 50,000,000 kobo)
    brand_camp_res = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(brand_token),
        json={
            "company_name": "Paystack Brand Corp",
            "contact_email": "brand@paystack.example.com",
            "contact_phone": "+2348055556666",
            "placements": ["public_homepage"],
            "headline": "Seamless Matchday Payments",
            "description": "Official payment partner.",
            "website_url": "https://paystack.com/gtex",
            "creative_asset_id": creative_asset["id"],
            "duration_days": 14,
            "is_subscription": True,
        },
    )
    assert brand_camp_res.status_code == 201, brand_camp_res.text
    brand_camp = brand_camp_res.json()
    assert brand_camp["currency"] == "NGN"
    assert brand_camp["price_minor_ngn"] == 50_000_000
    assert brand_camp["price_formatted_ngn"] == "₦500,000.00"

    # 7. Initiate NGN Payment with idempotency key
    with patch("httpx.post") as mock_post, patch("httpx.get") as mock_get:
        mock_init_res = MagicMock()
        mock_init_res.status_code = 200
        mock_init_res.raise_for_status = MagicMock()
        mock_init_res.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/auth_code_999",
                "reference": "GTEX-ADV-NGN-001",
            },
        }
        mock_post.return_value = mock_init_res

        mock_verify_res = MagicMock()
        mock_verify_res.status_code = 200
        mock_verify_res.raise_for_status = MagicMock()
        mock_verify_res.json.return_value = {
            "status": True,
            "data": {
                "status": "success",
                "amount": 50_000_000,
                "currency": "NGN",
                "reference": "GTEX-ADV-NGN-001",
            },
        }
        mock_get.return_value = mock_verify_res

        pay_init_1 = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(brand_token),
            json={
                "campaign_id": brand_camp["id"],
                "provider": "paystack",
                "idempotency_key": "idem-paystack-brand-001",
                "subscription_consent_accepted": True,
            },
        )
        assert pay_init_1.status_code == 201, pay_init_1.text
        payment_record = pay_init_1.json()
        assert payment_record["amount_minor_ngn"] == 50_000_000
        assert payment_record["currency"] == "NGN"

        # Duplicate initiation with same idempotency_key returns identical payment record
        pay_init_2 = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(brand_token),
            json={
                "campaign_id": brand_camp["id"],
                "provider": "paystack",
                "idempotency_key": "idem-paystack-brand-001",
                "subscription_consent_accepted": True,
            },
        )
        assert pay_init_2.status_code == 201
        assert pay_init_2.json()["id"] == payment_record["id"]

        # 8. Signed Paystack Webhook Verification -> Marks payment paid & generates NGN Invoice
        webhook_body = json.dumps(
            {
                "event": "charge.success",
                "data": {
                    "id": "ps_evt_999",
                    "reference": payment_record["reference"],
                    "status": "success",
                    "amount": 50_000_000,
                    "currency": "NGN",
                },
            }
        ).encode("utf-8")
        signature = hmac.new(
            b"sk_test_paystack_commercial_secret",
            webhook_body,
            hashlib.sha512,
        ).hexdigest()

        # Wire mock get reference to match the generated payment reference
        mock_verify_res.json.return_value["data"]["reference"] = payment_record["reference"]

        wh_res = client.post(
            "/api/v2/public/ads/webhooks/paystack",
            content=webhook_body,
            headers={"x-paystack-signature": signature, "Content-Type": "application/json"},
        )
        assert wh_res.status_code == 200, wh_res.text

    # Check invoice and subscription creation via billing ledger
    billing = client.get("/api/v2/advertiser/billing", headers=_auth_header(brand_token)).json()
    assert len(billing["invoices"]) == 1
    assert billing["invoices"][0]["total_minor_ngn"] == 50_000_000
    assert billing["invoices"][0]["total_formatted_ngn"] == "₦500,000.00"
    assert len(billing["subscriptions"]) == 1
    assert billing["subscriptions"][0]["status"] == "active"

    # 9. Admin Approves Campaign -> System automatically calculates start_at = now and end_at = now + 14 days
    approve_res = client.post(
        f"/api/v2/admin/advertising/campaigns/{brand_camp['id']}/moderate",
        headers=_auth_header(content_admin_token),
        json={"action": "approve", "note": "Creative verified silent and NGN payment settled."},
    )
    assert approve_res.status_code == 200, approve_res.text
    approved_camp = approve_res.json()
    assert approved_camp["is_approved"] is True
    assert approved_camp["is_active"] is True
    assert approved_camp["payment_status"] == "paid"

    # 10. Serve active brand campaign on public_homepage and record genuine impression + click
    serve_res = client.get("/api/v2/public/ads/campaigns", params={"placement": "public_homepage"})
    assert serve_res.status_code == 200
    served_list = serve_res.json()["campaigns"]
    assert any(c["id"] == brand_camp["id"] for c in served_list)

    # Record impression and click event
    client.post(
        "/api/v2/public/ads/events",
        json={"campaign_id": brand_camp["id"], "event_type": "impression", "idempotency_key": "impression-event-001"},
    )
    ev_res = client.post(
        "/api/v2/public/ads/events",
        json={"campaign_id": brand_camp["id"], "event_type": "click", "idempotency_key": "click-event-001"},
    )
    assert ev_res.status_code == 200

    detail_res = client.get(
        f"/api/v2/advertiser/campaigns/{brand_camp['id']}",
        headers=_auth_header(brand_token),
    )
    assert detail_res.status_code == 200
    rep = detail_res.json()
    assert rep["metrics"]["impressions"] >= 1
    assert rep["metrics"]["clicks"] == 1

    # 11. Music Promotion Workflow (Direct Audio Upload + Auto-filled Track Title + Rotation Feed)
    # Configure 21-day music promotion package price (₦180,000 = 18,000,000 kobo)
    client.put(
        "/api/v2/admin/advertising/pricing",
        headers=_auth_header(content_admin_token),
        json={
            "package_code": "music_promo_21d",
            "name": "21-Day GTEX TRAX Rotation",
            "division": "music",
            "description": "21 days of verified rotation inside GTEX TRAX.",
            "duration_days": 21,
            "placement_keys": ["music_rotation"],
            "price_minor_ngn": 18_000_000,
            "is_active": True,
        },
    )

    music_reg = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "music",
            "company_name": "Mavin Records",
            "email": "promo@mavin.example.com",
            "phone_number": "+2348077778888",
            "password": "MusicPassword!123",  # pragma: allowlist secret
        },
    )
    music_token = music_reg.json()["access_token"]

    valid_mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x10" + b"\x00" * 512
    audio_asset = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(music_token),
        data={"asset_kind": "music_audio"},
        files={"file": ("Lagos_Anthem_2027.mp3", valid_mp3, "audio/mpeg")},
    ).json()

    music_camp = client.post(
        "/api/v2/advertiser/campaigns/music",
        headers=_auth_header(music_token),
        json={
            "artist_name": "Rema",
            "track_title": None,  # Should auto-fill from Lagos_Anthem_2027.mp3
            "label_name": "Mavin Records",
            "audio_asset_id": audio_asset["id"],
            "duration_days": 21,
            "package_code": "music_promo_21d",
            "rights_declaration_accepted": True,
            "explicit_content": False,
        },
    )
    assert music_camp.status_code == 201, music_camp.text
    mc_data = music_camp.json()
    assert mc_data["music_title"] == "Lagos Anthem 2027"
    assert mc_data["price_minor_ngn"] == 18_000_000

    # Initiate & verify music payment
    with patch("httpx.post") as mock_post, patch("httpx.get") as mock_get:
        mock_kora_init = MagicMock()
        mock_kora_init.status_code = 200
        mock_kora_init.raise_for_status = MagicMock()
        mock_kora_init.json.return_value = {
            "status": True,
            "data": {
                "checkout_url": "https://checkout.korapay.com/kora_charge_999",
                "reference": "GTEX-KORA-REF-001",
            },
        }
        mock_post.return_value = mock_kora_init

        mock_kora_verify = MagicMock()
        mock_kora_verify.status_code = 200
        mock_kora_verify.raise_for_status = MagicMock()
        mock_kora_verify.json.return_value = {
            "status": True,
            "data": {
                "status": "success",
                "amount": 180000,
                "currency": "NGN",
                "reference": "GTEX-KORA-REF-001",
            },
        }
        mock_get.return_value = mock_kora_verify

        m_pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(music_token),
            json={"campaign_id": mc_data["id"], "provider": "korapay"},
        )
        assert m_pay_res.status_code == 201, m_pay_res.text
        m_pay = m_pay_res.json()
        assert m_pay["checkout_url"] == "https://checkout.korapay.com/kora_charge_999"

        mock_kora_verify.json.return_value["data"]["reference"] = m_pay["reference"]

        verify_res = client.post(
            f"/api/v2/advertiser/payments/{m_pay['reference']}/verify",
            headers=_auth_header(music_token),
        )
        assert verify_res.status_code == 200, verify_res.text
    client.post(
        f"/api/v2/admin/advertising/campaigns/{mc_data['id']}/moderate",
        headers=_auth_header(content_admin_token),
        json={"action": "approve"},
    )

    # Check Music Rotation Feed
    rot_res = client.get("/api/v2/public/ads/music/rotation")
    assert rot_res.status_code == 200
    tracks = rot_res.json()["tracks"]
    assert any(t["campaign_id"] == mc_data["id"] and t["title"] == "Lagos Anthem 2027" for t in tracks)

    # Record music play & qualified listen telemetry
    client.post(
        "/api/v2/public/ads/events",
        json={"campaign_id": mc_data["id"], "event_type": "play_started", "idempotency_key": "music-play-event-001"},
    )
    client.post(
        "/api/v2/public/ads/events",
        json={"campaign_id": mc_data["id"], "event_type": "qualified_listen", "idempotency_key": "music-qualified-001"},
    )
    m_rep = client.get(
        f"/api/v2/advertiser/campaigns/{mc_data['id']}",
        headers=_auth_header(music_token),
    ).json()
    assert m_rep["metrics"]["plays_started"] == 1
    assert m_rep["metrics"]["qualified_listens"] == 1

    # 12. RBAC Separation: Content Admin WITHOUT finance permission gets 403 on refund; Super/Finance Admin succeeds
    forbidden_refund = client.post(
        "/api/v2/admin/advertising/payments/refund",
        headers=_auth_header(content_admin_token),
        json={"payment_record_id": payment_record["id"], "reason": "Unauthorized attempt"},
    )
    assert forbidden_refund.status_code == 403

    authorized_refund = client.post(
        "/api/v2/admin/advertising/payments/refund",
        headers=_auth_header(super_admin_token),
        json={"payment_record_id": payment_record["id"], "reason": "Approved finance refund"},
    )
    assert authorized_refund.status_code == 201, authorized_refund.text
    assert authorized_refund.json()["status"] == "completed"
