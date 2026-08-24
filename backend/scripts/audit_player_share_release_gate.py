from __future__ import annotations

import argparse
import json
from typing import Any

from audit_player_share_lifecycle import audit as audit_lifecycle
from audit_player_share_trade_boundary import audit as audit_trade_boundary


def build_report() -> dict[str, Any]:
    lifecycle = audit_lifecycle()
    trade_boundary = audit_trade_boundary()
    checks = {
        "trade_boundary": bool(trade_boundary.get("pass")),
        "lifecycle": bool(lifecycle.get("pass")),
    }
    return {
        "name": "player_share_release_gate",
        "read_only": True,
        "checks": checks,
        "pass": all(checks.values()),
        "trade_boundary": trade_boundary,
        "lifecycle": lifecycle,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the read-only player-share economic release gate."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when any release-gate check fails",
    )
    args = parser.parse_args()
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
