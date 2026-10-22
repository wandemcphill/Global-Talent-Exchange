from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select

from app.main import (
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD,
    create_app,
)
from app.models.club_infra import ClubStadium
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.creator_application import CreatorApplication
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning, CreatorRegen, CreatorSquad
from app.models.user import User
from backend.tests.support.signup_payloads import user_signup_payload


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'creator-router.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client


def _register_creator_applicant(client: TestClient, *, email: str, username: str) -> str:
    # Creator access is applied for after normal GTEX user registration.
    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email=email,
            username=username,
            full_name="Creator Applicant",
            password="SuperSecret1",
            country="US",
        ),
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


def _mark_contacts_verified_for_test(app, *, email: str) -> None:
    """Fixture trusted contact state after the real verifier has run."""
    with app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        now = datetime.now(timezone.utc)
        user.phone_number = "+15555550123"
        user.email_verified_at = now
        user.phone_verified_at = now
        session.commit()


def _create_active_club(app, *, owner_user_id: str, slug: str) -> str:
    with app.state.session_factory() as session:
        club = ClubProfile(
            owner_user_id=owner_user_id,
            club_name=f"{slug} FC",
            club_type=ClubType.COMMUNITY,
            slug=slug,
            primary_color="#0F766E",
            secondary_color="#F8FAFC",
            accent_color="#F59E0B",
        )
        session.add(club)
        session.commit()
        return club.id


def test_owned_club_blocks_creator_promotion_submission(app_client) -> None:
    app, client = app_client
    token = _register_creator_applicant(client, email="active-owner@example.com", username="activeowner")
    _mark_contacts_verified_for_test(app, email="active-owner@example.com")
    with app.state.session_factory() as session:
        owner = session.scalar(select(User).where(User.email == "active-owner@example.com"))
        assert owner is not None
        owner_id = owner.id
    _create_active_club(app, owner_user_id=owner_id, slug="active-owner-club")

    response = client.post(
        "/api/creator/apply",
        headers=_creator_headers(token),
        json={
            "requested_handle": "active.owner.creator",
            "display_name": "Active Owner",
            "platform": "youtube",
            "follower_count": 1000,
            "social_links": ["https://youtube.com/@activeowner"],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "club_ownership_prevents_creator_promotion"


def test_creator_promotion_rechecks_club_ownership_at_approval(app_client) -> None:
    app, client = app_client
    token = _register_creator_applicant(client, email="race-owner@example.com", username="raceowner")
    _mark_contacts_verified_for_test(app, email="race-owner@example.com")
    headers = _creator_headers(token)
    apply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "race.owner.creator",
            "display_name": "Race Owner",
            "platform": "youtube",
            "follower_count": 1000,
            "social_links": ["https://youtube.com/@raceowner"],
        },
    )
    assert apply_response.status_code == 201, apply_response.text
    application_id = apply_response.json()["application_id"]
    with app.state.session_factory() as session:
        owner = session.scalar(select(User).where(User.email == "race-owner@example.com"))
        assert owner is not None
        owner_id = owner.id
    _create_active_club(app, owner_user_id=owner_id, slug="race-owner-club")

    approve_response = client.post(
        f"/api/admin/creator/applications/{application_id}/approve",
        headers=_admin_headers(client),
        json={"reason": "Test the final eligibility recheck."},
    )
    assert approve_response.status_code == 409, approve_response.text
    assert approve_response.json()["detail"] == "club_ownership_prevents_creator_promotion"
    with app.state.session_factory() as session:
        owner = session.scalar(select(User).where(User.email == "race-owner@example.com"))
        assert owner is not None
        assert owner.account_type.value == "user"
        assert session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == owner.id)) is None


