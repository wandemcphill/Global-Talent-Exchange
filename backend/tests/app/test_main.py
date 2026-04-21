from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from backend.tests.app._module_registration_contract_data import (
    CREATOR_MEDIA_OPENAPI_ABSENT_PATHS,
    CREATOR_MEDIA_OPENAPI_PRESENT_PATHS,
    MATCH_ENGINE_OPENAPI_PRESENT_PATHS,
)

APP_MAIN_SYSTEM_OPENAPI_PATHS = [
    "/health",
    "/ready",
    "/version",
    "/auth/register",
    "/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/auth/me",
    "/admin/config/supply-tiers",
    "/admin/config/liquidity-bands",
    "/admin/config/suspicion-thresholds",
    "/admin/config/player-card-market-integrity",
    "/admin/config/value-controls",
]

APP_MAIN_WALLET_AND_MARKET_OPENAPI_PATHS = [
    "/wallets/accounts",
    "/wallets/payment-events",
    "/api/wallets/accounts",
    "/api/v1/wallets/accounts",
    "/api/wallets/summary",
    "/api/v1/wallets/summary",
    "/api/wallets/ledger",
    "/api/v1/wallets/ledger",
    "/api/wallets/payment-events",
    "/api/v1/wallets/payment-events",
    "/players/summaries/recent",
    "/clubs/{club_id}",
    "/api/competitions",
    "/api/competitions/{competition_id}",
    "/api/competitions/{competition_id}/publish",
    "/api/competitions/{competition_id}/join",
    "/api/competitions/{competition_id}/financials",
    "/market/listings",
    "/market/summary/{asset_id}",
    "/market/offers",
    "/api/market/players",
    "/api/market/players/{player_id}",
    "/api/market/players/{player_id}/candles",
    "/api/market/ticker/{player_id}",
    "/value-engine/snapshots/rebuild",
    "/surveillance/suspicious-players",
    "/surveillance/suspicious-clusters",
    "/surveillance/thin-market-alerts",
    "/surveillance/holder-concentration-alerts",
    "/surveillance/circular-trade-alerts",
    "/api/orders",
    "/api/v1/orders",
    "/api/orders/{order_id}",
    "/api/v1/orders/{order_id}",
    "/api/orders/{order_id}/cancel",
    "/api/v1/orders/{order_id}/cancel",
    "/api/orders/book/{player_id}",
    "/api/v1/orders/book/{player_id}",
    "/api/portfolio",
    "/api/portfolio/snapshot",
    "/api/portfolio/summary",
    "/portfolios/me",
]

APP_MAIN_COMPETITION_ALIAS_OPENAPI_PATHS = [
    "/leagues/register",
    "/api/leagues/register",
    "/champions-league/qualification-map",
    "/api/champions-league/qualification-map",
    "/academy/registration",
    "/api/academy/registration",
    "/world-super-cup/qualification/explanation",
    "/api/world-super-cup/qualification/explanation",
    "/fast-cups/upcoming",
    "/api/fast-cups/upcoming",
]

APP_MAIN_CLUB_SURFACE_OPENAPI_PATHS = [
    "/api/clubs/{club_id}/reputation",
    "/api/v1/clubs/{club_id}/reputation",
    "/api/clubs/{club_id}/reputation/history",
    "/api/clubs/{club_id}/prestige",
    "/api/leaderboards/prestige",
    "/api/clubs/{club_id}/dynasty",
    "/api/clubs/{club_id}/dynasty/history",
    "/api/clubs/{club_id}/eras",
    "/api/leaderboards/dynasties",
    "/api/clubs/{club_id}/trophy-cabinet",
    "/api/clubs/{club_id}/identity",
    "/api/clubs/{club_id}/valuation",
    "/api/clubs/sale-market/listings",
    "/api/clubs/{club_id}/sale-market",
    "/api/clubs/{club_id}/sale-market/listing",
    "/api/clubs/{club_id}/sale-market/inquiries",
    "/api/clubs/{club_id}/sale-market/offers",
    "/api/clubs/{club_id}/sale-market/transfer",
    "/api/clubs/{club_id}/jerseys",
    "/api/clubs/{club_id}/badge",
]

