from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Sequence

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from sqlalchemy import func, select

from backend.app.core.config import load_settings
from backend.app.core.database import create_database_engine, create_session_factory, load_model_modules
from backend.app.ingestion.real_player_footballsquads_canonical_backfill import (
    FOOTBALLSQUADS_SOURCE_NAME,
    FootballsquadsCanonicalBackfillService,
)
from backend.app.models.real_player_reference_mapping import RealPlayerUnresolvedReference


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill the curated footballsquads canonical country mappings.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Render the report as JSON.",
    )
    return parser


def _snapshot_counts(session) -> dict[str, int]:
    filters = (
        RealPlayerUnresolvedReference.source_name == FOOTBALLSQUADS_SOURCE_NAME,
        RealPlayerUnresolvedReference.entity_type == "country",
    )
    resolved_filters = (*filters, RealPlayerUnresolvedReference.status == "resolved")
    unresolved_filters = (*filters, RealPlayerUnresolvedReference.status != "resolved")
    return {
        "resolved_reference_rows": int(
            session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference).where(*resolved_filters)) or 0
        ),
        "unresolved_reference_rows": int(
            session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference).where(*unresolved_filters)) or 0
        ),
        "resolved_occurrences": int(
            session.scalar(
                select(func.coalesce(func.sum(RealPlayerUnresolvedReference.occurrence_count), 0)).where(*resolved_filters)
            )
            or 0
        ),
        "unresolved_occurrences": int(
            session.scalar(
                select(func.coalesce(func.sum(RealPlayerUnresolvedReference.occurrence_count), 0)).where(*unresolved_filters)
            )
            or 0
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    try:
        session_factory = create_session_factory(engine)
        settings = load_settings(
            environ={
                **os.environ,
                "GTE_DATABASE_URL": args.database_url,
            }
        )
        with session_factory() as session:
            before = _snapshot_counts(session)
            report = FootballsquadsCanonicalBackfillService(
                settings=settings,
                entity_types=("country",),
            ).run(session)
            session.commit()
            after = _snapshot_counts(session)

        payload = {
            "resolved_countries": [item.label for item in report.resolved_countries],
            "remaining_unresolved_items": [item.to_dict() for item in report.remaining_unresolved_items],
            "resolved_reference_rows_this_run": after["resolved_reference_rows"] - before["resolved_reference_rows"],
            "remaining_unresolved_reference_rows": after["unresolved_reference_rows"],
            "before": before,
            "after": after,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"resolved_countries={', '.join(payload['resolved_countries']) or '(none)'}")
            print(f"resolved_reference_rows_this_run={payload['resolved_reference_rows_this_run']}")
            print(f"remaining_unresolved_reference_rows={payload['remaining_unresolved_reference_rows']}")
            print(
                "remaining_unresolved="
                f"{', '.join(item['raw_label'] or item['provider_reference_key'] for item in payload['remaining_unresolved_items']) or '(none)'}"
            )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
