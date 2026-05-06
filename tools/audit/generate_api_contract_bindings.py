from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
SHARED_DIR = REPO_ROOT / "shared"
FRONTEND_GENERATED_DIR = REPO_ROOT / "frontend" / "lib" / "data" / "generated"
CONTRACT_PATH = SHARED_DIR / "api_contract.json"
DART_BINDING_PATH = FRONTEND_GENERATED_DIR / "gte_api_contract.g.dart"

API_VERSION = "2"
API_VERSION_PREFIX = f"/api/v{API_VERSION}"
LEGACY_VERSION_PREFIX = "/api/v2"
API_VERSION_HEADER = "X-API-Version"
PUBLIC_EXEMPT_PATHS = ("/health", "/ready", "/version", "/docs", "/openapi.json", "/redoc")
PUBLIC_EXEMPT_PREFIXES = ("/generated-media", "/tts")
_PARAM_RE = re.compile(r"\{([^}]+)\}")
_NON_ALPHANUMERIC_RE = re.compile(r"[^a-zA-Z0-9]+")


def main() -> int:
    route_map = _read_json(DOCS_DIR / "ROUTE_MAP.json")
    final_api_schema = _read_json(DOCS_DIR / "FINAL_API_SCHEMA.json")
    deprecation_map = _read_json(DOCS_DIR / "DEPRECATION_MAP.json")

    contract = _build_contract(
        route_map=route_map,
        final_api_schema=final_api_schema,
        deprecation_map=deprecation_map,
    )
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    DART_BINDING_PATH.write_text(_render_dart_binding(contract), encoding="utf-8")
    return 0


def _build_contract(
    *,
    route_map: dict[str, Any],
    final_api_schema: dict[str, Any],
    deprecation_map: dict[str, Any],
) -> dict[str, Any]:
    route_inventory: dict[tuple[str, str], dict[str, Any]] = {}
    contract_routes: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    canonical_paths: dict[str, str] = {}
    deprecated_aliases: dict[str, str] = {}
    websocket_entries: dict[str, dict[str, Any]] = {}

    for route in route_map.get("routes", []):
        method = str(route.get("method") or "").upper()
        legacy_path = str(route.get("path") or "").strip()
        effective_paths = [
            str(path).strip()
            for path in (route.get("effective_paths") or [])
            if str(path).strip()
        ]
        if not method or not legacy_path:
            continue
        route_inventory[(method, legacy_path)] = route
        public_aliases = effective_paths or [legacy_path]
        preferred_source_path = _preferred_public_path(public_aliases)
        canonical_path = _canonicalize_path(preferred_source_path)
        aliases = set()
        for alias_source in {legacy_path, *public_aliases}:
            aliases.update(_route_aliases(alias_source, canonical_path))
        aliases = sorted(aliases)
        route_key = _route_key(method, canonical_path)
        record = {
            "method": method,
            "canonical_path": canonical_path,
            "aliases": aliases,
            "handler": route.get("handler"),
            "source_file": route.get("file"),
            "response_model": route.get("response_shape", {}).get("response_model"),
        }
        if method == "WEBSOCKET":
            websocket_entries[route_key] = record
        else:
            domain = str(route.get("domain") or "uncategorized")
            contract_routes[domain][route_key] = record
        canonical_paths[canonical_path] = route_key
        for alias in aliases:
            if alias != canonical_path:
                deprecated_aliases[alias] = canonical_path

    for entry in deprecation_map.get("entries", []):
        alias = str(entry.get("from") or "").strip()
        target = str(entry.get("to") or "").strip()
        if not alias or not target:
            continue
        deprecated_aliases[alias] = _canonicalize_path(target)

    return {
        "version": API_VERSION,
        "version_header": {
            "name": API_VERSION_HEADER,
            "value": API_VERSION,
        },
        "public_exempt_paths": list(PUBLIC_EXEMPT_PATHS),
        "public_exempt_prefixes": list(PUBLIC_EXEMPT_PREFIXES),
        "routes": {domain: dict(sorted(entries.items())) for domain, entries in sorted(contract_routes.items())},
        "websockets": dict(sorted(websocket_entries.items())),
        "canonical_paths": dict(sorted(canonical_paths.items())),
        "deprecated_aliases": dict(sorted(deprecated_aliases.items())),
    }


