from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from decimal import Decimal
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from uuid import uuid4
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_session_factory, ensure_database_schema_current
from app.core.event_backbone import build_outbox_event
from app.core.events import DomainEvent
from app.models.creator_attention_earnings import ClipEarningsLog, CreatorWallet
from app.models.user import User, UserRole
from app.services.creator_attention_earnings_service import CreatorAttentionEarningsService
from app.viral.ingestion_schemas import ClipEvent, ClipEventMetadata, ClipEventType
from app.viral.personalized_feed_service import (
    InMemoryPersonalizedFeedStore,
    PersonalizedFeedRankingService,
)
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedResponse,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
)
from app.viral.session_tracker import ViralSessionTracker


class _MemoryPublisher:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def publish(self, row) -> None:
        self.messages.append(str(row.event_id))

    def close(self) -> None:
        return None


class _SyntheticFeedService:
    def build_feed(self, *, limit: int = 20, allocate_impressions: bool = False):  # noqa: ARG002
        clips = [
            _build_clip(
                clip_id="clip-global",
                creator_id="creator-global",
                viral_score=95,
                ranking_score=95.0,
                event_type="goal",
                format_key="instant_clip",
            ),
            _build_clip(
                clip_id="clip-session",
                creator_id="creator-session",
                viral_score=78,
                ranking_score=78.0,
                event_type="tactical_swing",
                format_key="breakdown",
            ),
            _build_clip(
                clip_id="clip-bench",
                creator_id="creator-bench",
                viral_score=65,
                ranking_score=65.0,
                event_type="analysis",
                format_key="analysis",
            ),
        ]
        return ViralFeedResponse(clips=clips[:limit], generated_at=datetime.now(UTC), personalization={})


class _StaticFeedbackEngine:
    def creator_recommendation_boost(self, _creator_id: str) -> float:
        return 0.0


class _StaticColdStartManager:
    def is_new_user(self, _user_id: str) -> bool:
        return False

    def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
        return 0.0

    def creator_boost(self, _creator_id: str) -> float:
        return 0.0


