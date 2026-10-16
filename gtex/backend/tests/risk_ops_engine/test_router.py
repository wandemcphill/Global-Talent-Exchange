from __future__ import annotations

from starlette.requests import Request

from app.risk_ops_engine.router import _client_ip, admin_router, router


def test_ingest_signal_evaluate_and_release_action(client) -> None:
    signal_response = client.post(
        "/risk-ops/me/signals",
        headers={"x-device-id": "client-device-1"},
        json={
            "signal_type": "transaction_pattern",
            "signal_key": "fake_deposit",
            "metadata_json": {"fake_deposit": True},
        },
    )
    assert signal_response.status_code == 200
    assert signal_response.json()["user_id"] == "user-alpha"

    evaluate_response = client.post("/admin/risk-ops/evaluate", json={"user_id": "user-alpha"})
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["users_flagged"] == 1

    restrictions_response = client.get("/risk-ops/me/restrictions")
    assert restrictions_response.status_code == 200
    restrictions_payload = restrictions_response.json()
    assert restrictions_payload["wallet_frozen"] is True
    assert restrictions_payload["withdrawals_blocked"] is True

    actions_response = client.get("/admin/risk-ops/actions", params={"user_id": "user-alpha", "status": "active"})
    assert actions_response.status_code == 200
    action_id = actions_response.json()[0]["id"]

    release_response = client.post(
        f"/admin/risk-ops/actions/{action_id}/release",
        json={"release_note": "False positive after review."},
    )
    assert release_response.status_code == 200
    assert release_response.json()["status"] == "released"


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/risk-ops/me/overview",
        "headers": [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()],
    }
    return Request(scope)


def test_risk_ops_router_surface_and_client_ip_helper() -> None:
    user_paths = {route.path for route in router.routes}
    admin_paths = {route.path for route in admin_router.routes}

    assert "/risk-ops/me/overview" in user_paths
    assert "/risk-ops/me/restrictions" in user_paths
    assert "/risk-ops/me/signals" in user_paths
    assert "/admin/risk-ops/overview" in admin_paths
    assert "/admin/risk-ops/signals" in admin_paths
    assert "/admin/risk-ops/actions" in admin_paths
    assert "/admin/risk-ops/evaluate" in admin_paths

    forwarded_request = _request_with_headers(
        {"x-forwarded-for": "198.51.100.10, 203.0.113.10"},
    )
    cf_request = _request_with_headers({"cf-connecting-ip": "203.0.113.55"})
    empty_request = _request_with_headers({})

    assert _client_ip(forwarded_request) == "198.51.100.10"
    assert _client_ip(cf_request) == "203.0.113.55"
    assert _client_ip(empty_request) is None
