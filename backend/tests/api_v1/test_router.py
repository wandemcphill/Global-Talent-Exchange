from __future__ import annotations

import asyncio
from dataclasses import replace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from starlette.datastructures import Headers, QueryParams
from starlette.websockets import WebSocketDisconnect

from app.api_v1.router import stream_match_commentary
from app.live_matches.service import ensure_live_match_hub
from app.live_matches.legacy_runtime_access import issue_legacy_match_runtime_access_token
from app.match_engine.services.match_simulation_service import MatchSimulationService
from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService
from app.main import create_app
from backend.tests.match_engine.helpers import build_request


API_V2_HEADERS = {"X-API-Version": "2"}


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GTEX_ENABLE_LEGACY_MATCH_RUNTIME", "1")
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
            password=TEST_PASSWORD,
            display_name="V1 Fan",
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
        return user.id, token


def _seed_legacy_match_runtime_session(app, user_id: str, *, seed: int) -> tuple[str, str]:
    match_id = f"api-v1-legacy-runtime-{seed}"
    replay_payload = MatchSimulationService().build_replay_payload(
        build_request(seed=seed, match_id=match_id),
    )
    hub = ensure_live_match_hub(app)
    hub.start_stream(match_id, replay_payload, target_runtime_seconds=60.0)
    spectator_session = hub.join_spectate(match_id, user_id)
    access_token, _expires_in = issue_legacy_match_runtime_access_token(
        match_id=match_id,
        spectator_session_id=spectator_session.id,
        viewer_user_id=user_id,
    )
    return match_id, access_token


