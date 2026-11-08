from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.commercial_service import CommercialNetworkService
from app.ads_engine.router import public_router as ads_public_router, router as ads_router
from app.auth.dependencies import get_session
from app.auth.router import router as auth_router
from app.auth.security import hash_password
from app.auth.service import AuthService
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
from app.storage.base import StorageError, StorageNotFound
from app.storage.s3 import S3ObjectStorage

PAYSTACK_TEST_SECRET = "sk_test_paystack_security_secret_123"
KORAPAY_TEST_SECRET = "korapay_test_security_secret_456"


def _build_test_app(tmp_path: Path, monkeypatch) -> tuple[TestClient, sessionmaker[Session], Path]:
    media_dir = tmp_path / "media_store"
    media_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GTE_MEDIA_STORAGE_ROOT", str(media_dir))
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", PAYSTACK_TEST_SECRET)
    monkeypatch.setenv("KORAPAY_SECRET_KEY", KORAPAY_TEST_SECRET)
    monkeypatch.setenv("KORAPAY_WEBHOOK_SECRET", KORAPAY_TEST_SECRET)

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

    def _get_test_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _get_test_session
    return TestClient(app), session_factory, media_dir


def _create_admin(session_factory, user_id: str, email: str, username: str) -> str:
    with session_factory() as session:
        user = User(
            id=user_id,
            email=email,
            username=username,
            password_hash=hash_password("SuperSecretAdminPassword123!"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        auth_service = AuthService()
        tokens = auth_service.issue_session_tokens(user, session=session)
        session.commit()
        return tokens.access_token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_advertiser_and_campaign(client: TestClient, admin_token: str) -> tuple[str, str, dict]:
    cfg = client.patch(
        "/api/v2/admin/advertising/placements/public_homepage",
        headers=_auth_header(admin_token),
        json={"weekly_rate_minor_ngn": 25_000_000, "is_enabled": True},
    )
    assert cfg.status_code == 200, cfg.text

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Security Brand Ltd",
            "email": f"sec_{uuid4().hex[:8]}@brand.example.com",
            "phone_number": "+2348011112222",
            "password": "SecurePassword!123",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    adv_token = reg_res.json()["access_token"]

    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    media = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(adv_token),
        data={"asset_kind": "brand_image"},
        files={"file": ("creative.png", png_data, "image/png")},
    ).json()

    camp = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(adv_token),
        json={
            "company_name": "Security Brand Ltd",
            "contact_email": "security@brand.example.com",
            "contact_phone": "+2348011112222",
            "placements": ["public_homepage"],
            "headline": "Zero Trust Security",
            "description": "Safe payments everywhere.",
            "website_url": "https://security.example.com",
            "creative_asset_id": media["id"],
            "duration_days": 7,
        },
    ).json()
    return adv_token, camp["id"], camp


# ==============================================================================
# 1. WEBHOOK SIGNATURE AUTHENTICATION & FORGERY TESTS (SCENARIOS 1 - 5)
# ==============================================================================


