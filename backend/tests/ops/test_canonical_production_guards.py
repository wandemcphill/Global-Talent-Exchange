from __future__ import annotations

import importlib.util
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Pattern

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TEXT_SUFFIXES = {
    ".dart",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
}

PAYMENT_CANONICAL_SURFACES = (
    ".github/workflows/ci-staging.yml",
    ".github/workflows/deploy-production.yml",
    "backend/app/admin_finance",
    "backend/app/admin_godmode",
    "backend/app/models/regen_creation_order.py",
    "backend/app/models/wallet.py",
    "backend/app/regen_creation",
    "backend/app/services/ads",
    "backend/app/services/payment_gateway_service.py",
    "backend/app/treasury",
    "backend/app/wallets",
    "backend/config/admin_god_mode.json",
    "frontend/lib/data/admin_finance_api.dart",
    "frontend/lib/data/generated/gte_api_contract.g.dart",
    "frontend/lib/data/gte_api_repository.dart",
    "frontend/lib/data/regen_creation_api.dart",
    "frontend/lib/screens/wallet",
    "ops/k8s/base/secret.example.yaml",
    "render.yaml",
    "shared/api_contract.json",
)

ROUTE_PROMOTION_SURFACES = (
    ".github/workflows/ci-staging.yml",
    ".github/workflows/deploy-production.yml",
    "backend/app/api_v1",
    "backend/app/live_matches",
    "backend/app/match_engine",
    "backend/app/modules.py",
    "backend/app/routes",
    "frontend/lib/features/app_routes",
    "frontend/lib/features/match",
    "frontend/lib/navigation",
    "frontend/lib/router",
    "frontend/lib/screens/match",
    "ops/render",
    "shared/api_contract.json",
)

PUBLIC_MATCH_COPY_SURFACES = (
    "frontend/lib/features/app_routes",
    "frontend/lib/features/match",
    "frontend/lib/navigation",
    "frontend/lib/router",
    "frontend/lib/screens/match",
)

GUARDRAIL_SCANNER_TEST_ROOTS = (
    ".github",
    "backend/app/live_matches",
    "backend/tests/ops",
    "docs/guardrails",
    "frontend/lib/features/match",
    "frontend/lib/navigation",
    "frontend/lib/router",
    "ops/render",
    "scripts",
    "shared/api_contract.json",
    "tools/guardrails",
)

