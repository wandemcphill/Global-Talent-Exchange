from __future__ import annotations

import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.config import load_settings
from app.core.database import create_session_factory, ensure_database_schema_current
from app.main import create_app
from app.manager_market.seed_catalog import build_seed_catalog_entries
from app.manager_market.service import ManagerMarketService
from app.wallets.service import WalletService


def _expected_counts() -> tuple[int, int, int]:
    rows = build_seed_catalog_entries()
    total_count = len(rows)
    legendary_count = sum(1 for row in rows if row["rarity"] == "legendary")
    return total_count, legendary_count, total_count - legendary_count


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'manager-catalog.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    ensure_database_schema_current(engine)
    return engine, create_session_factory(engine)


def test_seed_catalog_inserts_expected_rows_and_preserves_legendary_count(tmp_path) -> None:
    expected_total, expected_legendary, expected_non_legendary = _expected_counts()
    engine, session_factory = _build_session_factory(tmp_path)
    service = ManagerMarketService(wallet_service=WalletService())

    try:
        with session_factory() as session:
            result = service.seed_catalog_entries(session)
            session.commit()

        assert result.inserted_count == expected_total
        assert result.total_count == expected_total
        assert result.legendary_count == expected_legendary
        assert result.non_legendary_count == expected_non_legendary

        with session_factory() as session:
            counts = service.catalog_counts(session)

        assert counts.total_count == expected_total
        assert counts.legendary_count == expected_legendary
        assert counts.non_legendary_count == expected_non_legendary
    finally:
        engine.dispose()


def test_seed_catalog_rerun_is_idempotent(tmp_path) -> None:
    expected_total, expected_legendary, expected_non_legendary = _expected_counts()
    engine, session_factory = _build_session_factory(tmp_path)
    service = ManagerMarketService(wallet_service=WalletService())

    try:
        with session_factory() as session:
            first_run = service.seed_catalog_entries(session)
            session.commit()

        with session_factory() as session:
            second_run = service.seed_catalog_entries(session)
            session.commit()

        assert first_run.inserted_count == expected_total
        assert second_run.inserted_count == 0
        assert second_run.total_count == expected_total
        assert second_run.legendary_count == expected_legendary
        assert second_run.non_legendary_count == expected_non_legendary
    finally:
        engine.dispose()


def test_manager_catalog_endpoint_returns_seeded_inventory(tmp_path) -> None:
    expected_total, expected_legendary, expected_non_legendary = _expected_counts()
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'manager-catalog-api.db').as_posix()}"
    media_root = tmp_path / "media"
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_APP_ENV": "local",
            "GTE_DATABASE_URL": database_url,
            "GTE_MEDIA_STORAGE_ROOT": str(media_root),
            "RUN_STARTUP_SEEDING": "false",
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(settings=settings, engine=engine, run_migration_check=True)
    service = ManagerMarketService(wallet_service=WalletService())

    try:
        with TestClient(app) as client:
            response = client.get("/api/managers/catalog", params={"limit": 1000})
            app.state.deferred_startup_thread.join(timeout=5)

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == expected_total
        assert len(payload["items"]) == expected_total
        assert sum(1 for item in payload["items"] if item["rarity"] == "legendary") == expected_legendary
        assert sum(1 for item in payload["items"] if item["rarity"] != "legendary") == expected_non_legendary

        with app.state.session_factory() as session:
            counts = service.catalog_counts(session)

        assert counts.total_count == expected_total
        assert counts.legendary_count == expected_legendary
        assert counts.non_legendary_count == expected_non_legendary
    finally:
        engine.dispose()
