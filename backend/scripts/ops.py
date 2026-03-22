from __future__ import annotations

import argparse
import json

from backend.app.core.config import get_settings
from backend.app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from backend.app.jobs.ops_jobs import OpsJobRunner


def build_runner() -> OpsJobRunner:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    return OpsJobRunner(session_factory=session_factory, settings=settings)


def main() -> int:
    parser = argparse.ArgumentParser(description="GTEX ops runners")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("media-retention", help="Archive expired highlights and purge old archives.")
    subparsers.add_parser("integrity-scan", help="Run integrity scan and suspicious cluster scan.")
    subparsers.add_parser("config-snapshot", help="Print config snapshot for media/sponsorship/payments.")

    args = parser.parse_args()
    runner = build_runner()

    if args.command == "media-retention":
        result = runner.run_media_retention()
    elif args.command == "integrity-scan":
        result = runner.run_integrity_scan()
    else:
        settings = get_settings()
        result = {
            "media_storage": {
                "storage_root": str(settings.media_storage.storage_root),
                "highlight_temp_prefix": settings.media_storage.highlight_temp_prefix,
                "highlight_archive_prefix": settings.media_storage.highlight_archive_prefix,
                "highlight_export_prefix": settings.media_storage.highlight_export_prefix,
                "download_expiry_minutes": settings.media_storage.download_expiry_minutes,
            },
            "sponsorship": {
                "default_campaign": settings.sponsorship_inventory.default_campaign,
                "surfaces": list(settings.sponsorship_inventory.surfaces),
                "campaign_codes": [c.code for c in settings.sponsorship_inventory.campaigns],
            },
            "payments": {
                "crypto_enabled": settings.crypto_deposit_enabled,
                "crypto_provider_key": settings.crypto_provider_key,
            },
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
