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

from backend.app.core.config import load_settings
from backend.app.core.database import create_database_engine, create_session_factory, load_model_modules
from backend.app.ingestion.real_player_footballsquads_canonical_backfill import (
    FootballsquadsCanonicalBackfillService,
)


def _render_counts(values: dict[str, int]) -> str:
    if not values:
        return "(none)"
    return ", ".join(
        f"{key}={count}"
        for key, count in sorted(values.items())
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill the curated footballsquads canonical club and competition mappings.",
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
                "DATABASE_URL": args.database_url,
                "GTE_DATABASE_URL": args.database_url,
            }
        )
        with session_factory() as session:
            report = FootballsquadsCanonicalBackfillService(settings=settings).run(session)
            session.commit()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(f"resolved_count={report.resolved_count}")
            print(f"resolved_by_entity_type={_render_counts(report.resolved_counts_by_entity_type)}")
            print(f"remaining_unresolved_count={report.remaining_unresolved_count}")
            print(
                "remaining_unresolved_by_entity_type="
                f"{_render_counts(report.remaining_unresolved_counts_by_entity_type)}"
            )
            print(
                "remaining_unresolved_categories="
                f"{_render_counts(report.remaining_unresolved_categories)}"
            )
            print(f"resolved_competitions={', '.join(item.label for item in report.resolved_competitions) or '(none)'}")
            print(f"resolved_clubs={', '.join(item.label for item in report.resolved_clubs) or '(none)'}")
            print(
                "remaining_unresolved="
                f"{', '.join(item.label for item in report.remaining_unresolved_items) or '(none)'}"
            )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
