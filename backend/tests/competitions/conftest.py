from __future__ import annotations

import pytest

from app.auth.dependencies import get_current_user
from app.models.user import KycStatus, User, UserRole


@pytest.fixture(autouse=True)
def _authenticated_competition_routes(app, app_session_factory):
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

    def _override_current_user() -> User:
        with app_session_factory() as session:
            user = session.get(User, user_id)
            assert user is not None
            return user

    app.dependency_overrides[get_current_user] = _override_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
