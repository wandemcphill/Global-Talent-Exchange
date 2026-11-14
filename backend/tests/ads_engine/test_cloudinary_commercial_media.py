from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import struct
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
from app.storage import (
    CloudinaryObjectStorage,
    LocalObjectStorage,
    StorageError,
    get_commercial_object_storage,
    get_default_object_storage,
    validate_commercial_storage_configuration,
)


def _build_cloudinary_test_app(
    tmp_path: Path,
    monkeypatch,
    *,
    enable_cloudinary: bool = True,
) -> tuple[TestClient, sessionmaker[Session]]:
    monkeypatch.setenv("GTE_MEDIA_STORAGE_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_paystack_commercial_secret")
    monkeypatch.setenv("KORAPAY_SECRET_KEY", "korapay_test_secret_key")
    monkeypatch.setenv("KORAPAY_WEBHOOK_SECRET", "korapay_test_webhook_secret")
    if enable_cloudinary:
        monkeypatch.setenv("GTE_COMMERCIAL_MEDIA_PROVIDER", "cloudinary")
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "gtex-cloud-test")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "123456789012345")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "super_secret_cloudinary_api_key_do_not_expose")

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


def _build_png(width: int = 800, height: int = 450) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr_data + b"\x00" * 128


def _build_wav(duration_seconds: int, byte_rate: int = 1000) -> bytes:
    data_size = duration_seconds * byte_rate
    riff_size = 36 + data_size
    fmt_chunk = struct.pack("<IHHIIHH", 16, 1, 1, 1000, byte_rate, 1, 8)
    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVEfmt " + fmt_chunk + b"data" + struct.pack("<I", data_size)
    return header + (b"\x00" * min(data_size, 1024))


def test_cloudinary_provider_selection_and_production_fail_safe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_MEDIA_STORAGE_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("GTE_COMMERCIAL_MEDIA_PROVIDER", "cloudinary")
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "gtex-prod-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "api-key-999")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "api-secret-999")

    comm_storage = get_commercial_object_storage()
    assert isinstance(comm_storage, CloudinaryObjectStorage)
    assert comm_storage.is_configured() is True
    assert validate_commercial_storage_configuration() == "cloudinary"

    # Non-commercial storage remains untouched by GTE_COMMERCIAL_MEDIA_PROVIDER
    default_storage = get_default_object_storage()
    assert isinstance(default_storage, LocalObjectStorage)

    # In production, missing Cloudinary credentials when GTE_COMMERCIAL_MEDIA_PROVIDER=cloudinary MUST fail closed
    monkeypatch.setenv("GTE_APP_ENV", "production")
    monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
    with pytest.raises(StorageError):
        get_commercial_object_storage()
    with pytest.raises(StorageError):
        validate_commercial_storage_configuration()


def test_cloudinary_folder_hierarchy_and_resource_types_for_all_5_asset_kinds(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Flutterwave Commercial",
            "email": "ads@flutterwave.example.com",
            "phone_number": "+2348011112222",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    workspace_id = reg_res.json()["workspace"]["id"]

    recorded_uploads: list[dict[str, object]] = []

    def fake_cloudinary_post(url: str, *, data: dict[str, str], files: dict[str, tuple], timeout: float):
        public_id = data["public_id"]
        folder = data.get("folder", "")
        full_public_id = f"{folder}/{public_id}" if folder else public_id
        resource_type = "video" if "/video/upload" in url else "image"
        filename, content_bytes, mime_type = files["file"]
        recorded_uploads.append(
            {
                "url": url,
                "folder": folder,
                "public_id": public_id,
                "full_public_id": full_public_id,
                "resource_type": resource_type,
                "filename": filename,
                "size": len(content_bytes),
                "mime_type": mime_type,
                "signature": data.get("signature"),
            }
        )
        ext = Path(filename).suffix.lstrip(".") or "bin"
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "asset_id": f"cld-asset-{len(recorded_uploads)}",
            "public_id": full_public_id,
            "version": 1731580000 + len(recorded_uploads),
            "resource_type": resource_type,
            "type": "upload",
            "format": ext,
            "bytes": len(content_bytes),
            "width": 1920 if resource_type == "image" else 1280,
            "height": 1080 if resource_type == "image" else 720,
            "duration": 30.0 if resource_type == "video" else None,
            "secure_url": f"https://res.cloudinary.com/gtex-cloud-test/{resource_type}/upload/v1731580000/{full_public_id}.{ext}",
        }
        return resp

    valid_png = _build_png(1920, 1080)
    silent_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 256
    valid_mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x10" + b"\x00" * 512

    uploads_to_test = [
        ("logo", "company-logo.png", valid_png, "image/png", f"gtex/commercial/brands/logos/{workspace_id}", "image"),
        (
            "brand_image",
            "hero-banner.png",
            valid_png,
            "image/png",
            f"gtex/commercial/brands/creatives/{workspace_id}",
            "image",
        ),
        (
            "brand_video",
            "silent-spot.mp4",
            silent_mp4,
            "video/mp4",
            f"gtex/commercial/brands/videos/{workspace_id}",
            "video",
        ),
        (
            "music_audio",
            "Afrobeats_Anthem.mp3",
            valid_mp3,
            "audio/mpeg",
            f"gtex/commercial/music/audio/{workspace_id}",
            "video",
        ),
        (
            "music_artwork",
            "cover-art.png",
            valid_png,
            "image/png",
            f"gtex/commercial/music/artwork/{workspace_id}",
            "image",
        ),
    ]

    with patch("app.storage.cloudinary.httpx.post", side_effect=fake_cloudinary_post):
        for kind, fname, payload_bytes, mime, expected_folder, expected_rtype in uploads_to_test:
            res = client.post(
                "/api/v2/advertiser/media/upload",
                headers=_auth_header(token),
                data={"asset_kind": kind},
                files={"file": (fname, payload_bytes, mime)},
            )
            assert res.status_code == 201, res.text
            body = res.json()
            assert body["storage_provider"] == "cloudinary"
            assert body["cloudinary_resource_type"] == expected_rtype
            assert body["cloudinary_public_id"].startswith(expected_folder + "/")
            # Public ID must include unpredictable random suffix, not just raw filename
            assert body["cloudinary_public_id"] != f"{expected_folder}/{Path(fname).stem}"
            assert body["cloudinary_url"].startswith(
                f"https://res.cloudinary.com/gtex-cloud-test/{expected_rtype}/upload/"
            )
            assert body["access_classification"] == "draft"
            assert body["original_filename"] == fname

            # Verify DB persistence: no BLOB bytes stored in AdvertiserMediaAsset.data
            with session_factory() as session:
                db_asset = session.get(AdvertiserMediaAsset, body["id"])
                assert db_asset is not None
                assert db_asset.data is None
                assert db_asset.storage_provider == "cloudinary"
                assert db_asset.storage_key == body["cloudinary_public_id"]
                assert db_asset.metadata_json["resource_type"] == expected_rtype
                assert db_asset.metadata_json["secure_url"] == body["cloudinary_url"]
                assert db_asset.metadata_json["original_filename"] == fname


