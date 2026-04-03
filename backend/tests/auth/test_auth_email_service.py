from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.tests.support.secrets import RECOVERY_TEST_PASSWORD, TEST_PASSWORD
from app.auth.service import AuthService, InvalidCredentialsError
from app.core.database import ensure_database_schema_current


@pytest.fixture(scope="module")
def session_factory(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("auth-email-service") / "auth-email-service.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield SessionLocal
    engine.dispose()


@pytest.fixture()
def session(session_factory):
    SessionLocal = session_factory
    with SessionLocal() as db_session:
        yield db_session


def test_prepare_signup_confirmation_and_confirm_email(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="fan.confirm@example.com",
        username="fanconfirm",
        password=TEST_PASSWORD,
        full_name="Fan User",
        region_code="NG",
    )
    confirmation_code = service.prepare_signup_confirmation(session, user=user)
    session.commit()

    confirmed_user = service.confirm_email_address(session, code=confirmation_code)
    session.commit()

    assert confirmed_user.email_verified_at is not None


def test_prepare_account_recovery_and_reset_password(session) -> None:
    service = AuthService()
    service.register_user(
        session,
        email="fan.recover@example.com",
        username="fanrecover",
        password=TEST_PASSWORD,
        full_name="Fan User",
        region_code="NG",
    )
    session.commit()

    user, recovery_code = service.prepare_account_recovery(session, email="fan.recover@example.com")
    assert user is not None
    assert recovery_code is not None

    service.reset_password_with_recovery(session, code=recovery_code, new_password=RECOVERY_TEST_PASSWORD)
    session.commit()

    authenticated_user = service.authenticate_user(
        session,
        email="fan.recover@example.com",
        password=RECOVERY_TEST_PASSWORD,
    )

    assert authenticated_user.email == "fan.recover@example.com"
    with pytest.raises(InvalidCredentialsError):
        service.authenticate_user(session, email="fan.recover@example.com", password=TEST_PASSWORD)
