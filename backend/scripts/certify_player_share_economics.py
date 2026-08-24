from __future__ import annotations

"""Read-only release certification for the player-share economic surface.

This command deliberately performs no repairs. It composes the two player-share
integrity audits so production certification cannot accidentally become a
mutation path.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from audit_player_share_integrity import audit as audit_integrity
from audit_player_share_lifecycle import audit as audit_lifecycle
from audit_player_share_trade_boundary import audit as audit_trade_boundary


ROOT = Path(__file__).resolve().parents[2]


def certify(*, strict: bool = False) -> dict[str, Any]:
    integrity = audit_integrity()
    lifecycle = audit_lifecycle()
    trade_boundary = audit_trade_boundary()

    checks = {
        "integrity": integrity,
        "lifecycle": lifecycle,
        "trade_boundary": trade_boundary,
    }

    failed: list[str] = []
    if not integrity.get("pass", False):
        failed.append("integrity")
    if not lifecycle.get("pass", False):
        failed.append("lifecycle")
    if not trade_boundary.get("pass", False):
        failed.append("trade_boundary")

    return {
        "certification": "FAIL" if failed else "PASS",
        "strict": strict,
        "read_only": True,
        "checks": checks,
        "failed_checks": failed,
        "repository_root": str(ROOT),
        "notes": [
            "This certification does not create, issue, synchronize, settle, or repair markets.",
            "A PASS certifies only the checks represented by these audits; it is not a substitute for live database-backed trade tests.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify player-share economic integrity without mutating production data.")
    parser.add_argument("--strict", action="store_true", help="return non-zero when any certification check fails")
    args = parser.parse_args()
    report = certify(strict=args.strict)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 1 if args.strict and report["certification"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
