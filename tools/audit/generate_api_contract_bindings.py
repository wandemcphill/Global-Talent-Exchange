from __future__ import annotations

import argparse
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
_RETIRED_TRANSFER_BID_REVIEW_QUEUE = "/" + "/".join(("api", "admin", "transfers", "bids", "review" + "-queue"))
_RETIRED_REALTIME_MATCH_GATEWAY = "/realtime/matches/{match_id}/gateway"
_RETIRED_REALTIME_MATCH_STREAM = "/realtime/matches/{match_id}/stream"
# Quarantined legacy pseudo-render payload. It may exist behind backend
# retirement guards temporarily, but generated contracts must never expose it.
_QUARANTINED_MATCH_VIEWER_ILLUSION = "/match-viewer/{match_key}/illusion"
_RETIRED_MATCH_ENGINE_RENDER_SYNC = "/match-engine/render-sync"
_RETIRED_MATCH_ENGINE_RENDER_SYNC_BY_KEY = "/match-engine/render-sync/{match_key}"


def _versioned_retired_variants(path: str) -> set[str]:
    return {
        path,
        f"/api{path}",
        f"/api/v1{path}",
        f"/api/v2{path}",
    }


RETIRED_PRODUCTION_PATHS = frozenset(
    {
        _RETIRED_TRANSFER_BID_REVIEW_QUEUE,
        _RETIRED_TRANSFER_BID_REVIEW_QUEUE.replace("/api/", "/api/v1/", 1),
        _RETIRED_TRANSFER_BID_REVIEW_QUEUE.replace("/api/", "/api/v2/", 1),
        *_versioned_retired_variants(_RETIRED_REALTIME_MATCH_GATEWAY),
        *_versioned_retired_variants(_RETIRED_REALTIME_MATCH_STREAM),
        *_versioned_retired_variants(_QUARANTINED_MATCH_VIEWER_ILLUSION),
        *_versioned_retired_variants(_RETIRED_MATCH_ENGINE_RENDER_SYNC),
        *_versioned_retired_variants(_RETIRED_MATCH_ENGINE_RENDER_SYNC_BY_KEY),
    }
)
_PARAM_RE = re.compile(r"\{([^}]+)\}")
_NON_ALPHANUMERIC_RE = re.compile(r"[^a-zA-Z0-9]+")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate GTEX API contract artifacts.",
    )
    parser.add_argument(
        "--from-shared",
        "--dart-only",
        action="store_true",
        dest="from_shared",
        help=(
            "Render only the frontend Dart binding from shared/api_contract.json. "
            "Use this when the shared contract has been patched directly and the "
            "docs route inventories have not caught up yet."
        ),
    )
    args = parser.parse_args()
    if args.from_shared:
        contract = _read_json(CONTRACT_PATH)
        FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        DART_BINDING_PATH.write_text(_render_dart_binding(contract), encoding="utf-8")
        return 0

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
        effective_paths = [str(path).strip() for path in (route.get("effective_paths") or []) if str(path).strip()]
        if not method or not legacy_path:
            continue
        route_inventory[(method, legacy_path)] = route
        public_aliases = effective_paths or [legacy_path]
        preferred_source_path = _preferred_public_path(public_aliases)
        canonical_path = _canonicalize_path(preferred_source_path)
        canonical_path = _canonical_payment_path(canonical_path)
        if _is_retired_production_path(canonical_path):
            continue
        aliases = set()
        for alias_source in {legacy_path, *public_aliases}:
            if _is_retired_production_path(alias_source):
                continue
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
        if _is_retired_production_path(alias) or _is_retired_production_path(target):
            continue
        deprecated_aliases[alias] = _canonicalize_path(target)

    _remove_noncanonical_payment_aliases(contract_routes, websocket_entries, deprecated_aliases)
    canonical_paths = _canonical_paths_from(contract_routes, websocket_entries)

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


def _canonical_payment_path(path: str) -> str:
    if path == f"{API_VERSION_PREFIX}/wallets/providers/{{provider_key}}/webhook":
        return f"{API_VERSION_PREFIX}/wallets/providers/korapay/webhook"
    return path


def _is_retired_production_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in RETIRED_PRODUCTION_PATHS or _canonicalize_path(normalized) in RETIRED_PRODUCTION_PATHS


def _route_aliases(legacy_path: str, canonical_path: str) -> set[str]:
    if _is_canonical_payment_only_path(canonical_path):
        return {canonical_path}
    if canonical_path.startswith(f"{API_VERSION_PREFIX}/auth/"):
        return {canonical_path}
    aliases = {canonical_path, _normalize_path(legacy_path)}
    legacy = _normalize_path(legacy_path)
    if (
        canonical_path.startswith(f"{API_VERSION_PREFIX}/")
        and legacy.startswith("/api/")
        and not legacy.startswith(f"{API_VERSION_PREFIX}/")
    ):
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


def _is_canonical_payment_only_path(path: str) -> bool:
    return path.startswith(f"{API_VERSION_PREFIX}/integrations/payments/") or path == (
        f"{API_VERSION_PREFIX}/wallets/providers/korapay/webhook"
    )


def _remove_noncanonical_payment_aliases(
    contract_routes: dict[str, dict[str, dict[str, Any]]],
    websocket_entries: dict[str, dict[str, Any]],
    deprecated_aliases: dict[str, str],
) -> None:
    for domain_entries in contract_routes.values():
        for route_key, entry in list(domain_entries.items()):
            canonical = _canonical_payment_path(str(entry.get("canonical_path") or ""))
            if not _is_canonical_payment_only_path(canonical):
                continue
            entry["canonical_path"] = canonical
            entry["aliases"] = [canonical]
            expected_key = _route_key(str(entry.get("method") or ""), canonical)
            if expected_key != route_key:
                domain_entries[expected_key] = entry
                del domain_entries[route_key]
    for route_key, entry in list(websocket_entries.items()):
        canonical = _canonical_payment_path(str(entry.get("canonical_path") or ""))
        if not _is_canonical_payment_only_path(canonical):
            continue
        entry["canonical_path"] = canonical
        entry["aliases"] = [canonical]
        expected_key = _route_key(str(entry.get("method") or ""), canonical)
        if expected_key != route_key:
            websocket_entries[expected_key] = entry
            del websocket_entries[route_key]
    for alias, target in list(deprecated_aliases.items()):
        canonical = _canonical_payment_path(target)
        if _is_canonical_payment_only_path(canonical):
            del deprecated_aliases[alias]


def _canonical_paths_from(
    contract_routes: dict[str, dict[str, dict[str, Any]]],
    websocket_entries: dict[str, dict[str, Any]],
) -> dict[str, str]:
    canonical_paths: dict[str, str] = {}
    for domain_entries in contract_routes.values():
        for route_key, entry in domain_entries.items():
            canonical_paths[str(entry["canonical_path"])] = route_key
    for route_key, entry in websocket_entries.items():
        canonical_paths[str(entry["canonical_path"])] = route_key
    return canonical_paths


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