def test_validation_rules_oversized_and_duration_enforcement(tmp_path: Path, monkeypatch) -> None:
    client, _ = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "music",
            "company_name": "Starboy Entertainment",
            "email": "music@starboy.example.com",
            "phone_number": "+2348033334444",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    )
    token = reg_res.json()["access_token"]

    # 1. Logo exceeding 5MB limit -> 413
    oversized_logo = _build_png() + (b"\x00" * (5 * 1024 * 1024 + 1024))
    logo_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "logo"},
        files={"file": ("huge-logo.png", oversized_logo, "image/png")},
    )
    assert logo_res.status_code == 413

    # 2. WAV audio exceeding 420 seconds (7 minutes) -> 422
    long_wav = _build_wav(duration_seconds=480, byte_rate=100)
    wav_res = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(token),
        data={"asset_kind": "music_audio"},
        files={"file": ("too-long.wav", long_wav, "audio/wav")},
    )
    assert wav_res.status_code == 422
    assert "420" in wav_res.json()["detail"]


def test_compensating_cloudinary_cleanup_on_db_failure_and_secret_redaction(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    reg_res = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "GTBank PLC",
            "email": "ads@gtbank.example.com",
            "phone_number": "+2348055551111",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    )
    token = reg_res.json()["access_token"]
    valid_png = _build_png()

    # 1. If Cloudinary upload fails, secret must never be exposed and no DB row created
    failed_http_resp = MagicMock()
    failed_http_resp.status_code = 500
    failed_http_resp.text = "Internal error with secret super_secret_cloudinary_api_key_do_not_expose"
    with patch("app.storage.cloudinary.httpx.post", return_value=failed_http_resp):
        fail_res = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token),
            data={"asset_kind": "logo"},
            files={"file": ("logo.png", valid_png, "image/png")},
        )
        assert fail_res.status_code in {502, 503}
        assert "super_secret_cloudinary_api_key_do_not_expose" not in fail_res.text

    with session_factory() as session:
        assert session.query(AdvertiserMediaAsset).count() == 0

    # 2. If Cloudinary upload succeeds but DB commit fails, compensating Cloudinary delete is called
    deleted_keys: list[tuple[str, str | None, str]] = []

    def fake_delete(self, key: str, *, resource_type: str | None = None, delivery_type: str = "upload") -> None:
        deleted_keys.append((key, resource_type, delivery_type))

    ok_http_resp = MagicMock()
    ok_http_resp.status_code = 200
    ok_http_resp.json.return_value = {
        "asset_id": "cld-orphan-1",
        "public_id": "gtex/commercial/brands/logos/ws/logo-orphan",
        "version": 1,
        "resource_type": "image",
        "format": "png",
        "bytes": len(valid_png),
        "secure_url": "https://res.cloudinary.com/gtex-cloud-test/image/upload/v1/gtex/commercial/brands/logos/ws/logo-orphan.png",
    }

    with (
        patch("app.storage.cloudinary.httpx.post", return_value=ok_http_resp),
        patch.object(CloudinaryObjectStorage, "delete", new=fake_delete),
        patch(
            "app.ads_engine.commercial_service.CommercialNetworkService.record_audit_log",
            side_effect=RuntimeError("Simulated DB failure"),
        ),
    ):
        db_fail_res = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token),
            data={"asset_kind": "logo"},
            files={"file": ("logo.png", valid_png, "image/png")},
        )
        assert db_fail_res.status_code == 503
        assert "rolled back" in db_fail_res.text
        assert len(deleted_keys) == 1
        assert deleted_keys[0][1] == "image"
        assert deleted_keys[0][2] == "authenticated"

    with session_factory() as session:
        assert session.query(AdvertiserMediaAsset).count() == 0


