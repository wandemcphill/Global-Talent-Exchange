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


def test_admin_buyback_preview_is_retired() -> None:
    client = _test_client()
    response = client.get("/api/orders/order-123/admin-buyback-preview")

    assert response.status_code == 410
    assert response.json()["detail"] == "Admin buyback is retired. GTEX does not buy player shares from users."


def test_admin_buyback_execution_is_retired() -> None:
    client = _test_client()
    response = client.post("/api/orders/order-123/admin-buyback")

    assert response.status_code == 410
    assert response.json()["detail"] == "Admin buyback is retired. GTEX does not buy player shares from users."


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
