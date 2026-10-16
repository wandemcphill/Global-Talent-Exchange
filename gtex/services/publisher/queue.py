from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal

PlatformName = Literal["tiktok", "instagram", "youtube"]
PublishPhase = Literal["immediate", "polished"]
PublishStatus = Literal["queued", "processing", "posted", "failed", "skipped"]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def build_job_id(clip_id: str, phase: PublishPhase, platform: PlatformName) -> str:
    digest = hashlib.sha1(f"{clip_id}|{phase}|{platform}".encode("utf-8")).hexdigest()[:16]
    return f"pub_{digest}"


@dataclass(frozen=True, slots=True)
class PublisherJob:
    clip_id: str
    match_id: str
    platform: PlatformName
    phase: PublishPhase
    scheduled_for: datetime
    video_path: str
    caption: str
    hashtags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = 3
    job_id: str | None = None

    def __post_init__(self) -> None:
        clip_id = self.clip_id.strip()
        match_id = self.match_id.strip()
        video_path = self.video_path.strip()
        caption = self.caption.strip()
        if not clip_id:
            raise ValueError("clip_id must not be empty.")
        if not match_id:
            raise ValueError("match_id must not be empty.")
        if not video_path:
            raise ValueError("video_path must not be empty.")
        if not caption:
            raise ValueError("caption must not be empty.")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        normalized_tags = tuple(tag.strip() for tag in self.hashtags if str(tag).strip())
        object.__setattr__(self, "clip_id", clip_id)
        object.__setattr__(self, "match_id", match_id)
        object.__setattr__(self, "video_path", video_path)
        object.__setattr__(self, "caption", caption)
        object.__setattr__(self, "hashtags", normalized_tags)
        object.__setattr__(self, "scheduled_for", _normalize_datetime(self.scheduled_for))
        object.__setattr__(
            self,
            "job_id",
            self.job_id or build_job_id(clip_id=clip_id, phase=self.phase, platform=self.platform),
        )