def test_asset_privacy_cross_workspace_isolation_and_public_cdn_delivery(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    with session_factory() as session:
        admin = User(
            id="comm-admin-1",
            email="admin@gtex.test",
            username="commadmin",
            password_hash=hash_password("AdminPass!123"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add(admin)
        session.flush()
        admin_token = AuthService().issue_session_tokens(admin, session=session).access_token
        session.commit()

    # Configure NGN rate on public_homepage
    client.patch(
        "/api/v2/admin/advertising/placements/public_homepage",
        headers=_auth_header(admin_token),
        json={"weekly_rate_minor_ngn": 10_000_000, "is_enabled": True},
    )

    adv1 = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Workspace One",
            "email": "one@workspace.example.com",
            "phone_number": "+2348010000001",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    ).json()
    token1 = adv1["access_token"]

    adv2 = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Workspace Two",
            "email": "two@workspace.example.com",
            "phone_number": "+2348010000002",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    ).json()
    token2 = adv2["access_token"]

    valid_png = _build_png()
    expected_cdn_url = "https://res.cloudinary.com/gtex-cloud-test/image/upload/v1731580001/gtex/commercial/brands/creatives/ws1/banner-1.png"
    ok_http_resp = MagicMock()
    ok_http_resp.status_code = 200
    ok_http_resp.json.return_value = {
        "asset_id": "cld-ws1-1",
        "public_id": "gtex/commercial/brands/creatives/ws1/banner-1",
        "version": 1731580001,
        "resource_type": "image",
        "format": "png",
        "bytes": len(valid_png),
        "secure_url": expected_cdn_url,
    }

    with patch("app.storage.cloudinary.httpx.post", return_value=ok_http_resp):
        asset_res = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token1),
            data={"asset_kind": "brand_image"},
            files={"file": ("banner.png", valid_png, "image/png")},
        )
    assert asset_res.status_code == 201
    asset = asset_res.json()
    asset_id = asset["id"]

    # 1. Unauthenticated request without preview token to draft asset MUST be rejected (403)
    unauth_res = client.get(f"/api/v2/public/ads/media/{asset_id}", follow_redirects=False)
    assert unauth_res.status_code == 403

    # 2. Other workspace user cannot access or attach Workspace One's draft asset (403)
    other_ws_media = client.get(
        f"/api/v2/public/ads/media/{asset_id}",
        headers=_auth_header(token2),
        follow_redirects=False,
    )
    assert other_ws_media.status_code == 403

    cross_camp = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(token2),
        json={
            "company_name": "Workspace Two",
            "contact_email": "two@workspace.example.com",
            "contact_phone": "+2348010000002",
            "placements": ["public_homepage"],
            "headline": "Unauthorized Asset Reference",
            "description": "Should fail.",
            "website_url": "https://ws2.example.com",
            "creative_asset_id": asset_id,
            "duration_days": 7,
        },
    )
    assert cross_camp.status_code == 403

    # 3. Workspace One owner CAN preview via signed preview_url or Authorization header (307 Redirect to Cloudinary)
    preview_res = client.get(asset["preview_url"], follow_redirects=False)
    assert preview_res.status_code == 307
    assert preview_res.headers["location"] == expected_cdn_url
    assert "private" in preview_res.headers.get("cache-control", "")

    # 4. Create campaign, settle NGN payment, and approve -> Asset becomes publicly deliverable via CDN
    camp = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(token1),
        json={
            "company_name": "Workspace One",
            "contact_email": "one@workspace.example.com",
            "contact_phone": "+2348010000001",
            "placements": ["public_homepage"],
            "headline": "Live Cloudinary Campaign",
            "description": "Served from Cloudinary CDN.",
            "website_url": "https://ws1.example.com",
            "creative_asset_id": asset_id,
            "duration_days": 7,
        },
    ).json()

    # Attempting to delete media attached to an active/under-review campaign must return 409 Conflict
    del_conflict = client.delete(f"/api/v2/advertiser/media/{asset_id}", headers=_auth_header(token1))
    assert del_conflict.status_code == 409

    with patch("httpx.post") as mock_post, patch("httpx.get") as mock_get:
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.raise_for_status = MagicMock()
        mock_init.json.return_value = {
            "status": True,
            "data": {"authorization_url": "https://checkout.paystack.com/1", "reference": "REF-CLD-1"},
        }
        mock_post.return_value = mock_init

        pay_rec = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(token1),
            json={"campaign_id": camp["id"], "provider": "paystack"},
        ).json()

        mock_ver = MagicMock()
        mock_ver.status_code = 200
        mock_ver.raise_for_status = MagicMock()
        mock_ver.json.return_value = {
            "status": True,
            "data": {"status": "success", "amount": 10_000_000, "currency": "NGN", "reference": pay_rec["reference"]},
        }
        mock_get.return_value = mock_ver

        client.post(f"/api/v2/advertiser/payments/{pay_rec['reference']}/verify", headers=_auth_header(token1))

    client.post(
        f"/api/v2/admin/advertising/campaigns/{camp['id']}/moderate",
        headers=_auth_header(admin_token),
        json={"action": "approve", "note": "Approved for live delivery"},
    )

    # Now unauthenticated public media request redirects (307) to Cloudinary CDN with public cache-control
    pub_media_res = client.get(f"/api/v2/public/ads/media/{asset_id}", follow_redirects=False)
    assert pub_media_res.status_code == 307
    assert pub_media_res.headers["location"] == expected_cdn_url
    assert "public" in pub_media_res.headers.get("cache-control", "")

    # And public campaign feed returns the direct Cloudinary CDN URL
    feed_res = client.get("/api/v2/public/ads/campaigns", params={"placement": "public_homepage"})
    assert feed_res.status_code == 200
    live_camp = next(c for c in feed_res.json()["campaigns"] if c["id"] == camp["id"])
    assert live_camp["creative_url"] == expected_cdn_url

    # 5. Taking down or pausing the campaign immediately revokes public media exposure
    client.post(
        f"/api/v2/admin/advertising/campaigns/{camp['id']}/moderate",
        headers=_auth_header(admin_token),
        json={"action": "takedown", "note": "Taken down"},
    )
    revoked_res = client.get(f"/api/v2/public/ads/media/{asset_id}", follow_redirects=False)
    assert revoked_res.status_code == 403