APP_MAIN_REFERRAL_AND_PLAYER_SURFACE_OPENAPI_PATHS = [
    "/api/referrals/share-codes",
    "/api/referrals/me/summary",
    "/api/admin/referrals/dashboard",
    "/api/admin/referrals/analytics/summary",
    "/replays/public/featured",
    "/api/replays/public/featured",
    "/api/players/{player_id}/career",
    "/api/players/{player_id}/agency",
    "/api/players/{player_id}/agency/contract-decision",
    "/api/players/{player_id}/agency/transfer-decision",
    "/api/players/{player_id}/contracts",
    "/api/players/{player_id}/injuries",
    "/api/transfers/windows",
    "/api/transfers/windows/{window_id}/bids",
    "/realtime/status",
]


def _create_app(*, engine, run_migration_check: bool):
    from app.main import create_app

    return create_app(engine=engine, run_migration_check=run_migration_check)


def _create_engine(database_url: str):
    from sqlalchemy import create_engine

    return create_engine(database_url, connect_args={"check_same_thread": False})


def _database_runtime_class():
    from app.core.database import DatabaseRuntime

    return DatabaseRuntime


def _auth_get_session_dependency():
    from app.auth.dependencies import get_session

    return get_session


def _build_alembic_head(engine_url: str) -> str | None:
    from app.core.database import build_alembic_config
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(build_alembic_config(engine_url)).get_current_head()


def _sql_text(statement: str):
    from sqlalchemy import text

    return text(statement)


def _test_client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def _copy_sqlite_template(template_path: Path, destination_path: Path) -> str:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, destination_path)
    return f"sqlite+pysqlite:///{destination_path.as_posix()}"


@pytest.fixture()
def migrated_database_url(tmp_path, migrated_sqlite_template):
    return _copy_sqlite_template(migrated_sqlite_template, tmp_path / "gte_app_test.db")


@pytest.fixture()
def app_and_engine(migrated_database_url):
    database_url = migrated_database_url
    engine = _create_engine(database_url)
    app = _create_app(engine=engine, run_migration_check=False)
    try:
        yield app, engine
    finally:
        engine.dispose()


def _resolve_session(app):
    session_dependency = app.dependency_overrides[_auth_get_session_dependency()]
    generator = session_dependency()
    session = next(generator)
    return session, generator


def _close_session(generator) -> None:
    with suppress(StopIteration):
        next(generator)


