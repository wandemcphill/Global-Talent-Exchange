from __future__ import annotations

import pytest

from backend.tests.app._module_registration_contract_data import (
    API_ONLY_FAMILY_OPENAPI_ABSENT_PATHS,
    API_ONLY_FAMILY_OPENAPI_PRESENT_PATHS,
    CORE_OPENAPI_PRESENT_PATHS,
    CREATOR_MEDIA_OPENAPI_ABSENT_PATHS,
    CREATOR_MEDIA_OPENAPI_PRESENT_PATHS,
    EXPECTED_REGISTERED_MODULES,
    MATCH_ENGINE_OPENAPI_ABSENT_PATHS,
    MATCH_ENGINE_OPENAPI_PRESENT_PATHS,
    NAMESPACED_OPENAPI_ABSENT_PATHS,
    NAMESPACED_OPENAPI_PRESENT_PATHS,
    PUBLIC_MISC_OPENAPI_ABSENT_PATHS,
    PUBLIC_MISC_OPENAPI_PRESENT_PATHS,
)


def test_real_app_registers_competition_and_identity_modules(
    mounted_app_contract_snapshot,
) -> None:
    registered_modules = mounted_app_contract_snapshot["registered_modules"]
    assert EXPECTED_REGISTERED_MODULES.issubset(registered_modules)


@pytest.mark.parametrize("path", MATCH_ENGINE_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_match_engine_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", MATCH_ENGINE_OPENAPI_ABSENT_PATHS)
def test_real_app_openapi_hides_legacy_match_engine_render_sync_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path not in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", CORE_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_core_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", CREATOR_MEDIA_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_creator_and_media_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", CREATOR_MEDIA_OPENAPI_ABSENT_PATHS)
def test_real_app_openapi_hides_wrong_family_creator_and_media_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path not in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", API_ONLY_FAMILY_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_api_only_family_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", API_ONLY_FAMILY_OPENAPI_ABSENT_PATHS)
def test_real_app_openapi_hides_legacy_api_only_family_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path not in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", NAMESPACED_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_namespaced_api_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", NAMESPACED_OPENAPI_ABSENT_PATHS)
def test_real_app_openapi_hides_legacy_namespaced_api_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path not in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", PUBLIC_MISC_OPENAPI_PRESENT_PATHS)
def test_real_app_openapi_exposes_expected_public_and_mixed_surface_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path in mounted_app_contract_snapshot["openapi_paths"]


@pytest.mark.parametrize("path", PUBLIC_MISC_OPENAPI_ABSENT_PATHS)
def test_real_app_openapi_hides_legacy_public_and_mixed_surface_paths(
    mounted_app_contract_snapshot,
    path: str,
) -> None:
    assert path not in mounted_app_contract_snapshot["openapi_paths"]
