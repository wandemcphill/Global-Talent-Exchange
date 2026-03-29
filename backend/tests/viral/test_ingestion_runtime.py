from __future__ import annotations

from app.core.events import DomainEvent, InMemoryEventPublisher
from app.viral.distribution import InMemoryViralDispatchPoolStore
from app.viral.ingestion_runtime import ViralDispatchRuntime


def test_viral_dispatch_runtime_seeds_pool_from_requested_events() -> None:
    publisher = InMemoryEventPublisher()
    store = InMemoryViralDispatchPoolStore()
    runtime = ViralDispatchRuntime(pool_store=store)
    runtime.ensure_event_subscription(publisher)

    publisher.publish(
        DomainEvent(
            name="viral.clip.dispatch.requested",
            payload={
                "clip_id": "clip-dispatch",
                "priority_score": 2.6,
                "metadata": {"source": "moments_engine"},
            },
            producer="moments_engine",
            aggregate_id="match-1",
            aggregate_type="competition_match",
        )
    )

    entries = store.top(limit=5)

    assert publisher.subscriber_count == 1
    assert len(entries) == 1
    assert entries[0].clip_id == "clip-dispatch"
    assert entries[0].score == 2.6
    assert entries[0].payload["initial_score"] == 2.6
    assert entries[0].payload["metadata"]["dispatch_event_name"] == "viral.clip.dispatch.requested"
    assert entries[0].payload["metadata"]["dispatch_producer"] == "moments_engine"
    assert entries[0].payload["metadata"]["aggregate_id"] == "match-1"
    assert entries[0].payload["metadata"]["aggregate_type"] == "competition_match"


def test_viral_dispatch_runtime_ignores_malformed_dispatch_events() -> None:
    store = InMemoryViralDispatchPoolStore()
    runtime = ViralDispatchRuntime(pool_store=store)

    runtime.handle_event(
        DomainEvent(
            name="viral.clip.dispatch.requested",
            payload={"priority_score": 1.7},
        )
    )

    assert store.top(limit=5) == []
