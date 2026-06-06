from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.modules import DOMAIN_MODULES

from backend.tests.app._module_registration_contract_data import EXPECTED_REGISTERED_MODULES


def test_real_app_registers_competition_and_identity_modules() -> None:
    registered_modules = {module.name for module in DOMAIN_MODULES}

    assert EXPECTED_REGISTERED_MODULES.issubset(registered_modules)


def test_streamer_tournaments_route_does_not_force_global_lazy_hydration(mounted_app) -> None:
    assert mounted_app.state.modules_hydrated is False

    with TestClient(mounted_app) as client:
        response = client.get(
            "/api/v2/streamer-tournaments",
            headers={"X-API-Version": "2"},
        )

    assert response.status_code == 200
    assert mounted_app.state.modules_hydrated is False


@pytest.mark.parametrize(
    ("path", "headers", "expected_status"),
    (
        ("/api/v2/broadcast/home", {"X-API-Version": "2"}, 200),
        ("/api/v2/match-viewer/nonexistent", {"X-API-Version": "2"}, 404),
    ),
)
def test_live_broadcast_and_match_viewer_routes_do_not_force_global_lazy_hydration(
    mounted_app,
    path: str,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    assert mounted_app.state.modules_hydrated is False

    with TestClient(mounted_app) as client:
        response = client.get(path, headers=headers)

    assert response.status_code == expected_status
    assert mounted_app.state.modules_hydrated is False
