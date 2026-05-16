from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.security import TokenError, create_access_token, decode_access_token
from app.models.club_profile import ClubProfile
from app.models.auth_session import AuthSession
from app.models.user import KycStatus, User, UserRole


@pytest.fixture(autouse=True)
def _authenticated_competition_routes(app, app_session_factory):
    def _resolve_user(request: Request) -> User:
        authorization = request.headers.get("authorization", "").strip()
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ", maxsplit=1)[1].strip()
        try:
            subject = decode_access_token(token).get("sub")
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if not isinstance(subject, str) or not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is missing a subject.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        with app_session_factory() as session:
            user = session.get(User, subject)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The authenticated user could not be loaded.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user

    def _override_current_user(request: Request) -> User:
        return _resolve_user(request)

    def _override_current_admin(request: Request) -> User:
        user = _resolve_user(request)
        if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access is required for this action.",
            )
        return user

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_current_admin] = _override_current_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def auth_user_factory(app_session_factory):
    from app.models.wallet import LedgerUnit
    from app.wallets.service import WalletService

    def create_user(
        *,
        suffix: str | None = None,
        funded_credit: Decimal | str | None = None,
        funded_coin: Decimal | str | None = None,
        role: UserRole = UserRole.USER,
    ) -> dict[str, str]:
        unique_suffix = suffix or uuid4().hex[:8]
        unique_token = uuid4().hex[:8]
        user_id = str(uuid4())
        session_id = str(uuid4())
        username = f"{unique_suffix}-{unique_token}".replace("-", "_")[:64]
        email = f"{unique_suffix}-{unique_token}@example.com"
        display_name = f"User {unique_suffix}"
        with app_session_factory() as session:
            user = User(
                id=user_id,
                email=email,
                username=username,
                display_name=display_name,
                full_name=display_name,
                phone_number="1234567890",
                password_hash="not-used",
                role=role,
                kyc_status=KycStatus.FULLY_VERIFIED,
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(user)
            session.add(
                AuthSession(
                    id=session_id,
                    user_id=user_id,
                    refresh_token_hash=f"competition-test-refresh-{session_id}",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                    last_used_at=datetime.now(timezone.utc),
                    device_id="competition-tests",
                )
            )
            session.flush()
            wallet_service = WalletService()
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

        access_token = create_access_token(
            user_id,
            claims={"sid": session_id, "role": role.value, "email": email},
        )
        return {
            "email": email,
            "password": "not-used",
            "headers": {"Authorization": f"Bearer {access_token}"},
            "user_id": user_id,
            "username": username,
            "display_name": display_name,
        }

    return create_user


@pytest.fixture
def competition_admin_headers(app_session_factory):
    user_id = str(uuid4())
    session_id = str(uuid4())
    suffix = uuid4().hex[:8]
    email = f"competition-admin-{suffix}@example.com"
    username = f"competition_admin_{suffix}"
    with app_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                username=username,
                display_name="Competition Admin",
                full_name="Competition Admin",
                phone_number="1234567890",
                password_hash="not-used",
                role=UserRole.SUPER_ADMIN,
                kyc_status=KycStatus.FULLY_VERIFIED,
            )
        )
        session.add(
            AuthSession(
                id=session_id,
                user_id=user_id,
                refresh_token_hash=f"competition-test-refresh-{session_id}",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                last_used_at=datetime.now(timezone.utc),
                device_id="competition-tests",
            )
        )
        session.commit()
    access_token = create_access_token(
        user_id,
        claims={"sid": session_id, "role": UserRole.SUPER_ADMIN.value, "email": email},
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def competition_club_factory(app_session_factory):
    def create_club(
        *,
        owner_user_id: str,
        slug: str | None = None,
        name: str | None = None,
    ) -> str:
        suffix = uuid4().hex[:8]
        club_slug = slug or f"competition-club-{suffix}"
        club_name = name or f"Competition Club {suffix}"
        with app_session_factory() as session:
            club = ClubProfile(
                owner_user_id=owner_user_id,
                club_name=club_name,
                short_name=club_name[:20],
                slug=club_slug,
                primary_color="#A6FF1A",
                secondary_color="#0B1210",
                accent_color="#58D5FF",
                country_code="NG",
                region_name="Lagos",
                city_name="Lagos",
            )
            session.add(club)
            session.commit()
            return club.id

    return create_club
