from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.schemas import CurrentUserUpdateRequest
from app.auth.security import decode_access_token, verify_password
from app.auth.service import AuthService, DuplicateUserError, InvalidCredentialsError
from app.models import Base, LedgerAccount, LedgerUnit


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(2048)"))
        connection.execute(text("ALTER TABLE users ADD COLUMN favourite_club VARCHAR(160)"))
        connection.execute(text("ALTER TABLE users ADD COLUMN nationality VARCHAR(120)"))
        connection.execute(text("ALTER TABLE users ADD COLUMN preferred_position VARCHAR(120)"))
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_register_user_creates_default_accounts(session) -> None:
    user = AuthService().register_user(
        session,
        email="owner@example.com",
        username="owner",
        password="SuperSecret1",
        display_name="Owner",
    )
    session.commit()

    accounts = session.scalars(select(LedgerAccount).where(LedgerAccount.owner_user_id == user.id)).all()
    assert {account.unit for account in accounts} == {LedgerUnit.COIN, LedgerUnit.CREDIT}
    assert verify_password("SuperSecret1", user.password_hash)


def test_register_user_rejects_duplicate_email(session) -> None:
    service = AuthService()
    service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password="SuperSecret1",
    )
    session.commit()

    with pytest.raises(DuplicateUserError, match="Email address is already registered"):
        service.register_user(
            session,
            email="owner@example.com",
            username="owner-2",
            password="AnotherSecret1",
        )


def test_authenticate_user_issues_token_and_updates_last_login(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password="SuperSecret1",
    )
    session.commit()

    authenticated_user = service.authenticate_user(session, email="owner@example.com", password="SuperSecret1")
    token, expires_in = service.issue_access_token(authenticated_user)
    session.commit()

    claims = decode_access_token(token)
    assert claims["sub"] == user.id
    assert claims["email"] == user.email
    assert expires_in == 3600
    assert authenticated_user.last_login_at is not None


def test_authenticate_user_rejects_invalid_password(session) -> None:
    service = AuthService()
    service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password="SuperSecret1",
    )
    session.commit()

    with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
        service.authenticate_user(session, email="owner@example.com", password="WrongPassword1")


def test_update_current_user_profile_reads_and_persists_allowed_fields(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password="SuperSecret1",
        display_name="Owner",
    )
    session.commit()
    session.refresh(user)

    profile = service.update_current_user_profile(
        session,
        user=user,
        payload=CurrentUserUpdateRequest(
            display_name="Updated Owner",
            avatar_url="https://cdn.example.com/owner.png",
            favourite_club="Barcelona",
            nationality="Spain",
            preferred_position="Midfielder",
        ),
    )
    session.commit()

    assert profile.display_name == "Updated Owner"
    assert profile.avatar_url == "https://cdn.example.com/owner.png"
    assert profile.favourite_club == "Barcelona"
    assert profile.nationality == "Spain"
    assert profile.preferred_position == "Midfielder"
