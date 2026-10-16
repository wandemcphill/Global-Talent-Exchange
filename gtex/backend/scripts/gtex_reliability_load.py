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
from app.models.tournament import TournamentGameType, TournamentPlayer
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.services.creator_attention_earnings_service import CreatorAttentionEarningsService
from app.tournaments.schemas import TournamentCreateRequest
from app.tournaments.service import TournamentService, TournamentValidationError
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
from app.wallets.service import LedgerPosting, WalletService


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

    with _database_context(database_url=args.database_url) as context:
        scenarios = [args.scenario] if args.scenario != "all" else [
            "tournament-join-spike",
            "tournament-burst",
            "feed-refresh-storm",
            "earnings-storm",
            "outbox-backlog",
        ]
        summary: dict[str, Any] = {}
        for scenario in scenarios:
            if scenario == "tournament-join-spike":
                summary[scenario] = run_tournament_join_spike(
                    context.session_factory,
                    users=max(args.users, 2),
                    concurrency=max(args.concurrency, 1),
                )
            elif scenario == "tournament-burst":
                summary[scenario] = run_tournament_burst(
                    context.session_factory,
                    tournaments=max(args.tournaments, 1),
                    players_per_tournament=8,
                    concurrency=max(args.concurrency, 1),
                )
            elif scenario == "feed-refresh-storm":
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


def run_tournament_join_spike(
    session_factory: sessionmaker[Session],
    *,
    users: int,
    concurrency: int,
) -> dict[str, Any]:
    user_ids = _create_users(session_factory, count=users, label="tour-spike")
    _fund_users(session_factory, user_ids=user_ids, amount=Decimal("500.0000"))
    with session_factory() as session:
        tournament = TournamentService(session=session).create_tournament(
            TournamentCreateRequest(
                name="Reliability Join Spike",
                game_type=TournamentGameType.SIMULATION,
                entry_fee=50,
                max_players=64,
                round_timeout_minutes=5,
            )
        )
        session.commit()
    tournament_id = str(tournament["tournament_id"])

    started_at = perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_join_tournament_once, session_factory, tournament_id, user_id) for user_id in user_ids]
        for future in as_completed(futures):
            results.append(future.result())
    duration = perf_counter() - started_at

    with session_factory() as session:
        view = TournamentService(session=session).get_tournament(tournament_id)
        players = list(
            session.scalars(
                select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id)
            ).all()
        )

    successful = [item for item in results if item["ok"]]
    unique_players = {player.user_id for player in players}
    unique_slots = {player.bracket_slot for player in players}
    return {
        "duration_seconds": round(duration, 4),
        "requested_joins": len(user_ids),
        "successful_joins": len(successful),
        "player_count": len(players),
        "unique_player_count": len(unique_players),
        "unique_slot_count": len(unique_slots),
        "status": view["status"],
        "prize_pool": view["prize_pool"],
        "expected_prize_pool": len(players) * int(view["entry_fee"]),
        "overfill_detected": len(players) > int(view["max_players"]),
        "duplicate_join_detected": len(players) != len(unique_players),
        "duplicate_slot_detected": len(players) != len(unique_slots),
        "failure_reasons": _count_values(item["reason"] for item in results if not item["ok"]),
    }


def run_tournament_burst(
    session_factory: sessionmaker[Session],
    *,
    tournaments: int,
    players_per_tournament: int,
    concurrency: int,
) -> dict[str, Any]:
    total_users = tournaments * players_per_tournament
    user_ids = _create_users(session_factory, count=total_users, label="tour-burst")
    _fund_users(session_factory, user_ids=user_ids, amount=Decimal("300.0000"))

    tournament_ids: list[str] = []
    with session_factory() as session:
        service = TournamentService(session=session)
        for index in range(tournaments):
            view = service.create_tournament(
                TournamentCreateRequest(
                    name=f"Reliability Burst {index}",
                    game_type=TournamentGameType.SIMULATION,
                    entry_fee=25,
                    max_players=players_per_tournament,
                    round_timeout_minutes=5,
                )
            )
            tournament_ids.append(str(view["tournament_id"]))
        session.commit()

    assignments: list[tuple[str, str]] = []
    cursor = 0
    for tournament_id in tournament_ids:
        for _ in range(players_per_tournament):
            assignments.append((tournament_id, user_ids[cursor]))
            cursor += 1

    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_join_tournament_once, session_factory, tournament_id, user_id)
            for tournament_id, user_id in assignments
        ]
        outcomes = [future.result() for future in as_completed(futures)]
    duration = perf_counter() - started_at

    with session_factory() as session:
        players = list(session.scalars(select(TournamentPlayer)).all())

    return {
        "duration_seconds": round(duration, 4),
        "tournaments_created": tournaments,
        "requested_joins": len(assignments),
        "successful_joins": sum(1 for item in outcomes if item["ok"]),
        "persisted_players": len(players),
        "duplicate_entries_detected": len(players) != len({(player.tournament_id, player.user_id) for player in players}),
        "failure_reasons": _count_values(item["reason"] for item in outcomes if not item["ok"]),
    }


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