def test_paystack_webhook_signature_verification_and_rejection(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-1", "admin1@gtex.test", "adm1")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {"status": True, "data": {"authorization_url": "https://ps.co/123", "reference": "REF1"}},
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()

    ref = pay_res["reference"]
    body = json.dumps(
        {
            "event": "charge.success",
            "data": {"id": "ps_sec_1", "reference": ref, "amount": 25_000_000, "currency": "NGN"},
        }
    ).encode("utf-8")

    # A. Missing signature header -> 401 Unauthorized
    res_no_sig = client.post(
        "/api/v2/public/ads/webhooks/paystack", content=body, headers={"Content-Type": "application/json"}
    )
    assert res_no_sig.status_code == 401
    assert "missing" in res_no_sig.json()["detail"].lower()

    # B. Forged / incorrect legacy signature -> 401 Unauthorized
    res_bad_sig = client.post(
        "/api/v2/public/ads/webhooks/paystack",
        content=body,
        headers={"Content-Type": "application/json", "x-paystack-signature": "forged_signature_hex_000"},
    )
    assert res_bad_sig.status_code == 401
    assert "failed" in res_bad_sig.json()["detail"].lower()

    # C. Valid legacy HMAC-SHA512 signature -> Processed successfully
    valid_sig = hmac.new(PAYSTACK_TEST_SECRET.encode("utf-8"), body, hashlib.sha512).hexdigest()
    with patch("httpx.get") as mock_verify:
        mock_verify.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "NGN", "reference": ref},
            },
        )
        res_valid = client.post(
            "/api/v2/public/ads/webhooks/paystack",
            content=body,
            headers={"Content-Type": "application/json", "x-paystack-signature": valid_sig},
        )
        assert res_valid.status_code == 200
        assert res_valid.json()["status"] == "processed"

    # D. Duplicate event replay -> Deduplicated without re-processing
    res_dup = client.post(
        "/api/v2/public/ads/webhooks/paystack",
        content=body,
        headers={"Content-Type": "application/json", "x-paystack-signature": valid_sig},
    )
    assert res_dup.status_code == 200
    assert res_dup.json()["status"] == "duplicate"


def test_paystack_webhook_timestamped_signature_and_rotation(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-rot", "admin_rot@gtex.test", "admrot")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {"status": True, "data": {"authorization_url": "https://ps.co/123", "reference": "REF_ROT"}},
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()

    ref = pay_res["reference"]
    body = json.dumps(
        {
            "event": "charge.success",
            "data": {"id": "ps_rot_1", "reference": ref, "amount": 25_000_000, "currency": "NGN"},
        }
    ).encode("utf-8")

    import time

    now_ts = int(time.time())

    # A. Stale timestamp (> 300s) -> 401 Unauthorized
    stale_ts = now_ts - 500
    signed_stale = f"{stale_ts}.".encode("utf-8") + body
    stale_sig = hmac.new(PAYSTACK_TEST_SECRET.encode("utf-8"), signed_stale, hashlib.sha512).hexdigest()
    res_stale = client.post(
        "/api/v2/public/ads/webhooks/paystack",
        content=body,
        headers={"Content-Type": "application/json", "paystack-signature": f"t={stale_ts},v1={stale_sig}"},
    )
    assert res_stale.status_code == 401
    assert "timestamp" in res_stale.json()["detail"].lower()

    # B. Valid timestamped signature with rotation overlap
    signed_now = f"{now_ts}.".encode("utf-8") + body
    valid_v1 = hmac.new(PAYSTACK_TEST_SECRET.encode("utf-8"), signed_now, hashlib.sha512).hexdigest()
    with patch("httpx.get") as mock_verify:
        mock_verify.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "NGN", "reference": ref},
            },
        )
        res_rot = client.post(
            "/api/v2/public/ads/webhooks/paystack",
            content=body,
            headers={
                "Content-Type": "application/json",
                "paystack-signature": f"t={now_ts},v1=old_invalid_key,v1={valid_v1}",
            },
        )
        assert res_rot.status_code == 200
        assert res_rot.json()["status"] == "processed"


def test_korapay_webhook_signature_verification_and_rejection(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-2", "admin2@gtex.test", "adm2")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {"status": True, "data": {"checkout_url": "https://kora.co/123", "reference": "KREF1"}},
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "korapay"},
        ).json()

    ref = pay_res["reference"]
    payload_data = {"id": "kora_evt_1", "reference": ref, "amount": 250000, "currency": "NGN"}
    full_payload = {"event": "charge.success", "data": payload_data}
    raw_body = json.dumps(full_payload).encode("utf-8")

    # A. Missing Korapay signature -> 401 Unauthorized
    res_no_sig = client.post(
        "/api/v2/public/ads/webhooks/korapay", content=raw_body, headers={"Content-Type": "application/json"}
    )
    assert res_no_sig.status_code == 401

    # B. Forged Korapay signature -> 401 Unauthorized
    res_bad_sig = client.post(
        "/api/v2/public/ads/webhooks/korapay",
        content=raw_body,
        headers={"Content-Type": "application/json", "x-korapay-signature": "bogus_kora_sig"},
    )
    assert res_bad_sig.status_code == 401

    # C. Valid Korapay signature (computed over data according to js_json_stringify contract)
    canonical_data = json.dumps(payload_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    valid_kora_sig = hmac.new(KORAPAY_TEST_SECRET.encode("utf-8"), canonical_data, hashlib.sha256).hexdigest()

    with patch("httpx.get") as mock_kora_verify:
        mock_kora_verify.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 250000, "currency": "NGN", "reference": ref},
            },
        )
        res_valid = client.post(
            "/api/v2/public/ads/webhooks/korapay",
            content=raw_body,
            headers={"Content-Type": "application/json", "x-korapay-signature": valid_kora_sig},
        )
        assert res_valid.status_code == 200


