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
    parser = argparse.ArgumentParser(description="Import staged real players from a bulk file.")
    parser.add_argument("--file", required=True, help="Path to the bulk JSON or JSONL file.")
    parser.add_argument("--provider", required=True, help="Provider label stored against the staged rows.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Commit staging rows in batches.")
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
        result = service.import_file(
            file_path=args.file,
            provider_name=args.provider,
            batch_size=args.batch_size,
        )
        print_result(result.model_dump(mode="json"))
        return 0 if result.run is not None and result.run.status not in {"partial", "failed", "cancelled"} else 2
    except RealPlayerBulkImportOpsError as exc:
        print_result(error_payload(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
