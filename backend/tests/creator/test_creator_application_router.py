from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select

from app.main import (
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD,
    create_app,
)
from app.models.club_infra import ClubStadium
from app.models.creator_application import CreatorApplication
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning, CreatorRegen, CreatorSquad


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'creator-router.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client


def _register_creator_user(client: TestClient, *, email: str, username: str) -> str:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "SuperSecret1",
            "full_name": "Creator User",
            "phone_number": "1234567890",
            "is_over_18": True,
            "region_code": "US",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": INITIAL_ADMIN_EMAIL, "password": INITIAL_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _creator_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_creator_application_submission_requires_verification_and_persists_application(app_client) -> None:
    app, client = app_client
    token = _register_creator_user(client, email="creator1@example.com", username="creatorone")
    headers = _creator_headers(token)

    apply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "creator.one",
            "display_name": "Creator One",
            "platform": "youtube",
            "follower_count": 250000,
            "social_links": ["https://youtube.com/@creatorone"],
        },
    )
    assert apply_response.status_code == 400
    assert apply_response.json()["detail"] == "email_verification_required"

    email_response = client.post("/api/creator/verify-email", headers=headers)
    phone_response = client.post("/api/creator/verify-phone", headers=headers)
    assert email_response.status_code == 200, email_response.text
    assert phone_response.status_code == 200, phone_response.text

    apply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "creator.one",
            "display_name": "Creator One",
            "platform": "youtube",
            "follower_count": 250000,
            "social_links": ["https://youtube.com/@creatorone"],
        },
    )
    assert apply_response.status_code == 201, apply_response.text
    assert apply_response.json()["status"] == "pending"
    assert apply_response.json()["requested_handle"] == "creator.one"

    with app.state.session_factory() as session:
        application = session.scalar(select(CreatorApplication).where(CreatorApplication.requested_handle == "creator.one"))
        assert application is not None
        assert application.platform == "youtube"
        assert application.email_verified_at is not None
        assert application.phone_verified_at is not None


def test_admin_request_verification_and_reject_flow(app_client) -> None:
    _app, client = app_client
    token = _register_creator_user(client, email="creator2@example.com", username="creatortwo")
    headers = _creator_headers(token)
    admin_headers = _admin_headers(client)

    assert client.post("/api/creator/verify-email", headers=headers).status_code == 200
    assert client.post("/api/creator/verify-phone", headers=headers).status_code == 200
    apply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "creator.two",
            "display_name": "Creator Two",
            "platform": "twitch",
            "follower_count": 54000,
            "social_links": ["https://twitch.tv/creatortwo"],
        },
    )
    application_id = apply_response.json()["application_id"]

    review_response = client.post(
        f"/api/admin/creator/applications/{application_id}/request-verification",
        headers=admin_headers,
        json={"reason": "Need stronger proof of channel ownership."},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["status"] == "verification_requested"

    reject_response = client.post(
        f"/api/admin/creator/applications/{application_id}/reject",
        headers=admin_headers,
        json={"reason": "Verification evidence was not supplied."},
    )
    assert reject_response.status_code == 200, reject_response.text
    assert reject_response.json()["status"] == "rejected"


def test_admin_approval_provisions_creator_assets(app_client) -> None:
    app, client = app_client
    token = _register_creator_user(client, email="creator3@example.com", username="creatorthree")
    headers = _creator_headers(token)
    admin_headers = _admin_headers(client)

    assert client.post("/api/creator/verify-email", headers=headers).status_code == 200
    assert client.post("/api/creator/verify-phone", headers=headers).status_code == 200
    apply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "creator.three",
            "display_name": "Creator Three",
            "platform": "tiktok",
            "follower_count": 1250000,
            "social_links": ["https://tiktok.com/@creatorthree"],
        },
    )
    assert apply_response.status_code == 201, apply_response.text
    application_id = apply_response.json()["application_id"]

    approve_response = client.post(
        f"/api/admin/creator/applications/{application_id}/approve",
        headers=admin_headers,
        json={"reason": "Creator approved for provisioning."},
    )
    assert approve_response.status_code == 200, approve_response.text
    body = approve_response.json()
    assert body["status"] == "approved"
    assert body["provisioning"] is not None

    with app.state.session_factory() as session:
        creator_profile = session.scalar(select(CreatorProfile).where(CreatorProfile.handle == "creator.three"))
        assert creator_profile is not None
        assert creator_profile.tier == "elite"

        provisioning = session.scalar(
            select(CreatorClubProvisioning).where(CreatorClubProvisioning.application_id == application_id)
        )
        assert provisioning is not None

        stadium = session.get(ClubStadium, provisioning.stadium_id)
        squad = session.get(CreatorSquad, provisioning.creator_squad_id)
        creator_regen = session.get(CreatorRegen, provisioning.creator_regen_id)

        assert stadium is not None
        assert squad is not None
        assert creator_regen is not None
        assert len(squad.first_team_json) == 25
        assert len(squad.academy_json) == 30
        assert creator_regen.club_id == provisioning.club_id