def _canonicalize_path(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized in PUBLIC_EXEMPT_PATHS or any(
        normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in PUBLIC_EXEMPT_PREFIXES
    ):
        return normalized
    if normalized.startswith(API_VERSION_PREFIX):
        return normalized
    if normalized == LEGACY_VERSION_PREFIX:
        return API_VERSION_PREFIX
    if normalized.startswith(f"{LEGACY_VERSION_PREFIX}/"):
        return f"{API_VERSION_PREFIX}/{normalized[len(f'{LEGACY_VERSION_PREFIX}/'):]}"
    if normalized == "/api":
        return API_VERSION_PREFIX
    if normalized.startswith("/api/"):
        return f"{API_VERSION_PREFIX}/{normalized[len('/api/'):].lstrip('/')}"
    return f"{API_VERSION_PREFIX}{normalized}"


def _route_aliases(legacy_path: str, canonical_path: str) -> set[str]:
    aliases = {canonical_path, _normalize_path(legacy_path)}
    legacy = _normalize_path(legacy_path)
    if canonical_path.startswith(f"{API_VERSION_PREFIX}/") and legacy.startswith("/api/"):
        aliases.add(f"/api/v1/{legacy[len('/api/'):].lstrip('/')}")
    elif not legacy.startswith(("/api/", "/auth/", "/ws/")) and legacy != "/":
        aliases.add(f"/api{legacy}")
        aliases.add(f"/api/v1{legacy}")
    elif canonical_path.startswith(f"{API_VERSION_PREFIX}/auth/") and legacy.startswith("/auth/"):
        suffix = legacy[len("/auth/") :]
        aliases.add(f"/api/auth/{suffix}")
        aliases.add(f"/api/v1/auth/{suffix}")
    elif canonical_path.startswith(f"{API_VERSION_PREFIX}/ws/") and legacy.startswith("/ws/"):
        suffix = legacy[len("/ws/") :]
        aliases.add(f"/api/v1/ws/{suffix}")
    return aliases


def _preferred_public_path(paths: list[str]) -> str:
    for path in paths:
        if path.startswith("/api/") or path.startswith("/auth/") or path.startswith("/ws/"):
            return path
    return paths[0]


def _route_key(method: str, path: str) -> str:
    slug = _NON_ALPHANUMERIC_RE.sub("_", path.strip("/")).strip("_").lower()
    slug = _PARAM_RE.sub("by_\\1", slug)
    if not slug:
        slug = "root"
    return f"{method.lower()}_{slug}"


def _normalize_path(path: str) -> str:
    raw = path.strip()
    if not raw:
        return "/"
    return "/" + raw.strip("/")


def _render_dart_binding(contract: dict[str, Any]) -> str:
    alias_map = dict(sorted(_flatten_aliases(contract).items()))
    canonical_paths = sorted(contract.get("canonical_paths", {}).keys())
    deprecated_aliases = dict(sorted((contract.get("deprecated_aliases") or {}).items()))
    lines = [
        "// GENERATED CODE - DO NOT EDIT BY HAND.",
        "// Source: shared/api_contract.json",
        "",
        f"const String gteApiContractVersion = '{contract['version']}';",
        f"const String gteApiVersionHeaderName = '{contract['version_header']['name']}';",
        f"const String gteApiVersionHeaderValue = '{contract['version_header']['value']}';",
        "",
        "const Set<String> gteApiPublicExemptPaths = <String>{",
    ]
    lines.extend(f"  '{path}'," for path in contract.get("public_exempt_paths", []))
    lines.extend(["};", "", "const Set<String> gteApiPublicExemptPrefixes = <String>{"])
    lines.extend(f"  '{path}'," for path in contract.get("public_exempt_prefixes", []))
    lines.extend(["};", "", "const Set<String> gteApiCanonicalPaths = <String>{"])
    lines.extend(f"  '{path}'," for path in canonical_paths)
    lines.extend(["};", "", "const Map<String, String> gteApiCanonicalPathByAlias = <String, String>{"])
    lines.extend(f"  '{alias}': '{target}'," for alias, target in alias_map.items())
    lines.extend(["};", "", "const Map<String, String> gteApiDeprecatedAliases = <String, String>{"])
    lines.extend(f"  '{alias}': '{target}'," for alias, target in deprecated_aliases.items())
    lines.extend(["};", ""])
    return "\n".join(lines)


def _flatten_aliases(contract: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for domain_entries in (contract.get("routes") or {}).values():
        for entry in domain_entries.values():
            canonical = entry["canonical_path"]
            for alias in entry.get("aliases", []):
                mapping[alias] = canonical
    for entry in (contract.get("websockets") or {}).values():
        canonical = entry["canonical_path"]
        for alias in entry.get("aliases", []):
            mapping[alias] = canonical
    return mapping


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

