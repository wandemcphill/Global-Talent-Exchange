"""Self-contained app fixtures for the Phase B security regression suite.

These build the schema straight from the model metadata instead of replaying the
alembic chain, so an authorization regression test fails for authorization
reasons only and never because migration replay is broken.
"""

from __future__ import annotations

import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.tests.support.secrets import TEST_PASSWORD


@pytest.fixture(scope="module")
def security_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-security") / "gte_security.db"
    media_root = tmp_path_factory.mktemp("gte-security-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}
    try:
        os.environ.update(managed_env)
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
def security_app(security_settings):
    from app.db import load_model_modules
    from app.main import create_app
    from app.models import Base

    engine = create_engine(security_settings.database_url, connect_args={"check_same_thread": False})
    load_model_modules()
    Base.metadata.create_all(engine)
    application = create_app(settings=security_settings, engine=engine, run_migration_check=False)
    yield application
    engine.dispose()


@pytest.fixture(scope="module")
def client(security_app):
    with TestClient(security_app) as test_client:
        yield test_client


def _login(client, email: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def member_headers(client, security_app):
    from app.auth.service import AuthService

    suffix = uuid4().hex[:8]
    email = f"security-member-{suffix}@example.com"
    with security_app.state.session_factory() as session:
        AuthService().register_user(
            session,
            email=email,
            username=f"security_member_{suffix}",
            password=TEST_PASSWORD,
            display_name=f"Security Member {suffix}",
        )
        session.commit()
    return _login(client, email)


@pytest.fixture(scope="module")
def admin_headers(client, security_app):
    from app.auth.service import AuthService
    from app.models.user import UserRole

    suffix = uuid4().hex[:8]
    email = f"security-admin-{suffix}@example.com"
    with security_app.state.session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email=email,
            username=f"security_admin_{suffix}",
            password=TEST_PASSWORD,
            display_name=f"Security Admin {suffix}",
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()
    return _login(client, email)
