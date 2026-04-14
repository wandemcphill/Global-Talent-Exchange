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


def test_render_hook_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_API_KEY", raising=False)

    with pytest.raises(deploy.RenderDeployError, match="RENDER_API_KEY must be set"):
        deploy.RenderHookClient()


def test_retrieve_deploy_uses_service_deploy_endpoint_with_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(**kwargs):
        captured.update(kwargs)
        return {"status": "deployed"}

    monkeypatch.setattr(deploy, "_request_json", fake_request_json)
    client = deploy.RenderHookClient(api_key="render-api-key")

    response = client.retrieve_deploy("srv/123", "dep 456")

    assert response == {"status": "deployed"}
    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.render.com/v1/services/srv%2F123/deploys/dep%20456"
    assert captured["request_label"] == "Render API"
    assert captured["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer render-api-key",
    }
