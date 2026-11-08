from __future__ import annotations

import os
from pathlib import Path

from app.storage.base import ObjectStorage, StorageError, StorageNotFound, StorageObject
from app.storage.local import LocalObjectStorage
from app.storage.s3 import S3ObjectStorage


def get_default_object_storage(root_override: Path | None = None) -> ObjectStorage:
    """Return the configured object storage backend.

    In production with GTE_S3_BUCKET (or AWS_S3_BUCKET/S3_BUCKET) configured, returns
    S3ObjectStorage for durable, re-deployment persistent, multi-instance shared cloud storage.
    Otherwise, returns LocalObjectStorage backed by GTE_MEDIA_STORAGE_ROOT or local disk.
    """
    s3_bucket = os.getenv("GTE_S3_BUCKET") or os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET")
    if s3_bucket:
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

    # Explicit production configuration guard: prevent silent write to ephemeral container disk
    app_env = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    allow_local_in_prod = os.getenv("GTE_ALLOW_LOCAL_STORAGE_IN_PRODUCTION", "false").strip().lower() in {
        "true",
        "1",
        "yes",
    }
    if app_env in {"production", "prod", "release", "staging"} and not allow_local_in_prod:
        raise StorageError(
            "Durable cloud object storage (GTE_S3_BUCKET) is not configured in production/staging. "
            "Local container storage is ephemeral and cannot be used for commercial network media."
        )

    if root_override:
        return LocalObjectStorage(root_override)

    root_env = os.getenv("GTE_MEDIA_STORAGE_ROOT")
    if root_env:
        return LocalObjectStorage(Path(root_env))

    backend_root = Path(__file__).resolve().parent.parent.parent
    return LocalObjectStorage(backend_root / "storage")


__all__ = [
    "LocalObjectStorage",
    "ObjectStorage",
    "S3ObjectStorage",
    "StorageError",
    "StorageNotFound",
    "StorageObject",
    "get_default_object_storage",
]
