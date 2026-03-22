from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
from typing import Any

from app.storage.base import ObjectStorage, StorageNotFound, StorageObject


def _normalize_key(key: str) -> PurePosixPath:
    raw = (key or "").strip().lstrip("/")
    candidate = PurePosixPath(raw)
    if not candidate.parts:
        raise ValueError("Storage key must not be empty.")
    if any(part in {"..", "."} for part in candidate.parts):
        raise ValueError("Storage key contains invalid segments.")
    return candidate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class LocalObjectStorage(ObjectStorage):
    root: Path

    def put_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> StorageObject:
        path = self._resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        payload = metadata or {}
        payload.setdefault("content_type", content_type)
        payload.setdefault("size_bytes", len(content))
        payload.setdefault("updated_at", _utcnow().isoformat())
        self._write_metadata(path, payload)
        return StorageObject(
            key=self._key_from_path(path),
            size_bytes=len(content),
            content_type=content_type,
            metadata=payload,
            updated_at=_utcnow(),
        )

    def get_bytes(self, *, key: str) -> bytes:
        path = self._resolve_path(key)
        if not path.exists():
            raise StorageNotFound(f"Storage key not found: {key}")
        return path.read_bytes()

    def open_file(self, *, key: str) -> Path:
        path = self._resolve_path(key)
        if not path.exists():
            raise StorageNotFound(f"Storage key not found: {key}")
        return path

    def delete(self, *, key: str) -> None:
        path = self._resolve_path(key)
        if path.exists():
            path.unlink()
        meta = self._metadata_path(path)
        if meta.exists():
            meta.unlink()

    def exists(self, *, key: str) -> bool:
        return self._resolve_path(key).exists()

    def list_prefix(self, *, prefix: str) -> list[str]:
        prefix_path = _normalize_key(prefix)
        root = (self.root / prefix_path).resolve()
        if not root.exists():
            return []
        keys: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name.endswith(".meta.json"):
                continue
            keys.append(self._key_from_path(path))
        return sorted(keys)

    def read_metadata(self, *, key: str) -> dict[str, Any]:
        path = self._resolve_path(key)
        meta_path = self._metadata_path(path)
        if not meta_path.exists():
            return {}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _resolve_path(self, key: str) -> Path:
        normalized = _normalize_key(key)
        path = (self.root / normalized).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root)):
            raise ValueError("Storage key resolved outside storage root.")
        return path

    def _metadata_path(self, path: Path) -> Path:
        return path.with_suffix(path.suffix + ".meta.json")

    def _write_metadata(self, path: Path, payload: dict[str, Any]) -> None:
        meta_path = self._metadata_path(path)
        meta_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _key_from_path(self, path: Path) -> str:
        return path.relative_to(self.root.resolve()).as_posix()


__all__ = ["LocalObjectStorage"]