# ==============================================================================
# 2. CLIENT PAYMENT VERIFICATION BYPASS REMOVAL & EXACT AMOUNT MATCHING
# ==============================================================================


def test_client_cannot_bypass_gateway_verification(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-3", "admin3@gtex.test", "adm3")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"authorization_url": "https://ps.co/123", "reference": "REF_BYPASS"},
            },
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()

    ref = pay_res["reference"]

    # 1. Gateway reports failed status -> Remains unpaid, returns 400
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "failed", "amount": 25_000_000, "currency": "NGN", "reference": ref},
            },
        )
        fail_res = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert fail_res.status_code == 400
        assert "failed" in fail_res.json()["detail"].lower()

    # 2. Gateway reports underpayment -> Remains unpaid, returns 400
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 1000, "currency": "NGN", "reference": ref},
            },
        )
        underpaid_res = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert underpaid_res.status_code == 400
        assert "underpayment" in underpaid_res.json()["detail"].lower()

    # 3. Gateway reports currency mismatch (USD instead of NGN) -> Returns 400
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "USD", "reference": ref},
            },
        )
        curr_res = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert curr_res.status_code == 400
        assert "currency mismatch" in curr_res.json()["detail"].lower()

    # 4. Gateway reports correct verified payment -> Successfully reconciles
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "NGN", "reference": ref},
            },
        )
        success_res = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert success_res.status_code == 200
        assert success_res.json()["status"] == "paid"


