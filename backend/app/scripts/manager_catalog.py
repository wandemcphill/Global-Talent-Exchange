from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

MODULE_PATH = Path((__file__ or sys.argv[0])).resolve()
ROOT_DIR = MODULE_PATH.parents[3]
BACKEND_DIR = ROOT_DIR / "backend"
for path in (ROOT_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.manager_market.service import ManagerMarketService
from app.wallets.service import WalletService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed or verify the GTEX bootstrap manager catalog.")
    parser.add_argument("--database-url", default=os.getenv("GTE_DATABASE_URL") or os.getenv("DATABASE_URL"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Persist the bootstrap manager catalog idempotently.")
    subparsers.add_parser("verify", help="Print manager catalog counts.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.database_url:
        raise SystemExit("A database URL is required via --database-url, GTE_DATABASE_URL, or DATABASE_URL.")

    settings = load_settings(environ={**os.environ, "GTE_DATABASE_URL": args.database_url})
    engine = create_database_engine(settings.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    service = ManagerMarketService(wallet_service=WalletService())

    with session_factory() as session:
        if args.command == "seed":
            seeded = service.seed_catalog_entries(session)
            session.commit()
            payload = {
                "attempted_count": seeded.attempted_count,
                "inserted_count": seeded.inserted_count,
                "total_count": seeded.total_count,
                "legendary_count": seeded.legendary_count,
                "non_legendary_count": seeded.non_legendary_count,
            }
        else:
            counts = service.catalog_counts(session)
            payload = {
                "total_count": counts.total_count,
                "legendary_count": counts.legendary_count,
                "non_legendary_count": counts.non_legendary_count,
            }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
