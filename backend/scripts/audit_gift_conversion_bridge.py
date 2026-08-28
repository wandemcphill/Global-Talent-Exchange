"""Read-only reconciliation for the FanCoin -> GTEX Coin gift conversion bridge.

Every FanCoin gift converts non-withdrawable FanCoin into withdrawable GTEX
Coin. The ledger stays balanced per unit, but that balance alone says nothing
about whether the resulting Coin liability is backed:

    CREDIT  bridge  +net   (FanCoin consumed, non-withdrawable)
    COIN    bridge  -net   (Coin issued, withdrawable)

PHASE_A_CROSS_CURRENCY_CONVERSION defers that reconciliation to "a later
treasury phase" and nothing observed the bridge accounts at all. This audit
provides that surface: it reports FanCoin consumed vs Coin issued vs the two
bridge balances, and checks the invariants that must hold if the bridge is
being used only as intended.

Read-only. Never mutates.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory  # noqa: E402
from app.models.economic_conversion import (  # noqa: E402
    EconomicConversion,
    EconomicConversionStatus,
)
from app.models.wallet import LedgerAccount, LedgerEntry, LedgerUnit  # noqa: E402

QUANTUM = Decimal("0.0001")
CREDIT_BRIDGE_CODE = "platform:credit:gift_conversion_bridge"
COIN_BRIDGE_CODE = "platform:coin:gift_conversion_bridge"
FEE_REVENUE_CODE = "platform:credit:gift_conversion_fee_revenue"


def _amount(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(QUANTUM)


def _account_balance(session, code: str) -> Decimal | None:
    account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
    if account is None:
        return None
    total = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
    )
    return _amount(total)


def audit_bridge(*, database_url: str | None = None) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            settled = session.execute(
                select(
                    func.count(EconomicConversion.id),
                    func.coalesce(func.sum(EconomicConversion.source_amount), 0),
                    func.coalesce(func.sum(EconomicConversion.platform_fee_amount), 0),
                    func.coalesce(func.sum(EconomicConversion.destination_amount), 0),
                ).where(EconomicConversion.status == EconomicConversionStatus.SETTLED)
            ).first()
            reversed_row = session.execute(
                select(
                    func.count(EconomicConversion.id),
                    func.coalesce(func.sum(EconomicConversion.destination_amount), 0),
                ).where(EconomicConversion.status == EconomicConversionStatus.REVERSED)
            ).first()

            settled_count = int(settled[0] or 0)
            fancoin_consumed = _amount(settled[1])
            platform_fee = _amount(settled[2])
            coin_issued = _amount(settled[3])
            reversed_count = int(reversed_row[0] or 0)
            coin_reversed = _amount(reversed_row[1])

            credit_bridge = _account_balance(session, CREDIT_BRIDGE_CODE)
            coin_bridge = _account_balance(session, COIN_BRIDGE_CODE)
            fee_revenue = _account_balance(session, FEE_REVENUE_CODE)

            # Outstanding Coin liability created by conversion, i.e. Coin issued
            # and not since compensated by a reversal. A reversal moves the
            # conversion out of SETTLED, so it has already dropped out of
            # `coin_issued`; subtracting `coin_reversed` here as well would
            # double-count it and report a negative liability.
            outstanding_coin = coin_issued

            gates: dict[str, bool] = {}
            # The Coin bridge is the mirror of outstanding issued Coin, so it
            # should sit at exactly -outstanding.
            if coin_bridge is not None:
                gates["coin_bridge_mirrors_outstanding_liability"] = coin_bridge == -outstanding_coin
            # The FanCoin bridge holds the consumed FanCoin backing that Coin.
            if credit_bridge is not None:
                gates["credit_bridge_mirrors_outstanding_liability"] = credit_bridge == outstanding_coin
            # A positive Coin bridge would mean Coin was returned without a
            # corresponding issuance: never expected.
            if coin_bridge is not None:
                gates["coin_bridge_not_positive"] = coin_bridge <= Decimal("0.0000")
            # FanCoin backing must never be negative: that would mean Coin was
            # issued against FanCoin the platform never actually received.
            if credit_bridge is not None:
                gates["credit_bridge_not_negative"] = credit_bridge >= Decimal("0.0000")
            # Conservation: every settled conversion splits gross into fee, burn
            # and destination, so fee + destination can never exceed gross.
            gates["fee_and_destination_within_gross"] = (platform_fee + coin_issued) <= fancoin_consumed

            return {
                "name": "gift_conversion_bridge",
                "read_only": True,
                "settled_conversions": settled_count,
                "reversed_conversions": reversed_count,
                "fancoin_consumed": str(fancoin_consumed),
                "platform_fee_fancoin": str(platform_fee),
                "coin_issued": str(coin_issued),
                "coin_reversed": str(coin_reversed),
                "outstanding_coin_liability": str(outstanding_coin),
                "credit_bridge_balance": None if credit_bridge is None else str(credit_bridge),
                "coin_bridge_balance": None if coin_bridge is None else str(coin_bridge),
                "fee_revenue_balance": None if fee_revenue is None else str(fee_revenue),
                "bridge_accounts_exist": credit_bridge is not None and coin_bridge is not None,
                "gates": gates,
                "pass": all(gates.values()) if gates else True,
            }
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only reconciliation of the FanCoin->GTEX Coin gift conversion bridge."
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--strict", action="store_true", help="return non-zero when a gate fails")
    args = parser.parse_args()
    report = audit_bridge(database_url=args.database_url)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