def test_stadium_perimeter_disabled_while_3d_gameplay_closed(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=False)

    with session_factory() as session:
        admin = User(
            id="comm-admin-stad",
            email="stad.admin@gtex.test",
            username="stadadmin",
            password_hash=hash_password("AdminPass!123"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add(admin)
        session.flush()
        admin_token = AuthService().issue_session_tokens(admin, session=session).access_token
        session.commit()

    # 1. Public placements list does NOT include stadium_perimeter
    pl_res = client.get("/api/v2/public/ads/placements")
    assert pl_res.status_code == 200
    assert all(p["placement_key"] != "stadium_perimeter" for p in pl_res.json())

    # 2. Price calculation for stadium_perimeter is rejected with 422
    calc_res = client.post(
        "/api/v2/public/ads/calculate-price",
        json={"division": "brand", "placements": ["stadium_perimeter"], "duration_days": 7},
    )
    assert calc_res.status_code == 422

    # 3. Admin cannot enable stadium_perimeter while 3D gameplay is closed
    patch_res = client.patch(
        "/api/v2/admin/advertising/placements/stadium_perimeter",
        headers=_auth_header(admin_token),
        json={"is_enabled": True, "delivery_surface_ready": True},
    )
    assert patch_res.status_code == 422

    # 4. Advertiser cannot book stadium_perimeter in a new brand campaign
    adv = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Stadium Test Brand",
            "email": "stadium@brand.example.com",
            "phone_number": "+2348099991111",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    ).json()
    adv_token = adv["access_token"]

    creative = client.post(
        "/api/v2/advertiser/media/upload",
        headers=_auth_header(adv_token),
        data={"asset_kind": "brand_image"},
        files={"file": ("banner.png", _build_png(), "image/png")},
    ).json()

    book_res = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(adv_token),
        json={
            "company_name": "Stadium Test Brand",
            "contact_email": "stadium@brand.example.com",
            "contact_phone": "+2348099991111",
            "placements": ["stadium_perimeter"],
            "headline": "Attempted 3D Perimeter Ad",
            "description": "Should be rejected.",
            "website_url": "https://stadium.example.com",
            "creative_asset_id": creative["id"],
            "duration_days": 7,
        },
    )
    assert book_res.status_code == 422


def _pay_and_approve_campaign(
    client: TestClient,
    *,
    adv_token: str,
    admin_token: str,
    campaign_id: str,
    amount_minor: int,
    ref_code: str,
) -> None:
    with patch("httpx.post") as mock_post, patch("httpx.get") as mock_get:
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.raise_for_status = MagicMock()
        mock_init.json.return_value = {
            "status": True,
            "data": {"authorization_url": f"https://checkout.paystack.com/{ref_code}", "reference": ref_code},
        }
        mock_post.return_value = mock_init

        pay_rec = client.post(
            "/api/v2/advertiser/payments/initiate",
            headers=_auth_header(adv_token),
            json={"campaign_id": campaign_id, "provider": "paystack"},
        ).json()

        mock_ver = MagicMock()
        mock_ver.status_code = 200
        mock_ver.raise_for_status = MagicMock()
        mock_ver.json.return_value = {
            "status": True,
            "data": {"status": "success", "amount": amount_minor, "currency": "NGN", "reference": pay_rec["reference"]},
        }
        mock_get.return_value = mock_ver

        ver_res = client.post(
            f"/api/v2/advertiser/payments/{pay_rec['reference']}/verify", headers=_auth_header(adv_token)
        )
        assert ver_res.status_code == 200, ver_res.text

    mod_res = client.post(
        f"/api/v2/admin/advertising/campaigns/{campaign_id}/moderate",
        headers=_auth_header(admin_token),
        json={"action": "approve", "note": "Approved in test"},
    )
    assert mod_res.status_code == 200, mod_res.text


