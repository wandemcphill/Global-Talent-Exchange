from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.tests.support.secrets import (
    BOOTSTRAP_TEST_ADMIN_PASSWORD,
    MEDIA_SIGNING_TEST_SECRET,
    TEST_AUTH_SECRET,
    TEST_PASSWORD,
)
from backend.tests.support.signup_payloads import user_signup_payload

SMOKE_DEMO_PLAYER_COUNT = 12
DEFAULT_TEST_DATABASE_URL = (
    f"sqlite+pysqlite:///{(Path(__file__).resolve().parents[2] / '.tmp_pytest_default.db').as_posix()}"
)

os.environ.setdefault("GTE_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
os.environ.setdefault("GTE_AUTH_SECRET", TEST_AUTH_SECRET)
os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", MEDIA_SIGNING_TEST_SECRET)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_ENABLED", "1")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_EMAIL", "admin@test.gtex.local")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_PASSWORD", BOOTSTRAP_TEST_ADMIN_PASSWORD)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_USERNAME", "gtex_test_admin")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME", "GTEX Test Admin")
os.environ.setdefault("GTE_DEFERRED_STARTUP_ENABLED", "0")
os.environ.setdefault("GTE_COMPETITIVE_INTEGRITY_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_FEDERATION_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_HISTORY_ENGAGEMENT_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_OUTBOX_RELAY_ENABLED", "0")
os.environ.setdefault("GTE_PORTRAIT_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_PROJECTION_WORKERS_ENABLED", "0")
os.environ.setdefault("GTE_REGEN_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_REAL_WORLD_SYNC_ENABLED", "0")
os.environ.setdefault("GTE_RUN_STARTUP_SEEDING", "0")
os.environ.setdefault("GTE_STARTUP_PROFILE", "test")
os.environ.setdefault("GTE_TASK_QUEUE_ENABLED", "0")
os.environ.setdefault("GTE_TEST_AUTH_FIXTURE_MODE", "1")
os.environ.setdefault("GTE_VIRAL_RANKING_WORKER_ENABLED", "0")


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}

    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield load_settings()
    finally:
        reset_settings_cache()
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_settings_cache()


@pytest.fixture(scope="module")
def app(test_settings):
    from app.main import create_app

    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(settings=test_settings, engine=engine, run_migration_check=True)
    yield application
    engine.dispose()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def app_session_factory(app, client):
    return app.state.session_factory


@pytest.fixture(scope="module")
def demo_seed(app, client):
    from app.ingestion.demo_bootstrap import DemoBootstrapService

    service = DemoBootstrapService(
        session_factory=app.state.session_factory,
        settings=app.state.settings,
        event_publisher=app.state.event_publisher,
    )
    return service.seed(player_target_count=SMOKE_DEMO_PLAYER_COUNT, batch_size=6)


@pytest.fixture(scope="module")
def demo_user_credentials(demo_seed):
    primary_user = demo_seed.demo_users[0]
    return {
        "email": primary_user.email,
        "password": primary_user.password,
    }


@pytest.fixture(scope="module")
def demo_auth_headers(client, demo_seed, demo_user_credentials):
    response = client.post(
        "/auth/login",
        json={
            "email": demo_user_credentials["email"],
            "password": demo_user_credentials["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bootstrap_admin_headers(client, app_session_factory):
    from app.auth.service import AuthService
    from app.models.user import UserRole

    with app_session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email=os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"],
            password=os.environ["GTE_BOOTSTRAP_ADMIN_PASSWORD"],
            username=os.environ["GTE_BOOTSTRAP_ADMIN_USERNAME"],
            display_name=os.environ["GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME"],
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"],
            "password": os.environ["GTE_BOOTSTRAP_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def competition_admin_headers(client, bootstrap_admin_headers, app_session_factory):
    del bootstrap_admin_headers
    suffix = f"competition-admin-{uuid4().hex[:8]}"
    password = TEST_PASSWORD
    email = f"{suffix}@example.com"
    username = suffix.replace("-", "_")

    from app.admin_godmode.service import AdminGodModeService
    from app.auth.service import AuthService
    from app.models.user import UserRole
    from app.wallets.service import WalletService

    with app_session_factory() as session:
        admin = AuthService().ensure_admin_user(
            session,
            email=email,
            username=username,
            password=password,
            display_name=f"Scoped {suffix}",
            role=UserRole.ADMIN,
        )
        AdminGodModeService(wallet_service=WalletService()).upsert_admin_assignment(
            client.app,
            session,
            admin=admin,
            role_name=None,
            permissions=["manage_competitions"],
            is_enabled=True,
        )
        session.commit()

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_user_factory(client, app_session_factory):
    def create_user(
        *,
        suffix: str | None = None,
        funded_credit: Decimal | str | None = None,
        funded_coin: Decimal | str | None = None,
    ) -> dict[str, str]:
        unique_suffix = suffix or uuid4().hex[:8]
        email = f"{unique_suffix}@example.com"
        username = unique_suffix.replace("-", "_")
        password = TEST_PASSWORD
        response = client.post(
            "/auth/signup/user",
            json=user_signup_payload(
                email=email,
                username=username,
                password=password,
                full_name=f"User {unique_suffix}",
            ),
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        user_id = payload["user"]["id"]

        if funded_credit is not None or funded_coin is not None:
            from app.models.user import User
            from app.models.wallet import LedgerUnit
            from app.wallets.service import WalletService

            wallet_service = WalletService()
            with app_session_factory() as session:
                user = session.get(User, user_id)
                assert user is not None
                if funded_credit is not None:
                    wallet_service.credit_trade_proceeds(
                        session,
                        user=user,
                        amount=Decimal(str(funded_credit)),
                        reference=f"seed:credit:{user_id}",
                        description="Competition test credit funding",
                        external_reference=f"seed:credit:{user_id}",
                        unit=LedgerUnit.CREDIT,
                    )
                if funded_coin is not None:
                    wallet_service.credit_trade_proceeds(
                        session,
                        user=user,
                        amount=Decimal(str(funded_coin)),
                        reference=f"seed:coin:{user_id}",
                        description="Competition test coin funding",
                        external_reference=f"seed:coin:{user_id}",
                        unit=LedgerUnit.COIN,
                    )
                session.commit()

        return {
            "email": email,
            "password": password,
            "headers": {"Authorization": f"Bearer {payload['access_token']}"},
            "user_id": user_id,
            "username": payload["user"]["username"],
            "display_name": payload["user"].get("display_name") or payload["user"]["username"],
        }

    return create_user