def test_exact_payment_reconciliation_all_states(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-recon", "admin_recon@gtex.test", "admrecon")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"authorization_url": "https://ps.co/recon", "reference": "REF_PS_RECON"},
            },
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()
    ref_ps = pay_res["reference"]

    # 1A. Underpayment Paystack: expected 25,000,000 kobo (250,000 NGN), provider reports 24,999,999 kobo
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 24_999_999, "currency": "NGN", "reference": ref_ps},
            },
        )
        res_under = client.post(f"/api/v2/advertiser/payments/{ref_ps}/verify", headers=_auth_header(adv_token))
        assert res_under.status_code == 400
        assert "underpayment" in res_under.json()["detail"].lower()

    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_ps))
        assert rec.status == "failed"
        assert rec.pricing_snapshot_json["reconciliation"]["type"] == "underpayment"

    # 1B. Overpayment Paystack: expected 25,000,000 kobo, provider reports 25,000,001 kobo
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_ps))
        rec.status = "pending"
        session.commit()

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_001, "currency": "NGN", "reference": ref_ps},
            },
        )
        res_over = client.post(f"/api/v2/advertiser/payments/{ref_ps}/verify", headers=_auth_header(adv_token))
        assert res_over.status_code == 400
        assert "overpayment" in res_over.json()["detail"].lower()

    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_ps))
        assert rec.status == "flagged_overpayment"
        assert rec.pricing_snapshot_json["reconciliation"]["type"] == "overpayment"
        assert rec.pricing_snapshot_json["reconciliation"]["requires_decision"] is True
        camp = session.get(BrandAdCampaign, camp_id)
        assert camp.status != "active"

    # 1C. Exact payment Paystack: exactly 25,000,000 kobo (250,000 NGN)
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_ps))
        rec.status = "pending"
        session.commit()

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "NGN", "reference": ref_ps},
            },
        )
        res_exact = client.post(f"/api/v2/advertiser/payments/{ref_ps}/verify", headers=_auth_header(adv_token))
        assert res_exact.status_code == 200
        assert res_exact.json()["status"] == "paid"

    # 1D. Duplicate payment check: re-verifying an already paid transaction
    with patch("httpx.get") as mock_get:
        res_dup = client.post(f"/api/v2/advertiser/payments/{ref_ps}/verify", headers=_auth_header(adv_token))
        assert res_dup.status_code == 200
        assert res_dup.json()["status"] == "paid"

    # 1E. Admin Full Refund
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_ps))
        svc = CommercialNetworkService(session)
        finance_admin = session.scalar(select(User).where(User.username == "admrecon"))
        from app.ads_engine.commercial_schemas import RefundCreateRequest

        ref_res = svc.create_admin_refund(
            finance_admin=finance_admin,
            payload=RefundCreateRequest(
                payment_record_id=rec.id,
                amount_minor_ngn=rec.amount_minor_ngn,
                reason="Customer requested full campaign cancellation",
            ),
        )
        assert ref_res.status == "completed"
        assert rec.status == "refunded"

    # 1F. Attempting to verify a refunded transaction raises 409 Conflict
    res_terminal = client.post(f"/api/v2/advertiser/payments/{ref_ps}/verify", headers=_auth_header(adv_token))
    assert res_terminal.status_code == 409

    # 2. Korapay Exact, Under, Over, and Reversed
    adv_kora_token, camp_id_kora, _ = _setup_advertiser_and_campaign(client, admin_token)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"checkout_url": "https://kora.co/recon", "reference": "REF_KORA_RECON"},
            },
        )
        kora_pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_kora_token),
            json={"campaign_id": camp_id_kora, "provider": "korapay"},
        ).json()
    ref_kora = kora_pay_res["reference"]

    # 2A. Korapay underpayment: expected 250,000 NGN, reports 249,999 NGN
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 249999, "currency": "NGN", "reference": ref_kora},
            },
        )
        res_kora_under = client.post(
            f"/api/v2/advertiser/payments/{ref_kora}/verify", headers=_auth_header(adv_kora_token)
        )
        assert res_kora_under.status_code == 400
        assert "underpayment" in res_kora_under.json()["detail"].lower()

    # 2B. Korapay overpayment: expected 250,000 NGN, reports 250,001 NGN
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_kora))
        rec.status = "pending"
        session.commit()

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 250001, "currency": "NGN", "reference": ref_kora},
            },
        )
        res_kora_over = client.post(
            f"/api/v2/advertiser/payments/{ref_kora}/verify", headers=_auth_header(adv_kora_token)
        )
        assert res_kora_over.status_code == 400
        assert "overpayment" in res_kora_over.json()["detail"].lower()

    # 2C. Korapay reversed: provider reports reversed
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_kora))
        rec.status = "pending"
        session.commit()

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "reversed", "amount": 250000, "currency": "NGN", "reference": ref_kora},
            },
        )
        res_kora_rev = client.post(
            f"/api/v2/advertiser/payments/{ref_kora}/verify", headers=_auth_header(adv_kora_token)
        )
        assert res_kora_rev.status_code == 400
        assert "reversed" in res_kora_rev.json()["detail"].lower()
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref_kora))
        assert rec.status == "reversed"


# ==============================================================================
# 3. CHECKOUT ADAPTER MISMATCH & FAIL CLOSED (SCENARIOS 12)
# ==============================================================================


def test_gateway_checkout_adapter_invokes_canonical_method_and_fails_closed(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-4", "admin4@gtex.test", "adm4")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.side_effect = Exception("Paystack upstream gateway timeout")
        init_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        )
        assert init_res.status_code == 502
        assert "failed" in init_res.json()["detail"].lower()
        assert "mock" not in init_res.json().get("checkout_url", "").lower()


