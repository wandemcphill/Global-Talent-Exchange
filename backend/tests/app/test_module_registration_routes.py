from __future__ import annotations

import pytest

from backend.tests.app._module_registration_contract_data import (
    CREATOR_AND_MEDIA_ROUTE_CASES,
    DAILY_CHALLENGES_AND_STREAMER_ROUTE_CASES,
    MODERATION_ROUTE_CASES,
    MOUNTED_MODULE_ROUTE_CASES,
    REWARD_AND_INTEGRITY_ROUTE_CASES,
)
from backend.tests.app._module_registration_contract_support import expected_contract_status, request_route


@pytest.mark.parametrize(
    ("method", "path", "json_body", "params", "expected_status"),
    MOUNTED_MODULE_ROUTE_CASES,
    ids=[f"{method} {path}" for method, path, _, _, _ in MOUNTED_MODULE_ROUTE_CASES],
)
def test_mounted_module_routes_resolve_on_the_real_app(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    params: dict[str, object] | None,
    expected_status: int,
) -> None:
    response = request_route(
        mounted_app_client,
        method,
        path,
        json_body=json_body,
        params=params,
        expected_status=expected_status,
    )
    assert response.status_code == expected_contract_status(path, expected_status, params=params)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "expected_status"),
    REWARD_AND_INTEGRITY_ROUTE_CASES,
    ids=[f"{method} {path}" for method, path, _, _ in REWARD_AND_INTEGRITY_ROUTE_CASES],
)
def test_reward_and_integrity_api_only_routes_resolve_on_the_real_app(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    expected_status: int,
) -> None:
    response = request_route(
        mounted_app_client,
        method,
        path,
        json_body=json_body,
        expected_status=expected_status,
    )
    assert response.status_code == expected_contract_status(path, expected_status)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "expected_status"),
    DAILY_CHALLENGES_AND_STREAMER_ROUTE_CASES,
    ids=[f"{method} {path}" for method, path, _, _ in DAILY_CHALLENGES_AND_STREAMER_ROUTE_CASES],
)
def test_daily_challenges_and_streamer_tournaments_api_only_routes_resolve_on_the_real_app(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    expected_status: int,
) -> None:
    response = request_route(
        mounted_app_client,
        method,
        path,
        json_body=json_body,
        expected_status=expected_status,
    )
    assert response.status_code == expected_contract_status(path, expected_status)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "expected_status"),
    MODERATION_ROUTE_CASES,
    ids=[f"{method} {path}" for method, path, _, _ in MODERATION_ROUTE_CASES],
)
def test_moderation_api_only_routes_resolve_on_the_real_app(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    expected_status: int,
) -> None:
    response = request_route(
        mounted_app_client,
        method,
        path,
        json_body=json_body,
        expected_status=expected_status,
    )
    assert response.status_code == expected_contract_status(path, expected_status)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "expected_status"),
    CREATOR_AND_MEDIA_ROUTE_CASES,
    ids=[f"{method} {path}" for method, path, _, _ in CREATOR_AND_MEDIA_ROUTE_CASES],
)
def test_creator_and_media_contract_routes_resolve_on_the_real_app(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    expected_status: int,
) -> None:
    response = request_route(
        mounted_app_client,
        method,
        path,
        json_body=json_body,
        expected_status=expected_status,
    )
    assert response.status_code == expected_contract_status(path, expected_status)