DART_STRING_RE = re.compile(
    r"(?P<prefix>r)?(?P<quote>'''|\"\"\"|'|\")(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)


def _text(path: str) -> str:
    return _cached_text(path)


def _load_guardrail_scanner():
    module_path = REPO_ROOT / "tools" / "guardrails" / "production_guardrail_scan.py"
    spec = importlib.util.spec_from_file_location("production_guardrail_scan", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


@lru_cache(maxsize=None)
def _cached_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def _iter_text_files(paths: tuple[str, ...]) -> tuple[Path, ...]:
    files: list[Path] = []
    seen: set[Path] = set()
    for raw_path in paths:
        path = REPO_ROOT / raw_path
        candidates = [path] if path.is_file() else path.rglob("*")
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            files.append(candidate)
    return tuple(files)


def _line_number(contents: str, offset: int) -> int:
    return contents.count("\n", 0, offset) + 1


def _format_hits(hits: list[tuple[Path, int, str]]) -> str:
    return "\n".join(f"{_relative(path)}:{line}: {label}" for path, line, label in hits)


def _is_documented_internal_exception(path: Path, label: str, contents: str) -> bool:
    relative = _relative(path)
    normalized = contents.lower()

    if relative == "ops/render/verify_match_center_routes.py" and label in {
        "legacy match runtime access route",
        "promoted 3D match route",
    }:
        return "forbidden_openapi_fragments" in normalized and "quarantined legacy match runtime route" in normalized

    return False


def _scan_text(
    paths: tuple[str, ...],
    patterns: tuple[tuple[str, Pattern[str]], ...],
    *,
    allow_documented_internal_exceptions: bool = False,
) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for path in _iter_text_files(paths):
        contents = _cached_text(_relative(path))
        for label, pattern in patterns:
            for match in pattern.finditer(contents):
                if allow_documented_internal_exceptions and _is_documented_internal_exception(path, label, contents):
                    continue
                hits.append((path, _line_number(contents, match.start()), label))
    return hits


def _scan_text_tokens(
    paths: tuple[str, ...],
    tokens: tuple[tuple[str, str], ...],
    *,
    allow_documented_internal_exceptions: bool = False,
) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    lowered_tokens = tuple((label, token.lower()) for label, token in tokens)
    for path in _iter_text_files(paths):
        contents = _cached_text(_relative(path))
        lowered_contents = contents.lower()
        for label, token in lowered_tokens:
            start = 0
            while True:
                match_start = lowered_contents.find(token, start)
                if match_start == -1:
                    break
                if allow_documented_internal_exceptions and _is_documented_internal_exception(path, label, contents):
                    start = match_start + len(token)
                    continue
                hits.append((path, _line_number(contents, match_start), label))
                start = match_start + len(token)
    return hits


def _scan_dart_string_literals(
    paths: tuple[str, ...],
    patterns: tuple[tuple[str, Pattern[str]], ...],
) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for path in _iter_text_files(paths):
        if path.suffix.lower() != ".dart":
            continue
        contents = _cached_text(_relative(path))
        for string_match in DART_STRING_RE.finditer(contents):
            value = string_match.group("value")
            for label, pattern in patterns:
                if pattern.search(value):
                    hits.append((path, _line_number(contents, string_match.start("value")), label))
    return hits


def test_render_deploy_uses_match_center_route_verification() -> None:
    legacy = "uni" + "ty"
    forbidden_tokens = (
        f"RENDER_VERIFY_{legacy.upper()}_ROUTES",
        f"RENDER_{legacy.upper()}_LIVE_VERIFY",
        f"verify_{legacy}_routes.py",
        f"/{legacy}-access",
    )

    for path in (
        ".github/workflows/deploy-production.yml",
        ".github/workflows/ci-staging.yml",
        "ops/render/deploy.py",
    ):
        contents = _text(path)
        for token in forbidden_tokens:
            assert token not in contents

    assert "RENDER_VERIFY_MATCH_CENTER_ROUTES" in _text(".github/workflows/deploy-production.yml")
    assert "RENDER_VERIFY_MATCH_CENTER_ROUTES" in _text(".github/workflows/ci-staging.yml")
    assert "verify_match_center_routes" in _text("ops/render/deploy.py")


def test_secret_examples_expose_only_canonical_payment_webhook_secret() -> None:
    stale_provider = "pay" + "stack"
    contents = _text("ops/k8s/base/secret.example.yaml").lower()

    assert stale_provider not in contents
    assert "g" + "te_korapay_webhook_secret" in contents


def test_canonical_payment_surfaces_do_not_expose_retired_provider() -> None:
    stale_provider = "pay" + "stack"
    hits = _scan_text_tokens(
        PAYMENT_CANONICAL_SURFACES,
        (
            ("retired payment provider name", stale_provider),
            ("retired payment provider environment variable", f"{stale_provider}_"),
            ("retired payment provider environment variable", f"gte_{stale_provider}_"),
        ),
    )

    assert not hits, _format_hits(hits)


def test_canonical_route_surfaces_do_not_promote_legacy_runtime_routes() -> None:
    legacy = "uni" + "ty"
    hits = _scan_text_tokens(
        ROUTE_PROMOTION_SURFACES,
        (
            ("legacy match runtime access route", f"{legacy}-access"),
            ("legacy match runtime access route", f"{legacy}_access"),
            ("retired route verifier", f"verify_{legacy}_routes"),
            ("retired route verification environment variable", f"render_verify_{legacy}_routes"),
            ("retired route verification environment variable", f"render_{legacy}_live_verify"),
            ("promoted 3D match route", "/matches/3d"),
            ("promoted 3D match route", "/matches/native-3d"),
        ),
        allow_documented_internal_exceptions=True,
    )

    assert not hits, _format_hits(hits)


def test_public_match_copy_does_not_promote_3d_ctas_or_pseudo_3d_labels() -> None:
    hits = _scan_dart_string_literals(
        PUBLIC_MATCH_COPY_SURFACES,
        (
            (
                "promoted 3D CTA",
                re.compile(
                    r"\b(?:open|watch|view|launch|enter|start|try|unlock|upgrade|switch(?:\s+to)?|continue\s+in)"
                    r"\s+(?:native\s+|flutter\s+|unity\s+)?3d\b",
                    re.IGNORECASE,
                ),
            ),
            ("pseudo-" + "3D public label", re.compile(r"\bpseudo[-_\s]?3d\b|\bPSEUDO_3D\b", re.IGNORECASE)),
        ),
    )

    assert not hits, _format_hits(hits)


def test_internal_legacy_3d_references_are_documented_and_canonicalized() -> None:
    match_view_type = _text("frontend/lib/features/match_center/models/match/gtex_match_view_type.dart")
    assert "enum GtexMatchViewType { twoD }" in match_view_type
    assert "GtexMatchViewType.pseudo3D" not in match_view_type
    assert "return GtexMatchViewType.twoD;" in match_view_type
    assert "return '2D';" in match_view_type
    assert "isLegacyQuarantined => false" in match_view_type

    app_destinations = _text("frontend/lib/navigation/app_destinations.dart").lower()
    assert "/internal/dev/match-runtime" in app_destinations
    assert "/internal/dev/native-match-runtime" in app_destinations
    assert "deprecated match rendering route quarantined behind internal builds" in app_destinations
    assert "/matches/3d" not in app_destinations
    assert "/matches/native-3d" not in app_destinations


@pytest.mark.parametrize(
    "forbidden_route",
    (
        "/api/matches/{match_id}/" + "uni" + "ty-access",
        "/api/matches/{match_id}/" + "uni" + "ty-access/refresh",
        "/api/matches/{match_id}/legacy-runtime-access",
        "/api/matches/{match_id}/legacy-runtime-access/refresh",
        "/matches/3d/live-match-001",
        "/matches/native-3d/live-match-001",
    ),
)
def test_match_center_verifier_rejects_quarantined_legacy_runtime_routes(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_route: str,
) -> None:
    module_path = REPO_ROOT / "ops" / "render" / "verify_match_center_routes.py"
    spec = importlib.util.spec_from_file_location("verify_match_center_routes", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    openapi = {
        "paths": {
            "/api/match-viewer/{match_key}": {"get": {}},
            "/api/match-viewer/{match_key}/session": {"get": {}},
            "/api/matches/live/active": {"get": {}},
            "/api/matches/{match_id}/spectate": {"post": {}},
            forbidden_route: {"post": {}},
        }
    }
    monkeypatch.setattr(module, "_load_openapi", lambda *_args, **_kwargs: openapi)

    with pytest.raises(module.RenderMatchCenterRouteVerificationError):
        module.verify_match_center_routes("https://api.example.test")


def test_match_center_verifier_requires_canonical_2d_and_realtime_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = REPO_ROOT / "ops" / "render" / "verify_match_center_routes.py"
    spec = importlib.util.spec_from_file_location("verify_match_center_routes", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    openapi = {
        "paths": {
            "/api/matches/{match_id}/live": {"get": {}},
            "/api/matches/{match_id}/commentary/stream": {"get": {}},
            "/api/matches/live/active": {"get": {}},
            "/api/matches/{match_id}/spectate": {"post": {}},
        }
    }
    monkeypatch.setattr(module, "_load_openapi", lambda *_args, **_kwargs: openapi)

    with pytest.raises(module.RenderMatchCenterRouteVerificationError) as excinfo:
        module.verify_match_center_routes("https://api.example.test")

    assert "/api/match-viewer/{match_key}" in str(excinfo.value)


def test_production_guardrail_scanner_has_no_unquarantined_violations() -> None:
    scanner = _load_guardrail_scanner()

    hits = scanner.scan(GUARDRAIL_SCANNER_TEST_ROOTS)
    violations = [hit for hit in hits if hit.classification == "violation"]

    assert not violations, "\n".join(
        f"{hit.path}:{hit.line}:{hit.column} {hit.rule} {hit.match!r} {hit.note}" for hit in violations[:50]
    )
    assert any(hit.classification == "quarantined" for hit in hits)


def test_canonical_acceptance_harness_uses_feature_first_match_center_paths() -> None:
    module_path = REPO_ROOT / "tools" / "quality" / "run_gtex_canonical_acceptance.py"
    spec = importlib.util.spec_from_file_location("run_gtex_canonical_acceptance", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    expected_paths = {
        "MATCH_SIMULATION_ENGINE_PATH": "frontend/lib/features/match_center/data/match/match_simulation_engine.dart",
        "REAL_MATCH_SCENE_DIRECTOR_PATH": "frontend/lib/features/match_center/presentation/real_match_scene_director.dart",
    }
    legacy_paths = {
        "frontend/lib/data/match/match_simulation_engine.dart",
        "frontend/lib/data/match/real_match_scene_director.dart",
        "frontend/lib/features/match/data/match/match_simulation_engine.dart",
        "frontend/lib/features/match/presentation/real_match_scene_director.dart",
    }

    actual_paths = {name: _relative(getattr(module, name)) for name in expected_paths}

    assert actual_paths == expected_paths
    assert not (set(actual_paths.values()) & legacy_paths)
    for relative_path in actual_paths.values():
        assert (REPO_ROOT / relative_path).is_file()


def test_local_acceptance_harness_runs_guardrails_and_diff_check() -> None:
    contents = _text("scripts/run_gtex_guardrails.ps1")

    assert "production_guardrail_scan.py --fail-on violation" in contents
    assert "tools/quality/run_gtex_canonical_acceptance.py" in contents
    assert "backend/tests/ops/test_canonical_production_guards.py" in contents
    assert "test/guardrails/forbidden_text_guard_test.dart" in contents
    assert "test/match_center/canonical_match_center_test.dart" in contents
    assert "test/match_center/live_match_realtime_test.dart" in contents
    assert "git diff --check" in contents
