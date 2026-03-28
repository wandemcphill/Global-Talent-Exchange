from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.main import create_app


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'api_v1_router.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        startup_thread = getattr(app.state, "deferred_startup_thread", None)
        if startup_thread is not None:
            startup_thread.join(timeout=10)
        yield app, client
    engine.dispose()


def _create_authenticated_user(app) -> tuple[str, str]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email="v1fan@example.com",
            username="v1fan",
            password="SuperSecret1",
            display_name="V1 Fan",
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
        return user.id, token


def test_api_v1_requires_auth_and_wraps_success_envelopes(app_client) -> None:
    app, client = app_client

    unauthorized = client.get("/api/v1/home/dashboard")

    assert unauthorized.status_code == 401
    assert unauthorized.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "unauthorized",
            "message": "Authentication credentials were not provided.",
            "details": None,
        },
    }

    _user_id, token = _create_authenticated_user(app)
    response = client.get(
        "/api/v1/home/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"]["club"]["name"] == "Lagos Titans"
    assert payload["data"]["live_matches"][0]["match_id"] == "m1"


def test_api_v1_http_facade_preserves_mutations_between_requests(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)
    headers = {"Authorization": f"Bearer {token}"}

    bid_response = client.post(
        "/api/v1/market/bid",
        headers=headers,
        json={"listing_id": "l1", "amount": 550000},
    )
    assert bid_response.status_code == 201, bid_response.text
    assert bid_response.json()["data"]["bid"]["amount"] == 550000

    listings_response = client.get(
        "/api/v1/market/listings",
        headers=headers,
        params={"page": 1, "rating_min": 80, "position": "ST"},
    )
    assert listings_response.status_code == 200, listings_response.text
    listings_payload = listings_response.json()["data"]
    assert listings_payload["total"] == 1
    assert listings_payload["listings"][0]["latest_bid"]["amount"] == 550000

    follow_response = client.post("/api/v1/users/scout_42/follow", headers=headers)
    assert follow_response.status_code == 200, follow_response.text
    assert follow_response.json()["data"]["following"] is True

    profile_response = client.get("/api/v1/users/scout_42", headers=headers)
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["data"]["followed_by_current_user"] is True

    claim_response = client.post("/api/v1/tasks/task_daily_login/claim", headers=headers)
    assert claim_response.status_code == 200, claim_response.text
    assert claim_response.json()["data"]["status"] == "claimed"

    tasks_response = client.get("/api/v1/tasks", headers=headers)
    assert tasks_response.status_code == 200, tasks_response.text
    claimed_task = next(item for item in tasks_response.json()["data"]["tasks"] if item["id"] == "task_daily_login")
    assert claimed_task["claimed"] is True

    tournament_response = client.post("/api/v1/tournaments/t1/join", headers=headers)
    assert tournament_response.status_code == 200, tournament_response.text
    assert tournament_response.json()["data"]["participant_count"] == 1

    federation_response = client.post(
        "/api/v1/federations",
        headers=headers,
        json={"name": "Lagos Managers Union", "region": "Nigeria"},
    )
    assert federation_response.status_code == 201, federation_response.text
    federation_id = federation_response.json()["data"]["federation"]["id"]

    vote_response = client.post(
        "/api/v1/federations/vote",
        headers=headers,
        json={"federation_id": federation_id, "proposal_id": "proposal_budget_1", "vote": "yes"},
    )
    assert vote_response.status_code == 200, vote_response.text
    assert vote_response.json()["data"]["vote"]["proposal_id"] == "proposal_budget_1"


def test_api_v1_websockets_emit_match_market_and_notification_events(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)
    headers = {"Authorization": f"Bearer {token}"}

    bid_response = client.post(
        "/api/v1/market/bid",
        headers=headers,
        json={"listing_id": "l1", "amount": 560000},
    )
    assert bid_response.status_code == 201, bid_response.text

    story_response = client.post(
        "/api/v1/stories/generate",
        headers=headers,
        json={"title": "Shock Winner", "story_type": "story_event", "subject_id": "m1"},
    )
    assert story_response.status_code == 201, story_response.text

    with client.websocket_connect(f"/api/v1/ws/match/m1?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "commentary"
        assert event["timestamp"] == 72

    with client.websocket_connect(f"/api/v1/ws/market/l1?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "new_bid"
        assert event["amount"] == 560000

    with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "story_event"
        assert event["title"] == "Shock Winner"
