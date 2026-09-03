"""Scheduled valuation rebuild: the production cadence for the value engine.

This is the cron entrypoint that makes the matchday economy live. Without it the
chain `match -> performance -> form -> valuation -> market -> ownership` is inert
between manual `POST /api/value/snapshots/rebuild` calls: performances are
recorded and form is derived, but nothing recomputes the published valuation, so
football never reaches a holder.

**This is deliberately not a second valuation pipeline.** It constructs the same
`IngestionValueEngineBridge` the API container builds, with the same
`PlayerSummaryProjector`, and calls the same `run()`. That method already wires
`MatchdayValuationSignalProvider` into `ValueSnapshotJob`, so the scheduled path
and the operator endpoint compute identical numbers by construction. The only
difference is `run_type` / `triggered_by`, which exist so the run record says who
asked.

Idempotent: snapshots are keyed on (player_id, as_of, snapshot_type) and upserted,
so re-running for the same instant rewrites rather than duplicates.

Usage:
    python scripts/rebuild_value_snapshots.py --database-url <url> [--lookback-days N]
                                              [--snapshot-type intraday] [--limit N]
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.players.service import PlayerSummaryProjector
from app.value_engine.service import IngestionValueEngineBridge


def build_bridge(session_factory: sessionmaker) -> IngestionValueEngineBridge:
    """Construct the bridge exactly as `ApplicationContext` does.

    Kept as a function so the scheduled-path test can assert that this entrypoint
    and the API build the same object, rather than trusting a comment.
    """
    return IngestionValueEngineBridge(
        session_factory=session_factory,
        summary_projector=PlayerSummaryProjector(),
    )


def run_scheduled_rebuild(
    session_factory: sessionmaker,
    *,
    as_of: datetime | None = None,
    lookback_days: int | None = None,
    snapshot_type: str = "intraday",
) -> list:
    """Run one scheduled valuation rebuild and return the snapshots produced."""
    bridge = build_bridge(session_factory)
    return bridge.run(
        as_of=as_of or datetime.now(timezone.utc),
        lookback_days=lookback_days,
        snapshot_type=snapshot_type,
        run_type="scheduled_rebuild",
        triggered_by="cron",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled value snapshot rebuild.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--snapshot-type", default="intraday")
    args = parser.parse_args()

    engine = create_engine(args.database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    started = datetime.now(timezone.utc)
    snapshots = run_scheduled_rebuild(
        session_factory,
        as_of=started,
        lookback_days=args.lookback_days,
        snapshot_type=args.snapshot_type,
    )

    moved_by_form = [
        snapshot
        for snapshot in snapshots
        if (snapshot.matchday_signal_audit or {}).get("applied") is True
        and (snapshot.matchday_signal_audit or {}).get("adjustment_pct")
    ]
    print(
        f"value snapshot rebuild: {len(snapshots)} snapshots, "
        f"{len(moved_by_form)} moved by matchday form, "
        f"elapsed {(datetime.now(timezone.utc) - started).total_seconds():.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
