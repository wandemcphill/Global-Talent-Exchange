from __future__ import annotations

from sqlalchemy import create_engine

from app.main import create_app


def test_global_memory_routes_register_without_running_lifespan() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=False)
    openapi_paths = app.openapi()["paths"]

    assert "/competitions" in openapi_paths
    assert "/enter" in openapi_paths
    assert "/rent" in openapi_paths
    assert "/national-pool" in openapi_paths
    assert "/player-history" in openapi_paths
    assert "/dynasty" in openapi_paths

