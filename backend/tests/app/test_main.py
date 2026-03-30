from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
import logging
import os
from uuid import uuid4

from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text

from app.auth.dependencies import get_session
from app.auth.router import register_user
from app.auth.schemas import RegisterRequest
from app.cache.redis_helpers import NullCacheBackend
from app.core.config import load_settings
from app.core.database import DatabaseRuntime, build_alembic_config
from app.ingestion.service import IngestionService
import app.main as main_module
from app.main import create_app
from app.market.router import create_listing
from app.market.schemas import ListingCreate
from app.models.user import User
from app.wallets.router import list_wallet_accounts


@pytest.fixture()
def app_and_engine():
    temp_root = Path(__file__).resolve().parents[2] / ".tmp_testdbs"
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = temp_root / f"gte_app_test_{uuid4().hex}.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        yield create_app(engine=engine, run_migration_check=True), engine
    finally:
        engine.dispose()
        with suppress(FileNotFoundError, PermissionError):
            database_path.unlink()


def _resolve_session(app):
    session_dependency = app.dependency_overrides[get_session]
    generator = session_dependency()
    session = next(generator)
    return session, generator


def _close_session(generator) -> None:
    with suppress(StopIteration):
        next(generator)


def _install_logger_info_spy(monkeypatch) -> list[str]:
    messages: list[str] = []

    def _record(message: object, *args: object, **_kwargs: object) -> None:
        template = str(message)
        if args:
            try:
                messages.append(template % args)
                return
            except (TypeError, ValueError):
                pass
        messages.append(template)

    import app.modules as modules_module

    monkeypatch.setattr(main_module.logger, "info", _record)
    monkeypatch.setattr(modules_module.logger, "info", _record)
    return messages


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
        assert "matches" in app.state.domain_modules
        assert "live_matches" in app.state.domain_modules
        assert "manager_duels" in app.state.domain_modules
        assert "manager_marketplace" in app.state.domain_modules
        assert "simulation_matchmaking" in app.state.domain_modules
        assert "ultimate_league" in app.state.domain_modules
        assert "competitive_integrity" in app.state.domain_modules
        assert "canonical_clubs" in app.state.domain_modules
        assert "player_lifecycle" in app.state.domain_modules
        assert "player_agency" in app.state.domain_modules
        assert "club_identity" in app.state.domain_modules
        assert "replay_archive" in app.state.domain_modules
        assert "notifications" in app.state.domain_modules
        assert "viral" in app.state.domain_modules
        assert "pundits" in app.state.domain_modules
        assert "infinite_league" in app.state.domain_modules
        assert "regen_universe" in app.state.domain_modules
        assert "football_universe" in app.state.domain_modules
        assert "broadcast_rights" in app.state.domain_modules
        assert "creators" in app.state.domain_modules
        assert "creator_marketplace" in app.state.domain_modules
        assert "referrals" in app.state.domain_modules
        assert "admin_referrals" in app.state.domain_modules
        assert "ownership_groups" in app.state.domain_modules

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
            },
            "schema": {
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
    assert "/players" in paths
    assert "/players/summaries/recent" in paths
    assert "/regen-universe/awards" in paths
    assert "/api/regen-universe/awards" in paths
    assert "/regen-universe/rankings" in paths
    assert "/regen-universe/hall-of-fame" in paths
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
    assert "/matches/start" in paths
    assert "/api/matches/start" in paths
    assert "/matches/complete" in paths
    assert "/api/matches/complete" in paths
    assert "/matches/{match_id}/replay" in paths
    assert "/api/matches/{match_id}/replay" in paths
    assert "/matches/{match_id}/analysis" in paths
    assert "/api/matches/{match_id}/analysis" in paths
    assert "/matches/{match_id}/spectate" in paths
    assert "/api/matches/{match_id}/highlights" in paths
    assert "/manager-duels" in paths
    assert "/manager-duels/leaderboard" in paths
    assert "/api/manager-duels/{duel_id}" in paths
    assert "/managers" in paths
    assert "/managers/leaderboard" in paths
    assert "/simulation-matchmaking/profiles/{user_id}" in paths
    assert "/api/simulation-matchmaking/profiles/{user_id}" in paths
    assert "/simulation-matchmaking/quick-game" in paths
    assert "/api/simulation-matchmaking/quick-game" in paths
    assert "/simulation-matchmaking/quick-tournament" in paths
    assert "/api/simulation-matchmaking/quick-tournament" in paths
    assert "/simulation-matchmaking/hosted-competitions/preview" in paths
    assert "/api/simulation-matchmaking/hosted-competitions/preview" in paths
    assert "/ultimate-league/tiers" in paths
    assert "/api/ultimate-league/tiers" in paths
    assert "/ultimate-league/competitors/{competitor_id}" in paths
    assert "/api/ultimate-league/competitors/{competitor_id}" in paths
    assert "/ultimate-league/standings/{tier}" in paths
    assert "/api/ultimate-league/standings/{tier}" in paths
    assert "/ultimate-league/matchmaking/batch" in paths
    assert "/api/ultimate-league/matchmaking/batch" in paths
    assert "/ultimate-league/matches/result" in paths
    assert "/api/ultimate-league/matches/result" in paths
    assert "/ultimate-league/tournaments" in paths
    assert "/api/ultimate-league/tournaments" in paths
    assert "/ultimate-league/tournaments/{tournament_id}" in paths
    assert "/api/ultimate-league/tournaments/{tournament_id}" in paths
    assert "/ultimate-league/tournaments/{tournament_id}/payouts/preview" in paths
    assert "/api/ultimate-league/tournaments/{tournament_id}/payouts/preview" in paths
    assert "/competitive-integrity/managers" in paths
    assert "/api/competitive-integrity/managers" in paths
    assert "/competitive-integrity/matches" in paths
    assert "/api/competitive-integrity/matches" in paths
    assert "/competitive-integrity/fast-game/runs" in paths
    assert "/api/competitive-integrity/fast-game/runs" in paths
    assert "/competitive-integrity/notifications/events" in paths
    assert "/api/competitive-integrity/notifications/events" in paths
    assert "/broadcast/{match_id}" in paths
    assert "/api/broadcast/{match_id}" in paths
    assert "/broadcast-rights/competitions/{competition_id}" in paths
    assert "/api/broadcast-rights/competitions/{competition_id}" in paths
    assert "/broadcast-rights/competitions/{competition_id}/acquire" in paths
    assert "/api/broadcast-rights/competitions/{competition_id}/acquire" in paths
    assert "/broadcast-rights/competitions/{competition_id}/auctions" in paths
    assert "/api/broadcast-rights/competitions/{competition_id}/auctions" in paths
    assert "/broadcast-rights/auctions/{auction_id}/bids" in paths
    assert "/api/broadcast-rights/auctions/{auction_id}/bids" in paths
    assert "/broadcast-rights/matches/{match_id}/access" in paths
    assert "/api/broadcast-rights/matches/{match_id}/access" in paths
    assert "/broadcast-rights/matches/{match_id}/distribute" in paths
    assert "/api/broadcast-rights/matches/{match_id}/distribute" in paths
    assert "/admin/broadcast-rights/jobs/run" in paths
    assert "/fans/{club_id}" in paths
    assert "/api/fans/{club_id}" in paths
    assert "/club/identity" in paths
    assert "/api/club/identity" in paths
    assert "/media" in paths
    assert "/api/media" in paths
    assert "/ownership-groups" in paths
    assert "/api/ownership-groups" in paths
    assert "/ownership-groups/{group_id}" in paths
    assert "/api/ownership-groups/{group_id}" in paths
    assert "/ownership-groups/{group_id}/clubs" in paths
    assert "/api/ownership-groups/{group_id}/clubs" in paths
    assert "/ownership-groups/{group_id}/budget/allocate" in paths
    assert "/api/ownership-groups/{group_id}/budget/allocate" in paths
    assert "/ownership-groups/{group_id}/budget/transfer" in paths
    assert "/api/ownership-groups/{group_id}/budget/transfer" in paths
    assert "/ownership-groups/transfers/validate" in paths
    assert "/api/ownership-groups/transfers/validate" in paths
    assert "/admin/ownership-groups/reputation-cycle" in paths
    assert "/api/clubs/{club_id}/reputation" in paths
    assert "/api/clubs/{club_id}/reputation/history" in paths
    assert "/api/clubs/{club_id}/prestige" in paths
    assert "/api/leaderboards/prestige" in paths
    assert "/api/clubs/{club_id}/dynasty" in paths
    assert "/api/clubs/{club_id}/dynasty/history" in paths
    assert "/api/clubs/{club_id}/eras" in paths
    assert "/api/leaderboards/dynasties" in paths
    assert "/api/clubs/{club_id}/trophy-cabinet" in paths
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
    assert "/api/creators/me/copilot/analyze" in paths
    assert "/campaigns" in paths
    assert "/campaigns/create" in paths
    assert "/campaigns/{id}/apply" in paths
    assert "/campaigns/{id}/accept" in paths
    assert "/campaigns/{id}/performance" in paths
    assert "/creators/marketplace" in paths
    assert "/creators/me/reputation" in paths
    assert "/api/campaigns" in paths
    assert "/api/campaigns/create" in paths
    assert "/api/campaigns/{id}/apply" in paths
    assert "/api/campaigns/{id}/accept" in paths
    assert "/api/campaigns/{id}/performance" in paths
    assert "/api/creators/marketplace" in paths
    assert "/api/creators/me/reputation" in paths
    assert "/api/referrals/share-codes" in paths
    assert "/api/referrals/me/summary" in paths
    assert "/api/admin/referrals/dashboard" in paths
    assert "/api/admin/referrals/analytics/summary" in paths
    assert "/notifications/me" in paths
    assert "/notifications" in paths
    assert "/api/notifications/me" in paths
    assert "/api/notifications" in paths
    assert "/api/viral/feed" in paths
    assert "/api/pundits/matches/{match_key}" in paths
    assert "/infinite-league/status" in paths
    assert "/api/infinite-league/status" in paths
    assert "/api/infinite-league/tick" in paths
    assert "/admin/ops/fan-updates" in paths
    assert "/admin/ops/media-generation" in paths
    assert "/admin/ops/identity-evolution" in paths
    assert "/admin/ops/broadcast-revenue" in paths
    assert "/admin/ops/broadcast-expiration" in paths
    assert "/admin/ops/ownership-groups/reputation" in paths
    assert "/api/admin/competitive-integrity/workers/run-once" in paths
    assert "/replays/public/featured" in paths
    assert "/api/replays/public/featured" in paths
    assert "/api/players/{player_id}/career" in paths
    assert "/api/players/{player_id}/agency" in paths
    assert "/api/players/{player_id}/agency/contract-decision" in paths
    assert "/api/players/{player_id}/agency/transfer-decision" in paths
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


def test_ready_returns_service_unavailable_when_schema_smoke_fails(app_and_engine, monkeypatch) -> None:
    app, _engine = app_and_engine

    def _raise_schema_error(_self) -> tuple[str, ...]:
        raise RuntimeError("Database schema smoke check failed. Missing tables: player_share_markets.")

    with TestClient(app) as client:
        monkeypatch.setattr(DatabaseRuntime, "check_schema_smoke", _raise_schema_error)
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": {
                "status": "ok",
                "detail": None,
            },
            "schema": {
                "status": "error",
                "detail": "Database schema smoke check failed. Missing tables: player_share_markets.",
            },
        },
    }


