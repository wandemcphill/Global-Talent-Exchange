from __future__ import annotations

import argparse
from datetime import datetime
import json
import os

from app.core.config import DEFAULT_DATABASE_URL, Settings, load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.schemas.player_seed import PlayerSeedMode, PlayerSeedRequest
from app.services.player_seed_service import PlayerSeedService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed GTEX players through the existing authoritative value engine.")
    parser.add_argument("--mode", choices=[mode.value for mode in PlayerSeedMode], default=PlayerSeedMode.FULL_SEED.value)
    parser.add_argument("--target-count", type=int, default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--seed", type=int, default=20260321)
    parser.add_argument("--batch-size", type=int, default=5_000)
    parser.add_argument("--free-agent-count", type=int, default=None)
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--as-of", default=None, help="ISO-8601 timestamp for the authoritative value snapshot run.")
    parser.add_argument("--checkpoint-path", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-provider-data", action="store_true")
    parser.add_argument("--database-url", default=os.getenv("GTE_DATABASE_URL", DEFAULT_DATABASE_URL))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    settings = load_settings(environ={**os.environ, "GTE_DATABASE_URL": args.database_url})
    request = PlayerSeedRequest.model_validate(
        {
            "mode": args.mode,
            "target_player_count": args.target_count,
            "provider_name": args.provider,
            "random_seed": args.seed,
            "batch_size": args.batch_size,
            "free_agent_count": args.free_agent_count,
            "replace_provider_data": not args.keep_provider_data,
            "resume_from_checkpoint": args.resume,
            "checkpoint_path": args.checkpoint_path,
            "lookback_days": args.lookback_days,
            "as_of": datetime.fromisoformat(args.as_of) if args.as_of else None,
        }
    )
    result = PlayerSeedService(
        session_factory=session_factory,
        settings=_settings_with_database_url(settings=settings, database_url=args.database_url),
    ).seed(request)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


def _settings_with_database_url(*, settings: Settings, database_url: str) -> Settings:
    if settings.database_url == database_url:
        return settings
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": database_url})


if __name__ == "__main__":
    main()
