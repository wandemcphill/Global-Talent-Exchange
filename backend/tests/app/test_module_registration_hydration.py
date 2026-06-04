from __future__ import annotations

import pytest

from backend.tests.app._module_registration_contract_data import (
    LIVE_BROADCAST_AND_MATCH_VIEWER_HYDRATION_ROUTE_CASES,
)


def test_streamer_tournaments_api_route_does_not_force_global_lazy_hydration(
    mounted_app,
    mounted_app_client,
) -> None:
    assert mounted_app.state.modules_hydrated is False

    response = mounted_app_client.get("/api/streamer-tournaments")

    assert response.status_code == 200
    assert mounted_app.state.modules_hydrated is False


@pytest.mark.parametrize(
    ("path", "headers", "expected_status"),
    LIVE_BROADCAST_AND_MATCH_VIEWER_HYDRATION_ROUTE_CASES,
)
def test_live_broadcast_and_match_viewer_routes_do_not_force_global_lazy_hydration(
    mounted_app,
    mounted_app_client,
    path: str,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    assert mounted_app.state.modules_hydrated is False

    response = mounted_app_client.get(path, headers=headers)

    assert response.status_code == expected_status
    assert mounted_app.state.modules_hydrated is False
