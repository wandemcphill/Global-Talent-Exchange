"""Smoke tests for publishing the React shell on the Render static site.

The GTEX React Web Application is published at the site root (`/`)
and Render rewrites client-side SPA routes to `/index.html`.
These tests lock that contract without cloning Flutter or installing
the full React toolchain.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDER_YAML = REPO_ROOT / "render.yaml"
BUILD_SCRIPT = REPO_ROOT / "ops" / "render" / "build-frontend.sh"
CLOUDFLARE_BUILD_SCRIPT = REPO_ROOT / "ops" / "cloudflare" / "build-frontend.sh"
PUBLISH_SCRIPT = REPO_ROOT / "ops" / "render" / "publish-react-shell.sh"
API_CLIENT = REPO_ROOT / "frontend" / "react-shell" / "src" / "lib" / "api.ts"
APP_ENTRY = REPO_ROOT / "frontend" / "react-shell" / "src" / "App.tsx"

PRODUCTION_API_ORIGIN = "https://gtex-api-opea.onrender.com"


@pytest.fixture(scope="module")
def blueprint() -> dict:
    return yaml.safe_load(RENDER_YAML.read_text(encoding="utf-8"))


def _service(blueprint: dict, name: str) -> dict:
    for service in blueprint["services"]:
        if service["name"] == name:
            return service
    raise AssertionError(f"service {name!r} is missing from render.yaml")


def _routes(service: dict) -> list[dict]:
    return list(service.get("routes") or [])


def _rewrite_matches(source: str, request_path: str) -> bool:
    """Render wildcard: '*' consumes the remainder of the path, including '/'."""
    if "*" not in source:
        return request_path == source
    prefix, _, suffix = source.partition("*")
    if not request_path.startswith(prefix):
        return False
    remainder = request_path[len(prefix) :]
    return remainder.endswith(suffix) if suffix else True


def resolve_static(root: Path, request_path: str, routes: list[dict]) -> str | None:
    """Return the publish-root relative file Render would serve, or None for 404.

    Existing files win. A directory request uses index.html when that file
    exists. Otherwise the first matching rewrite is applied once.
    """
    relative = request_path.lstrip("/")
    candidate = root / relative
    if candidate.is_file():
        return relative
    if request_path.endswith("/") and (candidate / "index.html").is_file():
        return f"{relative}index.html" if relative else "index.html"
    for route in routes:
        if route.get("type") != "rewrite":
            continue
        if _rewrite_matches(str(route["source"]), request_path):
            destination = str(route["destination"])
            if not (root / destination.lstrip("/")).is_file():
                return None
            return destination.lstrip("/")
    return None


def _run_publish(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")}
    env.update(extra_env)
    return subprocess.run(
        ["bash", str(PUBLISH_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_web_service_publishes_react_at_the_site_root(blueprint: dict) -> None:
    web = _service(blueprint, "gtex-web")
    assert web["runtime"] == "static"
    assert web["staticPublishPath"] == "frontend/build/web"
    assert web["buildCommand"] == "bash ops/render/build-frontend.sh"
    env = {item["key"]: item.get("value") for item in web.get("envVars", [])}
    assert env["GTE_API_BASE_URL"] == PRODUCTION_API_ORIGIN
    assert env["GTE_BACKEND_MODE"] == "live"
    assert env["GTEX_SHELL_V3"] == "true"
    assert env["NODE_VERSION"] == "20"


def test_web_service_routes_rewrite_to_index_html(blueprint: dict) -> None:
    routes = _routes(_service(blueprint, "gtex-web"))
    sources = [route["source"] for route in routes]
    assert "/*" in sources
    assert all(route["type"] == "rewrite" for route in routes)
    assert all(route["destination"] == "/index.html" for route in routes)


def test_static_resolution_serves_react_root_and_deep_links(blueprint: dict, tmp_path: Path) -> None:
    root = tmp_path / "web"
    (root / "static" / "js").mkdir(parents=True)
    (root / "img").mkdir()
    (root / "index.html").write_text("REACT", encoding="utf-8")
    (root / "static" / "js" / "main.js").write_text("bundle", encoding="utf-8")
    (root / "img" / "hero.jpg").write_text("image", encoding="utf-8")
    routes = _routes(_service(blueprint, "gtex-web"))

    def served(path: str) -> str | None:
        return resolve_static(root, path, routes)

    assert served("/") == "index.html"
    assert served("/login") == "index.html"
    assert served("/app/market") == "index.html"
    assert served("/console") == "index.html"
    assert served("/console/login") == "index.html"
    assert served("/static/js/main.js") == "static/js/main.js"
    assert served("/img/hero.jpg") == "img/hero.jpg"
    assert (root / served("/") or "").read_text(encoding="utf-8") == "REACT"


def test_production_flutter_builds_enable_p9_shell_by_default() -> None:
    script = CLOUDFLARE_BUILD_SCRIPT.read_text(encoding="utf-8")
    assert 'GTEX_SHELL_V3="${GTEX_SHELL_V3:-true}"' in script
    assert '--dart-define="GTEX_SHELL_V3=${GTEX_SHELL_V3}"' in script
    assert "GTEX_SHELL_V3 must be 'true' or 'false'." in script


def test_frontend_build_publishes_react_shell() -> None:
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail\n")
    assert "npm run build" in script
    assert "build/web" in script


def test_react_client_requires_the_canonical_api_and_console_basename() -> None:
    api = API_CLIENT.read_text(encoding="utf-8")
    app = APP_ENTRY.read_text(encoding="utf-8")
    assert "window.location.origin" not in api
    assert "REACT_APP_BACKEND_URL" in api
    assert 'endsWith("/api")' in api
    assert "ROUTER_BASENAME" in app
    assert "basename={ROUTER_BASENAME}" in app


@pytest.mark.skipif(os.name == "nt", reason="bash runner requires a POSIX environment")
def test_publish_script_rejects_a_missing_api_origin() -> None:
    result = _run_publish({})
    assert result.returncode != 0
    assert "GTE_API_BASE_URL" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="bash runner requires a POSIX environment")
def test_publish_script_rejects_an_api_suffix() -> None:
    result = _run_publish({"GTE_API_BASE_URL": f"{PRODUCTION_API_ORIGIN}/api"})
    assert result.returncode != 0
    assert "without a /api suffix" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="bash runner requires a POSIX environment")
def test_publish_script_refuses_a_publish_dir_override_on_render(tmp_path: Path) -> None:
    result = _run_publish(
        {
            "RENDER": "true",
            "GTE_API_BASE_URL": PRODUCTION_API_ORIGIN,
            "GTEX_WEB_PUBLISH_DIR": str(tmp_path / "web"),
        }
    )
    assert result.returncode != 0
    assert "Refusing GTEX_WEB_PUBLISH_DIR on Render" in result.stderr