def main() -> None:
    logging.getLogger("alembic").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Run GTEX backend reliability load scenarios.")
    parser.add_argument(
        "--scenario",
        choices=(
            "tournament-join-spike",
            "tournament-burst",
            "feed-refresh-storm",
            "earnings-storm",
            "outbox-backlog",
            "all",
        ),
        required=True,
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--users", type=int, default=256)
    parser.add_argument("--tournaments", type=int, default=32)
    parser.add_argument("--events", type=int, default=5000)
    parser.add_argument("--concurrency", type=int, default=32)
    args = parser.parse_args()
    retired_scenarios = {"tournament-join-spike", "tournament-burst"}
    if args.scenario in retired_scenarios:
        parser.error(
            "The legacy /api/tournaments engine is retired. "
            "These paid-entry load scenarios are disabled; migrate the load test to the hosted-competition engine."
        )

    with _database_context(database_url=args.database_url) as context:
        scenarios = [args.scenario] if args.scenario != "all" else [
            "feed-refresh-storm",
            "earnings-storm",
            "outbox-backlog",
        ]
        summary: dict[str, Any] = {}
        for scenario in scenarios:
            if scenario == "feed-refresh-storm":
                summary[scenario] = run_feed_refresh_storm(
                    users=max(args.users, 1),
                    concurrency=max(args.concurrency, 1),
                )
            elif scenario == "earnings-storm":
                summary[scenario] = run_earnings_storm(
                    context.session_factory,
                    creators=max(args.users // 16, 4),
                    viewers=max(args.users, 1),
                    events=max(args.events, 1),
                    concurrency=max(args.concurrency, 1),
                )
            else:
                summary[scenario] = run_outbox_backlog(
                    context.session_factory,
                    events=max(args.events, 1),
                    batch_size=max(args.concurrency * 4, 10),
                )
        print(json.dumps(summary, indent=2, default=_json_default))


def run_feed_refresh_storm(*, users: int, concurrency: int) -> dict[str, Any]:
    tracker = ViralSessionTracker()
    service = PersonalizedFeedRankingService(
        session=_NoDbSession(),
        feed_store=InMemoryPersonalizedFeedStore(),
        settings=SimpleNamespace(redis_url=None),
        feed_service=_SyntheticFeedService(),
        feedback_engine=_StaticFeedbackEngine(),
        cold_start_manager=_StaticColdStartManager(),
        session_tracker=tracker,
    )
    user_ids = [f"feed-user-{index}" for index in range(users)]

    def refresh_user(user_id: str) -> dict[str, Any]:
        session_id = f"session-{user_id}"
        baseline = service.get_for_you(user_id=user_id, limit=3, refresh=True, session_id=session_id)
        tracker.observe_many(
            [
                _build_session_event(
                    event_id=f"{user_id}-complete",
                    clip_id="clip-session",
                    session_id=session_id,
                    event_type=ClipEventType.COMPLETE,
                    watch_time_ms=12_000,
                    video_length_ms=12_000,
                    content_type="tactical",
                    format_key="breakdown",
                    clip_event_type="tactical_swing",
                ),
                _build_session_event(
                    event_id=f"{user_id}-like",
                    clip_id="clip-session",
                    session_id=session_id,
                    event_type=ClipEventType.LIKE,
                    watch_time_ms=12_000,
                    video_length_ms=12_000,
                    content_type="tactical",
                    format_key="breakdown",
                    clip_event_type="tactical_swing",
                ),
            ]
        )
        refreshed = service.get_for_you(user_id=user_id, limit=3, refresh=True, session_id=session_id)
        return {
            "baseline_top": baseline.items[0].clip_id if baseline.items else None,
            "refreshed_top": refreshed.items[0].clip_id if refreshed.items else None,
            "duplicate_count": len(refreshed.items) - len({item.clip_id for item in refreshed.items}),
        }

    started_at = perf_counter()
    outcomes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(refresh_user, user_id) for user_id in user_ids]
        for future in as_completed(futures):
            outcomes.append(future.result())
    duration = perf_counter() - started_at

    reranked = sum(1 for item in outcomes if item["refreshed_top"] == "clip-session")
    duplicates = sum(item["duplicate_count"] for item in outcomes)
    return {
        "duration_seconds": round(duration, 4),
        "users": users,
        "reranked_sessions": reranked,
        "reranked_ratio": round(reranked / users, 4) if users else 0.0,
        "duplicate_items_detected": duplicates,
    }


def run_earnings_storm(
    session_factory: sessionmaker[Session],
    *,
    creators: int,
    viewers: int,
    events: int,
    concurrency: int,
) -> dict[str, Any]:
    creator_ids = _create_users(session_factory, count=creators, label="creator-storm")
    viewer_ids = _create_users(session_factory, count=viewers, label="viewer-storm")

    def record(index: int) -> None:
        creator_id = creator_ids[index % len(creator_ids)]
        viewer_id = viewer_ids[index % len(viewer_ids)]
        clip_id = f"clip-{index % max(creators * 2, 1)}"
        with session_factory() as session:
            service = CreatorAttentionEarningsService(session=session, cache=None)
            if index % 3 == 0:
                clip = type(
                    "ClipStub",
                    (),
                    {
                        "clip_id": clip_id,
                        "match_id": f"match-{clip_id}",
                        "metadata": {"creator_user_id": creator_id},
                    },
                )()
                service.track_impression(
                    clip=clip,
                    viewer_user_id=viewer_id,
                    feed_source="load_test",
                    reference_key=f"earnings:impression:{index}",
                )
            elif index % 3 == 1:
                service.track_engagement_event(
                    name="clip.like",
                    clip_id=clip_id,
                    viewer_user_id=viewer_id,
                    metadata={"creator_id": creator_id},
                    reference_key=f"earnings:like:{index}",
                )
            else:
                service.track_engagement_event(
                    name="clip.share",
                    clip_id=clip_id,
                    viewer_user_id=viewer_id,
                    metadata={"creator_id": creator_id},
                    reference_key=f"earnings:share:{index}",
                )
            session.commit()

    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(record, index) for index in range(events)]
        for future in as_completed(futures):
            future.result()
    duration = perf_counter() - started_at

    with session_factory() as session:
        wallets = list(session.scalars(select(CreatorWallet)).all())
        logs = list(session.scalars(select(ClipEarningsLog)).all())
    wallet_total = sum((wallet.available_balance_credit for wallet in wallets), Decimal("0.0000"))
    ledger_total = sum((log.earnings_delta_credit for log in logs), Decimal("0.0000"))
    return {
        "duration_seconds": round(duration, 4),
        "events_requested": events,
        "wallets": len(wallets),
        "logs": len(logs),
        "wallet_total_credit": wallet_total,
        "ledger_total_credit": ledger_total,
        "wallet_matches_ledger": wallet_total == ledger_total,
    }


def run_outbox_backlog(
    session_factory: sessionmaker[Session],
    *,
    events: int,
    batch_size: int,
) -> dict[str, Any]:
    from app.infrastructure.outbox import flush_to_broker
    from app.models.event_backbone import EventOutbox

    with session_factory() as session:
        for index in range(events):
            session.add(
                build_outbox_event(
                    domain_event=DomainEvent(
                        name="feed.cache.refresh.requested",
                        event_id=str(uuid4()),
                        payload={"user_id": f"user-{index}", "limit": 20},
                        aggregate_id=f"user-{index}",
                        aggregate_type="personalized_feed",
                        partition_key=f"user-{index}",
                    )
                )
            )
        session.commit()

    publisher = _MemoryPublisher()
    started_at = perf_counter()
    delivered = 0
    while True:
        batch = flush_to_broker(
            session_factory=session_factory,
            publisher=publisher,
            batch_size=batch_size,
        )
        if batch == 0:
            break
        delivered += batch
    duration = perf_counter() - started_at

    with session_factory() as session:
        processed = list(
            session.scalars(select(EventOutbox).where(EventOutbox.status == "processed")).all()
        )
    return {
        "duration_seconds": round(duration, 4),
        "events_requested": events,
        "events_delivered": delivered,
        "processed_rows": len(processed),
        "publisher_messages": len(publisher.messages),
        "batch_size": batch_size,
    }


def _create_users(session_factory: sessionmaker[Session], *, count: int, label: str) -> list[str]:
    user_ids: list[str] = []
    with session_factory() as session:
        for index in range(count):
            suffix = uuid4().hex[:10]
            user = User(
                email=f"{label}-{index}-{suffix}@load.test",
                username=f"{label}_{index}_{suffix}",
                display_name=f"{label}-{index}",
                password_hash="load-test-hash",
                role=UserRole.USER,
            )
            session.add(user)
            session.flush()
            user_ids.append(str(user.id))
        session.commit()
    return user_ids


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


if __name__ == "__main__":
    main()