# ==============================================================================
# 4. MEDIA OBJECT STORAGE, RESTART SURVIVAL & BACKFILL (SCENARIOS 13 - 14)
# ==============================================================================


def test_media_storage_outage_fails_safely_and_backfill_resumes(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, media_dir = _build_test_app(tmp_path, monkeypatch)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Storage Test Corp",
            "email": "storage@test.example.com",
            "phone_number": "+2348099990000",
            "password": "Password!123",
        },
    )
    adv_token = reg_res.json()["access_token"]
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128

    upload_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(adv_token),
        data={"asset_kind": "logo"},
        files={"file": ("logo.png", png_data, "image/png")},
    )
    assert upload_res.status_code == 201
    asset_id = upload_res.json()["id"]
    storage_key = upload_res.json()["storage_key"]
    assert storage_key is not None
    assert (media_dir / storage_key).exists()

    with session_factory() as session:
        row = session.get(AdvertiserMediaAsset, asset_id)
        assert row.data is None
        assert row.storage_key == storage_key

    with patch("app.storage.LocalObjectStorage.put_bytes", side_effect=StorageError("Disk full")):
        outage_res = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "logo"},
            files={"file": ("logo2.png", png_data, "image/png")},
        )
        assert outage_res.status_code == 503
        assert "unavailable" in outage_res.json()["detail"].lower()

    legacy_data = b"\x89PNG\r\n\x1a\n" + b"\x01" * 64
    legacy_hash = hashlib.sha256(legacy_data).hexdigest()
    with session_factory() as session:
        legacy_asset = AdvertiserMediaAsset(
            workspace_id=row.workspace_id,
            uploaded_by_user_id=row.uploaded_by_user_id,
            asset_kind="logo",
            original_filename="legacy.png",
            sanitized_filename="legacy.png",
            mime_type="image/png",
            size_bytes=len(legacy_data),
            sha256_hash=legacy_hash,
            validation_status="valid",
            storage_provider="local_disk",
            storage_key=None,
            data=legacy_data,
        )
        session.add(legacy_asset)
        session.commit()
        legacy_id = legacy_asset.id

    with session_factory() as session:
        svc = CommercialNetworkService(session)
        backfill_summary = svc.backfill_legacy_media_blobs()
        assert backfill_summary["migrated"] >= 1
        assert len(backfill_summary["errors"]) == 0

    with session_factory() as session:
        migrated_row = session.get(AdvertiserMediaAsset, legacy_id)
        assert migrated_row.storage_key is not None
        assert (media_dir / migrated_row.storage_key).exists()
        svc = CommercialNetworkService(session)
        retrieved_bytes = svc.get_media_asset_bytes(migrated_row)
        assert retrieved_bytes == legacy_data