def test_cloudinary_media_revocation_all_triggers_and_shared_asset_safety(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    with session_factory() as session:
        admin = User(
            id="comm-admin-rev",
            email="rev.admin@gtex.test",
            username="revadmin",
            password_hash=hash_password("AdminPass!123"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add(admin)
        session.flush()
        admin_token = AuthService().issue_session_tokens(admin, session=session).access_token
        session.commit()

    for key, rate in (
        ("public_homepage", 5_000_000),
        ("halftime_sponsorship", 8_000_000),
        ("sponsored_cards", 4_000_000),
        ("music_rotation", 3_000_000),
    ):
        patch_pl = client.patch(
            f"/api/v2/admin/advertising/placements/{key}",
            headers=_auth_header(admin_token),
            json={"weekly_rate_minor_ngn": rate, "is_enabled": True},
        )
        assert patch_pl.status_code == 200, patch_pl.text
    pkg_res = client.put(
        "/api/v2/admin/advertising/pricing",
        headers=_auth_header(admin_token),
        json={
            "package_code": "music_rotation_7d",
            "name": "7-Day Music Rotation",
            "division": "music",
            "duration_days": 7,
            "placement_keys": ["music_rotation"],
            "price_minor_ngn": 3_000_000,
            "is_active": True,
        },
    )
    assert pkg_res.status_code == 200, pkg_res.text

    adv = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "music",
            "company_name": "Mavin Global Holdings",
            "email": "ads@mavin.example.com",
            "phone_number": "+2348080000001",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    ).json()
    adv_token = adv["access_token"]

    upload_seq = 0
    rename_calls: list[dict[str, str]] = []
    destroy_calls: list[dict[str, str]] = []

    def fake_cld_post(url: str, *, data: dict[str, str], files: dict | None = None, timeout: float = 120.0):
        nonlocal upload_seq
        resp = MagicMock()
        resp.status_code = 200
        if url.endswith("/rename"):
            rename_calls.append({"url": url, **data})
            from_id = data["from_public_id"]
            to_id = data["to_public_id"]
            rtype = "video" if "/video/rename" in url else "image"
            ext = "mp3" if rtype == "video" else "png"
            resp.json.return_value = {
                "public_id": to_id,
                "version": 1731590000 + len(rename_calls),
                "type": data.get("type", "authenticated"),
                "secure_url": f"https://res.cloudinary.com/gtex-cloud-test/{rtype}/authenticated/s--NEWSIG99--/v1/{to_id}.{ext}",
                "from_public_id": from_id,
            }
            return resp
        if url.endswith("/destroy"):
            destroy_calls.append({"url": url, **data})
            resp.json.return_value = {"result": "ok"}
            return resp
        upload_seq += 1
        public_id = f"{data.get('folder', '')}/{data['public_id']}".strip("/")
        rtype = "video" if "/video/upload" in url else "image"
        ext = "mp3" if rtype == "video" else "png"
        resp.json.return_value = {
            "asset_id": f"cld-rev-{upload_seq}",
            "public_id": public_id,
            "version": 1731580000 + upload_seq,
            "resource_type": rtype,
            "type": "authenticated",
            "format": ext,
            "bytes": len(files["file"][1]) if files else 256,
            "width": 1280 if rtype == "image" else None,
            "height": 720 if rtype == "image" else None,
            "duration": 30.0 if rtype == "video" else None,
            "secure_url": f"https://res.cloudinary.com/gtex-cloud-test/{rtype}/authenticated/s--ORIG{upload_seq:04d}--/v1/{public_id}.{ext}",
        }
        return resp

    valid_png = _build_png(1280, 720)
    valid_mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x10" + b"\x00" * 512

    with patch("app.storage.cloudinary.httpx.post", side_effect=fake_cld_post):
        shared_logo = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "logo"},
            files={"file": ("shared-logo.png", valid_png, "image/png")},
        ).json()
        banner_a = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "brand_image"},
            files={"file": ("banner-a.png", valid_png, "image/png")},
        ).json()
        banner_b = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "brand_image"},
            files={"file": ("banner-b.png", valid_png, "image/png")},
        ).json()
        banner_c = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "brand_image"},
            files={"file": ("banner-c.png", valid_png, "image/png")},
        ).json()
        track_mp3 = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "music_audio"},
            files={"file": ("afrobeat-hit.mp3", valid_mp3, "audio/mpeg")},
        ).json()
        track_art = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "music_artwork"},
            files={"file": ("cover.png", valid_png, "image/png")},
        ).json()
        orphan_draft = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(adv_token),
            data={"asset_kind": "brand_image"},
            files={"file": ("orphan-draft.png", valid_png, "image/png")},
        ).json()

        camp_a = client.post(
            "/api/v2/advertiser/campaigns/brand",
            headers=_auth_header(adv_token),
            json={
                "company_name": "Mavin Brand A",
                "contact_email": "ads@mavin.example.com",
                "contact_phone": "+2348080000001",
                "logo_asset_id": shared_logo["id"],
                "placements": ["public_homepage"],
                "headline": "Campaign A",
                "description": "Shares logo",
                "website_url": "https://mavin.example.com/a",
                "creative_asset_id": banner_a["id"],
                "duration_days": 7,
            },
        ).json()
        camp_b = client.post(
            "/api/v2/advertiser/campaigns/brand",
            headers=_auth_header(adv_token),
            json={
                "company_name": "Mavin Brand B",
                "contact_email": "ads@mavin.example.com",
                "contact_phone": "+2348080000001",
                "logo_asset_id": shared_logo["id"],
                "placements": ["halftime_sponsorship"],
                "headline": "Campaign B",
                "description": "Shares logo",
                "website_url": "https://mavin.example.com/b",
                "creative_asset_id": banner_b["id"],
                "duration_days": 7,
            },
        ).json()
        camp_c = client.post(
            "/api/v2/advertiser/campaigns/brand",
            headers=_auth_header(adv_token),
            json={
                "company_name": "Mavin Brand C",
                "contact_email": "ads@mavin.example.com",
                "contact_phone": "+2348080000001",
                "placements": ["sponsored_cards"],
                "headline": "Campaign C Reject/Takedown",
                "description": "Tests reject & takedown",
                "website_url": "https://mavin.example.com/c",
                "creative_asset_id": banner_c["id"],
                "duration_days": 7,
            },
        ).json()
        camp_music_res = client.post(
            "/api/v2/advertiser/campaigns/music",
            headers=_auth_header(adv_token),
            json={
                "package_code": "music_rotation_7d",
                "audio_asset_id": track_mp3["id"],
                "artwork_asset_id": track_art["id"],
                "track_title": "Lagos Sunrise",
                "artist_name": "Rema Test",
                "genre": "Afrobeats",
                "duration_days": 7,
                "rights_declaration_accepted": True,
                "rights_holder": "Mavin Global",
            },
        )
        assert camp_music_res.status_code == 201, camp_music_res.text
        camp_music = camp_music_res.json()

        _pay_and_approve_campaign(
            client,
            adv_token=adv_token,
            admin_token=admin_token,
            campaign_id=camp_a["id"],
            amount_minor=5_000_000,
            ref_code="REF-A",
        )
        _pay_and_approve_campaign(
            client,
            adv_token=adv_token,
            admin_token=admin_token,
            campaign_id=camp_b["id"],
            amount_minor=8_000_000,
            ref_code="REF-B",
        )
        _pay_and_approve_campaign(
            client,
            adv_token=adv_token,
            admin_token=admin_token,
            campaign_id=camp_c["id"],
            amount_minor=4_000_000,
            ref_code="REF-C",
        )
        _pay_and_approve_campaign(
            client,
            adv_token=adv_token,
            admin_token=admin_token,
            campaign_id=camp_music["id"],
            amount_minor=3_000_000,
            ref_code="REF-M",
        )

        client.put(
            f"/api/v2/ads/brand/admin/campaigns/{camp_music['id']}/music-rights",
            headers=_auth_header(admin_token),
            json={"music_rights_verified": True, "note": "Rights verified"},
        )
        assert client.get(f"/api/v2/public/ads/media/{shared_logo['id']}", follow_redirects=False).status_code == 307
        assert client.get(f"/api/v2/public/ads/media/{banner_a['id']}", follow_redirects=False).status_code == 307
        assert client.get(f"/api/v2/public/ads/media/{banner_c['id']}", follow_redirects=False).status_code == 307
        assert client.get(f"/api/v2/public/ads/media/{track_mp3['id']}", follow_redirects=False).status_code == 307

        # 1) Campaign suspension + Shared-asset safety: banner_a revoked, shared_logo stays public!
        rename_before = len(rename_calls)
        client.post(
            f"/api/v2/admin/advertising/campaigns/{camp_a['id']}/moderate",
            headers=_auth_header(admin_token),
            json={"action": "suspend", "note": "Suspend A"},
        )
        revoked_targets = {c["from_public_id"] for c in rename_calls[rename_before:]}
        assert banner_a["cloudinary_public_id"] in revoked_targets
        assert shared_logo["cloudinary_public_id"] not in revoked_targets
        assert all(c["invalidate"] == "true" for c in rename_calls[rename_before:])
        assert client.get(f"/api/v2/public/ads/media/{banner_a['id']}", follow_redirects=False).status_code == 403
        assert client.get(f"/api/v2/public/ads/media/{shared_logo['id']}", follow_redirects=False).status_code == 307

        # 2) Campaign rejection (moderate action='reject') -> revokes banner_c
        rename_before_rej = len(rename_calls)
        client.post(
            f"/api/v2/admin/advertising/campaigns/{camp_c['id']}/moderate",
            headers=_auth_header(admin_token),
            json={"action": "reject", "note": "Rejected creative"},
        )
        assert banner_c["cloudinary_public_id"] in {c["from_public_id"] for c in rename_calls[rename_before_rej:]}
        assert client.get(f"/api/v2/public/ads/media/{banner_c['id']}", follow_redirects=False).status_code == 403

        # 3) Campaign expiry -> revokes banner_b AND shared_logo (last active reference gone!)
        with session_factory() as session:
            db_camp_b = session.get(BrandAdCampaign, camp_b["id"])
            assert db_camp_b is not None
            db_camp_b.end_at = datetime.now(UTC) - timedelta(hours=2)
            session.commit()

        rename_before_exp = len(rename_calls)
        assert client.get(f"/api/v2/public/ads/media/{banner_b['id']}", follow_redirects=False).status_code == 403
        assert client.get(f"/api/v2/public/ads/media/{shared_logo['id']}", follow_redirects=False).status_code == 403
        exp_revoked = {c["from_public_id"] for c in rename_calls[rename_before_exp:]}
        assert banner_b["cloudinary_public_id"] in exp_revoked
        assert shared_logo["cloudinary_public_id"] in exp_revoked

        # 4) Rights-verification revocation (PUT /music-rights AND moderate action='revoke_rights')
        rename_before_rights = len(rename_calls)
        rights_rev = client.put(
            f"/api/v2/ads/brand/admin/campaigns/{camp_music['id']}/music-rights",
            headers=_auth_header(admin_token),
            json={"music_rights_verified": False, "note": "Rights revoked"},
        )
        assert rights_rev.status_code == 200
        assert client.get(f"/api/v2/public/ads/media/{track_mp3['id']}", follow_redirects=False).status_code == 403
        assert client.get(f"/api/v2/public/ads/media/{track_art['id']}", follow_redirects=False).status_code == 403
        rot_res = client.get("/api/v2/public/ads/music/rotation").json()
        assert all(t["campaign_id"] != camp_music["id"] for t in rot_res["tracks"])
        rights_revoked_targets = {c["from_public_id"] for c in rename_calls[rename_before_rights:]}
        assert track_mp3["cloudinary_public_id"] in rights_revoked_targets
        assert track_art["cloudinary_public_id"] in rights_revoked_targets

        # Also exercise admin moderate action='revoke_rights' directly
        mod_revoke_rights = client.post(
            f"/api/v2/admin/advertising/campaigns/{camp_music['id']}/moderate",
            headers=_auth_header(admin_token),
            json={"action": "revoke_rights", "note": "Admin rights takedown"},
        )
        assert mod_revoke_rights.status_code == 200

        # 5) Media deletion (unattached draft & taken-down campaign assets) -> calls Cloudinary destroy(invalidate=true)
        del_res = client.delete(f"/api/v2/advertiser/media/{orphan_draft['id']}", headers=_auth_header(adv_token))
        assert del_res.status_code == 200
        assert any(
            d["public_id"] == orphan_draft["cloudinary_public_id"]
            and d["invalidate"] == "true"
            and d.get("type") == "authenticated"
            for d in destroy_calls
        )
        assert client.get(f"/api/v2/public/ads/media/{orphan_draft['id']}", follow_redirects=False).status_code == 404

        # 6) Advertiser workspace suspension -> revokes assets and blocks previously minted preview tokens (403)
        ws_susp = client.post(
            f"/api/v2/admin/advertising/accounts/{adv['workspace']['id']}/action",
            headers=_auth_header(admin_token),
            json={"action": "suspend", "note": "Policy violation"},
        )
        assert ws_susp.status_code == 200
        assert client.get(shared_logo["preview_url"], follow_redirects=False).status_code == 403


