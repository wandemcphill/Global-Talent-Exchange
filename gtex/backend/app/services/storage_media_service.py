from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.config import MediaStorageConfig
from app.storage import ObjectStorage, StorageNotFound


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extension_for_content_type(content_type: str) -> str:
    normalized = (content_type or "").lower()
    if "mp4" in normalized:
        return ".mp4"
    if "mpeg" in normalized or "mp2t" in normalized:
        return ".mpeg"
    if "webm" in normalized:
        return ".webm"
    if "json" in normalized:
        return ".json"
    if "zip" in normalized:
        return ".zip"
    return ".bin"


@dataclass(frozen=True, slots=True)
class MediaAssetDescriptor:
    storage_key: str
    content_type: str
    size_bytes: int
    metadata: dict[str, Any]
    expires_at: datetime | None


@dataclass(slots=True)
class MediaStorageService:
    storage: ObjectStorage
    config: MediaStorageConfig

    def store_temporary_highlight(
        self,
        *,
        match_key: str,
        content: bytes,
        content_type: str,
        clip_label: str | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MediaAssetDescriptor:
        key = self._build_key(self.config.highlight_temp_prefix, match_key=match_key, suffix=_extension_for_content_type(content_type))
        expiry = expires_at or (_utcnow() + timedelta(hours=self.config.highlight_temp_ttl_hours))
        payload = {
            "match_key": match_key,
            "clip_label": clip_label,
            "kind": "highlight_temp",
            "expires_at": expiry.isoformat(),
        }
        if metadata:
            payload.update(metadata)
        stored = self.storage.put_bytes(key=key, content=content, content_type=content_type, metadata=payload)
        return MediaAssetDescriptor(
            storage_key=stored.key,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            metadata=stored.metadata,
            expires_at=expiry,
        )

    def store_archive_highlight(
        self,
        *,
        match_key: str,
        content: bytes,
        content_type: str,
        clip_label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MediaAssetDescriptor:
        key = self._build_key(self.config.highlight_archive_prefix, match_key=match_key, suffix=_extension_for_content_type(content_type))
        payload = {
            "match_key": match_key,
            "clip_label": clip_label,
            "kind": "highlight_archive",
        }
        if metadata:
            payload.update(metadata)
        stored = self.storage.put_bytes(key=key, content=content, content_type=content_type, metadata=payload)
        return MediaAssetDescriptor(
            storage_key=stored.key,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            metadata=stored.metadata,
            expires_at=None,
        )

    def store_export_package(
        self,
        *,
        match_key: str,
        content: bytes,
        content_type: str,
        export_label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MediaAssetDescriptor:
        key = self._build_key(self.config.highlight_export_prefix, match_key=match_key, suffix=_extension_for_content_type(content_type))
        payload = {
            "match_key": match_key,
            "export_label": export_label,
            "kind": "export_package",
        }
        if metadata:
            payload.update(metadata)
        stored = self.storage.put_bytes(key=key, content=content, content_type=content_type, metadata=payload)
        return MediaAssetDescriptor(
            storage_key=stored.key,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            metadata=stored.metadata,
            expires_at=None,
        )

    def archive_highlight(self, *, storage_key: str) -> MediaAssetDescriptor:
        metadata = self.storage.read_metadata(key=storage_key)
        match_key = metadata.get("match_key") or "unknown"
        content = self.storage.get_bytes(key=storage_key)
        content_type = metadata.get("content_type") or "application/octet-stream"
        archived = self.store_archive_highlight(
            match_key=str(match_key),
            content=content,
            content_type=str(content_type),
            clip_label=metadata.get("clip_label"),
            metadata={**metadata, "archived_from": storage_key, "archived_at": _utcnow().isoformat()},
        )
        self.storage.delete(key=storage_key)
        return archived

    def list_expired_temporary_highlights(self) -> list[str]:
        expired: list[str] = []
        for key in self.storage.list_prefix(prefix=self.config.highlight_temp_prefix):
            metadata = self.storage.read_metadata(key=key)
            raw_expiry = metadata.get("expires_at")
            if not raw_expiry:
                continue
            try:
                expiry = datetime.fromisoformat(str(raw_expiry))
            except ValueError:
                continue
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= _utcnow():
                expired.append(key)
        return expired

    def describe(self, *, storage_key: str) -> MediaAssetDescriptor:
        if not self.storage.exists(key=storage_key):
            raise StorageNotFound(f"Storage key not found: {storage_key}")
        metadata = self.storage.read_metadata(key=storage_key)
        content_type = metadata.get("content_type") or "application/octet-stream"
        size_bytes = int(metadata.get("size_bytes") or 0)
        expires_at = None
        raw_expiry = metadata.get("expires_at")
        if raw_expiry:
            try:
                expires_at = datetime.fromisoformat(str(raw_expiry))
            except ValueError:
                expires_at = None
        return MediaAssetDescriptor(
            storage_key=storage_key,
            content_type=str(content_type),
            size_bytes=size_bytes,
            metadata=metadata,
            expires_at=expires_at,
        )

    def _build_key(self, prefix: str, *, match_key: str, suffix: str) -> str:
        normalized_prefix = prefix.strip("/").replace("\\", "/")
        normalized_match = match_key.strip().replace("\\", "/")
        token = uuid4().hex[:12]
        return f"{normalized_prefix}/{normalized_match}/{token}{suffix}"


__all__ = ["MediaAssetDescriptor", "MediaStorageService"]
