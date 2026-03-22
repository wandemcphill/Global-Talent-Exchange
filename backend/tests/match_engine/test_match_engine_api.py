from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.match_engine.api.router import router
from backend.tests.match_engine.helpers import build_request


@pytest.fixture()
def client() -> TestClient:
    application = FastAPI()
    application.include_router(router)
    with TestClient(application) as test_client:
        yield test_client


@pytest.mark.parametrize("prefix", ["/match-engine", "/api/match-engine"])
def test_replay_endpoint_returns_authoritative_payload(client: TestClient, prefix: str) -> None:
    response = client.post(f"{prefix}/replay", json=build_request(seed=21).model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "match-001"
    assert body["summary"]["status"] == "completed"
    assert body["timeline"]["events"][0]["event_type"] == "kickoff"
    assert body["replay_log"]


@pytest.mark.parametrize("prefix", ["/match-engine", "/api/match-engine"])
def test_timeline_endpoint_returns_key_moment_sequence(client: TestClient, prefix: str) -> None:
    response = client.post(f"{prefix}/timeline", json=build_request(seed=22).model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "match-001"
    assert body["events"][0]["event_type"] == "kickoff"
    assert any(event["event_type"] == "halftime" for event in body["events"])


@pytest.mark.parametrize("prefix", ["/match-engine", "/api/match-engine"])
def test_summary_endpoint_returns_final_stats(client: TestClient, prefix: str) -> None:
    response = client.post(f"{prefix}/summary", json=build_request(seed=23).model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "match-001"
    assert "home_stats" in body
    assert "away_stats" in body
    assert body["summary_line"]
