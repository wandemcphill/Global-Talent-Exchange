from __future__ import annotations

import json
import os
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.config import Settings, load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.real_player_bulk_ops_service import (
    RealPlayerBulkImportOpsError,
    RealPlayerBulkImportOpsService,
)


def build_service(*, database_url: str) -> RealPlayerBulkImportOpsService:
    settings = _settings_with_database_url(database_url=database_url)
    engine = create_database_engine(database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    return RealPlayerBulkImportOpsService(
        session_factory=session_factory,
        settings=settings,
    )


def print_result(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def error_payload(exc: RealPlayerBulkImportOpsError) -> dict[str, object]:
    return {
        "error": str(exc),
        "status_code": exc.status_code,
    }


def _settings_with_database_url(*, database_url: str) -> Settings:
    return load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": database_url,
            "GTE_DATABASE_URL": database_url,
        }
    )


__all__ = [
    "RealPlayerBulkImportOpsError",
    "build_service",
    "error_payload",
    "print_result",
]
