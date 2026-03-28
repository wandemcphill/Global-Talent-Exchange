from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import os
from typing import Any

from services.publisher.hashtags import build_caption, generate_hashtags
from services.publisher.instagram import InstagramPublisher
from services.publisher.queue import PlatformName, PublishPhase, PublisherJob, PublisherQueue
from services.publisher.tiktok import TikTokPublisher
from services.publisher.youtube import YouTubePublisher


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _get_int(payload: Mapping[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _get_str(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _resolve_clip_id(clip: Mapping[str, Any]) -> str:
    direct = _get_str(clip, "clip_id", "highlight_id", "id")
    if direct:
        return direct
    seed = "|".join(
        part
        for part in (
            _get_str(clip, "match_id"),
            _get_str(clip, "video_path", "source_path", "video_url", "cdn_path"),
            _get_str(clip, "title"),
        )
        if part
    )
    if not seed:
        raise ValueError("Clip must provide clip_id/highlight_id or enough identifying fields.")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
    return f"clip_{digest}"


def _resolve_match_id(clip: Mapping[str, Any], clip_id: str) -> str:
    return _get_str(clip, "match_id") or f"match_for_{clip_id}"


def _resolve_video_path(clip: Mapping[str, Any], *, phase: PublishPhase) -> str | None:
    if phase == "polished":
        polished = _get_str(clip, "polished_video_path", "polished_source_path", "polished_video_url")
        if polished:
            return polished
    return _get_str(clip, "video_path", "source_path", "video_url", "cdn_path", "storage_key")


def _resolve_event_timestamp(clip: Mapping[str, Any], now: datetime) -> datetime:
    parsed = _parse_datetime(clip.get("event_timestamp") or clip.get("created_at") or clip.get("updated_at"))
    if parsed is None:
        return now
    return parsed


def _resolve_platforms(clip: Mapping[str, Any], policy: "PublisherSchedulePolicy") -> tuple[PlatformName, ...]:
    raw = clip.get("platforms")
    if isinstance(raw, (list, tuple, set)):
        resolved = tuple(str(item).strip().lower() for item in raw if str(item).strip())
        if resolved:
            return tuple(item for item in resolved if item in {"tiktok", "instagram", "youtube"})
    return policy.platforms


def _resolve_immediate_delay_seconds(clip: Mapping[str, Any], policy: "PublisherSchedulePolicy") -> int:
    viral_score = _get_int(clip, "viral_score", default=0)
    min_score = policy.min_viral_score + 1
    if viral_score <= min_score:
        return policy.immediate_max_delay_seconds
    top_band = max(100 - min_score, 1)
    normalized = min(max(viral_score - min_score, 0), top_band) / top_band
    spread = policy.immediate_max_delay_seconds - policy.immediate_min_delay_seconds
    return int(round(policy.immediate_max_delay_seconds - (spread * normalized)))


def _build_job_metadata(
    clip: Mapping[str, Any],
    *,
    clip_id: str,
    hashtags: tuple[str, ...],
    phase: PublishPhase,
) -> dict[str, Any]:
    metadata = dict(clip.get("metadata") or {})
    metadata.setdefault("clip_id", clip_id)
    metadata.setdefault("clip_title", _get_str(clip, "title") or "GTEX highlight")
    metadata.setdefault("minute", _get_int(clip, "minute", default=0))
    metadata.setdefault("team_name", _get_str(clip, "team_name"))
    metadata.setdefault("player_name", _get_str(clip, "player_name"))
    metadata.setdefault("event_type", _get_str(clip, "event_type") or "highlight")
    metadata.setdefault("viral_score", _get_int(clip, "viral_score", default=0))
    metadata.setdefault("hashtags", list(hashtags))
    metadata.setdefault("phase", phase)
    return metadata


@dataclass(frozen=True, slots=True)
class PublisherSchedulePolicy:
    min_viral_score: int = 70
    max_duration_seconds: int = 30
    immediate_min_delay_seconds: int = 30
    immediate_max_delay_seconds: int = 90
    polished_delay_seconds: int = 900
    max_attempts: int = 3
    platforms: tuple[PlatformName, ...] = ("tiktok", "instagram", "youtube")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "PublisherSchedulePolicy":
        env = environ or os.environ
        platforms = tuple(
            item.strip().lower()
            for item in env.get("GTE_PUBLISHER_PLATFORMS", "tiktok,instagram,youtube").split(",")
            if item.strip()
        )
        return cls(
            min_viral_score=max(int(env.get("GTE_PUBLISHER_MIN_VIRAL_SCORE", "70")), 0),
            max_duration_seconds=max(int(env.get("GTE_PUBLISHER_MAX_DURATION_SECONDS", "30")), 1),
            immediate_min_delay_seconds=max(int(env.get("GTE_PUBLISHER_IMMEDIATE_MIN_DELAY_SECONDS", "30")), 0),
            immediate_max_delay_seconds=max(int(env.get("GTE_PUBLISHER_IMMEDIATE_MAX_DELAY_SECONDS", "90")), 0),
            polished_delay_seconds=max(int(env.get("GTE_PUBLISHER_POLISHED_DELAY_SECONDS", "900")), 0),
            max_attempts=max(int(env.get("GTE_PUBLISHER_MAX_ATTEMPTS", "3")), 1),
            platforms=tuple(item for item in platforms if item in {"tiktok", "instagram", "youtube"})
            or ("tiktok", "instagram", "youtube"),
        )


def should_post(clip: Mapping[str, Any], policy: PublisherSchedulePolicy | None = None) -> bool:
    resolved_policy = policy or PublisherSchedulePolicy()
    viral_score = _get_int(clip, "viral_score", default=0)
    duration_seconds = _get_int(clip, "duration", "duration_seconds", default=0)
    video_path = _resolve_video_path(clip, phase="immediate")
    return viral_score > resolved_policy.min_viral_score and duration_seconds < resolved_policy.max_duration_seconds and bool(video_path)


def build_publish_jobs(
    clip: Mapping[str, Any],
    *,
    policy: PublisherSchedulePolicy | None = None,
    now: datetime | None = None,
) -> list[PublisherJob]:
    resolved_policy = policy or PublisherSchedulePolicy()
    runtime_now = now.astimezone(UTC) if now is not None else _utcnow()
    if not should_post(clip, resolved_policy):
        return []
    clip_id = _resolve_clip_id(clip)
    match_id = _resolve_match_id(clip, clip_id)
    hashtags = tuple(clip.get("hashtags") or generate_hashtags(clip))
    event_timestamp = _resolve_event_timestamp(clip, runtime_now)
    platforms = _resolve_platforms(clip, resolved_policy)

    immediate_delay_seconds = _resolve_immediate_delay_seconds(clip, resolved_policy)
    immediate_schedule = max(runtime_now, event_timestamp + timedelta(seconds=immediate_delay_seconds))
    immediate_caption = build_caption(clip, hashtags=hashtags, style="immediate")
    jobs: list[PublisherJob] = []

    raw_video_path = _resolve_video_path(clip, phase="immediate")
    if raw_video_path is None:
        return []
    for platform in platforms:
        jobs.append(
            PublisherJob(
                clip_id=clip_id,
                match_id=match_id,
                platform=platform,
                phase="immediate",
                scheduled_for=immediate_schedule,
                video_path=raw_video_path,
                caption=immediate_caption,
                hashtags=hashtags,
                metadata=_build_job_metadata(clip, clip_id=clip_id, hashtags=hashtags, phase="immediate"),
                max_attempts=resolved_policy.max_attempts,
            )
        )

    polished_enabled = bool(clip.get("publish_polished", True))
    polished_video_path = _resolve_video_path(clip, phase="polished")
    if polished_enabled and polished_video_path and polished_video_path != raw_video_path:
        polished_schedule = max(
            immediate_schedule,
            event_timestamp + timedelta(seconds=resolved_policy.polished_delay_seconds),
        )
        polished_caption = build_caption(clip, hashtags=hashtags, style="polished")
        for platform in platforms:
            jobs.append(
                PublisherJob(
                    clip_id=clip_id,
                    match_id=match_id,
                    platform=platform,
                    phase="polished",
                    scheduled_for=polished_schedule,
                    video_path=polished_video_path,
                    caption=polished_caption,
                    hashtags=hashtags,
                    metadata=_build_job_metadata(clip, clip_id=clip_id, hashtags=hashtags, phase="polished"),
                    max_attempts=resolved_policy.max_attempts,
                )
            )
    return jobs


def build_default_adapters(environ: Mapping[str, str] | None = None) -> dict[PlatformName, Any]:
    return {
        "tiktok": TikTokPublisher.from_env(environ),
        "instagram": InstagramPublisher.from_env(environ),
        "youtube": YouTubePublisher.from_env(environ),
    }


@dataclass(slots=True)
class PublisherScheduler:
    queue: PublisherQueue = field(default_factory=PublisherQueue)
    policy: PublisherSchedulePolicy = field(default_factory=PublisherSchedulePolicy)
    adapters: dict[PlatformName, Any] = field(default_factory=build_default_adapters)

    def schedule_clip(self, clip: Mapping[str, Any], *, now: datetime | None = None) -> list[Any]:
        jobs = build_publish_jobs(clip, policy=self.policy, now=now)
        return [self.queue.enqueue(job) for job in jobs]

    def publish_due_jobs(self, *, now: datetime | None = None, limit: int = 10) -> list[dict[str, Any]]:
        claimed = self.queue.claim_due_jobs(now=now, limit=limit)
        outcomes: list[dict[str, Any]] = []
        for record in claimed:
            adapter = self.adapters.get(record.job.platform)
            if adapter is None:
                skipped = self.queue.mark_skipped(
                    record.job.job_id,
                    reason=f"No adapter configured for {record.job.platform}.",
                )
                outcomes.append(
                    {
                        "job_id": skipped.job.job_id,
                        "platform": skipped.job.platform,
                        "phase": skipped.job.phase,
                        "status": skipped.status,
                        "error": skipped.last_error,
                    }
                )
                continue
            try:
                response = adapter.publish(
                    video_path=record.job.video_path,
                    caption=record.job.caption,
                    hashtags=record.job.hashtags,
                    metadata=record.job.metadata,
                )
                post_id = str(
                    response.get("post_id")
                    or response.get("id")
                    or f"{record.job.platform}-{record.job.phase}-{record.job.clip_id}"
                )
                posted = self.queue.mark_posted(
                    record.job.job_id,
                    post_id=post_id,
                    response=dict(response),
                )
                outcomes.append(
                    {
                        "job_id": posted.job.job_id,
                        "platform": posted.job.platform,
                        "phase": posted.job.phase,
                        "status": posted.status,
                        "post_id": posted.post_id,
                    }
                )
            except Exception as exc:
                failed = self.queue.mark_failed(
                    record.job.job_id,
                    error=str(exc),
                    requeue=record.attempt_count < record.max_attempts,
                )
                outcomes.append(
                    {
                        "job_id": failed.job.job_id,
                        "platform": failed.job.platform,
                        "phase": failed.job.phase,
                        "status": failed.status,
                        "error": failed.last_error,
                    }
                )
        return outcomes


__all__ = [
    "PublisherSchedulePolicy",
    "PublisherScheduler",
    "build_default_adapters",
    "build_publish_jobs",
    "should_post",
]
