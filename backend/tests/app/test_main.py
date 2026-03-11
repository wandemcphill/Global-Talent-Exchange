from __future__ import annotations

from contextlib import suppress
import pytest
from sqlalchemy import create_engine, text

from backend.app.auth.dependencies import get_session
from backend.app.auth.router import register_user
from backend.app.auth.schemas import RegisterRequest
from backend.app.main import create_app
from backend.app.market.router import create_listing
from backend.app.market.schemas import ListingCreate
from backend.app.models.user import User
from backend.app.value_engine.router import build_value_snapshots
from backend.app.value_engine.schemas import ValueSnapshotBatchRequest
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
        assert hasattr(app.state, "market_engine")
        session, session_generator = _resolve_session(app)
        try:
            health_route = next(route for route in app.routes if getattr(route, "path", None) == "/health")
            health_response = health_route.endpoint(session=session)
        finally:
            _close_session(session_generator)

    assert get_session in app.dependency_overrides
    assert health_response == {"status": "ok"}
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/auth/register" in paths
    assert "/wallets/accounts" in paths
    assert "/market/listings" in paths
    assert "/value-engine/snapshots" in paths

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "20260311_0001"


@pytest.mark.anyio
async def test_connected_routes_share_database_bootstrap(app_and_engine) -> None:
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
            snapshot_response = build_value_snapshots(
                ValueSnapshotBatchRequest.model_validate(
                    {
                        "as_of": "2026-03-06T00:00:00Z",
                        "inputs": [
                            {
                                "player_id": "player-1",
                                "player_name": "Ada Forward",
                                "reference_market_value_eur": 70000000,
                                "current_credits": 710.0,
                                "demand_signal": {
                                    "purchases": 4,
                                    "shortlist_adds": 10,
                                    "follows": 25,
                                },
                            }
                        ],
                    }
                )
            )
        finally:
            _close_session(session_generator)

    assert {account.unit.value for account in wallet_accounts} == {"coin", "credit"}
    assert listing_response.seller_user_id == register_response.user.id
    assert len(snapshot_response.snapshots) == 1
    assert snapshot_response.snapshots[0].player_id == "player-1"
    assert snapshot_response.snapshots[0].target_credits > 0