def test_s3_durable_cloud_object_storage(tmp_path: Path) -> None:
    s3_mock_bucket: dict[str, tuple[bytes, str, dict]] = {}

    def mock_http_handler(request: httpx.Request) -> httpx.Response:
        method = request.method
        url_path = request.url.path
        parts = url_path.lstrip("/").split("/", 1)
        key = parts[1] if len(parts) > 1 else ""

        if method == "PUT":
            content = request.content
            content_type = request.headers.get("content-type", "application/octet-stream")
            s3_mock_bucket[key] = (content, content_type, dict(request.headers))
            return httpx.Response(200, text="OK")
        elif method == "GET":
            if key not in s3_mock_bucket:
                return httpx.Response(404, text="Not Found")
            data, content_type, hdrs = s3_mock_bucket[key]
            return httpx.Response(200, content=data, headers={"content-type": content_type})
        elif method == "HEAD":
            if key not in s3_mock_bucket:
                return httpx.Response(404, text="Not Found")
            data, content_type, hdrs = s3_mock_bucket[key]
            return httpx.Response(200, headers={"content-type": content_type, "content-length": str(len(data))})
        elif method == "DELETE":
            s3_mock_bucket.pop(key, None)
            return httpx.Response(204)
        return httpx.Response(400)

    cache1 = tmp_path / "cache1"
    storage_inst1 = S3ObjectStorage(
        bucket="gtex-commercial-assets",
        endpoint_url="https://s3.eu-west-1.amazonaws.com",
        region="eu-west-1",
        access_key_id="test_key",
        secret_access_key="test_secret",
        local_cache_root=cache1,
    )

    test_bytes = b"GTEX Commercial Creative Banner 2026"
    test_key = "advertisers/w1/logos/logo.png"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.put.side_effect = lambda url, headers, content: mock_http_handler(
            httpx.Request("PUT", url, headers=headers, content=content)
        )
        mock_client.get.side_effect = lambda url, headers=None: mock_http_handler(
            httpx.Request("GET", url, headers=headers)
        )
        mock_client.head.side_effect = lambda url, headers=None: mock_http_handler(
            httpx.Request("HEAD", url, headers=headers)
        )
        mock_client.delete.side_effect = lambda url, headers=None: mock_http_handler(
            httpx.Request("DELETE", url, headers=headers)
        )
        mock_client_cls.return_value = mock_client

        stored = storage_inst1.put_bytes(key=test_key, content=test_bytes, content_type="image/png")
        assert stored.key == test_key
        assert stored.size_bytes == len(test_bytes)
        assert storage_inst1.exists(key=test_key) is True

        cache2 = tmp_path / "cache2"
        storage_inst2 = S3ObjectStorage(
            bucket="gtex-commercial-assets",
            endpoint_url="https://s3.eu-west-1.amazonaws.com",
            region="eu-west-1",
            access_key_id="test_key",
            secret_access_key="test_secret",
            local_cache_root=cache2,
        )

        retrieved_inst2 = storage_inst2.get_bytes(key=test_key)
        assert retrieved_inst2 == test_bytes

        file_path = storage_inst2.open_file(key=test_key)
        assert file_path.exists()
        assert file_path.read_bytes() == test_bytes

        storage_inst2.delete(key=test_key)
        assert storage_inst1.exists(key=test_key) is False

        with pytest.raises(StorageNotFound):
            storage_inst1.get_bytes(key=test_key)


# ==============================================================================
# 5. PUBLIC CAMPAIGN VIEW CTA LABEL SAFETY (SCENARIO 15)
# ==============================================================================


def test_public_campaign_view_handles_absent_and_present_cta():
    from app.ads_engine.schemas import PublicBrandAdCampaignView

    ad_no_cta = PublicBrandAdCampaignView(
        id="ad-1",
        brand_name="Brand A",
        headline="Headline A",
        placement="public_homepage",
        destination_url="https://example.com",
    )
    assert ad_no_cta.cta_label is None

    ad_with_cta = PublicBrandAdCampaignView(
        id="ad-2",
        brand_name="Brand B",
        headline="Headline B",
        placement="public_homepage",
        destination_url="https://example.com",
        cta_label="Explore More",
    )
    assert ad_with_cta.cta_label == "Explore More"


# ==============================================================================
# 6. CENTRAL REMEDIATION TASKS 1 - 4 REGRESSION TESTS
# ==============================================================================


