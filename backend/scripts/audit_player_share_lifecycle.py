from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_share_market_eligible
from app.models.player_token_market import PlayerShareMarket
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerUnit

DEFAULT_BATCH_SIZE = 1000
LIQUIDITY_QUANTUM = Decimal("0.0001")


def classify_market(*, status: str | None, eligible: bool, metadata: dict[str, Any] | None) -> dict[str, bool]:
    payload = metadata or {}
    auto_initialized = bool(payload.get("auto_initialized", False))
    issued_by_user_id = bool(str(payload.get("issued_by_user_id") or "").strip())
    market_issued = bool(payload.get("market_issued", False))
    active = status == "active"
    return {
        "active": active,
        "eligible": eligible,
        "auto_initialized": auto_initialized,
        "explicitly_issued": market_issued and issued_by_user_id and not auto_initialized,
        "blocked_active": active and not eligible,
        "legacy_active": active and eligible and not (market_issued and issued_by_user_id),
    }


def _amount(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or "0.0000")).quantize(LIQUIDITY_QUANTUM)


def _expected_liquidity_code(player_id: str) -> str:
    return f"platform:player_share:{player_id}:liquidity"


def audit_lifecycle(*, database_url: str | None, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            total = int(session.scalar(select(func.count(PlayerShareMarket.id))) or 0)
            active = 0
            explicit = 0
            auto_initialized = 0
            blocked_active = 0
            legacy_active = 0
            missing_liquidity_account = 0
            mismatched_liquidity_balance = 0
            negative_liquidity_balance = 0
            invalid_liquidity_unit = 0
            checked = 0
            last_player_id: str | None = None

            while True:
                statement = (
                    select(PlayerShareMarket)
                    .join(Player, Player.id == PlayerShareMarket.player_id)
                    .order_by(PlayerShareMarket.player_id.asc())
                    .limit(batch_size)
                )
                if last_player_id is not None:
                    statement = statement.where(PlayerShareMarket.player_id > last_player_id)
                markets = list(session.scalars(statement).all())
                if not markets:
                    break

                for market in markets:
                    checked += 1
                    metadata = dict(market.metadata_json or {})
                    state = classify_market(
                        status=market.status,
                        eligible=is_share_market_eligible(market.player),
                        metadata=metadata,
                    )
                    active += int(state["active"])
                    explicit += int(state["explicitly_issued"])
                    auto_initialized += int(state["auto_initialized"])
                    blocked_active += int(state["blocked_active"])
                    legacy_active += int(state["legacy_active"])

                    if not state["active"]:
                        continue

                    expected_code = _expected_liquidity_code(market.player_id)
                    account_code = str(metadata.get("liquidity_account_code") or "").strip()
                    account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == account_code)) if account_code else None
                    if account is None or account_code != expected_code:
                        missing_liquidity_account += 1
                        continue

                    if account.unit != LedgerUnit.COIN:
                        invalid_liquidity_unit += 1

                    projection = session.scalar(
                        select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id)
                    )
                    actual_balance = _amount(projection.balance if projection is not None else Decimal("0.0000"))
                    metadata_balance = _amount(metadata.get("liquidity_coin"))
                    if actual_balance < Decimal("0.0000"):
                        negative_liquidity_balance += 1
                    if actual_balance != metadata_balance:
                        mismatched_liquidity_balance += 1

                last_player_id = markets[-1].player_id

            return {
                "total_markets": total,
                "markets_checked": checked,
                "active_markets": active,
                "explicitly_issued_markets": explicit,
                "auto_initialized_markets": auto_initialized,
                "blocked_active_markets": blocked_active,
                "legacy_active_markets": legacy_active,
                "active_missing_liquidity_account": missing_liquidity_account,
                "active_liquidity_balance_mismatches": mismatched_liquidity_balance,
                "active_negative_liquidity_accounts": negative_liquidity_balance,
                "active_non_coin_liquidity_accounts": invalid_liquidity_unit,
                "read_only": True,
                "gates": {
                    "no_blocked_active_markets": blocked_active == 0,
                    "no_active_markets_missing_liquidity_account": missing_liquidity_account == 0,
                    "all_active_markets_explicitly_issued": legacy_active == 0,
                    "all_active_liquidity_balances_reconcile": mismatched_liquidity_balance == 0,
                    "no_negative_active_liquidity": negative_liquidity_balance == 0,
                    "all_active_liquidity_is_coin": invalid_liquidity_unit == 0,
                },
            }
    finally:
        engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only audit of player-share market lifecycle state.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    report = audit_lifecycle(database_url=args.database_url, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(report["gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
