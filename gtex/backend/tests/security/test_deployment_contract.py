"""Regression tests for the production deployment contract.

The live web service was compiled against gtex-api-cijn.onrender.com, which is
suspended, so every API call from the deployed site failed. These assertions pin
the blueprint to the current production hosts and to the canonical KoraPay
route so the same drift is caught in CI rather than in production.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PRODUCTION_API_ORIGIN = "https://gtex-api-opea.onrender.com"
PRODUCTION_WEB_ORIGIN = "https://gtex-web-tw6c.onrender.com"
CANONICAL_KORAPAY_WEBHOOK = f"{PRODUCTION_API_ORIGIN}/integrations/payments/korapay/webhook"
RETIRED_HOSTS = ("gtex-api-cijn.onrender.com", "gtex-web-5ivv.onrender.com", "gtex-web.onrender.com")

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def blueprint() -> dict:
    return yaml.safe_load((REPO_ROOT / "render.yaml").read_text(encoding="utf-8"))


def _env(blueprint: dict, service_name: str) -> dict[str, str]:
    for service in blueprint["services"]:
        if service["name"] == service_name:
            return {item["key"]: item.get("value") for item in service.get("envVars", [])}
    raise AssertionError(f"service {service_name!r} is missing from render.yaml")


def test_web_service_targets_the_live_api_host(blueprint: dict) -> None:
    assert _env(blueprint, "gtex-web")["GTE_API_BASE_URL"] == PRODUCTION_API_ORIGIN


def test_api_allows_the_live_web_origin(blueprint: dict) -> None:
    assert _env(blueprint, "gtex-api")["GTE_CORS_ALLOW_ORIGINS"] == PRODUCTION_WEB_ORIGIN


def test_korapay_notification_url_is_the_canonical_route(blueprint: dict) -> None:
    assert _env(blueprint, "gtex-api")["GTE_KORAPAY_NOTIFICATION_URL"] == CANONICAL_KORAPAY_WEBHOOK


def test_api_declares_its_trusted_proxy_hop_count(blueprint: dict) -> None:
    assert _env(blueprint, "gtex-api")["GTE_TRUSTED_PROXY_HOPS"] == "1"


@pytest.mark.parametrize("host", RETIRED_HOSTS)
def test_retired_hosts_are_not_referenced(host: str) -> None:
    assert host not in (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")


def test_default_cors_origin_is_the_live_web_host() -> None:
    from app.core.config import DEFAULT_CORS_ALLOWED_ORIGINS

    assert DEFAULT_CORS_ALLOWED_ORIGINS == (PRODUCTION_WEB_ORIGIN,)


@pytest.mark.parametrize("environment", ["production", "prod", "staging", "release"])
def test_localhost_cors_regex_is_dropped_in_deployed_environments(environment: str) -> None:
    from app.core.config import DEFAULT_CORS_ALLOW_ORIGIN_REGEX, _resolve_cors_allow_origin_regex

    assert _resolve_cors_allow_origin_regex(DEFAULT_CORS_ALLOW_ORIGIN_REGEX, app_env=environment) is None


def test_localhost_cors_regex_survives_local_development() -> None:
    from app.core.config import DEFAULT_CORS_ALLOW_ORIGIN_REGEX, _resolve_cors_allow_origin_regex

    resolved = _resolve_cors_allow_origin_regex(DEFAULT_CORS_ALLOW_ORIGIN_REGEX, app_env="development")
    assert resolved == DEFAULT_CORS_ALLOW_ORIGIN_REGEX


def test_explicit_operator_regex_is_never_discarded() -> None:
    from app.core.config import _resolve_cors_allow_origin_regex

    resolved = _resolve_cors_allow_origin_regex(r"https://.*\.gtex\.app$", app_env="production")
    assert resolved == r"https://.*\.gtex\.app$"