def test_payment_amount_precision_and_rejections(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-prec", "admin_prec@gtex.test", "admprec")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {"status": True, "data": {"authorization_url": "https://ps.co/prec", "reference": "REF_PREC"}},
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()
    ref = pay_res["reference"]

    # 1. Fractional kobo rejection: ₦250,000.004
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25000000.4, "currency": "NGN", "reference": ref},
            },
        )
        with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
            from app.wallets.providers.base import PaymentVerification

            mock_vp.return_value = PaymentVerification(
                reference=ref,
                provider_reference=ref,
                status="success",
                amount=Decimal("250000.004"),
                currency="NGN",
            )
            res_frac = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
            assert res_frac.status_code == 400
            assert "fractional kobo" in res_frac.json()["detail"].lower()

    # 2. NaN rejection
    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("NaN"),
            currency="NGN",
        )
        res_nan = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_nan.status_code == 400
        assert "not finite" in res_nan.json()["detail"].lower()

    # 3. Infinity rejection
    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("Infinity"),
            currency="NGN",
        )
        res_inf = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_inf.status_code == 400
        assert "not finite" in res_inf.json()["detail"].lower()

    # 4. Zero and Negative amount rejection
    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("0.00"),
            currency="NGN",
        )
        res_zero = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_zero.status_code == 400
        assert "strictly positive" in res_zero.json()["detail"].lower()

        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("-250000.00"),
            currency="NGN",
        )
        res_neg = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_neg.status_code == 400
        assert "strictly positive" in res_neg.json()["detail"].lower()

    # 5. One-kobo underpayment: expected 250,000.00 NGN (25,000,000 kobo), received 249,999.99 NGN (24,999,999 kobo)
    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("249999.99"),
            currency="NGN",
        )
        res_under = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_under.status_code == 400
        assert "underpayment" in res_under.json()["detail"].lower()

    # 6. One-kobo overpayment: expected 250,000.00 NGN, received 250,000.01 NGN
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref))
        rec.status = "pending"
        session.commit()

    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("250000.01"),
            currency="NGN",
        )
        res_over = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_over.status_code == 400
        assert "overpayment" in res_over.json()["detail"].lower()

    # 7. Exact amount: exactly 250,000.00 NGN (25,000,000 kobo)
    with session_factory() as session:
        rec = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == ref))
        rec.status = "pending"
        session.commit()

    with patch("app.wallets.providers.paystack.PaystackProviderAdapter.verify_payment") as mock_vp:
        mock_vp.return_value = PaymentVerification(
            reference=ref,
            provider_reference=ref,
            status="success",
            amount=Decimal("250000.00"),
            currency="NGN",
        )
        res_exact = client.post(f"/api/v2/advertiser/payments/{ref}/verify", headers=_auth_header(adv_token))
        assert res_exact.status_code == 200
        assert res_exact.json()["status"] == "paid"


def test_paystack_advanced_signature_and_whsec_whk_key_rotation(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    admin_token = _create_admin(session_factory, "adm-ps-adv", "admin_ps_adv@gtex.test", "admpsadv")
    adv_token, camp_id, _ = _setup_advertiser_and_campaign(client, admin_token)

    # Configure dedicated webhook secret starting with whsec_ and fallback
    WHSEC_SECRET = "whsec_primary_dedicated_secret_777"
    FALLBACK_SECRET = "whsec_fallback_rotation_secret_888"
    monkeypatch.setenv("PAYSTACK_WEBHOOK_SECRET", WHSEC_SECRET)
    monkeypatch.setenv("PAYSTACK_WEBHOOK_SECRET_FALLBACK", FALLBACK_SECRET)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"authorization_url": "https://ps.co/adv", "reference": "REF_PS_ADV"},
            },
        )
        pay_res = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": camp_id, "provider": "paystack"},
        ).json()
    ref = pay_res["reference"]

    body = json.dumps(
        {
            "event": "charge.success",
            "data": {"id": "ps_adv_1", "reference": ref, "amount": 25_000_000, "currency": "NGN"},
        }
    ).encode("utf-8")
    import time

    now_ts = int(time.time())

    # A. Future timestamp outside 300s window (> 300s in future) -> 401
    future_ts = now_ts + 400
    signed_future = f"{future_ts}.".encode("utf-8") + body
    future_sig = hmac.new(WHSEC_SECRET.encode("utf-8"), signed_future, hashlib.sha512).hexdigest()
    res_future = client.post(
        "/api/v2/public/ads/webhooks/paystack",
        content=body,
        headers={"Content-Type": "application/json", "paystack-signature": f"t={future_ts},v1={future_sig}"},
    )
    assert res_future.status_code == 401
    assert "timestamp" in res_future.json()["detail"].lower()

    # B. Tampered body with valid timestamp -> 401
    signed_now = f"{now_ts}.".encode("utf-8") + body
    valid_sig = hmac.new(WHSEC_SECRET.encode("utf-8"), signed_now, hashlib.sha512).hexdigest()
    tampered_body = json.dumps(
        {"event": "charge.success", "data": {"id": "ps_adv_1", "reference": ref, "amount": 100, "currency": "NGN"}}
    ).encode("utf-8")
    res_tampered = client.post(
        "/api/v2/public/ads/webhooks/paystack",
        content=tampered_body,
        headers={"Content-Type": "application/json", "paystack-signature": f"t={now_ts},v1={valid_sig}"},
    )
    assert res_tampered.status_code == 401
    assert "failed" in res_tampered.json()["detail"].lower()

    # C. Key ID identifier in v1: v1=whk_key01:hex_signature with secret rotation
    fallback_sig = hmac.new(FALLBACK_SECRET.encode("utf-8"), signed_now, hashlib.sha512).hexdigest()
    with patch("httpx.get") as mock_verify:
        mock_verify.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 25_000_000, "currency": "NGN", "reference": ref},
            },
        )
        res_rotation = client.post(
            "/api/v2/public/ads/webhooks/paystack",
            content=body,
            headers={
                "Content-Type": "application/json",
                "paystack-signature": f"t={now_ts},whk=whk_live_01,v1=whk_old:invalid_sig,v1=whk_live_01:{fallback_sig}",
            },
        )
        assert res_rotation.status_code == 200
        assert res_rotation.json()["status"] == "processed"


