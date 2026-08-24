from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(BACKEND_ROOT))

from scripts.audit_player_share_lifecycle import audit_lifecycle
from scripts.audit_player_share_trade_boundary import audit as audit_trade_boundary


def certify(*, database_url: str | None, batch_size: int) -> dict[str, Any]:
    lifecycle = audit_lifecycle(database_url=database_url, batch_size=batch_size)
    trade_boundary = audit_trade_boundary()
    gates = {
        "trade_boundary": bool(trade_boundary["pass"]),
        **{f"lifecycle_{name}": bool(value) for name, value in lifecycle["gates"].items()},
    }
    return {
        "certification": "player-share-economic-foundation",
        "read_only": True,
        "lifecycle": lifecycle,
        "trade_boundary": trade_boundary,
        "gates": gates,
        "pass": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only player-share economic certification gate.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    report = certify(database_url=args.database_url, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