@dataclass(frozen=True, slots=True)
class QueuedPublisherRecord:
    job: PublisherJob
    status: PublishStatus
    created_at: datetime
    updated_at: datetime
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    post_id: str | None = None
    platform_response: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PublisherQueue:
    database_path: str | Path = "tmp/publisher/publisher.db"

    def __post_init__(self) -> None:
        self.database_path = Path(self.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def enqueue(self, job: PublisherJob) -> QueuedPublisherRecord:
        timestamp = _utcnow().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO publish_jobs (
                    job_id,
                    clip_id,
                    match_id,
                    platform,
                    phase,
                    scheduled_for,
                    video_path,
                    caption,
                    hashtags_json,
                    metadata_json,
                    status,
                    created_at,
                    updated_at,
                    attempt_count,
                    max_attempts,
                    last_error,
                    post_id,
                    platform_response_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.clip_id,
                    job.match_id,
                    job.platform,
                    job.phase,
                    job.scheduled_for.isoformat(),
                    job.video_path,
                    job.caption,
                    json.dumps(list(job.hashtags), ensure_ascii=True, sort_keys=True),
                    json.dumps(job.metadata, ensure_ascii=True, sort_keys=True),
                    "queued",
                    timestamp,
                    timestamp,
                    0,
                    job.max_attempts,
                    None,
                    None,
                    json.dumps({}, ensure_ascii=True, sort_keys=True),
                ),
            )
        existing = self.get_by_target(clip_id=job.clip_id, phase=job.phase, platform=job.platform)
        if existing is None:  # pragma: no cover
            raise RuntimeError("Publisher job enqueue did not create or find a job record.")
        return existing

    def get(self, job_id: str) -> QueuedPublisherRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM publish_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def get_by_target(
        self,
        *,
        clip_id: str,
        phase: PublishPhase,
        platform: PlatformName,
    ) -> QueuedPublisherRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM publish_jobs WHERE clip_id = ? AND phase = ? AND platform = ?",
                (clip_id, phase, platform),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_jobs(self, *, status: PublishStatus | None = None) -> list[QueuedPublisherRecord]:
        query = "SELECT * FROM publish_jobs"
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY scheduled_for ASC, created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def claim_due_jobs(self, *, limit: int = 10, now: datetime | None = None) -> list[QueuedPublisherRecord]:
        claimed_ids: list[str] = []
        reference = _normalize_datetime(now or _utcnow()).isoformat()
        updated_at = _utcnow().isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM publish_jobs
                WHERE status = 'queued'
                  AND scheduled_for <= ?
                  AND attempt_count < max_attempts
                ORDER BY scheduled_for ASC, created_at ASC
                LIMIT ?
                """,
                (reference, max(limit, 1)),
            ).fetchall()
            for row in rows:
                result = connection.execute(
                    """
                    UPDATE publish_jobs
                    SET status = 'processing',
                        updated_at = ?,
                        attempt_count = attempt_count + 1
                    WHERE job_id = ?
                      AND status = 'queued'
                    """,
                    (updated_at, row["job_id"]),
                )
                if result.rowcount:
                    claimed_ids.append(str(row["job_id"]))
            connection.commit()
            if not claimed_ids:
                return []
            placeholders = ", ".join("?" for _ in claimed_ids)
            claimed_rows = connection.execute(
                f"SELECT * FROM publish_jobs WHERE job_id IN ({placeholders})",
                tuple(claimed_ids),
            ).fetchall()
        records = {str(row["job_id"]): self._row_to_record(row) for row in claimed_rows}
        return [records[job_id] for job_id in claimed_ids if job_id in records]

    def mark_posted(self, job_id: str, *, post_id: str, response: dict[str, Any]) -> QueuedPublisherRecord:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE publish_jobs
                SET status = 'posted',
                    updated_at = ?,
                    post_id = ?,
                    last_error = NULL,
                    platform_response_json = ?
                WHERE job_id = ?
                """,
                (
                    _utcnow().isoformat(),
                    post_id,
                    json.dumps(response, ensure_ascii=True, sort_keys=True),
                    job_id,
                ),
            )
        return self.get(job_id)  # pragma: no cover

    def mark_failed(
        self,
        job_id: str,
        *,
        error: str,
        requeue: bool = False,
    ) -> QueuedPublisherRecord:
        next_status: PublishStatus = "queued" if requeue else "failed"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE publish_jobs
                SET status = ?,
                    updated_at = ?,
                    last_error = ?
                WHERE job_id = ?
                """,
                (next_status, _utcnow().isoformat(), error.strip(), job_id),
            )
        return self.get(job_id)  # pragma: no cover

    def mark_skipped(self, job_id: str, *, reason: str) -> QueuedPublisherRecord:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE publish_jobs
                SET status = 'skipped',
                    updated_at = ?,
                    last_error = ?
                WHERE job_id = ?
                """,
                (_utcnow().isoformat(), reason.strip(), job_id),
            )
        return self.get(job_id)  # pragma: no cover

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS publish_jobs (
                    job_id TEXT PRIMARY KEY,
                    clip_id TEXT NOT NULL,
                    match_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    hashtags_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    last_error TEXT,
                    post_id TEXT,
                    platform_response_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_publish_jobs_target
                    ON publish_jobs (clip_id, phase, platform);
                CREATE INDEX IF NOT EXISTS idx_publish_jobs_due
                    ON publish_jobs (status, scheduled_for);
                """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_record(self, row: sqlite3.Row) -> QueuedPublisherRecord:
        hashtags = tuple(json.loads(str(row["hashtags_json"]) or "[]"))
        metadata = dict(json.loads(str(row["metadata_json"]) or "{}"))
        response = dict(json.loads(str(row["platform_response_json"]) or "{}"))
        job = PublisherJob(
            job_id=str(row["job_id"]),
            clip_id=str(row["clip_id"]),
            match_id=str(row["match_id"]),
            platform=str(row["platform"]),
            phase=str(row["phase"]),
            scheduled_for=datetime.fromisoformat(str(row["scheduled_for"])),
            video_path=str(row["video_path"]),
            caption=str(row["caption"]),
            hashtags=hashtags,
            metadata=metadata,
            max_attempts=int(row["max_attempts"]),
        )
        return QueuedPublisherRecord(
            job=job,
            status=str(row["status"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            last_error=str(row["last_error"]) if row["last_error"] is not None else None,
            post_id=str(row["post_id"]) if row["post_id"] is not None else None,
            platform_response=response,
        )


__all__ = [
    "PlatformName",
    "PublishPhase",
    "PublishStatus",
    "PublisherJob",
    "PublisherQueue",
    "QueuedPublisherRecord",
    "build_job_id",
]
