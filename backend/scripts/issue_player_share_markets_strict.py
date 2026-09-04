from __future__ import annotations

"""Strict bulk player-share issuer.

This command deliberately uses PlayerTokenMarketService.issue_market(), the
explicit issuance API. It never calls ensure_market(), which is reserved for
legacy compatibility/read-model synchronization and must never be the source
of bulk issuance provenance.

Dry-run remains the default. Activation requires an explicit admin actor id so
issuance is attributable in the domain event/audit trail.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "issue_player_share_markets.py"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_spec = importlib.util.spec_from_file_location("player_share_issuance_plan", SCRIPT_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load issuance planner: {SCRIPT_PATH}")
_planner = importlib.util.module_from_spec(_spec)
# Dataclasses resolve KW_ONLY / forward references via sys.modules.get(cls.__module__),
# so a dynamically loaded module must be registered before exec_module runs -- Python
# 3.14 raises AttributeError: 'NoneType' object has no attribute '__dict__' on the very
# first frozen/slots dataclass in the module (IssuancePlan) otherwise.
sys.modules[_spec.name] = _planner
_spec.loader.exec_module(_planner)

from app.core.database import create_database_engine, create_session_factory
from app.models.user import User
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService

DEFAULT_POLICY_PATH = _planner.DEFAULT_POLICY_PATH
_base_query = _planner._base_query
_build_plan = _planner._build_plan
_eligibility_block_reason = _planner._eligibility_block_reason
_load_policy = _planner._load_policy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explicit, auditable bulk issuance of GTEX player-share markets.")
    parser.add_argument(
        "--cohort-type",
        default="all",
        choices=["all", "import_batch", "league", "country", "supply_tier", "liquidity_band"],
    )
    parser.add_argument("--cohort-value")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--actor-user-id")
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--database-url")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.activate and not args.actor_user_id:
        raise SystemExit("--actor-user-id is required with --activate")
    if args.limit < 1 or args.limit > 5000:
        raise SystemExit("--limit must be between 1 and 5000")

    policy = _load_policy(Path(args.policy_path))
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    report = {
        "dry_run": not args.activate or args.dry_run,
        "activated": bool(args.activate and not args.dry_run),
        "cohort_type": args.cohort_type,
        "cohort_value": args.cohort_value,
        "limit": args.limit,
        "counts": {"created": 0, "skipped_existing": 0, "skipped_blocked": 0, "failed": 0},
        "created": [],
        "skipped_existing": [],
        "skipped_blocked": [],
        "failed": [],
    }

    with session_factory() as session:
        actor = None
        if args.activate:
            actor = session.scalar(select(User).where(User.id == args.actor_user_id))
            if actor is None:
                raise SystemExit(f"Admin actor {args.actor_user_id!r} was not found")

        players = list(session.scalars(_base_query(args, policy).limit(args.limit)).all())
        service = PlayerTokenMarketService(session)

        for player in players:
            block_reason = _eligibility_block_reason(player, policy)
            if block_reason is not None:
                report["counts"]["skipped_blocked"] += 1
                report["skipped_blocked"].append({"player_id": player.id, "reason": block_reason})
                continue

            plan = _build_plan(player, policy)
            market = player.share_market
            if market is not None:
                report["counts"]["skipped_existing"] += 1
                report["skipped_existing"].append(
                    {"player_id": player.id, "market_id": market.id, "status": market.status}
                )
                continue

            if not args.activate or args.dry_run:
                report["counts"]["created"] += 1
                report["created"].append(
                    {
                        "player_id": player.id,
                        "tier": plan.tier,
                        "status": plan.status,
                        "total_shares": plan.total_shares,
                        "share_price_coin": str(plan.share_price_coin),
                        "liquidity_coin": str(plan.liquidity_coin),
                        "mode": "dry_run",
                    }
                )
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
                    "bulk_issuance_policy": Path(args.policy_path).name,
                    "issuance_runner": Path(__file__).name,
                }
                report["counts"]["created"] += 1
                report["created"].append({"player_id": player.id, "market_id": market.id, "tier": plan.tier})
            except PlayerTokenMarketError as exc:
                report["counts"]["failed"] += 1
                report["failed"].append({"player_id": player.id, "reason": exc.reason, "detail": exc.detail})

        if args.activate and not args.dry_run:
            session.commit()
        else:
            session.rollback()

    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
