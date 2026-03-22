from __future__ import annotations

import argparse
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

from backend.app.core.database import create_database_engine, create_session_factory, load_model_modules
from backend.app.ingestion.real_player_batch_audit import FAIL_VERDICT, RealPlayerBatchAuditReport, RealPlayerBatchAuditService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit the first real-player batch against the authoritative GTEX pricing engine.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--first-batch", action="store_true", help="Audit the earliest persisted real-player ingestion batch.")
    selection.add_argument("--ingestion-batch-id", help="Audit an explicit real-player ingestion batch id.")
    return parser


def render_report(report: RealPlayerBatchAuditReport) -> str:
    return report.render_text()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    report = RealPlayerBatchAuditService(session_factory=session_factory).run(
        ingestion_batch_id=args.ingestion_batch_id,
        first_batch=bool(args.first_batch),
    )
    print(render_report(report))
    return 0 if report.verdict != FAIL_VERDICT else 2


if __name__ == "__main__":
    raise SystemExit(main())
