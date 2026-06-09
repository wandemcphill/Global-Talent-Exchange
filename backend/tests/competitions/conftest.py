from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import Request
from pytest import FixtureRequest
from sqlalchemy import create_engine

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.security import TokenError, create_access_token, decode_access_token
from app.auth.dependencies import get_current_user
from app.core.database import load_model_modules
from app.main import create_app
from app.models.base import Base
from app.models.user import KycStatus, User, UserRole


@pytest.fixture(scope="module")
def app(test_settings):
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    load_model_modules()
    Base.metadata.create_all(engine)
    application = create_app(settings=test_settings, engine=engine, run_migration_check=False)
    yield application
    engine.dispose()


@pytest.fixture(autouse=True)
def _authenticated_competition_routes(request: FixtureRequest):
    if "app" not in request.fixturenames and "client" not in request.fixturenames:
        yield
        return

    app = request.getfixturevalue("app")
    app_session_factory = request.getfixturevalue("app_session_factory")
    user_id = "competition-test-user"

    with app_session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            session.add(
                User(
                    id=user_id,
                    email="competition-tests@example.com",
                    username="competition-tests",
                    display_name="Competition Tests",
                    password_hash="not-used",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                )
            )
            session.commit()

    def _override_current_user(request: Request) -> User:
        resolved_user_id = user_id
        authorization = request.headers.get("authorization", "").strip()
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", maxsplit=1)[1].strip()
            try:
                subject = decode_access_token(token).get("sub")
                if isinstance(subject, str) and subject:
                    resolved_user_id = subject
            except TokenError:
                resolved_user_id = user_id

        with app_session_factory() as session:
            user = session.get(User, resolved_user_id)
            assert user is not None
            return user

    app.dependency_overrides[get_current_user] = _override_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _authorization_headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture
def competition_admin_headers(client, app_session_factory):
    suffix = f"competition-admin-{uuid4().hex[:8]}"
    email = f"{suffix}@example.com"
    username = suffix.replace("-", "_")

    from app.admin_godmode.service import AdminGodModeService
    from app.auth.service import AuthService
    from app.wallets.service import WalletService

    with app_session_factory() as session:
        admin = AuthService().ensure_admin_user(
            session,
            email=email,
            username=username,
            password=TEST_PASSWORD,
            display_name=f"Scoped {suffix}",
            role=UserRole.ADMIN,
        )
        admin.kyc_status = KycStatus.FULLY_VERIFIED
        AdminGodModeService(wallet_service=WalletService()).upsert_admin_assignment(
            client.app,
            session,
            admin=admin,
            role_name=None,
            permissions=["manage_competitions"],
            is_enabled=True,
        )
        session.commit()
        return _authorization_headers(admin.id)


@pytest.fixture
def auth_user_factory(app_session_factory):
    def create_user(
        *,
        suffix: str | None = None,
        funded_credit: Decimal | str | None = None,
        funded_coin: Decimal | str | None = None,
    ) -> dict[str, str]:
        unique_suffix = suffix or uuid4().hex[:8]
        email = f"{unique_suffix}@example.com"
        username = unique_suffix.replace("-", "_")
        display_name = f"User {unique_suffix}"

        from app.auth.service import AuthService
        from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
        from app.models.wallet import LedgerUnit
        from app.wallets.service import WalletService

        wallet_service = WalletService()
        with app_session_factory() as session:
            user = AuthService(wallet_service=wallet_service).register_user(
                session,
                email=email,
                username=username,
                password=TEST_PASSWORD,
                full_name=display_name,
                display_name=display_name,
                role=UserRole.USER,
            )
            user.kyc_status = KycStatus.FULLY_VERIFIED

            club_name = f"{display_name} FC"
            club = ClubProfile(
                owner_user_id=user.id,
                club_name=club_name,
                slug=f"{username}-fc",
                club_type=ClubType.COMMUNITY,
                lifecycle_status=ClubLifecycleStatus.ACTIVE,
                primary_color="#0f172a",
                secondary_color="#e2e8f0",
                accent_color="#22c55e",
            )
            session.add(club)
            session.flush()
            user_id = user.id

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
            "password": TEST_PASSWORD,
            "headers": _authorization_headers(user_id),
            "user_id": user_id,
            "username": username,
            "display_name": display_name,
            "club_name": club_name,
        }

    return create_user
