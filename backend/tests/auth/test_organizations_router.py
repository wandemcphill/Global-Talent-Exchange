from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.main import create_app
from app.models.user import UserRole


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'organizations_router.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client


def _create_authenticated_user(app, *, email: str, username: str, role: UserRole = UserRole.USER) -> tuple[str, str]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password="SuperSecret1",
            display_name=username,
            role=role,
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
        return user.id, token


def test_agency_creation_exposes_membership_context(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app, email="agent@example.com", username="agent")

    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Prime Agency", "organization_type": "agency"},
    )

    assert create_response.status_code == 201, create_response.text
    payload = create_response.json()
    assert payload["organization"]["organization_type"] == "agency"
    assert payload["membership"]["role"] == "agent"
    assert payload["membership"]["organization_id"] == payload["organization"]["id"]

    memberships_response = client.get(
        "/api/organizations/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert memberships_response.status_code == 200
    assert memberships_response.json()[0]["organization_name"] == "Prime Agency"


def test_admin_can_invite_user_and_acceptance_is_audited(app_client) -> None:
    app, client = app_client
    _admin_id, admin_token = _create_authenticated_user(
        app,
        email="admin@example.com",
        username="admin",
        role=UserRole.ADMIN,
    )
    _owner_id, owner_token = _create_authenticated_user(app, email="owner@example.com", username="owner")
    _invitee_id, invitee_token = _create_authenticated_user(app, email="invitee@example.com", username="invitee")

    organization_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "West Coast Agency", "organization_type": "agency"},
    )
    assert organization_response.status_code == 201, organization_response.text
    organization_id = organization_response.json()["organization"]["id"]

    invite_response = client.post(
        f"/api/organizations/{organization_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "invitee@example.com", "role": "agent"},
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_code = invite_response.json()["invite_code"]

    accept_response = client.post(
        "/api/organizations/invites/accept",
        headers={"Authorization": f"Bearer {invitee_token}"},
        json={"invite_code": invite_code},
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["role"] == "agent"
    assert accept_response.json()["organization_id"] == organization_id

    audit_response = client.get(
        f"/api/organizations/{organization_id}/audit-log",
        headers={"Authorization": f"Bearer {invitee_token}"},
    )

    assert audit_response.status_code == 200
    actions = [item["action"] for item in audit_response.json()]
    assert "organization.invite_issued" in actions
    assert "organization.invite_accepted" in actions
