from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.schemas import CurrentUserUpdateRequest
from app.auth.security import decode_access_token, decode_refresh_token, verify_password
from app.auth.service import (
    AuthService,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.models import AuthSession, Base, ClubProfile, LedgerAccount, LedgerUnit
from app.schemas.club_requests import ClubCreateRequest
from app.services.club_branding_service import ClubBrandingService


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
    issued_session = service.issue_session_tokens(authenticated_user, session=session)
    session.commit()

    claims = decode_access_token(issued_session.access_token)
    refresh_claims = decode_refresh_token(issued_session.refresh_token)
    auth_session = session.get(AuthSession, issued_session.session_id)
    club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == user.id))

    assert claims["sub"] == user.id
    assert claims["email"] == user.email
    assert claims["org_id"] == club.id
    assert claims["club_id"] == club.id
    assert refresh_claims["sid"] == issued_session.session_id
    assert issued_session.expires_in == 900
    assert issued_session.refresh_expires_in == 2592000
    assert auth_session is not None
    assert auth_session.user_id == user.id
    assert authenticated_user.last_login_at is not None


def test_issue_access_token_uses_primary_organization_role_for_club_owner(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="club@example.com",
        username="clubowner",
        password="SuperSecret1",
        display_name="Club Owner",
    )
    session.commit()

    club = ClubBrandingService(session).create_club_profile(
        owner_user_id=user.id,
        payload=ClubCreateRequest(
            club_name="Access FC",
            short_name="AFC",
            slug="access-fc",
            primary_color="#123456",
            secondary_color="#654321",
            accent_color="#abcdef",
            visibility="public",
        ),
    )
    session.refresh(user)

    token, _ = service.issue_access_token(user, session=session)
    claims = decode_access_token(token)

    assert claims["role"] == "club"
    assert claims["org_id"] == club.id


def test_refresh_session_rotates_refresh_token_and_logout_revokes_session(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="refresh@example.com",
        username="refresh-owner",
        password="SuperSecret1",
        display_name="Refresh Owner",
    )
    session.commit()

    issued = service.issue_session_tokens(user, session=session)
    session.commit()

    refreshed_user, refreshed = service.refresh_session_tokens(
        session,
        refresh_token=issued.refresh_token,
    )
    session.commit()

    assert refreshed_user.id == user.id
    assert refreshed.session_id == issued.session_id
    assert refreshed.refresh_token != issued.refresh_token

    service.revoke_session(session, session_id=issued.session_id, user_id=user.id)
    session.commit()

    with pytest.raises(InvalidSessionError):
        service.refresh_session_tokens(session, refresh_token=refreshed.refresh_token)


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
