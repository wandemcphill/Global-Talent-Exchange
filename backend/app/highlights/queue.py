from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Literal


HighlightRenderKind = Literal["clip", "reel"]
HighlightRenderStatus = Literal["queued", "processing", "succeeded", "failed"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_storage_key(key: str) -> str:
    raw = (key or "").strip().lstrip("/")
    path = PurePosixPath(raw)
    if not path.parts:
        raise ValueError("Storage key must not be empty.")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Storage key contains invalid segments.")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class HighlightRenderJob:
    kind: HighlightRenderKind
    match_id: str
    output_storage_key: str
    title: str
    duration_seconds: int
    highlight_id: str | None = None
    subtitle: str | None = None
    start_second: int | None = None
    end_second: int | None = None
    playback_speed: float | None = None
    source_path: str | None = None
    source_storage_key: str | None = None
    source_clip_storage_keys: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_storage_key", _normalize_storage_key(self.output_storage_key))
        if self.source_storage_key is not None:
            object.__setattr__(self, "source_storage_key", _normalize_storage_key(self.source_storage_key))
        if self.duration_seconds < 1:
            raise ValueError("duration_seconds must be at least 1.")
        normalized_sources = tuple(_normalize_storage_key(key) for key in self.source_clip_storage_keys)
        object.__setattr__(self, "source_clip_storage_keys", normalized_sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "match_id": self.match_id,
            "output_storage_key": self.output_storage_key,
            "title": self.title,
            "duration_seconds": self.duration_seconds,
            "highlight_id": self.highlight_id,
            "subtitle": self.subtitle,
            "start_second": self.start_second,
            "end_second": self.end_second,
            "playback_speed": self.playback_speed,
            "source_path": self.source_path,
            "source_storage_key": self.source_storage_key,
            "source_clip_storage_keys": list(self.source_clip_storage_keys),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HighlightRenderJob:
        return cls(
            kind=str(payload["kind"]),
            match_id=str(payload["match_id"]),
            output_storage_key=str(payload["output_storage_key"]),
            title=str(payload["title"]),
            duration_seconds=int(payload["duration_seconds"]),
            highlight_id=str(payload["highlight_id"]) if payload.get("highlight_id") is not None else None,
            subtitle=str(payload["subtitle"]) if payload.get("subtitle") is not None else None,
            start_second=int(payload["start_second"]) if payload.get("start_second") is not None else None,
            end_second=int(payload["end_second"]) if payload.get("end_second") is not None else None,
            playback_speed=float(payload["playback_speed"]) if payload.get("playback_speed") is not None else None,
            source_path=str(payload["source_path"]) if payload.get("source_path") else None,
            source_storage_key=str(payload["source_storage_key"]) if payload.get("source_storage_key") else None,
            source_clip_storage_keys=tuple(str(item) for item in payload.get("source_clip_storage_keys", [])),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class HighlightRenderJobRecord:
    job_id: str
    queue_name: str
    status: HighlightRenderStatus
    queued_at: datetime
    updated_at: datetime
    payload: HighlightRenderJob
    attempts: int = 0
    max_attempts: int = 1
    last_error: str | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "queue_name": self.queue_name,
            "status": self.status,
            "queued_at": self.queued_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "payload": self.payload.to_dict(),
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "completed_at": self.completed_at.isoformat() if self.completed_at is not None else None,
            "result": dict(self.result),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HighlightRenderJobRecord:
        completed_at_raw = payload.get("completed_at")
        return cls(
            job_id=str(payload["job_id"]),
            queue_name=str(payload["queue_name"]),
            status=str(payload["status"]),
            queued_at=datetime.fromisoformat(str(payload["queued_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            payload=HighlightRenderJob.from_dict(dict(payload["payload"])),
            attempts=int(payload.get("attempts", 0)),
            max_attempts=int(payload.get("max_attempts", 1)),
            last_error=str(payload["last_error"]) if payload.get("last_error") is not None else None,
            completed_at=datetime.fromisoformat(str(completed_at_raw)) if completed_at_raw else None,
            result=dict(payload.get("result") or {}),
        )


@dataclass(slots=True)
class FileHighlightRenderQueue:
    storage_root: Path
    queue_name: str = "clip_builder_queue"
    _root: Path = field(init=False)
    _pending_dir: Path = field(init=False)
    _processing_dir: Path = field(init=False)
    _completed_dir: Path = field(init=False)
    _failed_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self._root = self.storage_root / "_queues" / self.queue_name
        self._pending_dir = self._root / "pending"
        self._processing_dir = self._root / "processing"
        self._completed_dir = self._root / "completed"
        self._failed_dir = self._root / "failed"
        for directory in (self._pending_dir, self._processing_dir, self._completed_dir, self._failed_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        job: HighlightRenderJob,
        *,
        max_attempts: int = 1,
        replace_terminal: bool = False,
    ) -> HighlightRenderJobRecord:
        job_id = self.job_id_for_storage_key(job.output_storage_key)
        existing = self.get(job_id)
        if existing is not None:
            if replace_terminal and existing.status in {"succeeded", "failed"}:
                self._delete_record(job_id)
            else:
                return existing

        now = _utcnow()
        record = HighlightRenderJobRecord(
            job_id=job_id,
            queue_name=self.queue_name,
            status="queued",
            queued_at=now,
            updated_at=now,
            payload=job,
            attempts=0,
            max_attempts=max(1, max_attempts),
        )
        self._write_record(self._pending_path(job_id), record)
        return record

    def get(self, job_id: str) -> HighlightRenderJobRecord | None:
        for state in ("pending", "processing", "completed", "failed"):
            path = self._state_path(state, job_id)
            if path.exists():
                return self._read_record(path)
        return None

    def get_by_storage_key(self, storage_key: str) -> HighlightRenderJobRecord | None:
        return self.get(self.job_id_for_storage_key(storage_key))

    def claim_next(self) -> HighlightRenderJobRecord | None:
        for path in sorted(self._pending_dir.glob("*.json")):
            processing_path = self._processing_path(path.stem)
            try:
                path.replace(processing_path)
            except FileNotFoundError:
                continue
            record = self._read_record(processing_path)
            claimed = replace(
                record,
                status="processing",
                attempts=record.attempts + 1,
                updated_at=_utcnow(),
                last_error=None,
            )
            self._write_record(processing_path, claimed)
            return claimed
        return None

    def mark_succeeded(self, record: HighlightRenderJobRecord, *, result: dict[str, Any] | None = None) -> HighlightRenderJobRecord:
        completed_at = _utcnow()
        completed = replace(
            record,
            status="succeeded",
            updated_at=completed_at,
            completed_at=completed_at,
            last_error=None,
            result=dict(result or {}),
        )
        source_path = self._processing_path(record.job_id)
        target_path = self._completed_path(record.job_id)
        if source_path.exists():
            source_path.replace(target_path)
        self._write_record(target_path, completed)
        return completed

    def mark_pending(
        self,
        record: HighlightRenderJobRecord,
        *,
        error: str,
        result: dict[str, Any] | None = None,
    ) -> HighlightRenderJobRecord:
        pending = replace(
            record,
            status="queued",
            updated_at=_utcnow(),
            completed_at=None,
            last_error=error,
            result=dict(result or {}),
        )
        source_path = self._processing_path(record.job_id)
        target_path = self._pending_path(record.job_id)
        if source_path.exists():
            source_path.replace(target_path)
        self._write_record(target_path, pending)
        return pending

    def mark_failed(
        self,
        record: HighlightRenderJobRecord,
        *,
        error: str,
        result: dict[str, Any] | None = None,
    ) -> HighlightRenderJobRecord:
        completed_at = _utcnow()
        failed = replace(
            record,
            status="failed",
            updated_at=completed_at,
            completed_at=completed_at,
            last_error=error,
            result=dict(result or {}),
        )
        source_path = self._processing_path(record.job_id)
        target_path = self._failed_path(record.job_id)
        if source_path.exists():
            source_path.replace(target_path)
        self._write_record(target_path, failed)
        return failed

    @staticmethod
    def job_id_for_storage_key(storage_key: str) -> str:
        normalized = _normalize_storage_key(storage_key)
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:20]
        return f"highlight_{digest}"

    def _delete_record(self, job_id: str) -> None:
        for state in ("pending", "processing", "completed", "failed"):
            path = self._state_path(state, job_id)
            if path.exists():
                path.unlink()

    def _pending_path(self, job_id: str) -> Path:
        return self._pending_dir / f"{job_id}.json"

    def _processing_path(self, job_id: str) -> Path:
        return self._processing_dir / f"{job_id}.json"

    def _completed_path(self, job_id: str) -> Path:
        return self._completed_dir / f"{job_id}.json"

    def _failed_path(self, job_id: str) -> Path:
        return self._failed_dir / f"{job_id}.json"

    def _state_path(self, state: str, job_id: str) -> Path:
        return {
            "pending": self._pending_path(job_id),
            "processing": self._processing_path(job_id),
            "completed": self._completed_path(job_id),
            "failed": self._failed_path(job_id),
        }[state]

    def _write_record(self, path: Path, record: HighlightRenderJobRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(path)

    def _read_record(self, path: Path) -> HighlightRenderJobRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return HighlightRenderJobRecord.from_dict(payload)


__all__ = [
    "FileHighlightRenderQueue",
    "HighlightRenderJob",
    "HighlightRenderJobRecord",
    "HighlightRenderKind",
    "HighlightRenderStatus",
]
