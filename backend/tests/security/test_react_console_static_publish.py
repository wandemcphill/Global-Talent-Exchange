"""Smoke tests for publishing the React shell beside Flutter on the static site.

Flutter stays the document at `/`. The React shell is built into `console/`
and Render rewrites only `/console` client routes. These tests lock that
contract without cloning Flutter or installing the React toolchain.
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
    )


def test_web_service_still_publishes_flutter_at_the_site_root(blueprint: dict) -> None:
    web = _service(blueprint, "gtex-web")
    assert web["runtime"] == "static"
    assert web["staticPublishPath"] == "frontend/build/web"
    assert web["buildCommand"] == "bash ops/render/build-frontend.sh"
    env = {item["key"]: item.get("value") for item in web.get("envVars", [])}
    assert env["GTE_API_BASE_URL"] == PRODUCTION_API_ORIGIN
    assert env["GTE_BACKEND_MODE"] == "live"
    assert env["GTEX_SHELL_V3"] == "true"
    assert env["NODE_VERSION"] == "20"


def test_console_rewrites_do_not_catch_flutter_or_api_paths(blueprint: dict) -> None:
    routes = _routes(_service(blueprint, "gtex-web"))
    sources = [route["source"] for route in routes]
    assert sources == ["/console", "/console/", "/console/*"]
    assert all(route["type"] == "rewrite" for route in routes)
    assert all(route["destination"] == "/console/index.html" for route in routes)
    forbidden = {"/", "/*", "/api", "/api/*", "/index.html"}
    assert forbidden.isdisjoint(sources)


def test_static_resolution_keeps_flutter_root_and_react_deep_links(blueprint: dict, tmp_path: Path) -> None:
    root = tmp_path / "web"
    (root / "console" / "static" / "js").mkdir(parents=True)
    (root / "console" / "img").mkdir()
    (root / "index.html").write_text("FLUTTER", encoding="utf-8")
    (root / "main.dart.js").write_text("dart", encoding="utf-8")
    (root / "console" / "index.html").write_text("REACT", encoding="utf-8")
    (root / "console" / "static" / "js" / "main.js").write_text("bundle", encoding="utf-8")
    (root / "console" / "img" / "hero.jpg").write_text("image", encoding="utf-8")
    routes = _routes(_service(blueprint, "gtex-web"))

    def served(path: str) -> str | None:
        return resolve_static(root, path, routes)

    assert served("/") == "index.html"
    assert served("/main.dart.js") == "main.dart.js"
    assert served("/console") == "console/index.html"
    assert served("/console/") == "console/index.html"
    assert served("/console/index.html") == "console/index.html"
    assert served("/console/login") == "console/index.html"
    assert served("/console/app/market") == "console/index.html"
    assert served("/console/payment/callback") == "console/index.html"
    assert served("/console/static/js/main.js") == "console/static/js/main.js"
    assert served("/console/img/hero.jpg") == "console/img/hero.jpg"
    assert served("/app/market") is None
    assert served("/design-lab") is None
    assert served("/api/v2/auth/login") is None
    assert (root / served("/") or "").read_text(encoding="utf-8") == "FLUTTER"
    assert (root / "console" / "index.html").read_text(encoding="utf-8") == "REACT"


def test_production_flutter_builds_enable_p9_shell_by_default() -> None:
    for build_path in (BUILD_SCRIPT, CLOUDFLARE_BUILD_SCRIPT):
        script = build_path.read_text(encoding="utf-8")
        assert 'GTEX_SHELL_V3="${GTEX_SHELL_V3:-true}"' in script
        assert '--dart-define="GTEX_SHELL_V3=${GTEX_SHELL_V3}"' in script
        assert "GTEX_SHELL_V3 must be 'true' or 'false'." in script


def test_frontend_build_publishes_react_only_after_flutter() -> None:
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail\n")
    flutter_build = script.index("flutter build web --release")
    react_publish = script.index('bash "${SCRIPT_DIR}/publish-react-shell.sh"')
    assert flutter_build < react_publish
    assert "|| true" not in script.split("publish-react-shell.sh", 1)[1]


def test_react_client_requires_the_canonical_api_and_console_basename() -> None:
    api = API_CLIENT.read_text(encoding="utf-8")
    app = APP_ENTRY.read_text(encoding="utf-8")
    assert "window.location.origin" not in api
    assert "REACT_APP_BACKEND_URL" in api
    assert 'endsWith("/api")' in api
    assert "ROUTER_BASENAME" in app
    assert "basename={ROUTER_BASENAME}" in app


def test_publish_script_rejects_a_missing_api_origin() -> None:
    result = _run_publish({})
    assert result.returncode != 0
    assert "GTE_API_BASE_URL" in result.stderr
    assert "npm" not in result.stdout
    assert "npm" not in result.stderr


def test_publish_script_rejects_an_api_suffix() -> None:
    result = _run_publish({"GTE_API_BASE_URL": f"{PRODUCTION_API_ORIGIN}/api"})
    assert result.returncode != 0
    assert "without a /api suffix" in result.stderr
    assert "npm" not in result.stderr


def test_publish_script_rejects_a_missing_flutter_host(tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    result = _run_publish(
        {
            "GTE_API_BASE_URL": PRODUCTION_API_ORIGIN,
            "GTEX_WEB_PUBLISH_DIR": str(web),
        }
    )
    assert result.returncode != 0
    assert "Flutter web output is missing" in result.stderr
    assert "npm" not in result.stderr


def test_publish_script_rejects_a_non_flutter_site_root(tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    result = _run_publish(
        {
            "GTE_API_BASE_URL": PRODUCTION_API_ORIGIN,
            "GTEX_WEB_PUBLISH_DIR": str(web),
        }
    )
    assert result.returncode != 0
    assert "not the Flutter host" in result.stderr
    assert "npm" not in result.stderr


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
    assert "npm" not in result.stderr
