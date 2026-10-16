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
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchResumeRequest,
    RealPlayerImportBatchRunRequest,
)
from app.ingestion.real_player_import_ops_service import RealPlayerImportOpsError, RealPlayerImportOpsService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate GTEX real-player batch imports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a real-player import manifest in dry-run or write mode.")
    run_parser.add_argument("--manifest-path", required=True)
    run_parser.add_argument("--mode", choices=["dry-run", "write"], default="dry-run")
    run_parser.add_argument("--provider-name", default=None)
    run_parser.add_argument("--provider-job-key", default=None)
    run_parser.add_argument("--source-type", default="json_manifest")
    run_parser.add_argument("--batch-key", default=None)
    run_parser.add_argument("--restart", action="store_true")

    resume_parser = subparsers.add_parser("resume", help="Resume a previously tracked real-player import batch.")
    resume_parser.add_argument("--batch-id", required=True)
    resume_parser.add_argument("--mode", choices=["dry-run", "write"], default=None)

    status_parser = subparsers.add_parser("status", help="Inspect tracked real-player import batches.")
    status_parser.add_argument("--batch-id", default=None)
    status_parser.add_argument("--batch-key", default=None)
    status_parser.add_argument("--include-rows", action="store_true")
    status_parser.add_argument("--limit", type=int, default=20)
    status_parser.add_argument("--batch-status", default=None)
    status_parser.add_argument("--provider-name", default=None)

    issues_parser = subparsers.add_parser("issues", help="Inspect unresolved row-level issues for a tracked batch.")
    issues_parser.add_argument("--batch-id", required=True)
    issues_parser.add_argument("--issue-type", default=None)
    issues_parser.add_argument("--all", action="store_true")

    valuation_parser = subparsers.add_parser("valuation-status", help="Inspect valuation generation status for a tracked batch.")
    valuation_parser.add_argument("--batch-id", required=True)

    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    return parser


def build_service(*, database_url: str) -> RealPlayerImportOpsService:
    settings = _settings_with_database_url(database_url=database_url)
    engine = create_database_engine(database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    return RealPlayerImportOpsService(
        session_factory=session_factory,
        database_url=database_url,
        settings=settings,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    service = build_service(database_url=args.database_url)
    try:
        if args.command == "run":
            result = service.run_batch(
                actor_user_id=None,
                payload=RealPlayerImportBatchRunRequest(
                    manifest_path=args.manifest_path,
                    mode=args.mode,
                    provider_name=args.provider_name,
                    provider_job_key=args.provider_job_key,
                    source_type=args.source_type,
                    batch_key=args.batch_key,
                    restart=bool(args.restart),
                ),
            )
            _print_json(result.model_dump(mode="json"))
            return 0

        if args.command == "resume":
            result = service.resume_batch(
                batch_id=args.batch_id,
                actor_user_id=None,
                payload=RealPlayerImportBatchResumeRequest(mode=args.mode),
            )
            _print_json(result.model_dump(mode="json"))
            return 0

        if args.command == "status":
            if args.batch_id:
                result = service.get_batch(args.batch_id, include_rows=bool(args.include_rows))
                _print_json(result.model_dump(mode="json"))
                return 0
            result = service.list_batches(
                limit=args.limit,
                batch_status=args.batch_status,
                provider_name=args.provider_name,
                batch_key=args.batch_key,
            )
            _print_json([item.model_dump(mode="json") for item in result])
            return 0

        if args.command == "issues":
            result = service.list_unresolved_issues(
                batch_id=args.batch_id,
                issue_type=args.issue_type,
                unresolved_only=not bool(args.all),
            )
            _print_json([item.model_dump(mode="json") for item in result])
            return 0

        result = service.get_valuation_status(batch_id=args.batch_id)
        _print_json(result.model_dump(mode="json"))
        return 0
    except RealPlayerImportOpsError as exc:
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


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
