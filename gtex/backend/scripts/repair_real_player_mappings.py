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
    parser = argparse.ArgumentParser(description="Repair staged real-player mappings for a run or unresolved rows.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id", help="Tracked bulk import run id.")
    target.add_argument("--state", choices=["unresolved"], help="Repair every staged row in the unresolved state set.")
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
        result = service.repair_mappings(
            run_id=args.run_id,
            state=args.state,
        )
        print_result(result.model_dump(mode="json"))
        return 0
    except RealPlayerBulkImportOpsError as exc:
        print_result(error_payload(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
