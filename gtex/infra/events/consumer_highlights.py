from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_TOPIC = "match.events"
DEFAULT_GROUP_ID = "gtex-highlights"
DEFAULT_CLIENT_ID = "gtex-highlights-consumer"
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_QUEUE_FILE = "tmp/highlight_jobs.jsonl"
DEFAULT_VIDEO_ROOT = "/videos"
DEFAULT_CLIP_ROOT = "/clips"

_BOOTSTRAP_SERVERS_ENV = "GTE_EVENT_PIPELINE_BOOTSTRAP_SERVERS"
_TOPIC_ENV = "GTE_EVENT_PIPELINE_TOPIC"
_GROUP_ID_ENV = "GTE_EVENT_PIPELINE_HIGHLIGHTS_GROUP_ID"
_CLIENT_ID_ENV = "GTE_EVENT_PIPELINE_HIGHLIGHTS_CLIENT_ID"
_QUEUE_URL_ENV = "GTE_HIGHLIGHT_JOB_QUEUE_URL"
_QUEUE_FILE_ENV = "GTE_HIGHLIGHT_JOB_QUEUE_FILE"
_TIMEOUT_ENV = "GTE_HIGHLIGHT_JOB_QUEUE_TIMEOUT_SECONDS"
_VIDEO_ROOT_ENV = "GTE_HIGHLIGHT_SOURCE_VIDEO_DIR"
_CLIP_ROOT_ENV = "GTE_HIGHLIGHT_OUTPUT_DIR"

