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

from backend.app.core.database import create_database_engine, create_session_factory, load_model_modules
from backend.app.ingestion.real_player_import_validation import RealPlayerImportValidationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize post-import real-player data quality and valuation coverage.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--batch-key",
        default=None,
        help="Explicit real-player import batch key. Defaults to the latest batch.",
    )
    parser.add_argument(
        "--provider-name",
        default=None,
        help="Optional provider filter when selecting the latest batch.",
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
        report = RealPlayerImportValidationService(session_factory=session_factory).run(
            batch_key=args.batch_key,
            provider_name=args.provider_name,
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(report.render_text())
        return 0 if report.verdict == "pass" else 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