def test_startup_logs_completion_and_skips_non_local_seeding(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'startup-log-test.db').as_posix()}"
    media_root = tmp_path / "media"
    monkeypatch.setattr(main_module, "_ensure_initial_admin", lambda *args, **kwargs: None)
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_APP_ENV": "development",
            "GTE_DATABASE_URL": database_url,
            "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(settings=settings, engine=engine, run_migration_check=False)

    messages = _install_logger_info_spy(monkeypatch)
    with TestClient(app):
        app.state.deferred_startup_thread.join(timeout=5)

    assert "app.startup.complete" in messages
    assert any(message.startswith("app.startup.seed.skipped") for message in messages)


def test_startup_logs_completion_and_skips_seeding_when_disabled(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'startup-seeding-disabled.db').as_posix()}"
    media_root = tmp_path / "media"
    monkeypatch.setattr(main_module, "_ensure_initial_admin", lambda *args, **kwargs: None)
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
    app = create_app(settings=settings, engine=engine, run_migration_check=False)

    messages = _install_logger_info_spy(monkeypatch)
    with TestClient(app):
        app.state.deferred_startup_thread.join(timeout=5)

    assert "app.startup.complete" in messages
    assert any(message == "app.startup.seed.skipped seed=policy_documents reason=disabled" for message in messages)


