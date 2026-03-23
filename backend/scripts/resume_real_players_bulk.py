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
    parser = argparse.ArgumentParser(description="Resume a partial staged real-player bulk import run.")
    parser.add_argument("--run-id", required=True, help="Tracked bulk import run id.")
    parser.add_argument("--batch-size", type=int, default=None, help="Optional batch-size override for the resumed run.")
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
        result = service.resume_import(
            run_id=args.run_id,
            batch_size=args.batch_size,
        )
        print_result(result.model_dump(mode="json"))
        return 0 if result.run is not None and result.run.status not in {"partial", "failed", "cancelled"} else 2
    except RealPlayerBulkImportOpsError as exc:
        print_result(error_payload(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
