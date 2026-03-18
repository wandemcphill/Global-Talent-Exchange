from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone

from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text

from backend.app.auth.dependencies import get_session
from backend.app.auth.router import register_user
from backend.app.auth.schemas import RegisterRequest
from backend.app.cache.redis_helpers import NullCacheBackend
from backend.app.core.database import DatabaseRuntime, build_alembic_config
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


def test_app_startup_runs_migrations_and_registers_core_routes(app_and_engine) -> None:
    app, engine = app_and_engine

    with TestClient(app) as client:
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
        assert "leagues" in app.state.domain_modules
        assert "champions_league" in app.state.domain_modules
        assert "academy" in app.state.domain_modules
        assert "world_super_cup" in app.state.domain_modules
        assert "fast_cups" in app.state.domain_modules
        assert "match_engine" in app.state.domain_modules
        assert "canonical_clubs" in app.state.domain_modules
        assert "player_lifecycle" in app.state.domain_modules
        assert "club_identity" in app.state.domain_modules
        assert "replay_archive" in app.state.domain_modules
        assert "notifications" in app.state.domain_modules
        assert "creators" in app.state.domain_modules
        assert "referrals" in app.state.domain_modules
        assert "admin_referrals" in app.state.domain_modules

        health_response = client.get("/health")
        ready_response = client.get("/ready")
        version_response = client.get("/version")

    assert get_session in app.dependency_overrides
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json() == {
        "status": "ready",
        "checks": {
            "database": {
                "status": "ok",
                "detail": None,
            }
        },
    }
    assert version_response.status_code == 200
    assert version_response.json() == {
        "app_name": app.state.settings.app_name,
        "environment": app.state.settings.app_env,
        "api_version": app.state.settings.app_version,
        "phase_marker": app.state.settings.phase_marker,
    }
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/ready" in paths
    assert "/version" in paths
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/api/auth/me" in paths
    assert "/admin/config/supply-tiers" in paths
    assert "/admin/config/liquidity-bands" in paths
    assert "/admin/config/suspicion-thresholds" in paths
    assert "/admin/config/player-card-market-integrity" in paths
    assert "/admin/config/value-controls" in paths
    assert "/wallets/accounts" in paths
    assert "/wallets/payment-events" in paths
    assert "/api/wallets/accounts" in paths
    assert "/api/wallets/summary" in paths
    assert "/api/wallets/ledger" in paths
    assert "/api/wallets/payment-events" in paths
    assert "/players/summaries/recent" in paths
    assert "/clubs/{club_id}" in paths
    assert "/api/competitions" in paths
    assert "/api/competitions/{competition_id}" in paths
    assert "/api/competitions/{competition_id}/publish" in paths
    assert "/api/competitions/{competition_id}/join" in paths
    assert "/api/competitions/{competition_id}/financials" in paths
    assert "/market/listings" in paths
    assert "/market/summary/{asset_id}" in paths
    assert "/market/offers" in paths
    assert "/api/market/players" in paths
    assert "/api/market/players/{player_id}" in paths
    assert "/api/market/players/{player_id}/candles" in paths
    assert "/api/market/ticker/{player_id}" in paths
    assert "/value-engine/snapshots/rebuild" in paths
    assert "/surveillance/suspicious-players" in paths
    assert "/surveillance/suspicious-clusters" in paths
    assert "/surveillance/thin-market-alerts" in paths
    assert "/surveillance/holder-concentration-alerts" in paths
    assert "/surveillance/circular-trade-alerts" in paths
    assert "/api/orders" in paths
    assert "/api/orders/{order_id}" in paths
    assert "/api/orders/{order_id}/cancel" in paths
    assert "/api/orders/book/{player_id}" in paths
    assert "/api/portfolio" in paths
    assert "/api/portfolio/snapshot" in paths
    assert "/api/portfolio/summary" in paths
    assert "/portfolios/me" in paths
    assert "/leagues/register" in paths
    assert "/api/leagues/register" in paths
    assert "/champions-league/qualification-map" in paths
    assert "/api/champions-league/qualification-map" in paths
    assert "/academy/registration" in paths
    assert "/api/academy/registration" in paths
    assert "/world-super-cup/qualification/explanation" in paths
    assert "/api/world-super-cup/qualification/explanation" in paths
    assert "/fast-cups/upcoming" in paths
    assert "/api/fast-cups/upcoming" in paths
    assert "/match-engine/replay" in paths
    assert "/api/match-engine/replay" in paths
    assert "/api/clubs/{club_id}/reputation" in paths
    assert "/api/clubs/{club_id}/reputation/history" in paths
    assert "/api/clubs/{club_id}/prestige" in paths
    assert "/api/leaderboards/prestige" in paths
    assert "/api/clubs/{club_id}/dynasty" in paths
    assert "/api/clubs/{club_id}/dynasty/history" in paths
    assert "/api/clubs/{club_id}/eras" in paths
    assert "/api/leaderboards/dynasties" in paths
    assert "/api/clubs/{club_id}/identity" in paths
    assert "/api/clubs/{club_id}/valuation" in paths
    assert "/api/clubs/sale-market/listings" in paths
    assert "/api/clubs/{club_id}/sale-market" in paths
    assert "/api/clubs/{club_id}/sale-market/listing" in paths
    assert "/api/clubs/{club_id}/sale-market/inquiries" in paths
    assert "/api/clubs/{club_id}/sale-market/offers" in paths
    assert "/api/clubs/{club_id}/sale-market/transfer" in paths
    assert "/api/clubs/{club_id}/jerseys" in paths
    assert "/api/clubs/{club_id}/badge" in paths
    assert "/api/creators/profile" in paths
    assert "/api/creators/profile/me" in paths
    assert "/api/creators/me/summary" in paths
    assert "/api/referrals/share-codes" in paths
    assert "/api/referrals/me/summary" in paths
    assert "/api/admin/referrals/dashboard" in paths
    assert "/api/admin/referrals/analytics/summary" in paths
    assert "/notifications/me" in paths
    assert "/api/notifications/me" in paths
    assert "/replays/public/featured" in paths
    assert "/api/replays/public/featured" in paths
    assert "/api/players/{player_id}/career" in paths
    assert "/api/players/{player_id}/contracts" in paths
    assert "/api/players/{player_id}/injuries" in paths
    assert "/api/transfers/windows" in paths
    assert "/api/transfers/windows/{window_id}/bids" in paths
    assert "/realtime/status" in paths

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    target_head = ScriptDirectory.from_config(build_alembic_config(str(engine.url))).get_current_head()
    assert revision == target_head


def test_ready_returns_service_unavailable_when_database_check_fails(app_and_engine, monkeypatch) -> None:
    app, _engine = app_and_engine

    def _raise_db_error(_self) -> bool:
        raise RuntimeError("db offline")

    with TestClient(app) as client:
        monkeypatch.setattr(DatabaseRuntime, "ping", _raise_db_error)
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": {
                "status": "error",
                "detail": "db offline",
            }
        },
    }


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
