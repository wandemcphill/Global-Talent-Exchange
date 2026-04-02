from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.request_security import RequestHardeningMiddleware


def _build_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestHardeningMiddleware)

    @app.post("/echo")
    async def echo_request(request: Request) -> dict[str, object]:
        payload = await request.json()
        return {
            "query": dict(request.query_params),
            "body": payload,
        }

    return TestClient(app)


def test_request_hardening_blocks_injection_payloads() -> None:
    client = _build_client()

    response = client.post(
        "/echo",
        json={"note": "<script>alert('xss')</script>"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["location"] == "body.note"
    assert payload["reason"] == "script_tag"


def test_request_hardening_sanitizes_control_characters_in_query_and_body() -> None:
    client = _build_client()

    response = client.post(
        "/echo?search=ayo%00striker",
        json={"note": "fan\u0000club"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["search"] == "ayostriker"
    assert payload["body"]["note"] == "fanclub"
