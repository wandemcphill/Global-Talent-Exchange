"""Guards against API contract drift.

Three distinct failure modes are covered here, because the CI quality gate
covers none of them:

1. ``test_every_backend_route_is_declared_in_the_api_contract`` fails when a
   backend router declares a route that ``shared/api_contract.json`` does not
   know about. ``check_api_contract_violations.py`` only inspects *frontend*
   Dart sources, so a backend route stays invisible to CI until some Dart file
   happens to call it. That is how 27 routes drifted out of the contract
   between 2026-07-02 and 2026-09-03.

2. ``test_generated_contract_artifacts_match_their_source`` fails when
   ``shared/api_contract.json`` or the generated Dart binding has been
   hand-edited, or left stale relative to ``docs/ROUTE_MAP.json``.

3. ``test_route_map_route_count_matches_its_routes`` fails when
   ``docs/ROUTE_MAP.json`` itself has been hand-edited. Commit 2310e987 did
   exactly that and the mismatched counter it left behind went unnoticed for
   two months.

The fix for any of these is always the sanctioned pipeline, never a hand
edit::

    python tools/audit/generate_contract_audit.py
    python tools/audit/generate_api_contract_bindings.py

See docs/phase4/GTEX_PHASE4_CONTRACT_DRIFT_AUDIT.md.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_TOOLS = REPO_ROOT / "tools" / "audit"
CONTRACT_PATH = REPO_ROOT / "shared" / "api_contract.json"
ROUTE_MAP_PATH = REPO_ROOT / "docs" / "ROUTE_MAP.json"
DEPRECATION_MAP_PATH = REPO_ROOT / "docs" / "DEPRECATION_MAP.json"
FINAL_API_SCHEMA_PATH = REPO_ROOT / "docs" / "FINAL_API_SCHEMA.json"
DART_BINDING_PATH = REPO_ROOT / "frontend" / "lib" / "data" / "generated" / "gte_api_contract.g.dart"

REGENERATE_HINT = (
    "Regenerate with the sanctioned pipeline (do not hand-edit generated artifacts):\n"
    "    python tools/audit/generate_contract_audit.py\n"
    "    python tools/audit/generate_api_contract_bindings.py"
)


def _load_tool(name: str) -> ModuleType:
    """Import an audit tool by path.

    The tools live outside any package and are not importable normally. They are
    imported rather than copied so the test can never disagree with the
    generator about what a route is or how a canonical path is derived.
    """
    spec = importlib.util.spec_from_file_location(f"_gtex_audit_{name}", AUDIT_TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Must be registered before exec: the module defines a frozen dataclass, and
    # dataclasses resolves __module__ through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def contract_audit() -> ModuleType:
    return _load_tool("generate_contract_audit")


@pytest.fixture(scope="module")
def contract_bindings() -> ModuleType:
    return _load_tool("generate_api_contract_bindings")


@pytest.fixture(scope="module")
def committed_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _declared_routes(contract: dict[str, Any]) -> set[tuple[str, str]]:
    """Every (method, canonical_path) pair the contract declares."""
    declared: set[tuple[str, str]] = set()
    for domain_entries in (contract.get("routes") or {}).values():
        for entry in domain_entries.values():
            declared.add((entry["method"], entry["canonical_path"]))
    for entry in (contract.get("websockets") or {}).values():
        declared.add((entry["method"], entry["canonical_path"]))
    return declared


def test_every_backend_route_is_declared_in_the_api_contract(
    contract_audit: ModuleType,
    contract_bindings: ModuleType,
    committed_contract: dict[str, Any],
) -> None:
    """No backend router may expose a route the shared contract does not declare.

    This scans backend/app from source (~30s) rather than trusting the committed
    ROUTE_MAP.json, because a stale ROUTE_MAP.json is itself the drift being
    guarded against.
    """
    backend_routes, _mounts = contract_audit._scan_backend_routes()
    assert backend_routes, "route scanner returned nothing; the scanner itself is broken"

    fresh_contract = contract_bindings._build_contract(
        route_map=contract_audit._build_route_map(backend_routes),
        # Accepted but unused by _build_contract; passed for signature fidelity.
        final_api_schema=json.loads(FINAL_API_SCHEMA_PATH.read_text(encoding="utf-8")),
        deprecation_map=json.loads(DEPRECATION_MAP_PATH.read_text(encoding="utf-8")),
    )

    undeclared = sorted(_declared_routes(fresh_contract) - _declared_routes(committed_contract))
    assert not undeclared, (
        f"{len(undeclared)} backend route(s) are not declared in shared/api_contract.json.\n"
        "A Dart caller of any of these would fail at runtime: gteCanonicalApiPath raises\n"
        "StateError for undeclared paths, which surfaces as a bogus network error.\n\n"
        + "\n".join(f"  {method:9s} {path}" for method, path in undeclared)
        + "\n\n"
        + REGENERATE_HINT
    )


def test_generated_contract_artifacts_match_their_source(contract_bindings: ModuleType) -> None:
    """shared/api_contract.json and the Dart binding must be pipeline output.

    Both files carry no "generated" marker that CI enforces, and both have been
    hand-edited in the past. This pins them to what the generator produces from
    the committed ROUTE_MAP.json.
    """
    expected_contract = contract_bindings._build_contract(
        route_map=json.loads(ROUTE_MAP_PATH.read_text(encoding="utf-8")),
        final_api_schema=json.loads(FINAL_API_SCHEMA_PATH.read_text(encoding="utf-8")),
        deprecation_map=json.loads(DEPRECATION_MAP_PATH.read_text(encoding="utf-8")),
    )

    actual_contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert actual_contract == expected_contract, "shared/api_contract.json is stale or hand-edited.\n" + REGENERATE_HINT

    expected_dart = contract_bindings._render_dart_binding(expected_contract)
    actual_dart = DART_BINDING_PATH.read_text(encoding="utf-8")
    assert actual_dart == expected_dart, (
        "frontend/lib/data/generated/gte_api_contract.g.dart is stale or hand-edited.\n" + REGENERATE_HINT
    )


def test_route_map_route_count_matches_its_routes() -> None:
    """route_count is the cheapest tell that ROUTE_MAP.json was hand-edited.

    Commit 2310e987 injected a route by hand and left route_count behind, which
    is how the hand-edit stayed undetected for two months.
    """
    route_map = json.loads(ROUTE_MAP_PATH.read_text(encoding="utf-8"))
    assert route_map["route_count"] == len(route_map["routes"]), (
        f"docs/ROUTE_MAP.json declares route_count={route_map['route_count']} but contains "
        f"{len(route_map['routes'])} routes, so it was edited by hand.\n" + REGENERATE_HINT
    )
