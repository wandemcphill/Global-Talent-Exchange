from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import resolve_database_url
from app.core.database import create_database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description="GTEX deployment preflight checks.")
    parser.add_argument("--database-url", default=None, help="Database URL override.")
    args = parser.parse_args()

    database_url = args.database_url or resolve_database_url(os.environ)
    engine = create_database_engine(database_url)
    redacted_url = make_url(str(engine.url)).render_as_string(hide_password=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "check": "database_credentials",
                    "database_url": redacted_url,
                    "detail": str(exc.orig if getattr(exc, "orig", None) is not None else exc),
                    "hint": "Verify Render DATABASE_URL/GTE_DATABASE_URL username, password, host, and attached database before running migration checks.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "check": "database_credentials",
                "database_url": redacted_url,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