def test_app_startup_registers_core_routes_and_health_endpoints(app_and_engine) -> None:
    app, engine = app_and_engine

    with _test_client(app) as client:
        assert hasattr(app.state, "settings")
        assert hasattr(app.state, "db_engine")
        assert hasattr(app.state, "session_factory")
        assert app.state.outbox_relay is not None
        assert hasattr(app.state, "market_engine")
        assert hasattr(app.state, "ingestion_pipeline")
        assert hasattr(app.state, "value_engine_bridge")
        assert hasattr(app.state, "ingestion_job_runner")
        assert "health" in app.state.domain_modules
        assert "admin" in app.state.domain_modules
        assert "surveillance" in app.state.domain_modules
        assert "value_engine" in app.state.domain_modules
        assert "leagues" in app.state.domain_modules
        assert "champions_league" in app.state.domain_modules
        assert "academy" in app.state.domain_modules
        assert "world_super_cup" in app.state.domain_modules
        assert "fast_cups" in app.state.domain_modules
        assert "match_engine" in app.state.domain_modules
        assert "canonical_clubs" in app.state.domain_modules
        assert "player_lifecycle" in app.state.domain_modules
        assert "player_agency" in app.state.domain_modules
        assert "club_identity" in app.state.domain_modules
        assert "replay_archive" in app.state.domain_modules
        assert "notifications" in app.state.domain_modules
        assert "creators" in app.state.domain_modules
        assert "referrals" in app.state.domain_modules
        assert "admin_referrals" in app.state.domain_modules

        health_response = client.get("/health")
        ready_response = client.get("/ready")
        version_response = client.get("/version")
        docs_response = client.get("/docs")

    assert _auth_get_session_dependency() in app.dependency_overrides
    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert health_payload["status"] == "ok"
    assert health_payload["checks"]["api"] == {"status": "ok", "detail": None}
    assert health_payload["checks"]["database"] == {"status": "ok", "detail": None}
    assert health_payload["checks"]["redis"] == {
        "status": "skipped",
        "detail": "Redis is not configured; distributed cache, rate limiting, and queue-backed fan-out are unavailable.",
    }
    assert health_payload["checks"]["kafka"] == {
        "status": "skipped",
        "detail": "Kafka brokers are not configured; event streaming is running in local fallback mode.",
    }
    assert health_payload["runtime_mode"] == "degraded"
    assert any("Redis is not configured" in reason for reason in health_payload["mode_reasons"])
    assert any("Kafka brokers are not configured" in reason for reason in health_payload["mode_reasons"])
    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["status"] == "ready"
    assert ready_payload["checks"]["api"] == {"status": "ok", "detail": None}
    assert ready_payload["checks"]["database"] == {"status": "ok", "detail": None}
    assert ready_payload["checks"]["redis"] == {
        "status": "skipped",
        "detail": "Redis is not configured; distributed cache, rate limiting, and queue-backed fan-out are unavailable.",
    }
    assert ready_payload["checks"]["kafka"] == {
        "status": "skipped",
        "detail": "Kafka brokers are not configured; event streaming is running in local fallback mode.",
    }
    assert ready_payload["checks"]["schema"] == {"status": "ok", "detail": None}
    assert ready_payload["runtime_mode"] == "degraded"
    assert version_response.status_code == 200
    assert version_response.json() == {
        "app_name": app.state.settings.app_name,
        "environment": app.state.settings.app_env,
        "api_version": app.state.settings.app_version,
        "phase_marker": app.state.settings.phase_marker,
    }
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    paths = app.openapi()["paths"]
    for path in APP_MAIN_SYSTEM_OPENAPI_PATHS:
        assert path in paths
    for path in APP_MAIN_WALLET_AND_MARKET_OPENAPI_PATHS:
        assert path in paths
    for path in APP_MAIN_COMPETITION_ALIAS_OPENAPI_PATHS:
        assert path in paths
    for path in MATCH_ENGINE_OPENAPI_PRESENT_PATHS:
        assert path in paths
    for path in (
        "/api/match-engine/replay",
        "/api/match-engine/summary",
    ):
        assert path in paths
    for path in APP_MAIN_CLUB_SURFACE_OPENAPI_PATHS:
        assert path in paths
    for path in CREATOR_MEDIA_OPENAPI_PRESENT_PATHS:
        assert path in paths
    for path in CREATOR_MEDIA_OPENAPI_ABSENT_PATHS:
        assert path not in paths
    for path in APP_MAIN_REFERRAL_AND_PLAYER_SURFACE_OPENAPI_PATHS:
        assert path in paths
    assert "/api/notifications/me" in paths
    assert "/notifications/me" not in paths

    with engine.connect() as connection:
        revision = connection.execute(_sql_text("SELECT version_num FROM alembic_version")).scalar_one()

    target_head = _build_alembic_head(str(engine.url))
    assert revision == target_head


