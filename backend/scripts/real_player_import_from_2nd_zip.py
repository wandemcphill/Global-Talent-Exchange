from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Sequence

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.config import Settings, load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.second_zip_real_player_ops_service import (
    SecondZipRealPlayerOpsError,
    SecondZipRealPlayerOpsService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the GTEX 2nd.zip real-player import path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preload_parser = subparsers.add_parser("preload", help="Preload 2nd.zip countries, competitions, and clubs.")
    preload_parser.add_argument("--file", required=True)

    import_parser = subparsers.add_parser("import", help="Read 2nd.zip and stage a dry run.")
    import_parser.add_argument("--file", required=True)
    import_parser.add_argument("--batch-size", type=int, default=1000)
    import_parser.add_argument("--limit", type=int, default=None)

    resume_parser = subparsers.add_parser("resume", help="Resume an interrupted 2nd.zip run.")
    resume_parser.add_argument("--run-id", required=True)

    repair_parser = subparsers.add_parser("repair", help="Re-evaluate unresolved or partial 2nd.zip rows.")
    repair_group = repair_parser.add_mutually_exclusive_group(required=True)
    repair_group.add_argument("--run-id")
    repair_group.add_argument("--state")

    publish_parser = subparsers.add_parser("publish", help="Publish verified 2nd.zip rows through the existing write path.")
    publish_parser.add_argument("--run-id", required=True)
    publish_parser.add_argument("--limit", type=int, default=None)
    publish_parser.add_argument("--tier", default=None)

    report_parser = subparsers.add_parser("report", help="Report current 2nd.zip run counts.")
    report_parser.add_argument("--run-id", required=True)

    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    return parser


def build_service(*, database_url: str) -> SecondZipRealPlayerOpsService:
    settings = _settings_with_database_url(database_url=database_url)
    engine = create_database_engine(database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    return SecondZipRealPlayerOpsService(
        session_factory=session_factory,
        settings=settings,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(_normalize_global_args(argv))
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    service = build_service(database_url=args.database_url)
    try:
        if args.command == "preload":
            result = service.preload_references(archive_path=args.file)
            _print_json(result.to_dict())
            return 0

        if args.command == "import":
            result = service.import_archive(
                archive_path=args.file,
                batch_size=args.batch_size,
                limit=args.limit,
            )
            _print_json(result.to_dict())
            return 0

        if args.command == "resume":
            result = service.resume_run(run_id=args.run_id)
            _print_json(result.to_dict())
            return 0

        if args.command == "repair":
            results = service.repair_run(run_id=args.run_id, state=args.state)
            payload: object = results[0].to_dict() if len(results) == 1 else [item.to_dict() for item in results]
            _print_json(payload)
            return 0

        if args.command == "publish":
            result = service.publish_run(
                run_id=args.run_id,
                limit=args.limit,
                tier=args.tier,
            )
            _print_json(result.to_dict())
            return 0

        result = service.report_run(run_id=args.run_id)
        _print_json(result.to_dict())
        return 0
    except SecondZipRealPlayerOpsError as exc:
        _print_json({"error": str(exc), "status_code": exc.status_code})
        return 2


def _settings_with_database_url(*, database_url: str) -> Settings:
    return load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": database_url,
            "GTE_DATABASE_URL": database_url,
        }
    )


def _normalize_global_args(argv: Sequence[str] | None) -> Sequence[str] | None:
    if argv is None:
        return None

    args = list(argv)
    try:
        index = args.index("--database-url")
    except ValueError:
        return args

    if index + 1 >= len(args):
        return args

    return [
        "--database-url",
        args[index + 1],
        *args[:index],
        *args[index + 2 :],
    ]


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