def test_placement_creative_restrictions_and_chunked_size_limits(tmp_path: Path, monkeypatch) -> None:
    client, session_factory = _build_cloudinary_test_app(tmp_path, monkeypatch, enable_cloudinary=True)

    with session_factory() as session:
        admin = User(
            id="comm-admin-pl",
            email="pl.admin@gtex.test",
            username="pladmin",
            password_hash=hash_password("AdminPass!123"),
            role=UserRole.ADMIN,
            account_type=PublicAccountType.USER,
            is_active=True,
        )
        session.add(admin)
        session.flush()
        admin_token = AuthService().issue_session_tokens(admin, session=session).access_token
        session.commit()

    for key in ("public_homepage", "login_page", "halftime_sponsorship", "sponsored_cards"):
        client.patch(
            f"/api/v2/admin/advertising/placements/{key}",
            headers=_auth_header(admin_token),
            json={"weekly_rate_minor_ngn": 4_000_000, "is_enabled": True},
        )

    adv = client.post(
        "/api/v2/advertiser/auth/register",
        json={
            "account_type": "business",
            "company_name": "Kuda Bank",
            "email": "brand@kuda.example.com",
            "phone_number": "+2348070001111",
            "password": "StrongPassword!123",  # pragma: allowlist secret
        },
    ).json()
    token = adv["access_token"]

    def fake_upload_post(url: str, *, data: dict[str, str], files: dict, timeout: float = 120.0):
        resp = MagicMock()
        resp.status_code = 200
        public_id = f"{data.get('folder', '')}/{data['public_id']}".strip("/")
        rtype = "video" if "/video/upload" in url else "image"
        fname = files["file"][0]
        dur = 40.0 if "40s" in fname else (15.0 if rtype == "video" else None)
        ext = Path(fname).suffix.lstrip(".") or "bin"
        resp.json.return_value = {
            "asset_id": f"cld-lim-{fname}",
            "public_id": public_id,
            "version": 1731580001,
            "resource_type": rtype,
            "type": "authenticated",
            "format": ext,
            "bytes": len(files["file"][1]),
            "width": 1920,
            "height": 1080,
            "duration": dur,
            "secure_url": f"https://res.cloudinary.com/gtex-cloud-test/{rtype}/authenticated/s--TESTSIGN--/v1/{public_id}.{ext}",
        }
        return resp

    silent_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 512
    large_12mb_png = _build_png(1920, 1080) + (b"\x00" * (12 * 1024 * 1024))
    near_limit_logo = _build_png(512, 512) + (b"\x00" * (4 * 1024 * 1024))
    raw_over_limit = b"\x00" * (5 * 1024 * 1024 + 512)

    with patch("app.storage.cloudinary.httpx.post", side_effect=fake_upload_post):
        vid_40s = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token),
            data={"asset_kind": "brand_video"},
            files={"file": ("kuda-40s-spot.mp4", silent_mp4, "video/mp4")},
        )
        assert vid_40s.status_code == 201, vid_40s.text
        vid_id = vid_40s.json()["id"]

        img_12mb = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token),
            data={"asset_kind": "brand_image"},
            files={"file": ("kuda-12mb.png", large_12mb_png, "image/png")},
        )
        assert img_12mb.status_code == 201, img_12mb.text
        img_id = img_12mb.json()["id"]

        logo_4mb = client.post(
            "/api/v2/advertiser/media/upload",
            headers=_auth_header(token),
            data={"asset_kind": "logo"},
            files={"file": ("kuda-4mb-logo.png", near_limit_logo, "image/png")},
        )
        assert logo_4mb.status_code == 201

    # Raw stream / Content-Length > 5MB for logo immediately returns 413
    raw_reject = client.post(
        "/api/v2/advertiser/media/upload",
        headers={
            **_auth_header(token),
            "x-asset-kind": "logo",
            "x-filename": "too-big.png",
            "content-type": "image/png",
        },
        content=raw_over_limit,
    )
    assert raw_reject.status_code == 413

    # 1. 40s video passes on halftime_sponsorship (max 45s)
    halftime_ok = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(token),
        json={
            "company_name": "Kuda Bank",
            "contact_email": "brand@kuda.example.com",
            "contact_phone": "+2348070001111",
            "placements": ["halftime_sponsorship"],
            "headline": "40s Halftime Takeover",
            "description": "Allowed up to 45s.",
            "website_url": "https://kuda.example.com",
            "creative_asset_id": vid_id,
            "duration_days": 7,
        },
    )
    assert halftime_ok.status_code == 201, halftime_ok.text

    # 2. Same 40s video rejected on public_homepage (30s max) & login_page (20s max)
    for restricted_key, expected_sec in (("public_homepage", "30 seconds"), ("login_page", "20 seconds")):
        rejected = client.post(
            "/api/v2/advertiser/campaigns/brand",
            headers=_auth_header(token),
            json={
                "company_name": "Kuda Bank",
                "contact_email": "brand@kuda.example.com",
                "contact_phone": "+2348070001111",
                "placements": [restricted_key],
                "headline": "Too Long For Placement",
                "description": "Should be rejected.",
                "website_url": "https://kuda.example.com",
                "creative_asset_id": vid_id,
                "duration_days": 7,
            },
        )
        assert rejected.status_code == 422
        assert expected_sec in rejected.json()["detail"]

    # 3. 12MB image accepted by upload (15MB global limit), rejected by sponsored_cards (10MB placement limit)
    card_too_big = client.post(
        "/api/v2/advertiser/campaigns/brand",
        headers=_auth_header(token),
        json={
            "company_name": "Kuda Bank",
            "contact_email": "brand@kuda.example.com",
            "contact_phone": "+2348070001111",
            "placements": ["sponsored_cards"],
            "headline": "Too Heavy Card",
            "description": "Exceeds 10MB.",
            "website_url": "https://kuda.example.com",
            "creative_asset_id": img_id,
            "duration_days": 7,
        },
    )
    assert card_too_big.status_code == 422
    assert "exceeds maximum allowed" in card_too_big.json()["detail"]


