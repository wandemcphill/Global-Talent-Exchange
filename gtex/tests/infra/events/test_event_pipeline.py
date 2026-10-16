from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

from infra.events.consumer_commentary import process_stream as process_commentary_stream
from infra.events.consumer_highlights import build_highlight_job, detect_highlight, process_stream as process_highlight_stream
from infra.events.producer import publish_event


class _FakeFuture:
    def __init__(self) -> None:
        self.timeout: int | None = None

    def get(self, timeout: int | None = None) -> None:
        self.timeout = timeout


class _FakeProducer:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.flush_calls = 0

    def send(self, topic, *, value, key=None, headers=None):  # noqa: ANN001
        future = _FakeFuture()
        self.messages.append(
            {
                "topic": topic,
                "value": value,
                "key": key,
                "headers": headers,
                "future": future,
            }
        )
        return future

    def flush(self) -> None:
        self.flush_calls += 1


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self) -> None:
        self.posts: list[dict[str, object]] = []

    def post(self, url, *, json=None, timeout=None, headers=None):  # noqa: ANN001
        self.posts.append({"url": url, "json": json, "timeout": timeout, "headers": headers})
        return _FakeResponse()

    def close(self) -> None:
        return None


class _FakeMessage:
    def __init__(self, value) -> None:  # noqa: ANN001
        self.value = value


class _FakeConsumer(list):
    def __init__(self, values: list[object]) -> None:
        super().__init__(_FakeMessage(value) for value in values)
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1


def _workspace_temp_dir() -> Path:
    root = Path.cwd() / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="event-pipeline-", dir=root))


def _workspace_temp_file(*, suffix: str) -> Path:
    root = Path.cwd() / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    handle, file_name = tempfile.mkstemp(prefix="event-pipeline-", suffix=suffix, dir=root)
    os.close(handle)
    Path(file_name).unlink(missing_ok=True)
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)
    return Path(file_name)


def test_publish_event_uses_match_id_as_message_key_and_flushes() -> None:
    producer = _FakeProducer()

    publish_event(
        {
            "match_id": "match-009",
            "minute": 77,
            "event_type": "goal",
        },
        topic="match.events",
        headers={"producer": "thread-c"},
        producer=producer,
    )

    assert producer.flush_calls == 1
    assert producer.messages[0]["topic"] == "match.events"
    assert producer.messages[0]["key"] == "match-009"
    assert producer.messages[0]["value"]["event_type"] == "goal"
    assert producer.messages[0]["headers"] == [("producer", b"thread-c")]
    assert producer.messages[0]["future"].timeout == 30


def test_commentary_consumer_posts_payload_and_commits_after_success() -> None:
    consumer = _FakeConsumer(
        [
            {
                "event_id": "event-1",
                "match_id": "match-42",
                "minute": 12,
                "event_type": "goal",
            }
        ]
    )
    session = _FakeSession()

    delivered = process_commentary_stream(
        consumer,
        endpoint="http://commentary:8000/commentary",
        session=session,
        timeout_seconds=3,
    )

    assert delivered == 1
    assert consumer.commit_calls == 1
    assert session.posts == [
        {
            "url": "http://commentary:8000/commentary",
            "json": {
                "event_id": "event-1",
                "match_id": "match-42",
                "minute": 12,
                "event_type": "goal",
            },
            "timeout": 3.0,
            "headers": {"Idempotency-Key": "event-1"},
        }
    ]


def test_highlight_consumer_detects_goal_and_writes_job_file() -> None:
    temp_dir = _workspace_temp_dir()
    queue_file = _workspace_temp_file(suffix=".jsonl")
    try:
        event = {
            "event_id": "event-99",
            "match_id": "match-99",
            "minute": 88,
            "second": 14,
            "event_type": "goal",
        }
        detected = detect_highlight(event)

        assert detected is not None
        job = build_highlight_job(
            event,
            detected,
            video_root=temp_dir / "videos",
            clip_root=temp_dir / "clips",
        )

        assert job["start"] == "01:27:52"
        assert job["end"] == "01:28:30"
        assert job["output"].endswith("match-99_88_goal.mp4")

        consumer = _FakeConsumer([event])

        queued = process_highlight_stream(
            consumer,
            queue_file=queue_file,
            video_root=temp_dir / "videos",
            clip_root=temp_dir / "clips",
        )

        assert queued == 1
        assert consumer.commit_calls == 1
        payloads = [json.loads(line) for line in queue_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert payloads == [job]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        queue_file.unlink(missing_ok=True)


def test_highlight_consumer_skips_non_highlight_events() -> None:
    queue_file = _workspace_temp_file(suffix=".jsonl")
    try:
        consumer = _FakeConsumer(
            [
                {
                    "match_id": "match-11",
                    "minute": 33,
                    "event_type": "throw_in",
                }
            ]
        )

        queued = process_highlight_stream(consumer, queue_file=queue_file)

        assert queued == 0
        assert consumer.commit_calls == 1
        assert queue_file.exists() is False
    finally:
        queue_file.unlink(missing_ok=True)
