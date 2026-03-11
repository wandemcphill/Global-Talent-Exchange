from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from backend.app.auth.dependencies import get_session
from backend.app.auth.router import register_user
from backend.app.auth.schemas import RegisterRequest
from backend.app.cache.redis_helpers import NullCacheBackend
from backend.app.ingestion.service import IngestionService
from backend.app.main import create_app
from backend.app.market.router import create_listing
from backend.app.market.schemas import ListingCreate
from backend.app.models.user import User
from backend.app.wallets.router import list_wallet_accounts


@pytest.fixture()
def app_and_engine(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_app_test.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    return create_app(engine=engine, run_migration_check=True), engine


def _resolve_session(app):
    session_dependency = app.dependency_overrides[get_session]
    generator = session_dependency()
    session = next(generator)
    return session, generator


def _close_session(generator) -> None:
    with suppress(StopIteration):
        next(generator)


@pytest.mark.anyio
async def test_app_startup_runs_migrations_and_registers_core_routes(app_and_engine) -> None:
    app, engine = app_and_engine

    async with app.router.lifespan_context(app):
        assert hasattr(app.state, "settings")
        assert hasattr(app.state, "db_engine")
        assert hasattr(app.state, "session_factory")
        assert hasattr(app.state, "market_engine")
        assert hasattr(app.state, "ingestion_pipeline")
        assert hasattr(app.state, "value_engine_bridge")
        assert hasattr(app.state, "ingestion_job_runner")
        assert "health" in app.state.domain_modules
        assert "admin" in app.state.domain_modules
        assert "surveillance" in app.state.domain_modules
        assert "value_engine" in app.state.domain_modules

        session, session_generator = _resolve_session(app)
        try:
            health_route = next(route for route in app.routes if getattr(route, "path", None) == "/health")
            health_response = health_route.endpoint(request=SimpleNamespace(app=app))
        finally:
            _close_session(session_generator)

    assert get_session in app.dependency_overrides
    assert health_response["status"] == "ok"
    assert health_response["components"]["database"]["status"] == "ok"
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/admin/config/supply-tiers" in paths
    assert "/admin/config/liquidity-bands" in paths
    assert "/admin/config/suspicion-thresholds" in paths
    assert "/admin/config/value-controls" in paths
    assert "/wallets/accounts" in paths
    assert "/wallets/payment-events" in paths
    assert "/players/summaries/recent" in paths
    assert "/clubs/{club_id}" in paths
    assert "/competitions/{competition_id}" in paths
    assert "/market/listings" in paths
    assert "/market/summary/{asset_id}" in paths
    assert "/market/offers" in paths
    assert "/value-engine/snapshots/rebuild" in paths
    assert "/surveillance/suspicious-players" in paths
    assert "/surveillance/suspicious-clusters" in paths
    assert "/surveillance/thin-market-alerts" in paths
    assert "/surveillance/holder-concentration-alerts" in paths
    assert "/surveillance/circular-trade-alerts" in paths
    assert "/portfolios/me" in paths
    assert "/notifications/me" in paths
    assert "/realtime/status" in paths

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "20260311_0004"


@pytest.mark.anyio
async def test_connected_modules_share_database_bootstrap_and_value_jobs(app_and_engine) -> None:
    app, _engine = app_and_engine

    async with app.router.lifespan_context(app):
        session, session_generator = _resolve_session(app)
        try:
            register_response = register_user(
                RegisterRequest(
                    email="fan@example.com",
                    username="fanuser",
                    password="SuperSecret1",
                    display_name="Fan User",
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
