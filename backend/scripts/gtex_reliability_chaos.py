from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import json
from decimal import Decimal
from time import sleep
from typing import Any
from uuid import uuid4
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.event_backbone import build_outbox_event, defer_session_callback_until_commit
from app.core.events import DomainEvent
from app.infrastructure.distributed_lock import DistributedLockService
from app.infrastructure.outbox import flush_to_broker
from app.models.base import Base
from app.models.event_backbone import EventDeadLetter, EventOutbox
from app.models.scale_backbone import OrchestratorClipStateRecord, OrchestratorConfigRecord, PersonalizedFeedCacheEntryRecord
from app.orchestrator.global_state import GLOBAL_CONFIG_KEY, PersistentGlobalFeedStateStore
from app.viral.personalized_feed_service import PersistentPersonalizedFeedStore


class _FailingPublisher:
    def publish(self, row) -> None:
        del row
        raise RuntimeError("chaos publisher failure")

    def close(self) -> None:
        return None


class _FailingReadSessionFactory:
    def __call__(self):
        raise OperationalError("SELECT 1", {}, RuntimeError("read replica unavailable"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GTEX backend chaos probes.")
    parser.add_argument(
        "--scenario",
        choices=("deferred-callback", "replica-fallback", "redis-fallback", "outbox-dlq", "all"),
        required=True,
    )
    args = parser.parse_args()

    scenarios = [args.scenario] if args.scenario != "all" else [
        "deferred-callback",
        "replica-fallback",
        "redis-fallback",
        "outbox-dlq",
    ]
    summary: dict[str, Any] = {}
    for scenario in scenarios:
        if scenario == "deferred-callback":
            summary[scenario] = run_deferred_callback_probe()
        elif scenario == "replica-fallback":
            summary[scenario] = run_replica_fallback_probe()
        elif scenario == "redis-fallback":
            summary[scenario] = run_redis_fallback_probe()
        else:
            summary[scenario] = run_outbox_dlq_probe()
    print(json.dumps(summary, indent=2, default=_json_default))


def run_deferred_callback_probe() -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    fired: list[str] = []

    with session_factory() as session:
        session.execute(text("SELECT 1"))
        defer_session_callback_until_commit(session, callback=lambda: fired.append("outer"))
        savepoint = session.begin_nested()
        defer_session_callback_until_commit(session, callback=lambda: fired.append("nested"))
        before_nested_commit = list(fired)
        savepoint.commit()
        after_nested_commit = list(fired)
        session.commit()

    return {
        "before_nested_commit": before_nested_commit,
        "after_nested_commit": after_nested_commit,
        "after_outer_commit": list(fired),
        "passed": fired == ["outer", "nested"],
    }


def run_replica_fallback_probe() -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            PersonalizedFeedCacheEntryRecord.__table__,
            OrchestratorClipStateRecord.__table__,
            OrchestratorConfigRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add(
            PersonalizedFeedCacheEntryRecord(
                id=str(uuid4()),
                subject_key="viewer-chaos",
                clip_id="clip-chaos",
                position=1,
                score=99.0,
                payload_json={"clip_id": "clip-chaos"},
            )
        )
        session.add(
            OrchestratorClipStateRecord(
                clip_id="clip-chaos",
                stage="test",
                allocated_impressions=100,
                consumed_impressions=1,
                velocity_score=1.2,
                quality_score=0.8,
                trust_score=1.0,
                is_ad=False,
                is_moment=False,
                bid_weight=0.0,
                age_hours=0.1,
                metadata_json={},
                updated_at=datetime.now(UTC),
            )
        )
        session.add(
            OrchestratorConfigRecord(
                config_key=GLOBAL_CONFIG_KEY,
                payload_json={"expand_threshold": 0.8},
            )
        )
        session.commit()

    read_factory = _FailingReadSessionFactory()
    feed_store = PersistentPersonalizedFeedStore(
        session_factory=session_factory,
        read_session_factory=read_factory,
    )
    global_store = PersistentGlobalFeedStateStore(
        session_factory=session_factory,
        read_session_factory=read_factory,
        cache_store=None,
    )

    entries = feed_store.top("viewer-chaos", 5)
    clip_state = global_store.load_clip("clip-chaos")
    config = global_store.load_config()

    return {
        "feed_fallback_clip_ids": [entry.clip_id for entry in entries],
        "global_state_clip_id": clip_state.clip_id if clip_state is not None else None,
        "config_expand_threshold": config.expand_threshold,
        "passed": [entry.clip_id for entry in entries] == ["clip-chaos"] and clip_state is not None,
    }


def run_redis_fallback_probe() -> dict[str, Any]:
    service = DistributedLockService(redis_url="redis://127.0.0.1:1/0")
    results: dict[str, bool] = {}

    with service.tournament_join_lock("chaos", wait_timeout_seconds=0.1) as first:
        results["first_acquired"] = bool(first)

        def attempt_second() -> bool:
            with service.tournament_join_lock("chaos", wait_timeout_seconds=0.05) as second:
                return bool(second)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(attempt_second)
            sleep(0.1)
            results["second_acquired_while_held"] = bool(future.result())

    with service.tournament_join_lock("chaos", wait_timeout_seconds=0.1) as third:
        results["third_acquired_after_release"] = bool(third)

    return {
        "redis_client_available": service._client is not None,  # noqa: SLF001
        **results,
        "passed": results["first_acquired"] and not results["second_acquired_while_held"] and results["third_acquired_after_release"],
    }


def run_outbox_dlq_probe() -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[EventOutbox.__table__, EventDeadLetter.__table__],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    event_id = str(uuid4())
    with session_factory() as session:
        session.add(
            build_outbox_event(
                domain_event=DomainEvent(
                    name="feed.cache.refresh.requested",
                    event_id=event_id,
                    payload={"user_id": "chaos-user"},
                    aggregate_id="chaos-user",
                    aggregate_type="personalized_feed",
                    partition_key="chaos-user",
                )
            )
        )
        session.commit()

    flush_to_broker(
        session_factory=session_factory,
        publisher=_FailingPublisher(),
        batch_size=10,
        max_attempts=1,
    )

    with session_factory() as session:
        row = session.scalar(select(EventOutbox).where(EventOutbox.event_id == event_id))
        dead_letter = session.scalar(
            select(EventDeadLetter).where(
                EventDeadLetter.consumer_name == "outbox-relay",
                EventDeadLetter.event_id == event_id,
            )
        )

    return {
        "outbox_status": row.status if row is not None else None,
        "dead_lettered": dead_letter is not None,
        "attempts": dead_letter.attempts if dead_letter is not None else 0,
        "passed": row is not None and row.status == "dead_letter" and dead_letter is not None,
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


if __name__ == "__main__":
    main()
