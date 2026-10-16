from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.config import Settings, load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.real_player_ingestion_service import (
    RealPlayerBatchBlockedError,
    RealPlayerIngestionService,
)
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


REPORT_ROOT = Path("ops/reports/real_player_ingestion")
_UNSAFE_PATH_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the controlled GTEX real-player ingestion batch.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Run the validate-only preflight for a curated real-player batch.")
    write_parser = subparsers.add_parser("write", help="Run the write path for a curated real-player batch after an internal preflight.")

    for subparser in (validate_parser, write_parser):
        subparser.add_argument("--input", required=True, help="Path to the curated real-player batch JSON manifest.")
        subparser.add_argument("--database-url", required=True, help="Target database URL.")
        subparser.add_argument("--as-of", required=True, help="ISO-8601 timestamp used for authoritative pricing.")
        subparser.add_argument("--batch-id", required=True, help="Explicit ingestion batch identifier.")
        subparser.add_argument("--ingestion-source-version", required=True, help="Explicit ingestion source version.")
        subparser.add_argument("--lookback-days", type=int, default=None, help="Optional value-engine lookback window.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    request = _load_request(
        input_path=args.input,
        as_of=_parse_datetime(args.as_of),
        batch_id=args.batch_id,
        ingestion_source_version=args.ingestion_source_version,
        lookback_days=args.lookback_days,
    )
    service = _build_service(database_url=args.database_url)

    if args.command == "validate":
        report = service.validate(request)
        payload = _payload(
            command="validate",
            status="validated",
            input_path=args.input,
            report=report.model_dump(mode="json"),
        )
        report_path = _write_report(batch_id=report.ingestion_batch_id, command="validate", payload=payload)
        payload["report_path"] = str(report_path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    try:
        report = service.write_batch(request)
        payload = _payload(
            command="write",
            status="success",
            input_path=args.input,
            report=report.model_dump(mode="json"),
        )
        report_path = _write_report(batch_id=report.ingestion_batch_id, command="write", payload=payload)
        payload["report_path"] = str(report_path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except RealPlayerBatchBlockedError as exc:
        payload = _payload(
            command="write",
            status="aborted",
            input_path=args.input,
            report=exc.report.model_dump(mode="json"),
        )
        report_path = _write_report(batch_id=exc.report.ingestion_batch_id, command="write", payload=payload)
        payload["report_path"] = str(report_path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2


def _build_service(*, database_url: str) -> RealPlayerIngestionService:
    engine = create_database_engine(database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    settings = _settings_with_database_url(database_url=database_url)
    return RealPlayerIngestionService(session_factory=session_factory, settings=settings)


def _load_request(
    *,
    input_path: str,
    as_of: datetime,
    batch_id: str,
    ingestion_source_version: str,
    lookback_days: int | None,
) -> RealPlayerIngestionRequest:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    request = RealPlayerIngestionRequest.model_validate(payload)
    updates: dict[str, Any] = {
        "as_of": as_of,
        "ingestion_batch_id": batch_id,
        "ingestion_source_version": ingestion_source_version,
    }
    if lookback_days is not None:
        updates["lookback_days"] = lookback_days
    return request.model_copy(update=updates)


def _settings_with_database_url(*, database_url: str) -> Settings:
    return load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": database_url,
            "GTE_DATABASE_URL": database_url,
        }
    )


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)


def _payload(*, command: str, status: str, input_path: str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": command,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "input_path": str(Path(input_path).resolve()),
        "report": report,
        "status": status,
    }


def _write_report(*, batch_id: str, command: str, payload: dict[str, Any]) -> Path:
    safe_batch_id = _sanitize_batch_id(batch_id)
    report_dir = REPORT_ROOT / safe_batch_id
    report_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"{command}-{run_stamp}.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return report_path.resolve()


def _sanitize_batch_id(value: str) -> str:
    cleaned = _UNSAFE_PATH_CHARS.sub("-", value.strip())
    return cleaned.strip("-.") or "real-player-batch"


if __name__ == "__main__":
    raise SystemExit(main())
