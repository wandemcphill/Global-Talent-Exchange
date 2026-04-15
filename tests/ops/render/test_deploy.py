from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_deploy_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "ops" / "render" / "deploy.py"
    module_name = "gtex_ops_render_deploy_test"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load deploy module from {module_path}")

    sys.path.insert(0, str(module_path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


deploy = _load_deploy_module()
TEST_RENDER_CREDENTIAL = "render-api-key"  # pragma: allowlist secret


def test_render_hook_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_API_KEY", raising=False)

    with pytest.raises(deploy.RenderDeployError, match="RENDER_API_KEY must be set"):
        deploy.RenderHookClient()


def test_load_service_targets_allows_missing_hooks_in_api_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_SERVICE_API", "srv-api")
    monkeypatch.delenv("RENDER_DEPLOY_HOOK_API", raising=False)

    targets = deploy._load_service_targets("api")

    assert targets == [
        deploy.ServiceTarget(
            name="api",
            env_key="API",
            service_id="srv-api",
            deploy_hook_url="",
        )
    ]


def test_retrieve_deploy_uses_service_deploy_endpoint_with_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(**kwargs):
        captured.update(kwargs)
        return {"status": "deployed"}

    monkeypatch.setattr(deploy, "_request_json", fake_request_json)
    client = deploy.RenderHookClient(api_key=TEST_RENDER_CREDENTIAL)

    response = client.retrieve_deploy("srv/123", "dep 456")

    assert response == {"status": "deployed"}
    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.render.com/v1/services/srv%2F123/deploys/dep%20456"
    assert captured["request_label"] == "Render API"
    assert captured["headers"] == {
        "Accept": "application/json",
        "Authorization": f"Bearer {TEST_RENDER_CREDENTIAL}",
    }


def test_create_deploy_uses_service_deploy_collection_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(**kwargs):
        captured.update(kwargs)
        return {"id": "dep-456"}

    monkeypatch.setattr(deploy, "_request_json", fake_request_json)
    client = deploy.RenderHookClient(api_key=TEST_RENDER_CREDENTIAL)

    response = client.create_deploy("srv/123")

    assert response == {"id": "dep-456"}
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.render.com/v1/services/srv%2F123/deploys"
    assert captured["payload"] == {}
    assert captured["request_label"] == "Render API"
    assert captured["headers"] == {
        "Accept": "application/json",
        "Authorization": f"Bearer {TEST_RENDER_CREDENTIAL}",
        "Content-Type": "application/json",
    }


def test_deploy_with_hook_only_falls_back_to_health_check_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    wait_calls: list[dict[str, object]] = []
    health_calls: list[dict[str, object]] = []

    def fake_wait_for_deploy(*args, **kwargs):
        wait_calls.append(kwargs)
        raise deploy.RenderDeployHttpError(status_code=404, message="deploy status missing")

    monkeypatch.setattr(
        deploy.RenderHookClient,
        "trigger_deploy",
        lambda self, hook_url: {"id": "dep-123"},
    )
    monkeypatch.setattr(deploy, "_wait_for_deploy", fake_wait_for_deploy)
    monkeypatch.setattr(
        deploy,
        "_run_health_check",
        lambda **kwargs: health_calls.append(kwargs),
    )
    monkeypatch.setattr(deploy, "_log", messages.append)

    deploy._deploy_with_hook_only(
        deploy.RenderHookClient(api_key=TEST_RENDER_CREDENTIAL),
        target=deploy.ServiceTarget(
            name="api",
            env_key="API",
            service_id="srv-123",
            deploy_hook_url="https://example.test/hook",
        ),
        health_url="https://example.test/health",
        deploy_timeout_seconds=30,
        health_timeout_seconds=45,
        poll_interval_seconds=1,
    )

    assert len(wait_calls) == 1
    assert health_calls == [
        {
            "url": "https://example.test/health",
            "timeout_seconds": 45,
            "poll_interval_seconds": 1,
        }
    ]
    assert messages == [
        "[api] triggering deploy hook",
        "[api] deploy status unavailable in hook-only mode; falling back to health check",
        "[api] health check passed",
    ]