def test_korapay_serialization_cross_language_vectors():
    from app.wallets.providers.korapay import _js_json_stringify

    # Verified Node.js v24 reference vectors:
    node_vectors = {
        "nested": '{"a":1,"b":{"c":[1,2,{"d":"test"}]}}',
        "unicode": '{"name":"Kázèém Olúwásèyí","flag":"🇳🇬"}',
        "int": '{"amount":250000}',
        "decimal": '{"rate":250000.5}',
        "intFloat": '{"amount":250000}',
        "sci": '{"val":100000}',
        "ordering": '{"z":1,"a":2,"m":3}',
        "numericKeys": '{"2":"two","10":"ten","alpha":"val"}',
        "escaped": '{"text":"Line 1\\nLine 2\\t\\"quoted\\"\\\\slash"}',
        "nullBool": '{"is_active":true,"is_deleted":false,"comment":null}',
    }

    inputs = {
        "nested": {"a": 1, "b": {"c": [1, 2, {"d": "test"}]}},
        "unicode": {"name": "Kázèém Olúwásèyí", "flag": "🇳🇬"},
        "int": {"amount": 250000},
        "decimal": {"rate": 250000.5},
        "intFloat": {"amount": 250000.0},
        "sci": {"val": 1e5},
        "ordering": {"z": 1, "a": 2, "m": 3},
        "numericKeys": {"10": "ten", "2": "two", "alpha": "val"},
        "escaped": {"text": 'Line 1\nLine 2\t"quoted"\\slash'},
        "nullBool": {"is_active": True, "is_deleted": False, "comment": None},
    }

    for name, input_val in inputs.items():
        res = _js_json_stringify(input_val)
        expected = node_vectors[name]
        assert res == expected, f"Mismatch on vector '{name}': got {res}, expected {expected}"


def test_s3_production_safety_guard(tmp_path: Path, monkeypatch) -> None:
    client, session_factory, _ = _build_test_app(tmp_path, monkeypatch)
    _create_admin(session_factory, "adm-s3-guard", "admin_s3_guard@gtex.test", "adms3guard")

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Guard Test Corp",
            "email": "guard@test.example.com",
            "phone_number": "+2348077778888",
            "password": "Password!123",
        },
    )
    adv_token = reg_res.json()["access_token"]
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128

    # In production without GTE_S3_BUCKET configured, upload must fail safely with HTTP 503
    monkeypatch.setenv("GTE_APP_ENV", "production")
    monkeypatch.delenv("GTE_S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)

    outage_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(adv_token),
        data={"asset_kind": "logo"},
        files={"file": ("guard_logo.png", png_data, "image/png")},
    )
    assert outage_res.status_code == 503
    assert "unavailable" in outage_res.json()["detail"].lower()