def test_production_startup_gate_blocks_missing_cloudinary_credentials(monkeypatch) -> None:
    from cryptography.fernet import Fernet
    from app.core.config import load_settings
    from app.main import _enforce_strict_live_startup_gate

    monkeypatch.setenv("GTE_APP_ENV", "production")
    monkeypatch.setenv("GTE_STARTUP_PROFILE", "production")
    monkeypatch.setenv("GTE_INGESTION_PROVIDER", "sportmonks")
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.setenv("GTE_TEST_AUTH_FIXTURE_MODE", "0")
    monkeypatch.setenv("GTE_BOOTSTRAP_ADMIN_ENABLED", "0")
    monkeypatch.setenv("GTE_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GTE_AUTH_SECRET", "prod-test-auth-secret-unique-value-9876543210")
    monkeypatch.setenv("GTE_MEDIA_SIGNING_SECRET", "prod-test-media-signing-secret-unique-9876543210")
    monkeypatch.setenv("GTE_FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GTE_COMMERCIAL_MEDIA_PROVIDER", "cloudinary")
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
    monkeypatch.delenv("CLOUDINARY_URL", raising=False)

    settings = load_settings()
    with pytest.raises(RuntimeError, match="commercial_storage_unconfigured"):
        _enforce_strict_live_startup_gate(settings, production_like=True)

    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "gtex-prod")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "prod-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "prod-secret")
    _enforce_strict_live_startup_gate(settings, production_like=True)
