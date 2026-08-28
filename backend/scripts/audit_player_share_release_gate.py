from __future__ import annotations

import argparse
import json
from typing import Any

from audit_player_share_lifecycle import DEFAULT_BATCH_SIZE, audit_lifecycle
from audit_player_share_trade_boundary import audit as audit_trade_boundary


def build_report(*, database_url: str | None = None, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    # The trade-boundary check is a source audit and always runs. The lifecycle
    # check reconciles live market rows against ledger liquidity, so it needs a
    # database. When none is reachable the gate reports the check as not run and
    # does not pass: a release gate that silently skips a check is worse than one
    # that fails loudly.
    trade_boundary = audit_trade_boundary()
    lifecycle_ran = True
    try:
        lifecycle: dict[str, Any] = audit_lifecycle(database_url=database_url, batch_size=batch_size)
    except Exception as exc:  # noqa: BLE001 - surfaced in the report, never swallowed
        lifecycle_ran = False
        lifecycle = {"error": f"{type(exc).__name__}: {exc}", "gates": {}}

    lifecycle_gates = lifecycle.get("gates") or {}
    checks = {
        "trade_boundary": bool(trade_boundary.get("pass")),
        "lifecycle": bool(lifecycle_ran and lifecycle_gates and all(lifecycle_gates.values())),
    }
    return {
        "name": "player_share_release_gate",
        "read_only": True,
        "checks": checks,
        "lifecycle_ran": lifecycle_ran,
        "pass": all(checks.values()),
        "trade_boundary": trade_boundary,
        "lifecycle": lifecycle,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only player-share economic release gate.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when any release-gate check fails",
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    report = build_report(database_url=args.database_url, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
