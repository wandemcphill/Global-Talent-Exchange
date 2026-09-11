from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_session
from app.orders.router import router


def _test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: None
    return TestClient(app)


def test_admin_buyback_routes_are_not_exposed() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = {route.path for route in app.routes}

    assert all("admin-buyback" not in path for path in paths)


def test_player_order_creation_remains_retired() -> None:
    client = _test_client()
    response = client.post(
        "/api/orders",
        json={
            "player_id": "retired-system-b",
            "side": "buy",
            "quantity": 1,
            "max_price": 1,
        },
    )

    assert response.status_code == 410
    assert "/market/buy" in response.json()["detail"]
