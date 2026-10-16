"""Backfill player-share markets for every real, league-assigned player that is missing one.

Context: the real-player ingestion pipeline writes profiles + pricing snapshots but never
issues share markets (issuance is a deliberate, admin-attributed step). After a large league
expansion this leaves thousands of real players priced-but-not-tradable. This script closes
that gap in one auditable pass.

It reuses the eligibility gate + issuance plan from ``issue_player_share_markets`` and the
strict ``PlayerTokenMarketService.issue_market`` path (admin-attributed, emits a
``player_share_events`` row per issuance). It is idempotent: players that already have a
market are skipped, so it can be re-run after an interruption.

Designed to run co-located with the database (e.g. a Render one-off job); per-issuance
latency over a remote pooler makes a laptop run impractical at this volume.

Usage:
    python backend/scripts/backfill_real_league_share_markets.py \
        --actor-user-id <admin-user-id> --activate
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(BACKEND_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

import issue_player_share_markets as planner  # noqa: E402
from app.core.database import create_database_engine  # noqa: E402
from app.ingestion.models import Player  # noqa: E402
from app.models.player_token_market import PlayerShareMarket  # noqa: E402
from app.models.user import User  # noqa: E402
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService  # noqa: E402

DEFAULT_POLICY_PATH = BACKEND_ROOT / "config" / "player_share_issuance.toml"

_LOAD_OPTS = (
    selectinload(Player.share_market),
    selectinload(Player.country),
    selectinload(Player.current_club),
    selectinload(Player.current_competition),
    selectinload(Player.internal_league),
    selectinload(Player.supply_tier),
    selectinload(Player.liquidity_band),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-user-id", required=True, help="Admin/super-admin user id to attribute issuance to.")
    parser.add_argument("--database-url", default=None, help="Overrides the configured database URL.")
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--limit", type=int, default=None, help="Cap on players to consider (for testing).")
    parser.add_argument("--max-retry", type=int, default=5)
    parser.add_argument("--activate", action="store_true", help="Persist issuance. Without it, this is a dry run.")
    return parser.parse_args()


def _candidate_ids(engine, limit: int | None) -> list[str]:
    stmt = (
        select(Player.id)
        .outerjoin(PlayerShareMarket, PlayerShareMarket.player_id == Player.id)
        .where(
            Player.is_real_player.is_(True),
            Player.is_tradable.is_(True),
            Player.real_world_league_name.isnot(None),
            PlayerShareMarket.id.is_(None),
        )
        .order_by(Player.real_world_league_name, Player.id)
    )
    if limit:
        stmt = stmt.limit(limit)
    with Session(engine) as session:
        return [row[0] for row in session.execute(stmt).all()]


def _run_batch(engine, policy, policy_name: str, actor_id: str, batch_ids: list[str], activate: bool) -> dict:
    local = {
        "created": 0,
        "skipped_existing": 0,
        "skipped_blocked": 0,
        "failed": 0,
        "blocked_reasons": {},
        "by_status": {},
        "by_tier": {},
        "failed_detail": [],
    }
    with Session(engine) as session:
        actor = session.scalar(select(User).where(User.id == actor_id))
        if actor is None:
            raise SystemExit(f"actor {actor_id!r} not found")
        players = list(session.scalars(select(Player).options(*_LOAD_OPTS).where(Player.id.in_(batch_ids))).all())
        service = PlayerTokenMarketService(session)
        for player in players:
            if player.share_market is not None:
                local["skipped_existing"] += 1
                continue
            block = planner._eligibility_block_reason(player, policy)
            if block is not None:
                local["skipped_blocked"] += 1
                local["blocked_reasons"][block] = local["blocked_reasons"].get(block, 0) + 1
                continue
            plan = planner._build_plan(player, policy)
            if not activate:
                local["created"] += 1
                local["by_status"][plan.status] = local["by_status"].get(plan.status, 0) + 1
                local["by_tier"][plan.tier] = local["by_tier"].get(plan.tier, 0) + 1
                continue
            try:
                market = service.issue_market(
                    actor=actor,
                    player_id=player.id,
                    total_shares=plan.total_shares,
                    share_price_coin=plan.share_price_coin,
                    liquidity_coin=plan.liquidity_coin,
                    status=plan.status,
                )
                market.metadata_json = {
                    **(market.metadata_json or {}),
                    "issuance_tier": plan.tier,
                    "initial_circulating_cap": plan.initial_circulating_cap,
                    "initial_mm_inventory_target": plan.initial_mm_inventory_target,
                    "bulk_issuance_policy": policy_name,
                    "issuance_runner": Path(__file__).name,
                }
                local["created"] += 1
                local["by_status"][plan.status] = local["by_status"].get(plan.status, 0) + 1
                local["by_tier"][plan.tier] = local["by_tier"].get(plan.tier, 0) + 1
            except PlayerTokenMarketError as exc:
                local["failed"] += 1
                local["failed_detail"].append(
                    {"player_id": player.id, "reason": getattr(exc, "reason", ""), "detail": str(exc)[:200]}
                )
        if activate:
            session.commit()
        else:
            session.rollback()
    return local


def main() -> int:
    args = parse_args()
    policy_name = Path(args.policy_path).name
    policy = planner._load_policy(Path(args.policy_path))
    engine = create_database_engine(args.database_url)

    ids = _candidate_ids(engine, args.limit)
    report = {
        "activate": bool(args.activate),
        "candidates": len(ids),
        "created": 0,
        "skipped_existing": 0,
        "skipped_blocked": 0,
        "failed": 0,
        "blocked_reasons": {},
        "by_status": {},
        "by_tier": {},
        "failed_detail": [],
    }
    print(f"[backfill] candidates missing a market: {len(ids)}  activate={args.activate}", flush=True)

    t0 = time.time()
    for start in range(0, len(ids), args.batch_size):
        batch_ids = ids[start : start + args.batch_size]
        for attempt in range(1, args.max_retry + 1):
            try:
                local = _run_batch(engine, policy, policy_name, args.actor_user_id, batch_ids, args.activate)
                for k in ("created", "skipped_existing", "skipped_blocked", "failed"):
                    report[k] += local[k]
                for k in ("blocked_reasons", "by_status", "by_tier"):
                    for kk, vv in local[k].items():
                        report[k][kk] = report[k].get(kk, 0) + vv
                report["failed_detail"].extend(local["failed_detail"])
                elapsed = time.time() - t0
                rate = report["created"] / max(elapsed, 1e-6)
                print(
                    f"[backfill] {start + len(batch_ids)}/{len(ids)}  "
                    f"created={report['created']} blocked={report['skipped_blocked']} "
                    f"failed={report['failed']}  {rate:.0f}/s",
                    flush=True,
                )
                break
            except Exception as exc:  # noqa: BLE001 - ops resilience
                print(
                    f"[backfill] batch @{start} attempt {attempt}/{args.max_retry}: "
                    f"{exc.__class__.__name__}: {str(exc)[:160]}",
                    flush=True,
                )
                if attempt == args.max_retry:
                    report["failed_detail"].append(
                        {"batch_start": start, "reason": "batch_gave_up", "detail": str(exc)[:200]}
                    )
                else:
                    time.sleep(min(3 * attempt, 20))

    print("\n[backfill] RESULT", flush=True)
    print(json.dumps(report, indent=2, default=str), flush=True)
    return 1 if report["failed"] or any(d.get("reason") == "batch_gave_up" for d in report["failed_detail"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
