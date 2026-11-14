from __future__ import annotations

import os
from pathlib import Path

from app.storage.base import ObjectStorage, StorageError, StorageNotFound, StorageObject
from app.storage.cloudinary import (
    COMMERCIAL_FOLDER_BY_ASSET_KIND,
    COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND,
    CloudinaryObjectStorage,
    generate_commercial_public_id,
    resolve_commercial_cloudinary_folder,
    resolve_commercial_resource_type,
    sign_cloudinary_params,
)
from app.storage.local import LocalObjectStorage
from app.storage.s3 import S3ObjectStorage

_PRODUCTION_ENVS = {"production", "prod", "release", "staging"}


def _is_production_env() -> bool:
    app_env = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    return app_env in _PRODUCTION_ENVS


def _allow_local_in_prod() -> bool:
    return os.getenv("GTE_ALLOW_LOCAL_STORAGE_IN_PRODUCTION", "false").strip().lower() in {
        "true",
        "1",
        "yes",
    }


def _build_s3_storage_from_env() -> S3ObjectStorage | None:
    s3_bucket = (os.getenv("GTE_S3_BUCKET") or os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET") or "").strip()
    if not s3_bucket:
        return None
    endpoint = os.getenv("GTE_S3_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL_S3") or "https://s3.amazonaws.com"
    region = os.getenv("GTE_S3_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    access_key = os.getenv("GTE_S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("GTE_S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    return S3ObjectStorage(
        bucket=s3_bucket,
        endpoint_url=endpoint,
        region=region,
        access_key_id=access_key,
        secret_access_key=secret_key,
    )


def _build_local_storage(root_override: Path | None = None) -> LocalObjectStorage:
    if root_override:
        return LocalObjectStorage(root_override)
    root_env = os.getenv("GTE_MEDIA_STORAGE_ROOT")
    if root_env:
        return LocalObjectStorage(Path(root_env))
    backend_root = Path(__file__).resolve().parent.parent.parent
    return LocalObjectStorage(backend_root / "storage")


def get_default_object_storage(root_override: Path | None = None) -> ObjectStorage:
    """Return the configured object storage backend for non-commercial storage consumers.

    In production with GTE_S3_BUCKET (or AWS_S3_BUCKET/S3_BUCKET) configured, returns
    S3ObjectStorage for durable, re-deployment persistent, multi-instance shared cloud storage.
    Otherwise, returns LocalObjectStorage backed by GTE_MEDIA_STORAGE_ROOT or local disk.
    """
    s3_storage = _build_s3_storage_from_env()
    if s3_storage is not None:
        return s3_storage

    if _is_production_env() and not _allow_local_in_prod():
        raise StorageError(
            "Durable cloud object storage (GTE_S3_BUCKET) is not configured in production/staging. "
            "Local container storage is ephemeral and cannot be used for commercial network media."
        )

    return _build_local_storage(root_override)


def get_commercial_object_storage(root_override: Path | None = None) -> ObjectStorage:
    """Return the configured primary storage adapter for GTEX Commercial Advertising Network uploads.

    Respects ``GTE_COMMERCIAL_MEDIA_PROVIDER`` ('cloudinary', 's3', 'local_disk'):
    - When ``GTE_COMMERCIAL_MEDIA_PROVIDER=cloudinary``, requires ``CLOUDINARY_CLOUD_NAME``,
      ``CLOUDINARY_API_KEY``, and ``CLOUDINARY_API_SECRET``. Fails closed if missing; never falls
      back to local container storage.
    - When ``GTE_COMMERCIAL_MEDIA_PROVIDER=s3``, requires S3 bucket configuration.
    - When unset in development/test, uses Cloudinary if configured, else S3 if configured, else local disk.
    - In production/staging, never falls back to local disk unless explicitly overridden for isolated tests.
    """
    provider = (os.getenv("GTE_COMMERCIAL_MEDIA_PROVIDER") or "").strip().lower()

    if provider == "cloudinary":
        cloudinary_storage = CloudinaryObjectStorage.from_env()
        if not cloudinary_storage.is_configured():
            raise StorageError(
                "Commercial media provider is set to 'cloudinary' (GTE_COMMERCIAL_MEDIA_PROVIDER=cloudinary), "
                "but CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, or CLOUDINARY_API_SECRET is missing."
            )
        return cloudinary_storage

    if provider == "s3":
        s3_storage = _build_s3_storage_from_env()
        if s3_storage is None:
            raise StorageError(
                "Commercial media provider is set to 's3' (GTE_COMMERCIAL_MEDIA_PROVIDER=s3), "
                "but GTE_S3_BUCKET is not configured."
            )
        return s3_storage

    if provider in {"local", "local_disk", "local_object_storage"}:
        if _is_production_env() and not _allow_local_in_prod():
            raise StorageError(
                "Local container storage cannot be selected for commercial advertising media in production/staging."
            )
        return _build_local_storage(root_override)

    if provider not in {"", "auto"}:
        raise StorageError(
            f"Unsupported GTE_COMMERCIAL_MEDIA_PROVIDER='{provider}'. Expected 'cloudinary', 's3', or 'local_disk'."
        )

    # Auto / unset mode: prefer Cloudinary when configured, then S3, then local (dev/test only)
    cloudinary_storage = CloudinaryObjectStorage.from_env()
    if cloudinary_storage.is_configured():
        return cloudinary_storage

    s3_storage = _build_s3_storage_from_env()
    if s3_storage is not None:
        return s3_storage

    if _is_production_env() and not _allow_local_in_prod():
        raise StorageError(
            "Durable cloud storage (GTE_COMMERCIAL_MEDIA_PROVIDER=cloudinary or GTE_S3_BUCKET) is not configured "
            "in production/staging. Local container storage is ephemeral and forbidden."
        )

    return _build_local_storage(root_override)


def get_storage_for_provider(
    provider_name: str | None,
    *,
    root_override: Path | None = None,
) -> ObjectStorage:
    """Return the storage adapter matching an asset's recorded ``storage_provider``.

    Enables mixed-provider read/delete compatibility across Cloudinary, legacy S3, and local test storage.
    """
    normalized = (provider_name or "").strip().lower()
    if normalized == "cloudinary":
        storage = CloudinaryObjectStorage.from_env()
        if not storage.is_configured():
            raise StorageError("Cloudinary credentials are required to read/manage Cloudinary-backed media assets.")
        return storage
    if normalized == "s3":
        s3_storage = _build_s3_storage_from_env()
        if s3_storage is None:
            raise StorageError("S3 configuration (GTE_S3_BUCKET) is required to read legacy S3 media assets.")
        return s3_storage
    if normalized in {"local", "local_disk", "local_object_storage"}:
        return _build_local_storage(root_override)
    return get_commercial_object_storage(root_override=root_override)


def validate_commercial_storage_configuration() -> str:
    """Validate commercial media storage configuration at startup or service initialization.

    Returns the resolved provider name ('cloudinary', 's3', or 'local_disk').
    Raises ``StorageError`` if configuration is invalid or missing in production.
    """
    storage = get_commercial_object_storage()
    if isinstance(storage, CloudinaryObjectStorage):
        return "cloudinary"
    if isinstance(storage, S3ObjectStorage):
        return "s3"
    return "local_disk"


__all__ = [
    "COMMERCIAL_FOLDER_BY_ASSET_KIND",
    "COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND",
    "CloudinaryObjectStorage",
    "LocalObjectStorage",
    "ObjectStorage",
    "S3ObjectStorage",
    "StorageError",
    "StorageNotFound",
    "StorageObject",
    "generate_commercial_public_id",
    "get_commercial_object_storage",
    "get_default_object_storage",
    "get_storage_for_provider",
    "resolve_commercial_cloudinary_folder",
    "resolve_commercial_resource_type",
    "sign_cloudinary_params",
    "validate_commercial_storage_configuration",
]
