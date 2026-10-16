from __future__ import annotations

from app.backbone.kafka import KafkaMessage
from app.viral.aggregation_worker import ClipEventAggregationService, clip_metrics_key


class _FakePipeline:
    def __init__(self, client: "_FakeRedis") -> None:
        self.client = client
        self.operations: list[tuple[str, tuple[object, ...]]] = []

    def hincrbyfloat(self, key: str, field: str, amount: float) -> "_FakePipeline":
        self.operations.append(("hincrbyfloat", (key, field, amount)))
        return self

    def expire(self, key: str, ttl: int) -> "_FakePipeline":
        self.operations.append(("expire", (key, ttl)))
        return self

    def execute(self) -> list[object]:
        results: list[object] = []
        for operation, args in self.operations:
            if operation == "hincrbyfloat":
                results.append(self.client.hincrbyfloat(*args))
            elif operation == "expire":
                results.append(self.client.expire(*args))
        return results


class _FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, float]] = {}
        self.values: dict[str, str] = {}
        self.expiry: dict[str, int] = {}

    def pipeline(self, transaction: bool = False) -> _FakePipeline:
        return _FakePipeline(self)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.expiry[key] = ex
        return True

    def hincrbyfloat(self, key: str, field: str, amount: float) -> float:
        hash_payload = self.hashes.setdefault(key, {})
        hash_payload[field] = hash_payload.get(field, 0.0) + float(amount)
        return hash_payload[field]

    def expire(self, key: str, ttl: int) -> bool:
        self.expiry[key] = ttl
        return True

    def close(self) -> None:
        return None


def test_aggregation_worker_deduplicates_and_rolls_up_metrics() -> None:
    redis_client = _FakeRedis()
    service = ClipEventAggregationService(redis_client=redis_client, dedupe_ttl_seconds=3600)
    first_event = {
        "event_id": "5a2f0d83-0246-4d4f-ae49-a808dbd551f3",
        "clip_id": "clip-7",
        "user_id": "user-1",
        "session_id": "session-1",
        "timestamp": "2026-03-28T12:00:00Z",
        "event_type": "view",
        "watch_time_ms": 2400,
        "video_length_ms": 12000,
        "metadata": {
            "device": "ios",
            "country": "NG",
            "referrer": "feed",
        },
    }
    duplicate_event = dict(first_event)
    second_event = {
        "event_id": "15b2a344-bd17-4695-82d9-d0f0e69a0d31",
        "clip_id": "clip-7",
        "user_id": None,
        "session_id": "session-2",
        "timestamp": "2026-03-28T12:00:03Z",
        "event_type": "scroll",
        "watch_time_ms": 500,
        "video_length_ms": 12000,
        "metadata": {
            "device": "android",
            "country": "US",
            "referrer": "discover",
        },
    }
    result = service.process_messages(
        [
            KafkaMessage(topic="clip.view", key="clip-7", value=first_event),
            KafkaMessage(topic="clip.view", key="clip-7", value=duplicate_event),
            KafkaMessage(topic="clip.scroll", key="clip-7", value=second_event),
        ]
    )

    metrics = redis_client.hashes[clip_metrics_key("clip-7")]
    assert result.received == 3
    assert result.processed == 2
    assert result.duplicates == 1
    assert result.invalid == 0
    assert metrics["views"] == 1
    assert metrics["skips"] == 1
    assert metrics["total_watch_time"] == 2900


def test_aggregation_worker_skips_invalid_messages() -> None:
    redis_client = _FakeRedis()
    service = ClipEventAggregationService(redis_client=redis_client, dedupe_ttl_seconds=3600)

    result = service.process_messages(
        [
            KafkaMessage(
                topic="clip.view",
                key="clip-9",
                value={
                    "event_id": "not-a-uuid",
                    "clip_id": "clip-9",
                    "user_id": None,
                    "session_id": "session-1",
                    "timestamp": "2026-03-28T12:00:00Z",
                    "event_type": "view",
                    "watch_time_ms": 100,
                    "video_length_ms": 1000,
                    "metadata": {
                        "device": "ios",
                        "country": "NG",
                        "referrer": "feed",
                    },
                },
            )
        ]
    )

    assert result.received == 1
    assert result.processed == 0
    assert result.duplicates == 0
    assert result.invalid == 1
