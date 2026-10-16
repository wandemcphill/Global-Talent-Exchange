from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.app.cache.redis_helpers import build_cache_backend
from backend.app.ingestion.constants import DEFAULT_DATABASE_URL, ENV_DATABASE_URL
from backend.app.ingestion.service import IngestionService
import backend.app.ingestion.models  # noqa: F401
import backend.app.models  # noqa: F401
from backend.app.models.base import Base


def main() -> None:
    database_url = os.getenv(ENV_DATABASE_URL, DEFAULT_DATABASE_URL)
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    cache_backend = build_cache_backend()

    with SessionLocal() as session:
        service = IngestionService(session, cache_backend=cache_backend)
        summaries = [
            service.bootstrap_sync(provider_name="mock"),
            service.sync_matches(provider_name="mock"),
            service.sync_standings(provider_name="mock"),
            service.sync_player_stats(provider_name="mock"),
        ]
        session.commit()

    print(json.dumps([summary.model_dump() for summary in summaries], indent=2, default=str))


if __name__ == "__main__":
    main()
