from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.commercial_service import CommercialNetworkService
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
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
from app.models.user import User
from app.storage.base import StorageObject
from app.storage.cloudinary import CloudinaryObjectStorage
from scripts.migrate_commercial_media_to_cloudinary import migrate_commercial_media_assets


def _build_migration_session() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
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
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_idempotent_s3_and_blob_migration_to_cloudinary_and_mixed_provider_reads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_MEDIA_STORAGE_ROOT", str(tmp_path / "media"))
    session_factory = _build_migration_session()

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
    png_sha = hashlib.sha256(png_bytes).hexdigest()

    mp3_bytes = b"ID3\x04\x00\x00\x00\x00\x00\x10" + b"\x00" * 256
    mp3_sha = hashlib.sha256(mp3_bytes).hexdigest()

    # Write local/S3-simulated file on disk for asset 1
    local_key = "commercial/media/ws-alpha/2026/11/legacy-banner.png"
    local_file = tmp_path / "media" / local_key
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(png_bytes)

    with session_factory() as session:
        # Asset 1: stored in local/S3 object storage without DB BLOB
        asset_obj = AdvertiserMediaAsset(
            id="asset-legacy-storage-1",
            workspace_id="ws-alpha",
            uploaded_by_user_id=None,
            asset_kind="brand_image",
            original_filename="legacy-banner.png",
            sanitized_filename="legacy-banner.png",
            mime_type="image/png",
            size_bytes=len(png_bytes),
            sha256_hash=png_sha,
            is_silent_verified=True,
            has_audio_track=False,
            validation_status="valid",
            storage_provider="local",
            storage_key=local_key,
            access_classification="draft",
            metadata_json={"legacy": True},
            data=None,
        )
        # Asset 2: stored in legacy DB BLOB
        asset_blob = AdvertiserMediaAsset(
            id="asset-legacy-blob-2",
            workspace_id="ws-beta",
            uploaded_by_user_id=None,
            asset_kind="music_audio",
            original_filename="Afrobeat_Single.mp3",
            sanitized_filename="Afrobeat_Single.mp3",
            mime_type="audio/mpeg",
            size_bytes=len(mp3_bytes),
            sha256_hash=mp3_sha,
            is_silent_verified=False,
            has_audio_track=True,
            validation_status="valid",
            storage_provider="database",
            storage_key=None,
            access_classification="public_campaign",
            metadata_json={},
            data=mp3_bytes,
        )
        session.add_all([asset_obj, asset_blob])
        session.commit()

    uploaded_calls: list[dict[str, object]] = []
    mock_cloudinary = MagicMock(spec=CloudinaryObjectStorage)
    mock_cloudinary.is_configured.return_value = True

    def fake_put_bytes(
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict | None = None,
        resource_type: str | None = None,
        max_retries: int = 3,
    ) -> StorageObject:
        uploaded_calls.append(
            {
                "key": key,
                "size": len(content),
                "content_type": content_type,
                "resource_type": resource_type,
                "metadata": metadata,
            }
        )
        rtype = resource_type or "image"
        ext = "mp3" if "audio" in content_type else "png"
        return StorageObject(
            key=key,
            size_bytes=len(content),
            content_type=content_type,
            updated_at=datetime.now(UTC),
            metadata={
                "storage_backend": "cloudinary",
                "cloudinary_asset_id": f"cld-{len(uploaded_calls)}",
                "cloudinary_public_id": key,
                "cloudinary_version": 1731580099,
                "resource_type": rtype,
                "format": ext,
                "bytes": len(content),
                "secure_url": f"https://res.cloudinary.com/gtex-cloud-test/{rtype}/upload/v1731580099/{key}.{ext}",
            },
        )

    mock_cloudinary.put_bytes.side_effect = fake_put_bytes

    # 1. Dry-run mode: inspects and validates both records without uploading or mutating DB
    with session_factory() as session:
        dry_summary = migrate_commercial_media_assets(
            session,
            cloudinary_storage=mock_cloudinary,
            dry_run=True,
            batch_size=10,
        )
        assert dry_summary["dry_run"] is True
        assert dry_summary["dry_run_candidates"] == 2
        assert dry_summary["migrated"] == 0
        assert len(uploaded_calls) == 0

        a1 = session.get(AdvertiserMediaAsset, "asset-legacy-storage-1")
        assert a1 is not None and a1.storage_provider == "local"

    # 2. Live migration run: uploads both assets to Cloudinary in proper folders & resource types
    with session_factory() as session:
        live_summary = migrate_commercial_media_assets(
            session,
            cloudinary_storage=mock_cloudinary,
            dry_run=False,
            batch_size=10,
        )
        assert live_summary["migrated"] == 2
        assert live_summary["failed"] == 0
        assert len(uploaded_calls) == 2

        # Verify folder & resource_type mapping
        call_img = next(c for c in uploaded_calls if c["content_type"] == "image/png")
        call_aud = next(c for c in uploaded_calls if c["content_type"] == "audio/mpeg")
        assert str(call_img["key"]).startswith("gtex/commercial/brands/creatives/ws-alpha/")
        assert call_img["resource_type"] == "image"
        assert str(call_aud["key"]).startswith("gtex/commercial/music/audio/ws-beta/")
        assert call_aud["resource_type"] == "video"

        # Verify DB records updated and source files/BLOBs were NOT deleted automatically
        a1 = session.get(AdvertiserMediaAsset, "asset-legacy-storage-1")
        a2 = session.get(AdvertiserMediaAsset, "asset-legacy-blob-2")
        assert a1 is not None and a1.storage_provider == "cloudinary"
        assert a1.metadata_json["migration"]["previous_storage_provider"] == "local"
        assert a1.metadata_json["migration"]["previous_storage_key"] == local_key
        assert local_file.exists()

        assert a2 is not None and a2.storage_provider == "cloudinary"
        assert a2.metadata_json["migration"]["previous_storage_provider"] == "database"
        assert a2.data == mp3_bytes  # Legacy BLOB preserved during migration

        # Mixed-provider read check
        svc = CommercialNetworkService(session)
        assert svc.get_cloudinary_delivery_url(a1).startswith(
            "https://res.cloudinary.com/gtex-cloud-test/image/upload/"
        )
        assert svc.get_cloudinary_delivery_url(a2).startswith(
            "https://res.cloudinary.com/gtex-cloud-test/video/upload/"
        )

    # 3. Idempotent re-run: running migration a second time skips already migrated records with zero duplicate uploads
    with session_factory() as session:
        second_summary = migrate_commercial_media_assets(
            session,
            cloudinary_storage=mock_cloudinary,
            dry_run=False,
            batch_size=10,
        )
        assert second_summary["already_migrated_skipped"] == 2
        assert second_summary["migrated"] == 0
        assert len(uploaded_calls) == 2
