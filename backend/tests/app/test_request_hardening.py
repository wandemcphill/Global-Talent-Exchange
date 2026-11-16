from __future__ import annotations

import asyncio

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
    assert payload["code"] == "validation_error"
    assert "body.note" in payload["message"]
    assert "script_tag" in payload["message"]


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


def test_request_hardening_closes_quietly_when_the_client_disconnects() -> None:
    app = FastAPI()
    app.add_middleware(RequestHardeningMiddleware)

    @app.post("/echo")
    async def echo_request(request: Request) -> dict[str, bool]:
        await request.json()
        return {"ok": True}

    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, str]:
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/echo",
        "raw_path": b"/echo",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    asyncio.run(app(scope, receive, send))
    assert sent[0]["status"] == 499
