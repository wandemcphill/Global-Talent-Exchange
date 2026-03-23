from __future__ import annotations

import argparse
import os
from typing import Sequence

try:
    from real_player_bulk_ops_common import (
        RealPlayerBulkImportOpsError,
        build_service,
        error_payload,
        print_result,
    )
except ModuleNotFoundError:
    from backend.scripts.real_player_bulk_ops_common import (
        RealPlayerBulkImportOpsError,
        build_service,
        error_payload,
        print_result,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish publish-ready staged real players into GTEX.")
    parser.add_argument("--run-id", required=True, help="Tracked bulk import run id.")
    parser.add_argument("--limit", required=True, type=int, help="Maximum publish-ready rows to process.")
    parser.add_argument("--priority", required=True, help="Priority bucket to publish.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the selected rows without writing players.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    service = build_service(database_url=args.database_url)
    try:
        result = service.publish_ready_players(
            run_id=args.run_id,
            limit=args.limit,
            priority_bucket=args.priority,
            dry_run=bool(args.dry_run),
        )
        print_result(result.model_dump(mode="json"))
        if args.dry_run:
            return 0
        return 0 if int(result.details_json.get("published_now") or 0) > 0 else 2
    except RealPlayerBulkImportOpsError as exc:
        print_result(error_payload(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
