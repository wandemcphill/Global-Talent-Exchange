from __future__ import annotations

import pytest
from fastapi import Request
from pytest import FixtureRequest

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.models.user import KycStatus, User, UserRole


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
