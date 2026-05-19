from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.tests.support.secrets import ALTERNATE_TEST_PASSWORD, TEST_PASSWORD, WRONG_TEST_PASSWORD
from app.access_control.service import AccessControlService
from app.auth.schemas import CurrentUserUpdateRequest
from app.auth.security import decode_access_token, decode_refresh_token, verify_password
from app.auth.service import (
    AuthError,
    AuthService,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.models import AuthSession, Base, ClubProfile, LedgerAccount, LedgerUnit, UserWallet
from app.models.user import PublicAccountType
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
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_register_user_creates_default_accounts(session) -> None:
    user = AuthService().register_user(
        session,
        email="owner@example.com",
        username="owner",
        password=TEST_PASSWORD,
        display_name="Owner",
    )
    session.commit()

    accounts = session.scalars(select(LedgerAccount).where(LedgerAccount.owner_user_id == user.id)).all()
    wallet = session.scalar(select(UserWallet).where(UserWallet.user_id == user.id))
    assert {account.unit for account in accounts} == {LedgerUnit.COIN, LedgerUnit.CREDIT}
    assert wallet is not None
    assert wallet.balance == Decimal("0.0000")
    assert wallet.currency in {"coin", "credit"}
    assert wallet.compliance_status == "verified"
    assert verify_password(TEST_PASSWORD, user.password_hash)


def test_register_user_rejects_duplicate_email(session) -> None:
    service = AuthService()
    service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password=TEST_PASSWORD,
    )
    session.commit()

    with pytest.raises(DuplicateUserError, match="Email address is already registered"):
        service.register_user(
            session,
            email="owner@example.com",
            username="owner-2",
            password=ALTERNATE_TEST_PASSWORD,
        )


def test_authenticate_user_issues_token_and_updates_last_login(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password=TEST_PASSWORD,
    )
    session.commit()

    club = ClubBrandingService(session).create_club_profile(
        owner_user_id=user.id,
        payload=ClubCreateRequest(
            club_name="Refresh Club",
            short_name="RFC",
            slug="refresh-club",
            primary_color="#123456",
            secondary_color="#654321",
            accent_color="#abcdef",
            visibility="public",
        ),
    )
    session.refresh(user)
    authenticated_user = service.authenticate_user(session, email="owner@example.com", password=TEST_PASSWORD)
    issued_session = service.issue_session_tokens(authenticated_user, session=session)
    session.commit()

    claims = decode_access_token(issued_session.access_token)
    refresh_claims = decode_refresh_token(issued_session.refresh_token)
    auth_session = session.get(AuthSession, issued_session.session_id)

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


def test_creator_account_ignores_legacy_club_context(session) -> None:
    service = AuthService()
    creator = service.register_user(
        session,
        email="creator@example.com",
        username="creator",
        password=TEST_PASSWORD,
        display_name="Creator",
        account_type=PublicAccountType.CREATOR,
    )
    ClubBrandingService(session).create_club_profile(
        owner_user_id=creator.id,
        payload=ClubCreateRequest(
            club_name="Legacy Creator FC",
            short_name="LCF",
            slug="legacy-creator-fc",
            primary_color="#123456",
            secondary_color="#654321",
            accent_color="#abcdef",
            visibility="public",
        ),
    )
    session.commit()
    session.refresh(creator)

    access_context = AccessControlService(session).bind_user_access_context(creator)
    bootstrap = service.build_session_bootstrap_state(session, creator)

    assert bootstrap.club is None
    assert access_context.active_organization_id is None
    assert access_context.permissions == ()
    assert access_context.effective_role == creator.role
    with pytest.raises(AuthError, match="football user accounts"):
        service.ensure_user_club_context(session, creator)


def test_issue_access_token_uses_primary_organization_role_for_club_owner(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="club@example.com",
        username="clubowner",
        password=TEST_PASSWORD,
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
        password=TEST_PASSWORD,
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
        password=TEST_PASSWORD,
    )
    session.commit()

    with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
        service.authenticate_user(session, email="owner@example.com", password=WRONG_TEST_PASSWORD)


def test_update_current_user_profile_reads_and_persists_allowed_fields(session) -> None:
    service = AuthService()
    user = service.register_user(
        session,
        email="owner@example.com",
        username="owner",
        password=TEST_PASSWORD,
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