def test_api_v1_requires_auth_and_wraps_success_envelopes(app_client) -> None:
    app, client = app_client

    unauthorized = client.get("/api/v2/home/dashboard", headers=API_V2_HEADERS)

    assert unauthorized.status_code == 401
    assert unauthorized.json() == {
        "error": True,
        "message": "Authentication credentials were not provided.",
        "code": "unauthorized",
    }

    _user_id, token = _create_authenticated_user(app)
    response = client.get(
        "/api/v2/home/dashboard",
        headers={**API_V2_HEADERS, "Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "error" not in payload
    assert "code" not in payload
    assert payload["data"]["club"]["name"] == "Lagos Titans"
    assert payload["data"]["live_matches"][0]["match_id"] == "m1"


def test_api_v1_protected_environment_does_not_serve_demo_dashboard(app_client) -> None:
    app, client = app_client
    app.state.settings = replace(app.state.settings, app_env="production")
    _user_id, token = _create_authenticated_user(app)

    response = client.get(
        "/api/v2/home/dashboard",
        headers={**API_V2_HEADERS, "Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["club"]["name"] == "V1 Fan"
    assert payload["live_matches"] == []
    assert payload["stories"] == []
    assert payload["transfer_alerts"] == []


def test_api_v1_protected_environment_rejects_demo_mutations(app_client) -> None:
    app, client = app_client
    app.state.settings = replace(app.state.settings, app_env="production")
    _user_id, token = _create_authenticated_user(app)

    response = client.post(
        "/api/v2/market/bid",
        headers={**API_V2_HEADERS, "Authorization": f"Bearer {token}"},
        json={"listing_id": "l1", "amount": 550000},
    )

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["code"] in {"unavailable", "service_unavailable"}


def test_api_v2_club_facade_uses_backend_club_ops_truth_in_production(app_client) -> None:
    app, client = app_client
    app.state.settings = replace(app.state.settings, app_env="production")
    _user_id, token = _create_authenticated_user(app)
    headers = {**API_V2_HEADERS, "Authorization": f"Bearer {token}"}

    finances_response = client.get("/api/v2/clubs/club-api/finances", headers=headers)
    assert finances_response.status_code == 200, finances_response.text
    finances = finances_response.json()["data"]
    assert finances["club_id"] == "club-api"
    assert finances["balance_summary"]["current_balance"] == 15_000
    assert finances["budget"]["available_budget_minor"] == 1_500_000

    squad_response = client.get("/api/v2/clubs/club-api/squad", headers=headers)
    assert squad_response.status_code == 200, squad_response.text
    squad = squad_response.json()["data"]
    assert squad["club_id"] == "club-api"
    assert squad["players"] == []


def test_api_v1_http_facade_preserves_supported_mutations_and_blocks_deprecated_synthetic_routes(
    app_client,
) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)
    headers = {**API_V2_HEADERS, "Authorization": f"Bearer {token}"}

    bid_response = client.post(
        "/api/v2/market/bid",
        headers=headers,
        json={"listing_id": "l1", "amount": 550000},
    )
    assert bid_response.status_code == 201, bid_response.text
    assert bid_response.json()["data"]["bid"]["amount"] == 550000

    listings_response = client.get(
        "/api/v2/market/listings",
        headers=headers,
        params={"page": 1, "rating_min": 80, "position": "ST"},
    )
    assert listings_response.status_code == 200, listings_response.text
    listings_payload = listings_response.json()["data"]
    assert listings_payload["total"] == 1
    assert listings_payload["listings"][0]["latest_bid"]["amount"] == 550000

    follow_response = client.post("/api/v2/users/scout_42/follow", headers=headers)
    assert follow_response.status_code == 410, follow_response.text
    assert follow_response.json()["code"] == "DEPRECATED_ROUTE"

    claim_response = client.post("/api/v2/tasks/task_daily_login/claim", headers=headers)
    assert claim_response.status_code == 410, claim_response.text
    assert claim_response.json()["code"] == "DEPRECATED_ROUTE"

    tasks_response = client.get("/api/v2/tasks", headers=headers)
    assert tasks_response.status_code == 410, tasks_response.text
    assert tasks_response.json()["code"] == "DEPRECATED_ROUTE"

    tournament_response = client.post("/api/v2/tournaments/t1/join", headers=headers)
    assert tournament_response.status_code == 410, tournament_response.text
    assert tournament_response.json()["code"] == "DEPRECATED_ROUTE"

    canonical_federation_response = client.post(
        "/api/v2/federations",
        headers=headers,
        json={"name": "Lagos Managers Union"},
    )
    assert canonical_federation_response.status_code == 201, canonical_federation_response.text
    assert canonical_federation_response.json()["data"]["name"] == "Lagos Managers Union"

    join_federation_response = client.post(
        "/api/v2/federations/federation_africa_managers/join",
        headers=headers,
    )
    assert join_federation_response.status_code == 410, join_federation_response.text
    assert join_federation_response.json()["code"] == "DEPRECATED_ROUTE"

    vote_response = client.post(
        "/api/v2/federations/vote",
        headers=headers,
        json={
            "federation_id": "federation_africa_managers",
            "proposal_id": "proposal_budget_1",
            "vote": "yes",
        },
    )
    assert vote_response.status_code == 410, vote_response.text
    assert vote_response.json()["code"] == "DEPRECATED_ROUTE"


def test_api_v1_websockets_emit_match_market_and_notification_events(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)
    headers = {**API_V2_HEADERS, "Authorization": f"Bearer {token}"}

    bid_response = client.post(
        "/api/v2/market/bid",
        headers=headers,
        json={"listing_id": "l1", "amount": 560000},
    )
    assert bid_response.status_code == 201, bid_response.text

    story_response = client.post(
        "/api/v2/stories/generate",
        headers=headers,
        json={"title": "Shock Winner", "story_type": "story_event", "subject_id": "m1"},
    )
    assert story_response.status_code == 201, story_response.text

    with client.websocket_connect(f"/api/v2/ws/match/m1?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "commentary"
        assert event["timestamp"] == 72

    with client.websocket_connect(f"/api/v2/ws/market/l1?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "new_bid"
        assert event["amount"] == 560000

    with client.websocket_connect(f"/api/v2/ws/notifications?token={token}") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "story_event"
        assert event["title"] == "Shock Winner"


def test_api_v1_match_websocket_supports_legacy_match_runtime_stream(app_client) -> None:
    app, client = app_client
    user_id, _token = _create_authenticated_user(app)
    match_id, legacy_runtime_access_token = _seed_legacy_match_runtime_session(app, user_id, seed=81)

    socket = _RecordingWebSocket(
        app=app,
        query_params={"format": "legacy", "access_token": legacy_runtime_access_token},
    )
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(asyncio.wait_for(stream_match_commentary(socket, match_id), timeout=0.25))

    assert socket.accepted is True
    first_payload = socket.sent_payloads[0]
    assert first_payload["matchId"] == match_id
    assert "players" in first_payload
    assert "ballPosition" in first_payload
    assert "events" in first_payload


def test_api_v1_legacy_match_runtime_survives_http_bootstrap_before_websocket(app_client) -> None:
    app, client = app_client
    user_id, _token = _create_authenticated_user(app)
    match_id, legacy_runtime_access_token = _seed_legacy_match_runtime_session(app, user_id, seed=82)

    live_response = client.get(
        f"/api/v2/match/{match_id}/live",
        headers={**API_V2_HEADERS, "Authorization": f"Bearer {legacy_runtime_access_token}"},
    )
    assert live_response.status_code == 200, live_response.text
    first_frame = live_response.json()["data"]

    socket = _RecordingWebSocket(
        app=app,
        query_params={"format": "legacy", "access_token": legacy_runtime_access_token},
    )
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(asyncio.wait_for(stream_match_commentary(socket, match_id), timeout=0.25))

    assert socket.sent_payloads[0]["matchId"] == match_id
    assert first_frame["matchId"] == match_id


def test_api_v1_legacy_match_runtime_access_route_is_hidden_from_contract(app_client) -> None:
    app, client = app_client
    user_id, token = _create_authenticated_user(app)
    match_id, _legacy_runtime_access_token = _seed_legacy_match_runtime_session(app, user_id, seed=83)

    response = client.post(
        f"/api/matches/{match_id}/legacy-runtime-access",
        headers={**API_V2_HEADERS, "Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 410
    assert response.json()["code"] == "DEPRECATED_ROUTE"


def test_api_v1_match_websocket_rejects_legacy_runtime_without_access_token(app_client) -> None:
    app, client = app_client
    user_id, _token = _create_authenticated_user(app)
    match_id, _legacy_runtime_access_token = _seed_legacy_match_runtime_session(app, user_id, seed=84)

    socket = _RecordingWebSocket(app=app, query_params={"format": "legacy"})
    asyncio.run(stream_match_commentary(socket, match_id))

    assert socket.close_code == 4401
    assert socket.close_reason == "unauthorized"
    assert socket.accepted is False


def test_api_v1_match_websocket_rejects_legacy_runtime_with_invalid_access_token(app_client) -> None:
    app, client = app_client
    user_id, _token = _create_authenticated_user(app)
    match_id, _legacy_runtime_access_token = _seed_legacy_match_runtime_session(app, user_id, seed=85)

    socket = _RecordingWebSocket(
        app=app,
        query_params={"format": "legacy", "access_token": "not-a-real-legacy-runtime-access-token"},
    )
    asyncio.run(stream_match_commentary(socket, match_id))

    assert socket.close_code == 4401
    assert socket.close_reason == "unauthorized"
    assert socket.accepted is False


def test_api_v1_match_websocket_rejects_non_legacy_requests_pre_accept(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)
    unauthorized_socket = _RecordingWebSocket(app=app)
    asyncio.run(stream_match_commentary(unauthorized_socket, "m1"))

    assert unauthorized_socket.close_code == 4401
    assert unauthorized_socket.close_reason == "unauthorized"
    assert unauthorized_socket.accepted is False

    missing_socket = _RecordingWebSocket(app=app, token=token)
    asyncio.run(stream_match_commentary(missing_socket, "missing-match"))

    assert missing_socket.close_code == 4404
    assert missing_socket.close_reason == "not_found"
    assert missing_socket.accepted is False


class _RecordingWebSocket:
    def __init__(self, *, app, token: str | None = None, query_params: dict[str, str] | None = None) -> None:
        self.scope = {"app": app}
        params = query_params if query_params is not None else ({} if token is None else {"token": token})
        self.query_params = QueryParams(params)
        self.headers = Headers({})
        self.accepted = False
        self.close_code: int | None = None
        self.close_reason: str | None = None
        self.sent_payloads: list[dict[str, object]] = []

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.close_code = code
        self.close_reason = reason

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload) -> None:
        self.sent_payloads.append(payload)
        return None

    async def receive_text(self) -> str:
        raise WebSocketDisconnect(code=1000)
