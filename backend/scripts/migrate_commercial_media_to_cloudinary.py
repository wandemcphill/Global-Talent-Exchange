from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for candidate in (str(BACKEND_DIR), str(ROOT_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ads_engine.commercial_service import CommercialNetworkService
from app.core.database import create_database_engine, create_session_factory
from app.models.commercial_network import AdvertiserMediaAsset, CommercialAuditLog
from app.storage.cloudinary import (
    CloudinaryObjectStorage,
    resolve_commercial_cloudinary_folder,
    resolve_commercial_resource_type,
)

logger = logging.getLogger("gtex.commercial.migration")


def build_migration_public_id(
    *,
    asset_id: str,
    asset_kind: str,
    workspace_id: str | None,
    original_filename: str | None,
    sha256_checksum: str,
) -> str:
    folder = resolve_commercial_cloudinary_folder(asset_kind, workspace_id)
    stem = Path(original_filename or "asset").stem
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()[:36] or "asset"
    clean_id = re.sub(r"[^a-zA-Z0-9]+", "", str(asset_id or "id")).lower()[:16] or "asset"
    digest_short = (sha256_checksum or "000000000000")[:12].lower()
    return f"{folder}/{safe_stem}-{clean_id}-{digest_short}"


def migrate_commercial_media_assets(
    session: Session,
    *,
    cloudinary_storage: CloudinaryObjectStorage | None = None,
    dry_run: bool = False,
    batch_size: int = 50,
    max_retries: int = 3,
    workspace_id: str | None = None,
    asset_id: str | None = None,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    storage = cloudinary_storage
    if not dry_run:
        if storage is None:
            storage = CloudinaryObjectStorage.from_env()
        if not storage.is_configured():
            raise RuntimeError(
                "Cloudinary credentials (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET) "
                "are required to run live commercial media migration."
            )

    stmt = select(AdvertiserMediaAsset).order_by(
        AdvertiserMediaAsset.created_at.asc(),
        AdvertiserMediaAsset.id.asc(),
    )
    if workspace_id:
        stmt = stmt.where(AdvertiserMediaAsset.workspace_id == workspace_id)
    if asset_id:
        stmt = stmt.where(AdvertiserMediaAsset.id == asset_id)

    all_rows = session.scalars(stmt).all()
    service = CommercialNetworkService(session)

    total_examined = 0
    already_migrated_skipped = 0
    invalid_skipped = 0
    migrated_count = 0
    dry_run_count = 0
    failed_count = 0
    errors: list[dict[str, Any]] = []
    migrated_items: list[dict[str, Any]] = []

    processed_in_batch = 0
    for asset in all_rows:
        total_examined += 1
        if asset.validation_status != "valid":
            invalid_skipped += 1
            continue

        existing_meta = dict(asset.metadata_json or {})
        if (
            asset.storage_provider == "cloudinary"
            and asset.storage_key
            and (existing_meta.get("secure_url") or existing_meta.get("cloudinary_url"))
        ):
            already_migrated_skipped += 1
            continue

        if processed_in_batch >= batch_size:
            break
        processed_in_batch += 1

        try:
            raw_bytes = service.get_media_asset_bytes(asset)
            if not raw_bytes:
                raise RuntimeError(
                    f"Asset '{asset.id}' returned 0 bytes from source storage '{asset.storage_provider}'."
                )

            actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
            if asset.sha256_hash and asset.sha256_hash.lower() != actual_sha256.lower():
                raise RuntimeError(
                    f"SHA-256 checksum mismatch for asset '{asset.id}': "
                    f"expected {asset.sha256_hash}, got {actual_sha256}."
                )

            actual_size = len(raw_bytes)
            if asset.size_bytes and int(asset.size_bytes) > 0 and int(asset.size_bytes) != actual_size:
                raise RuntimeError(
                    f"Byte size mismatch for asset '{asset.id}': " f"expected {asset.size_bytes}, got {actual_size}."
                )

            target_public_id = build_migration_public_id(
                asset_id=asset.id,
                asset_kind=asset.asset_kind,
                workspace_id=asset.workspace_id,
                original_filename=asset.original_filename or asset.sanitized_filename,
                sha256_checksum=actual_sha256,
            )
            resource_type = resolve_commercial_resource_type(asset.asset_kind, content_type=asset.mime_type)

            if dry_run:
                dry_run_count += 1
                migrated_items.append(
                    {
                        "asset_id": asset.id,
                        "workspace_id": asset.workspace_id,
                        "asset_kind": asset.asset_kind,
                        "source_provider": asset.storage_provider,
                        "source_key": asset.storage_key,
                        "target_provider": "cloudinary",
                        "target_public_id": target_public_id,
                        "resource_type": resource_type,
                        "size_bytes": actual_size,
                        "sha256": actual_sha256,
                        "status": "dry_run_ready",
                    }
                )
                continue

            assert storage is not None
            stored_obj = storage.put_bytes(
                key=target_public_id,
                content=raw_bytes,
                content_type=asset.mime_type,
                resource_type=resource_type,
                max_retries=max_retries,
                metadata={
                    "workspace_id": asset.workspace_id or "global",
                    "asset_kind": asset.asset_kind,
                    "original_filename": asset.original_filename,
                    "sha256": actual_sha256,
                    "access_classification": asset.access_classification or "draft",
                    "migrated_from": asset.storage_provider or "legacy",
                },
            )

            cloud_meta = dict(stored_obj.metadata or {})
            reported_bytes = int(cloud_meta.get("bytes") or stored_obj.size_bytes or actual_size)
            if reported_bytes != actual_size:
                raise RuntimeError(
                    f"Cloudinary uploaded size verification failed for asset '{asset.id}': "
                    f"uploaded {actual_size} bytes but provider reported {reported_bytes} bytes."
                )

            secure_url = str(cloud_meta.get("secure_url") or "").strip() or storage.build_delivery_url(
                stored_obj.key,
                resource_type=resource_type,
                format_ext=cloud_meta.get("format"),
                version=cloud_meta.get("cloudinary_version"),
            )
            if not secure_url:
                raise RuntimeError(f"Cloudinary did not return a valid delivery URL for asset '{asset.id}'.")

            previous_provider = asset.storage_provider
            previous_key = asset.storage_key
            now_iso = datetime.now(UTC).isoformat()

            updated_metadata = {
                **existing_meta,
                "storage_provider": "cloudinary",
                "cloudinary_public_id": stored_obj.key,
                "resource_type": cloud_meta.get("resource_type") or resource_type,
                "delivery_type": cloud_meta.get("delivery_type") or "authenticated",
                "secure_url": secure_url,
                "cloudinary_asset_id": cloud_meta.get("cloudinary_asset_id"),
                "cloudinary_version": cloud_meta.get("cloudinary_version"),
                "format": cloud_meta.get("format"),
                "bytes": actual_size,
                "width": cloud_meta.get("width") or asset.width,
                "height": cloud_meta.get("height") or asset.height,
                "duration": cloud_meta.get("duration") or asset.duration_seconds,
                "original_filename": asset.original_filename,
                "migration": {
                    "migrated_at": now_iso,
                    "previous_storage_provider": previous_provider,
                    "previous_storage_key": previous_key,
                    "preserved_legacy_blob": asset.data is not None,
                    "sha256_verified": actual_sha256,
                },
            }

            asset.storage_provider = "cloudinary"
            asset.storage_key = stored_obj.key
            asset.sha256_hash = actual_sha256
            asset.size_bytes = actual_size
            if cloud_meta.get("width") and not asset.width:
                asset.width = int(cloud_meta["width"])
            if cloud_meta.get("height") and not asset.height:
                asset.height = int(cloud_meta["height"])
            if cloud_meta.get("duration") and not asset.duration_seconds:
                asset.duration_seconds = int(round(float(cloud_meta["duration"])))
            asset.metadata_json = updated_metadata

            session.add(
                CommercialAuditLog(
                    actor_user_id=asset.uploaded_by_user_id,
                    workspace_id=asset.workspace_id,
                    entity_type="media_asset",
                    entity_id=asset.id,
                    action="migrated_media_asset_to_cloudinary",
                    metadata_json={
                        "previous_storage_provider": previous_provider,
                        "previous_storage_key": previous_key,
                        "cloudinary_public_id": stored_obj.key,
                        "resource_type": resource_type,
                        "size_bytes": actual_size,
                    },
                )
            )
            session.commit()
            migrated_count += 1
            migrated_items.append(
                {
                    "asset_id": asset.id,
                    "workspace_id": asset.workspace_id,
                    "asset_kind": asset.asset_kind,
                    "previous_provider": previous_provider,
                    "previous_key": previous_key,
                    "cloudinary_public_id": stored_obj.key,
                    "secure_url": secure_url,
                    "resource_type": resource_type,
                    "size_bytes": actual_size,
                    "status": "migrated",
                }
            )
        except Exception as exc:
            session.rollback()
            failed_count += 1
            logger.error("Failed migrating commercial media asset id=%s: %s", asset.id, exc)
            errors.append(
                {
                    "asset_id": asset.id,
                    "workspace_id": asset.workspace_id,
                    "asset_kind": asset.asset_kind,
                    "storage_provider": asset.storage_provider,
                    "storage_key": asset.storage_key,
                    "error": str(exc),
                }
            )

    return {
        "dry_run": dry_run,
        "batch_size": batch_size,
        "total_examined": total_examined,
        "already_migrated_skipped": already_migrated_skipped,
        "invalid_skipped": invalid_skipped,
        "migrated": migrated_count,
        "dry_run_candidates": dry_run_count,
        "failed": failed_count,
        "items": migrated_items,
        "errors": errors,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotent S3 / Legacy BLOB to Cloudinary migration utility for GTEX Commercial Advertising media."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL") or os.getenv("GTE_DATABASE_URL") or "",
        help="SQLAlchemy database URL (defaults to DATABASE_URL or GTE_DATABASE_URL).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and validate non-Cloudinary media records without uploading or modifying the database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Maximum number of non-Cloudinary media assets to process in this run (default: 50).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum upload retries per asset on transient network/provider errors (default: 3).",
    )
    parser.add_argument(
        "--workspace-id",
        default=None,
        help="Optional workspace ID filter.",
    )
    parser.add_argument(
        "--asset-id",
        default=None,
        help="Optional single media asset ID filter.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    if not args.database_url:
        logger.error("No database URL provided. Set DATABASE_URL or pass --database-url.")
        return 2

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        summary = migrate_commercial_media_assets(
            session,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            max_retries=args.max_retries,
            workspace_id=args.workspace_id,
            asset_id=args.asset_id,
        )
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