_MAJOR_GOAL_TYPES = {
    "goal",
    "goals",
    "own_goal",
    "penalty_goal",
    "penalty_scored",
    "winner",
}
_MAJOR_CARD_TYPES = {"red_card", "second_yellow_red", "straight_red"}
_MAJOR_SAVE_TYPES = {"save", "penalty_save", "big_save"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DetectedHighlight:
    label: str
    start_seconds: int
    end_seconds: int
    confidence: float


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_bootstrap_servers(raw: str | None = None) -> list[str]:
    candidate = raw if raw is not None else os.getenv(_BOOTSTRAP_SERVERS_ENV, DEFAULT_BOOTSTRAP_SERVERS)
    servers = _split_csv(candidate)
    return servers or [DEFAULT_BOOTSTRAP_SERVERS]


def resolve_topic(raw: str | None = None) -> str:
    candidate = raw if raw is not None else os.getenv(_TOPIC_ENV, DEFAULT_TOPIC)
    normalized = candidate.strip()
    return normalized or DEFAULT_TOPIC


def resolve_timeout_seconds(raw: float | str | None = None) -> float:
    candidate = raw if raw is not None else os.getenv(_TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(float(candidate), 0.1)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def resolve_queue_file(raw: str | None = None) -> Path:
    candidate = raw if raw is not None else os.getenv(_QUEUE_FILE_ENV, DEFAULT_QUEUE_FILE)
    normalized = candidate.strip()
    return Path(normalized or DEFAULT_QUEUE_FILE)


def resolve_video_root(raw: str | None = None) -> Path:
    candidate = raw if raw is not None else os.getenv(_VIDEO_ROOT_ENV, DEFAULT_VIDEO_ROOT)
    normalized = candidate.strip()
    return Path(normalized or DEFAULT_VIDEO_ROOT)


def resolve_clip_root(raw: str | None = None) -> Path:
    candidate = raw if raw is not None else os.getenv(_CLIP_ROOT_ENV, DEFAULT_CLIP_ROOT)
    normalized = candidate.strip()
    return Path(normalized or DEFAULT_CLIP_ROOT)


def create_consumer(
    *,
    bootstrap_servers: str | list[str] | tuple[str, ...] | None = None,
    topic: str | None = None,
    group_id: str | None = None,
    client_id: str | None = None,
) -> Any:
    from kafka import KafkaConsumer  # type: ignore[import-not-found]

    servers = resolve_bootstrap_servers(",".join(bootstrap_servers) if isinstance(bootstrap_servers, (list, tuple)) else bootstrap_servers)
    return KafkaConsumer(
        resolve_topic(topic),
        bootstrap_servers=servers,
        group_id=(group_id or os.getenv(_GROUP_ID_ENV, DEFAULT_GROUP_ID)).strip() or DEFAULT_GROUP_ID,
        client_id=(client_id or os.getenv(_CLIENT_ID_ENV, DEFAULT_CLIENT_ID)).strip() or DEFAULT_CLIENT_ID,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def _commit(consumer: Any) -> None:
    if hasattr(consumer, "commit"):
        consumer.commit()


def _event_type(event: Mapping[str, Any]) -> str:
    return str(event.get("event_type") or event.get("type") or "").strip().lower()


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clip_bounds(*, event_seconds: int, pre_roll: int, post_roll: int) -> tuple[int, int]:
    start = max(0, event_seconds - pre_roll)
    end = max(start + 1, event_seconds + post_roll)
    return start, end


def detect_highlight(event: Mapping[str, Any]) -> DetectedHighlight | None:
    minute = _safe_int(event.get("minute"))
    if minute is None:
        return None
    second = _safe_int(event.get("second"))
    clock_second = _safe_int(event.get("clock_second"))
    event_seconds = max(0, minute) * 60 + max(0, second if second is not None else clock_second or 0)

    normalized_type = _event_type(event)
    importance = _safe_float(event.get("importance") or event.get("importance_score")) or 0.0
    forced = bool(event.get("highlight") or event.get("is_highlight"))

    if forced:
        start, end = _clip_bounds(event_seconds=event_seconds, pre_roll=18, post_roll=12)
        return DetectedHighlight(label=normalized_type or "highlight", start_seconds=start, end_seconds=end, confidence=1.0)

    if normalized_type in _MAJOR_GOAL_TYPES:
        pre_roll = 22 if minute >= 85 else 18
        post_roll = 16 if minute >= 85 else 12
        label = "last_minute_goal" if minute >= 85 else "goal"
        start, end = _clip_bounds(event_seconds=event_seconds, pre_roll=pre_roll, post_roll=post_roll)
        return DetectedHighlight(label=label, start_seconds=start, end_seconds=end, confidence=0.98)

    if normalized_type in _MAJOR_CARD_TYPES:
        start, end = _clip_bounds(event_seconds=event_seconds, pre_roll=12, post_roll=8)
        return DetectedHighlight(label="red_card", start_seconds=start, end_seconds=end, confidence=0.94)

    if normalized_type in _MAJOR_SAVE_TYPES and importance >= 4.0:
        start, end = _clip_bounds(event_seconds=event_seconds, pre_roll=10, post_roll=8)
        return DetectedHighlight(label="big_save", start_seconds=start, end_seconds=end, confidence=0.8)

    if normalized_type in {"penalty_awarded", "penalty"}:
        start, end = _clip_bounds(event_seconds=event_seconds, pre_roll=15, post_roll=10)
        return DetectedHighlight(label="penalty_drama", start_seconds=start, end_seconds=end, confidence=0.78)

    return None


def _slugify(value: str) -> str:
    pieces = [character.lower() if character.isalnum() else "_" for character in value]
    collapsed = "".join(pieces)
    while "__" in collapsed:
        collapsed = collapsed.replace("__", "_")
    return collapsed.strip("_") or "highlight"


def _format_timestamp(total_seconds: int) -> str:
    hours, remainder = divmod(max(0, total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def build_highlight_job(
    event: Mapping[str, Any],
    detected: DetectedHighlight,
    *,
    video_root: str | Path | None = None,
    clip_root: str | Path | None = None,
) -> dict[str, Any]:
    match_id = str(event.get("match_id") or "").strip()
    if not match_id:
        raise ValueError("Highlight events require a non-empty 'match_id'.")
    minute = _safe_int(event.get("minute")) or 0
    event_type = _event_type(event) or detected.label
    output_name = f"{match_id}_{minute:02d}_{_slugify(event_type)}.mp4"
    return {
        "match_id": match_id,
        "event_id": event.get("event_id"),
        "event_type": event_type,
        "minute": minute,
        "label": detected.label,
        "confidence": round(detected.confidence, 3),
        "input": str(resolve_video_root(str(video_root)) / f"{match_id}.mp4") if video_root is not None else str(resolve_video_root() / f"{match_id}.mp4"),
        "start": _format_timestamp(detected.start_seconds),
        "end": _format_timestamp(detected.end_seconds),
        "output": str(resolve_clip_root(str(clip_root)) / output_name) if clip_root is not None else str(resolve_clip_root() / output_name),
    }


def push_job(
    job: Mapping[str, Any],
    *,
    queue_url: str | None = None,
    queue_file: str | Path | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
) -> str:
    resolved_queue_url = (queue_url if queue_url is not None else os.getenv(_QUEUE_URL_ENV, "")).strip()
    if resolved_queue_url:
        managed_session = session or requests.Session()
        created_session = session is None
        try:
            response = managed_session.post(
                resolved_queue_url,
                json=dict(job),
                timeout=resolve_timeout_seconds(timeout_seconds),
            )
            response.raise_for_status()
            return resolved_queue_url
        finally:
            if created_session:
                managed_session.close()

    target_file = resolve_queue_file(str(queue_file) if queue_file is not None else None)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with target_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(job), sort_keys=True))
        handle.write("\n")
    return str(target_file)


def process_stream(
    consumer: Iterable[object],
    *,
    queue_url: str | None = None,
    queue_file: str | Path | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
    video_root: str | Path | None = None,
    clip_root: str | Path | None = None,
) -> int:
    queued = 0
    for message in consumer:
        payload = getattr(message, "value", message)
        if not isinstance(payload, Mapping):
            logger.warning("highlight_consumer.skipping_invalid_payload", extra={"payload_type": type(payload).__name__})
            _commit(consumer)
            continue
        detected = detect_highlight(payload)
        if detected is not None:
            job = build_highlight_job(payload, detected, video_root=video_root, clip_root=clip_root)
            push_job(
                job,
                queue_url=queue_url,
                queue_file=queue_file,
                session=session,
                timeout_seconds=timeout_seconds,
            )
            queued += 1
        _commit(consumer)
    return queued


def run_consumer(
    *,
    consumer: Any | None = None,
    queue_url: str | None = None,
    queue_file: str | Path | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
    video_root: str | Path | None = None,
    clip_root: str | Path | None = None,
) -> int:
    managed_consumer = consumer or create_consumer()
    managed_session = session or requests.Session()
    created_consumer = consumer is None
    created_session = session is None
    try:
        return process_stream(
            managed_consumer,
            queue_url=queue_url,
            queue_file=queue_file,
            session=managed_session,
            timeout_seconds=timeout_seconds,
            video_root=video_root,
            clip_root=clip_root,
        )
    finally:
        if created_session:
            managed_session.close()
        if created_consumer and hasattr(managed_consumer, "close"):
            managed_consumer.close()


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    run_consumer()


if __name__ == "__main__":
    main()