def test_startup_tolerates_unavailable_redis(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'startup-redis-degraded.db').as_posix()}"
    media_root = tmp_path / "media"
    monkeypatch.setattr(main_module, "_ensure_initial_admin", lambda *args, **kwargs: None)
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_APP_ENV": "development",
            "GTE_DATABASE_URL": database_url,
            "GTE_MEDIA_STORAGE_ROOT": str(media_root),
            "GTE_REDIS_URL": "redis://127.0.0.1:1/0",
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(settings=settings, engine=engine, run_migration_check=False)

    messages = _install_logger_info_spy(monkeypatch)
    with TestClient(app) as client:
        response = client.get("/health")
        app.state.deferred_startup_thread.join(timeout=5)

    assert response.status_code == 200
    assert isinstance(app.state.cache_backend, NullCacheBackend)
    assert "app.startup.complete" in messages


def test_main_module_exposes_lazy_asgi_app(monkeypatch) -> None:
    sentinel = object()
    call_count = 0

    def _build_app():
        nonlocal call_count
        call_count += 1
        return sentinel

    monkeypatch.setattr(main_module, "_ASGI_APP", None)
    monkeypatch.setattr(main_module, "create_app", _build_app)

    first = getattr(main_module, "app")
    second = getattr(main_module, "app")

    assert first is sentinel
    assert second is sentinel
    assert call_count == 1


def test_get_asgi_app_defaults_production_boot_to_skip_runtime_migration_check(monkeypatch) -> None:
    sentinel = object()
    captured: dict[str, object] = {}

    class _Settings:
        app_env = "production"
        run_migration_check = True

    def _build_app(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.delenv("GTE_RUN_MIGRATION_CHECK", raising=False)
    monkeypatch.setattr(main_module, "_ASGI_APP", None)
    monkeypatch.setattr(main_module, "get_settings", lambda: _Settings())
    monkeypatch.setattr(main_module, "create_app", _build_app)

    app = main_module.get_asgi_app()

    assert app is sentinel
    assert captured["run_migration_check"] is False


def test_get_asgi_app_uses_configured_migration_check_outside_production(monkeypatch) -> None:
    sentinel = object()
    captured: dict[str, object] = {}

    class _Settings:
        app_env = "development"
        run_migration_check = True

    def _build_app(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(main_module, "_ASGI_APP", None)
    monkeypatch.setattr(main_module, "get_settings", lambda: _Settings())
    monkeypatch.setattr(main_module, "create_app", _build_app)

    app = main_module.get_asgi_app()

    assert app is sentinel
    assert captured["run_migration_check"] is True


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
                    full_name="Fan User",
                    region_code="NG",
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