def _join_tournament_once(
    session_factory: sessionmaker[Session],
    tournament_id: str,
    user_id: str,
) -> dict[str, Any]:
    with session_factory() as session:
        service = TournamentService(session=session)
        try:
            service.join_tournament(tournament_id, user_id=user_id)
            session.commit()
            return {"ok": True, "reason": None}
        except TournamentValidationError as exc:
            session.rollback()
            return {"ok": False, "reason": exc.reason}


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


def _fund_users(
    session_factory: sessionmaker[Session],
    *,
    user_ids: list[str],
    amount: Decimal,
) -> None:
    wallet_service = WalletService()
    with session_factory() as session:
        treasury_account = wallet_service.ensure_operations_account(session, LedgerUnit.CREDIT)
        users = list(session.scalars(select(User).where(User.id.in_(user_ids))).all())
        for user in users:
            user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
            wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=user_account, amount=amount),
                    LedgerPosting(account=treasury_account, amount=-amount),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
                reference=f"load-fund:{user.id}",
                description="GTEX reliability load funding",
                idempotency_key=f"load-fund:{user.id}",
            )
        session.commit()


class _NoDbSession:
    def get_bind(self):
        return None


class _DatabaseContext:
    def __init__(self, engine: Engine, session_factory: sessionmaker[Session], tempdir: TemporaryDirectory[str] | None) -> None:
        self.engine = engine
        self.session_factory = session_factory
        self.tempdir = tempdir

    def close(self) -> None:
        self.engine.dispose()
        if self.tempdir is not None:
            self.tempdir.cleanup()


def _database_context(*, database_url: str | None):
    tempdir = None if database_url else TemporaryDirectory(prefix="gtex-reliability-load-")
    resolved_database_url = database_url or f"sqlite+pysqlite:///{Path(tempdir.name) / 'load.db'}"
    connect_args = {"check_same_thread": False} if resolved_database_url.startswith("sqlite") else {}
    engine = create_engine(resolved_database_url, connect_args=connect_args)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    context = _DatabaseContext(engine=engine, session_factory=session_factory, tempdir=tempdir)
    return _context_manager(context)


def _context_manager(context: _DatabaseContext):
    class _Manager:
        def __enter__(self) -> _DatabaseContext:
            return context

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb
            context.close()

    return _Manager()


def _build_clip(
    *,
    clip_id: str,
    creator_id: str,
    viral_score: int,
    ranking_score: float,
    event_type: str,
    format_key: str,
) -> ViralClipView:
    return ViralClipView(
        clip_id=clip_id,
        match_id=f"match-{clip_id}",
        highlight_id=f"highlight-{clip_id}",
        title=clip_id,
        event_type=event_type,
        minute=88,
        viral_score=viral_score,
        engagement=80.0,
        freshness=90.0,
        ranking_score=ranking_score,
        tags=[event_type],
        breakdown=ViralScoreBreakdownView(total=viral_score, base_event=50),
        caption=ViralCaptionView(hook=clip_id, caption=clip_id),
        distribution_accounts=[],
        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text=clip_id),
        formats=[],
        analytics=ViralClipAnalyticsView(
            clip_id=clip_id,
            view_count=1000,
            completions=800,
            watch_time=12.0,
            total_watch_time=12000.0,
            loops=220.0,
            loop_rate=0.22,
            shares=90,
            comments=24,
            skips=200,
            completion_rate=0.8,
            share_rate=0.09,
            comment_rate=0.024,
            views_last_10min=240,
            views_last_60min=640,
        ),
        feedback=ViralFeedbackLoopView(
            performance_tier="high_retention",
            recommendation="increase",
            increase_similar_clips=True,
            actions=["boost"],
            viral_analysis="strong retention",
        ),
        metadata={"creator_id": creator_id, "format_key": format_key},
    )


def _build_session_event(
    *,
    event_id: str,
    clip_id: str,
    session_id: str,
    event_type: ClipEventType,
    watch_time_ms: int,
    video_length_ms: int,
    content_type: str,
    format_key: str,
    clip_event_type: str,
) -> ClipEvent:
    return ClipEvent(
        event_id=event_id,
        clip_id=clip_id,
        user_id=None,
        session_id=session_id,
        timestamp=datetime.now(UTC),
        event_type=event_type,
        watch_time_ms=watch_time_ms,
        video_length_ms=video_length_ms,
        metadata=ClipEventMetadata(
            device="ios",
            country="NG",
            referrer="load-test",
            content_type=content_type,
            format_key=format_key,
            clip_event_type=clip_event_type,
            tags=[clip_event_type],
        ),
    )


def _count_values(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


if __name__ == "__main__":
    main()