def test_sold_club_no_longer_blocks_creator_promotion(app_client) -> None:
    app, client = app_client
    token = _register_creator_applicant(client, email="sold-owner@example.com", username="soldowner")
    _mark_contacts_verified_for_test(app, email="sold-owner@example.com")
    with app.state.session_factory() as session:
        owner = session.scalar(select(User).where(User.email == "sold-owner@example.com"))
        buyer = User(
            email="club-buyer@example.com",
            username="clubbuyer",
            password_hash="test-hash",
            full_name="Club Buyer",
        )
        session.add(buyer)
        session.flush()
        assert owner is not None
        club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Sold Club FC",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="sold-club-fc",
            primary_color="#0F766E",
            secondary_color="#F8FAFC",
            accent_color="#F59E0B",
        )
        session.add(club)
        session.flush()
        # ClubSaleMarketService settles a sale by changing owner_user_id to
        # the buyer. A former owner with no active club is eligible to apply.
        club.owner_user_id = buyer.id
        session.commit()

    response = client.post(
        "/api/creator/apply",
        headers=_creator_headers(token),
        json={
            "requested_handle": "sold.owner.creator",
            "display_name": "Sold Owner",
            "platform": "youtube",
            "follower_count": 1000,
            "social_links": ["https://youtube.com/@soldowner"],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"


def test_creator_application_submission_requires_verification_and_persists_application(app_client) -> None:
    app, client = app_client
    token = _register_creator_applicant(client, email="creator1@example.com", username="creatorone")
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

    # These legacy endpoints must not self-certify a user's own contacts.
    email_response = client.post("/api/creator/verify-email", headers=headers)
    phone_response = client.post("/api/creator/verify-phone", headers=headers)
    assert email_response.status_code == 400, email_response.text
    assert email_response.json()["detail"] == "email_verification_must_use_auth_confirmation"
    assert phone_response.status_code == 400, phone_response.text
    assert phone_response.json()["detail"] == "secure_phone_verification_unavailable"
    with app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "creator1@example.com"))
        assert user is not None
        assert user.email_verified_at is None
        assert user.phone_verified_at is None

    # This direct state setup simulates contacts already verified by a trusted
    # provider; these tests cover application/review lifecycle, not fake OTPs.
    _mark_contacts_verified_for_test(app, email="creator1@example.com")

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
        application = session.scalar(
            select(CreatorApplication).where(CreatorApplication.requested_handle == "creator.one")
        )
        assert application is not None
        assert application.platform == "youtube"
        assert application.email_verified_at is not None
        assert application.phone_verified_at is not None


def test_admin_request_verification_and_reject_flow(app_client) -> None:
    _app, client = app_client
    token = _register_creator_applicant(client, email="creator2@example.com", username="creatortwo")
    headers = _creator_headers(token)
    admin_headers = _admin_headers(client)

    _mark_contacts_verified_for_test(_app, email="creator2@example.com")
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
    token = _register_creator_applicant(client, email="creator3@example.com", username="creatorthree")
    headers = _creator_headers(token)
    admin_headers = _admin_headers(client)

    _mark_contacts_verified_for_test(app, email="creator3@example.com")
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

    # Approval promotes the normal member/club-owner account into the dedicated
    # Creator account type. It is no longer a switchable capability.
    login_response = client.post(
        "/auth/login",
        json={"email": "creator3@example.com", "password": "SuperSecret1"},
    )
    assert login_response.status_code == 200, login_response.text
    issued = login_response.json()
    assert issued["user"]["account_type"] == "creator"
    assert issued["landing_route"] == "/app/hub"
    bootstrap_response = client.get(
        "/api/v2/session/bootstrap",
        headers={
            "X-API-Version": "2",
            "Authorization": f"Bearer {issued['access_token']}",
            "X-User-Id": issued["user"]["id"],
            "X-Session-Id": issued["session_id"],
            "X-Device-Id": "creator-approved-test",
        },
    )
    assert bootstrap_response.status_code == 200, bootstrap_response.text
    bootstrap = bootstrap_response.json()["data"]
    assert bootstrap["account_type"] == "creator"
    assert bootstrap["creator"]["status"] == "active"
    assert "creator" in bootstrap["roles"]
    assert bootstrap["onboarding"]["requires_club"] is False
    assert bootstrap["onboarding"]["suggested_route"] == "/app/hub"

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

    reapply_response = client.post(
        "/api/creator/apply",
        headers=headers,
        json={
            "requested_handle": "creator.three.again",
            "display_name": "Creator Three",
            "platform": "tiktok",
            "follower_count": 1250000,
            "social_links": ["https://tiktok.com/@creatorthree"],
        },
    )
    assert reapply_response.status_code == 409, reapply_response.text
    assert reapply_response.json()["detail"] == "creator_promotion_requires_normal_account"