def test_app_startup_repairs_schema_when_smoke_detects_stale_database(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_schema_repair.db').as_posix()}"
    engine = _create_engine(database_url)
    app = _create_app(engine=engine, run_migration_check=False)

    try:
        with _test_client(app) as client:
            ready_response = client.get("/ready")

        assert ready_response.status_code == 200
        assert ready_response.json()["status"] == "ready"

        with engine.connect() as connection:
            revision = connection.execute(_sql_text("SELECT version_num FROM alembic_version")).scalar_one()

        target_head = _build_alembic_head(str(engine.url))
        assert revision == target_head
    finally:
        engine.dispose()


def test_app_startup_fails_stamped_head_database_with_missing_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_stamped_head_schema_repair.db').as_posix()}"
    engine = _create_engine(database_url)
    target_head = _build_alembic_head(str(engine.url))
    assert target_head is not None

    with engine.begin() as connection:
        connection.execute(_sql_text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY)"))
        connection.execute(
            _sql_text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"), {"version_num": target_head}
        )

    app = _create_app(engine=engine, run_migration_check=False)

    try:
        with pytest.raises(RuntimeError, match="Database schema smoke check failed."):
            with _test_client(app):
                pass
    finally:
        engine.dispose()


def test_ready_returns_service_unavailable_when_database_check_fails(app_and_engine, monkeypatch) -> None:
    app, _engine = app_and_engine
    database_runtime = _database_runtime_class()

    def _raise_db_error(_self) -> bool:
        raise RuntimeError("db offline")

    with _test_client(app) as client:
        monkeypatch.setattr(database_runtime, "ping", _raise_db_error)
        response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["api"] == {"status": "ok", "detail": None}
    assert payload["checks"]["database"] == {"status": "error", "detail": "db offline"}
    assert payload["checks"]["redis"] == {
        "status": "skipped",
        "detail": "Redis is not configured; distributed cache, rate limiting, and queue-backed fan-out are unavailable.",
    }
    assert payload["checks"]["kafka"] == {
        "status": "skipped",
        "detail": "Kafka brokers are not configured; event streaming is running in local fallback mode.",
    }


def test_app_startup_fails_when_schema_smoke_fails_even_without_migration_upgrade(monkeypatch, tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_schema_smoke_failure.db').as_posix()}"
    engine = _create_engine(database_url)
    app = _create_app(engine=engine, run_migration_check=False)
    database_runtime = _database_runtime_class()

    def _raise_schema_error(_self):
        raise RuntimeError("schema drift")

    monkeypatch.setattr(database_runtime, "check_schema_smoke", _raise_schema_error)

    try:
        with pytest.raises(RuntimeError, match="schema drift"):
            with _test_client(app):
                pass
    finally:
        engine.dispose()


def test_app_startup_and_ready_skip_schema_smoke_when_env_enabled(app_and_engine, monkeypatch) -> None:
    app, _engine = app_and_engine
    database_runtime = _database_runtime_class()

    def _raise_schema_error(_self, **_kwargs):
        raise RuntimeError("schema drift")

    monkeypatch.setenv("SKIP_SCHEMA_CHECK", "true")
    monkeypatch.setattr(database_runtime, "check_schema_smoke", _raise_schema_error)

    with _test_client(app) as client:
        ready_response = client.get("/ready")

    assert ready_response.status_code == 200
    payload = ready_response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["api"] == {"status": "ok", "detail": None}
    assert payload["checks"]["database"] == {"status": "ok", "detail": None}
    assert payload["checks"]["redis"] == {
        "status": "skipped",
        "detail": "Redis is not configured; distributed cache, rate limiting, and queue-backed fan-out are unavailable.",
    }
    assert payload["checks"]["kafka"] == {
        "status": "skipped",
        "detail": "Kafka brokers are not configured; event streaming is running in local fallback mode.",
    }
    assert "schema" not in payload["checks"]


@pytest.mark.anyio
async def test_connected_modules_share_database_bootstrap_and_value_jobs(app_and_engine) -> None:
    app, _engine = app_and_engine
    from app.auth.router import register_user
    from app.auth.schemas import RegisterRequest
    from app.cache.redis_helpers import NullCacheBackend
    from app.ingestion.service import IngestionService
    from app.market.router import create_listing
    from app.market.schemas import ListingCreate
    from app.models.user import User
    from app.wallets.router import list_wallet_accounts

    async with app.router.lifespan_context(app):
        session, session_generator = _resolve_session(app)
        try:
            register_response = register_user(
                RegisterRequest(
                    email="fan@example.com",
                    username="fanuser",
                    password="SuperSecret1",  # pragma: allowlist secret
                    full_name="Fan User",
                ),
                session,
            )
            current_user = session.get(User, register_response.user.id)

            wallet_accounts = list_wallet_accounts(session=session, current_user=current_user)
            listing_response = create_listing(
                ListingCreate(
                    asset_id="asset-1",
                    listing_type="transfer",
                    ask_price=125,
                ),
                current_user=current_user,
                market_engine=app.state.market_engine,
            )

            ingestion_service = IngestionService(session, cache_backend=NullCacheBackend())
            ingestion_service.bootstrap_sync(provider_name="mock")
            ingestion_service.sync_matches(provider_name="mock")
            ingestion_service.sync_player_stats(provider_name="mock")
            session.commit()

            snapshots = app.state.value_engine_bridge.run(
                as_of=datetime(2026, 3, 11, tzinfo=timezone.utc),
            )
            later_snapshots = app.state.value_engine_bridge.run(
                as_of=datetime(2026, 3, 12, tzinfo=timezone.utc),
            )
            job_summary = app.state.ingestion_job_runner.nightly_full_sync()
        finally:
            _close_session(session_generator)

    assert {account.unit.value for account in wallet_accounts} == {"coin", "credit"}
    assert listing_response.seller_user_id == register_response.user.id
    assert len(snapshots) >= 1
    assert len(later_snapshots) >= 1
    assert all(snapshot.target_credits > 0 for snapshot in snapshots)
    first_run = {snapshot.player_id: snapshot for snapshot in snapshots}
    for snapshot in later_snapshots:
        if snapshot.player_id in first_run:
            assert snapshot.previous_credits == first_run[snapshot.player_id].target_credits
    assert job_summary.status == "success"
    assert len(app.state.value_engine_bridge.last_run_snapshots) >= 1
