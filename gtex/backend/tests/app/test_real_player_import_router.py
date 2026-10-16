from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.core.config import load_settings
from app.ingestion.real_player_import_service import RealPlayerImportService
from app.ingestion.real_player_import_schemas import RealPlayerImportTriggerRequest
from app.ingestion.router import get_real_player_import_status, trigger_real_player_import
from app.models.base import Base


def test_router_handlers_trigger_real_player_import_and_read_status() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = load_settings(
        environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"},
        config_root=(Path(__file__).resolve().parents[2] / "config"),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))

    try:
        with session_factory() as session:
            summary = trigger_real_player_import(
                RealPlayerImportTriggerRequest(
                    provider_name="mock",
                    batch_size=2,
                    max_pages=1,
                    cursor_key="router-real-player-import",
                ),
                session=session,
                request=request,
            )

            assert summary.status == "partial_success"
            assert summary.records_seen == 2
            assert summary.inserted_count == 2
            assert summary.pages_processed == 1
            assert summary.next_cursor == "2"
            assert summary.exhausted is False

            status = get_real_player_import_status(
                provider_name="mock",
                cursor_key="router-real-player-import",
                service=RealPlayerImportService(
                    session,
                    settings=settings,
                ),
            )

            assert status.provider_name == "mock"
            assert status.cursor_key == "router-real-player-import"
            assert status.staged_player_count == 2
            assert status.cursor is not None
            assert status.cursor.cursor_value == "2"
            assert status.latest_run is not None
            assert status.latest_run.job_name == "real_player_directory_import"
            assert status.recent_runs[0].status == "partial_success"
    finally:
        engine.dispose()
