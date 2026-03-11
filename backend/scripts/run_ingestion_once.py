from __future__ import annotations

import argparse
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
from backend.app.ingestion.constants import DEFAULT_DATABASE_URL, DEFAULT_PROVIDER_NAME, ENV_DATABASE_URL
from backend.app.ingestion.service import IngestionService
import backend.app.ingestion.models  # noqa: F401
import backend.app.models  # noqa: F401
from backend.app.models.base import Base


def build_session_factory():
    database_url = os.getenv(ENV_DATABASE_URL, DEFAULT_DATABASE_URL)
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ingestion operation.")
    parser.add_argument("operation", choices=["bootstrap", "incremental", "matches", "standings", "stats", "competition", "club", "player"])
    parser.add_argument("--provider", default=os.getenv("GTE_INGESTION_PROVIDER", DEFAULT_PROVIDER_NAME))
    parser.add_argument("--competition-id")
    parser.add_argument("--club-id")
    parser.add_argument("--player-id")
    parser.add_argument("--season-id")
    parser.add_argument("--cursor-key", default="default")
    args = parser.parse_args()

    session_factory = build_session_factory()
    cache_backend = build_cache_backend()
    with session_factory() as session:
        service = IngestionService(session, cache_backend=cache_backend)
        if args.operation == "bootstrap":
            summary = service.bootstrap_sync(
                provider_name=args.provider,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        elif args.operation == "incremental":
            summary = service.sync_incremental(provider_name=args.provider, cursor_key=args.cursor_key)
        elif args.operation == "matches":
            summary = service.sync_matches(
                provider_name=args.provider,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        elif args.operation == "standings":
            summary = service.sync_standings(
                provider_name=args.provider,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        elif args.operation == "stats":
            summary = service.sync_player_stats(
                provider_name=args.provider,
                competition_external_id=args.competition_id,
                club_external_id=args.club_id,
                player_external_id=args.player_id,
                season_external_id=args.season_id,
            )
        elif args.operation == "competition":
            if not args.competition_id:
                raise SystemExit("--competition-id is required for competition refresh.")
            summary = service.refresh_competition(
                provider_name=args.provider,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        elif args.operation == "club":
            if not args.club_id:
                raise SystemExit("--club-id is required for club refresh.")
            summary = service.refresh_club(
                provider_name=args.provider,
                club_external_id=args.club_id,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        else:
            if not args.player_id:
                raise SystemExit("--player-id is required for player refresh.")
            summary = service.refresh_player(
                provider_name=args.provider,
                player_external_id=args.player_id,
                club_external_id=args.club_id,
                competition_external_id=args.competition_id,
                season_external_id=args.season_id,
            )
        session.commit()
        print(json.dumps(summary.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
