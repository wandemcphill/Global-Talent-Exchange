from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"
FRONTEND_LIB = REPO_ROOT / "frontend" / "lib"
DOCS_DIR = REPO_ROOT / "docs"
MODULES_FILE = BACKEND_APP / "modules.py"
RENDER_FILE = REPO_ROOT / "render.yaml"
APP_CONFIG_FILE = FRONTEND_LIB / "app" / "gte_app_config.dart"
FRONTEND_AUDIT_EXCLUDED_FILE_FRAGMENTS = (
    "frontend/lib/data/generated/gte_api_contract.g.dart",
    "frontend/lib/data/gte_api_contract.dart",
    "frontend/lib/features/shared/data/gte_feature_support.dart",
)

ROUTER_DECLARATION_RE = re.compile(
    r"(?P<name>\w+)\s*=\s*APIRouter\((?P<args>.*?)\)",
    re.DOTALL,
)
PREFIX_RE = re.compile(r"prefix\s*=\s*['\"](?P<prefix>[^'\"]+)['\"]")
ROUTE_DECORATOR_RE = re.compile(
    r"@(?P<router>\w+)\.(?P<method>get|post|put|patch|delete|websocket)\("
    r"\s*['\"](?P<path>[^'\"]*)['\"](?P<args>.*?)\)",
    re.DOTALL,
)
DECORATED_FUNCTION_RE = re.compile(
    r"(?P<decorators>(?:@\w+\.(?:get|post|put|patch|delete|websocket)\(.*?\)\s*)+)"
    r"(?:async\s+)?def\s+(?P<handler>\w+)\((?P<signature>.*?)\)"
    r"(?:\s*->\s*(?P<returns>[^:\n]+))?:",
    re.DOTALL,
)
INCLUDE_ROUTER_RE = re.compile(r"(?P<parent>\w+)\.include_router\(\s*(?P<child>\w+)")
RESPONSE_MODEL_RE = re.compile(r"response_model\s*=\s*(?P<model>[^,\)\n]+)")
MODULE_ENTRY_RE = re.compile(
    r"_module\(\s*['\"](?P<name>[^'\"]+)['\"]\s*,(?P<body>.*?)\)",
    re.DOTALL,
)
ROUTER_PATH_RE = re.compile(r"router_path\s*=\s*['\"](?P<router_path>[^'\"]+)['\"]")
API_ALIAS_RE = re.compile(r"with_api_alias\s*=\s*True")
API_ONLY_RE = re.compile(r"api_only\s*=\s*True")
STRING_PATH_RE = re.compile(r"['\"](?P<path>/(?:api|auth|tts|generated-media|realtime|ws)[^'\"]*)['\"]")
HARDCODED_URL_RE = re.compile(r"['\"](?P<url>(?:https?|wss?)://[^'\"]+)['\"]")
METHOD_CONTEXT_RE = re.compile(r"['\"](?P<method>GET|POST|PUT|PATCH|DELETE)['\"]")
CALL_CONTEXT_RE = re.compile(r"(?P<call>_request|request|resolveUri|uriFor|client\.request)\s*\($")


@dataclass(frozen=True)
class ModuleMount:
    name: str
    router_path: str
    transform: str


def main() -> int:
    backend_routes, module_mounts = _scan_backend_routes()
    frontend_calls = _scan_frontend_calls()
    route_map = _build_route_map(backend_routes)
    classifications = _classify_routes(backend_routes)
    mismatches, critical_issues = _analyze_mismatches(backend_routes, frontend_calls)
    final_api_schema, deprecation_map = _build_canonical_contract(
        backend_routes,
        frontend_calls,
        classifications,
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(DOCS_DIR / "ROUTE_MAP.json", route_map)
    _write_markdown(
        DOCS_DIR / "ROUTE_CLASSIFICATION.md",
        _render_route_classification(classifications, module_mounts),
    )
    _write_json(DOCS_DIR / "FRONTEND_API_MAP.json", _render_frontend_api_map(frontend_calls))
    _write_markdown(DOCS_DIR / "WEB_MOBILE_DIFF.md", _render_web_mobile_diff(frontend_calls))
    _write_markdown(DOCS_DIR / "MISMATCH_REPORT.md", _render_mismatch_report(mismatches))
    _write_markdown(DOCS_DIR / "CRITICAL_ISSUES.md", _render_critical_issues(critical_issues))
    _write_json(DOCS_DIR / "FINAL_API_SCHEMA.json", final_api_schema)
    _write_json(DOCS_DIR / "DEPRECATION_MAP.json", deprecation_map)
    _write_markdown(
        DOCS_DIR / "PRE_DELETION_VALIDATION.md",
        _render_pre_deletion_validation(mismatches, deprecation_map["entries"]),
    )
    _write_markdown(DOCS_DIR / "ENV_AUDIT.md", _render_env_audit(frontend_calls))
    return 0


def _scan_backend_routes() -> tuple[list[dict], list[ModuleMount]]:
    modules_text = MODULES_FILE.read_text(encoding="utf-8", errors="ignore")
    module_mounts: list[ModuleMount] = []
    mount_lookup: dict[tuple[str, str], list[ModuleMount]] = defaultdict(list)
    for match in MODULE_ENTRY_RE.finditer(modules_text):
        body = match.group("body")
        router_path_match = ROUTER_PATH_RE.search(body)
        if not router_path_match:
            continue
        transform = "none"
        if API_ALIAS_RE.search(body):
            transform = "with_api_alias"
        elif API_ONLY_RE.search(body):
            transform = "api_only"
        mount = ModuleMount(
            name=match.group("name"),
            router_path=router_path_match.group("router_path"),
            transform=transform,
        )
        module_mounts.append(mount)
        module_path, router_var = mount.router_path.split(":")
        mount_lookup[(module_path, router_var)].append(mount)

    routes: list[dict] = []
    for file_path in BACKEND_APP.rglob("*.py"):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        module_path = "app." + ".".join(file_path.relative_to(BACKEND_APP).with_suffix("").parts)
        router_prefixes: dict[str, str] = {}
        for match in ROUTER_DECLARATION_RE.finditer(text):
            prefix_match = PREFIX_RE.search(match.group("args"))
            router_prefixes[match.group("name")] = _normalize_path(prefix_match.group("prefix") if prefix_match else "")
        parent_routers: dict[str, list[str]] = defaultdict(list)
        for match in INCLUDE_ROUTER_RE.finditer(text):
            parent_routers[match.group("child")].append(match.group("parent"))

        for function_match in DECORATED_FUNCTION_RE.finditer(text):
            decorators = function_match.group("decorators")
            request_shape = _infer_request_shape(function_match.group("signature"))
            returns = function_match.group("returns").strip() if function_match.group("returns") else None
            handler = function_match.group("handler")
            for match in ROUTE_DECORATOR_RE.finditer(decorators):
                router_var = match.group("router")
                route_path = match.group("path")
                local_paths = [
                    _join_paths(prefix, route_path)
                    for prefix in _router_prefix_paths(router_var, router_prefixes, parent_routers)
                ]
                local_path = local_paths[0]
                mounts = _route_mounts(module_path, router_var, mount_lookup, parent_routers)
                effective_paths = _effective_paths(local_paths, mounts)
                response_model_match = RESPONSE_MODEL_RE.search(match.group("args"))
                routes.append(
                    {
                        "method": match.group("method").upper(),
                        "path": local_path,
                        "effective_paths": effective_paths,
                        "file": str(file_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "handler": handler,
                        "router_variable": router_var,
                        "module_path": module_path,
                        "module_mounts": [mount.name for mount in mounts],
                        "request_shape": request_shape,
                        "response_shape": {
                            "response_model": (
                                response_model_match.group("model").strip() if response_model_match else None
                            ),
                            "returns": returns,
                        },
                        "version": _infer_version(module_path, effective_paths),
                        "domain": _infer_domain(module_path, mounts),
                    }
                )
    return routes, module_mounts


def _scan_frontend_calls() -> list[dict]:
    calls: list[dict] = []
    for file_path in FRONTEND_LIB.rglob("*.dart"):
        rel = str(file_path.relative_to(REPO_ROOT)).replace("\\", "/")
        if any(fragment in rel for fragment in FRONTEND_AUDIT_EXCLUDED_FILE_FRAGMENTS):
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        base_url_source = _infer_base_url_source(text)
        for path_match in STRING_PATH_RE.finditer(text):
            endpoint = path_match.group("path")
            context_window = text[max(0, path_match.start() - 220) : path_match.start() + 80]
            method_match = METHOD_CONTEXT_RE.search(context_window)
            call_match = CALL_CONTEXT_RE.search(context_window.strip())
            calls.append(
                {
                    "file": rel,
                    "transport_call": call_match.group("call") if call_match else "string_reference",
                    "method": method_match.group("method") if method_match else "INFERRED",
                    "endpoint": endpoint,
                    "expected_shape": _infer_expected_shape(text, path_match.start()),
                    "base_url_source": base_url_source,
                    "platforms": ["web", "mobile"],
                }
            )
        for url_match in HARDCODED_URL_RE.finditer(text):
            url = url_match.group("url")
            if "fixture.invalid" in url or "runtime-config.invalid" in url:
                continue
            calls.append(
                {
                    "file": rel,
                    "transport_call": "hardcoded_url",
                    "method": "N/A",
                    "endpoint": url,
                    "expected_shape": None,
                    "base_url_source": base_url_source,
                    "platforms": ["web", "mobile"],
                }
            )
    return _dedupe_calls(calls)


def _build_route_map(backend_routes: list[dict]) -> dict:
    return {
        "generated_from": "tools/audit/generate_contract_audit.py",
        "route_count": len(backend_routes),
        "routes": sorted(
            backend_routes,
            key=lambda route: (route["domain"], route["method"], route["path"], route["file"]),
        ),
    }


def _classify_routes(backend_routes: list[dict]) -> dict[str, list[dict]]:
    routes_by_signature: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for route in backend_routes:
        for effective_path in route["effective_paths"]:
            routes_by_signature[(route["method"], _normalize_signature(effective_path))].append(route)

    keep: list[dict] = []
    migrate: list[dict] = []
    delete: list[dict] = []
    for signature, routes in routes_by_signature.items():
        ordered = sorted(routes, key=_route_rank, reverse=True)
        canonical = ordered[0]
        keep.append(
            {
                "signature": f"{signature[0]} {signature[1]}",
                "route": _route_descriptor(canonical),
                "reason": _canonical_reason(canonical),
            }
        )
        for legacy in ordered[1:]:
            record = {
                "signature": f"{signature[0]} {signature[1]}",
                "route": _route_descriptor(legacy),
                "target": canonical["effective_paths"][0],
                "reason": _legacy_reason(legacy, canonical),
            }
            if legacy["version"] == "v1" or "api_v1" in legacy["module_path"]:
                migrate.append(record)
            else:
                delete.append(record)
    return {
        "KEEP": sorted(keep, key=lambda item: item["signature"]),
        "MIGRATE_TO": sorted(migrate, key=lambda item: item["signature"]),
        "DELETE": sorted(delete, key=lambda item: item["signature"]),
    }


def _analyze_mismatches(
    backend_routes: list[dict],
    frontend_calls: list[dict],
) -> tuple[list[dict], list[dict]]:
    backend_paths = {path for route in backend_routes for path in route["effective_paths"]}
    mismatches: list[dict] = []
    critical: list[dict] = []

    if any(call["file"].endswith("gte_api_repository.dart") for call in frontend_calls):
        critical.append(
            {
                "severity": "HIGH",
                "title": "Shared Flutter repository still forces /api/v1",
                "details": (
                    "frontend/lib/data/gte_api_repository.dart rewrites most '/api/*' "
                    "requests through gteVersionedApiPath(), keeping the primary app shell on "
                    "legacy api_v1 contracts even when richer canonical routes exist."
                ),
                "evidence": ["frontend/lib/data/gte_api_repository.dart: gteVersionedApiPath"],
            }
        )

    critical.append(
        {
            "severity": "HIGH",
            "title": "Parallel routing and API access patterns still coexist",
            "details": (
                "The premium shell now mounts through a central GoRouter, but feature screens "
                "and older API helpers still retain imperative or legacy access paths. This is "
                "the main reason updates do not feel uniformly reflected across web and mobile."
            ),
            "evidence": [
                "frontend/lib/router/app_router.dart",
                "frontend/lib/navigation/app_router.dart",
                "frontend/lib/features/app_routes/gte_navigation_helpers.dart",
            ],
        }
    )

    for call in frontend_calls:
        endpoint = call["endpoint"]
        if endpoint.startswith(("http://", "https://", "ws://", "wss://")):
            continue
        runtime_endpoint = _resolve_runtime_endpoint(endpoint)
        if runtime_endpoint not in backend_paths and endpoint not in backend_paths:
            mismatches.append(
                {
                    "severity": "HIGH" if endpoint.startswith("/api/") else "MEDIUM",
                    "file": call["file"],
                    "method": call["method"],
                    "endpoint": endpoint,
                    "runtime_endpoint": runtime_endpoint,
                    "issue": "No exact backend route match found in static route inventory.",
                }
            )
        if endpoint.startswith("/api/") and runtime_endpoint.startswith("/api/v2/"):
            mismatches.append(
                {
                    "severity": "MEDIUM",
                    "file": call["file"],
                    "method": call["method"],
                    "endpoint": endpoint,
                    "runtime_endpoint": runtime_endpoint,
                    "issue": "Frontend call is version-upgraded into legacy api_v1 space at runtime.",
                }
            )
        if call["base_url_source"] == "hardcoded_localhost":
            mismatches.append(
                {
                    "severity": "MEDIUM",
                    "file": call["file"],
                    "method": call["method"],
                    "endpoint": endpoint,
                    "runtime_endpoint": runtime_endpoint,
                    "issue": "Hardcoded localhost fallback bypasses the shared runtime base-url contract.",
                }
            )
    return mismatches, critical


def _build_canonical_contract(
    backend_routes: list[dict],
    frontend_calls: list[dict],
    classifications: dict[str, list[dict]],
) -> tuple[dict, dict]:
    keep_by_domain: dict[str, list[dict]] = defaultdict(list)
    backend_by_effective_path: dict[str, list[dict]] = defaultdict(list)
    for route in backend_routes:
        for path in route["effective_paths"]:
            backend_by_effective_path[path].append(route)

    for entry in classifications["KEEP"]:
        descriptor = entry["route"]
        route = next(
            route
            for route in backend_routes
            if route["file"] == descriptor["file"]
            and route["handler"] == descriptor["handler"]
            and descriptor["path"] in route["effective_paths"]
        )
        keep_by_domain[route["domain"]].append(
            {
                "method": route["method"],
                "path": descriptor["path"],
                "handler": route["handler"],
                "response_model": route["response_shape"]["response_model"],
            }
        )

    deprecation_entries: list[dict] = []
    for call in frontend_calls:
        endpoint = call["endpoint"]
        runtime_endpoint = _resolve_runtime_endpoint(endpoint)
        if runtime_endpoint.startswith("/api/v2/"):
            unversioned = "/api/" + runtime_endpoint[len("/api/v2/") :]
            if backend_by_effective_path.get(unversioned):
                deprecation_entries.append(
                    {
                        "consumer": call["file"],
                        "from": runtime_endpoint,
                        "to": unversioned,
                        "reason": "Canonical non-v1 route exists and should replace the legacy api_v1 contract.",
                    }
                )

    final_api_schema = {
        "domains": {
            domain: sorted(routes, key=lambda item: (item["path"], item["method"]))
            for domain, routes in sorted(keep_by_domain.items())
        }
    }
    return final_api_schema, {"entries": _dedupe_dicts(deprecation_entries)}


def _render_route_classification(classifications: dict[str, list[dict]], mounts: list[ModuleMount]) -> str:
    duplicate_mounts = Counter(mount.router_path for mount in mounts)
    lines = [
        "# Route Classification",
        "",
        "Generated deterministically from `tools/audit/generate_contract_audit.py`.",
        "",
        "## Module Mount Summary",
        "",
        f"- Backend module mounts discovered: **{len(mounts)}**",
        f"- Router paths mounted more than once: **{sum(1 for count in duplicate_mounts.values() if count > 1)}**",
        "",
    ]
    for section in ("KEEP", "MIGRATE_TO", "DELETE"):
        lines.extend([f"## {section}", ""])
        entries = classifications[section]
        if not entries:
            lines.extend(["- None", ""])
            continue
        for entry in entries[:200]:
            route = entry["route"]
            target = f" -> `{entry['target']}`" if "target" in entry else ""
            lines.append(
                f"- `{entry['signature']}`: `{route['path']}` in `{route['file']}` ({route['handler']}){target} - {entry['reason']}"
            )
        if len(entries) > 200:
            lines.append(f"- ... and {len(entries) - 200} more")
        lines.append("")
    return "\n".join(lines)


def _render_frontend_api_map(frontend_calls: list[dict]) -> dict:
    return {
        "generated_from": "tools/audit/generate_contract_audit.py",
        "call_count": len(frontend_calls),
        "calls": sorted(
            frontend_calls,
            key=lambda call: (call["file"], call["endpoint"], call["method"]),
        ),
    }


def _render_web_mobile_diff(frontend_calls: list[dict]) -> str:
    shared_files = sorted({call["file"] for call in frontend_calls})
    hardcoded = sorted(
        {
            f"{call['file']} -> {call['endpoint']}"
            for call in frontend_calls
            if call["base_url_source"] == "hardcoded_localhost"
        }
    )
    lines = [
        "# Web vs Mobile API Diff",
        "",
        "GTEX currently uses a **single Flutter client codebase** for both web and mobile.",
        "There is no separate Next.js/React web frontend in this repository to reconcile against.",
        "",
        "## Shared Source of Truth",
        "",
        f"- Shared Flutter client files with API calls discovered: **{len(shared_files)}**",
        "- Web and mobile therefore inherit the same endpoint usage and the same stale/legacy risks.",
        "",
        "## Divergence Risks",
        "",
        "- The main risk is runtime configuration drift, not separate platform code.",
        "- Hardcoded localhost defaults still exist in some data clients and can bypass the runtime env contract.",
        "",
        "### Hardcoded localhost callsites",
        "",
    ]
    lines.extend([*(f"- `{item}`" for item in hardcoded)] if hardcoded else ["- None"])
    return "\n".join(lines)


def _render_mismatch_report(mismatches: list[dict]) -> str:
    lines = [
        "# Mismatch Report",
        "",
        f"- Total mismatches detected: **{len(mismatches)}**",
        "",
    ]
    for severity in ("HIGH", "MEDIUM", "LOW"):
        scoped = [item for item in mismatches if item["severity"] == severity]
        lines.extend([f"## {severity}", ""])
        if not scoped:
            lines.extend(["- None", ""])
            continue
        for item in scoped[:200]:
            lines.append(
                f"- `{item['file']}` {item['method']} `{item['endpoint']}` -> `{item['runtime_endpoint']}`: {item['issue']}"
            )
        if len(scoped) > 200:
            lines.append(f"- ... and {len(scoped) - 200} more")
        lines.append("")
    return "\n".join(lines)


def _render_critical_issues(issues: list[dict]) -> str:
    lines = ["# Critical Issues", ""]
    for issue in issues:
        lines.extend(
            [
                f"## {issue['severity']} - {issue['title']}",
                "",
                issue["details"],
                "",
                "Evidence:",
            ]
        )
        lines.extend(f"- `{evidence}`" for evidence in issue["evidence"])
        lines.append("")
    return "\n".join(lines)


def _render_pre_deletion_validation(mismatches: list[dict], deprecations: list[dict]) -> str:
    blocking = [item for item in mismatches if item["severity"] in {"HIGH", "MEDIUM"}]
    lines = [
        "# Pre-Deletion Validation",
        "",
        "## Status",
        "",
    ]
    if blocking or deprecations:
        lines.extend(
            [
                "**STOP** - destructive cleanup is not yet safe.",
                "",
                "Frontend references and route mismatches still remain, especially around the shared Flutter repository and legacy `/api/v1` usage.",
                "",
                f"- Blocking mismatches: **{len(blocking)}**",
                f"- Pending legacy route migrations: **{len(deprecations)}**",
                "- Required next move: migrate remaining consumers onto the canonical routes in `FINAL_API_SCHEMA.json`, then re-scan.",
            ]
        )
    else:
        lines.extend(
            [
                "**PASS** - no remaining frontend references to deprecated routes were detected in the static scan.",
                "",
                "- Proceed with hard cleanup only after a runtime smoke pass.",
            ]
        )
    return "\n".join(lines)


def _render_env_audit(frontend_calls: list[dict]) -> str:
    render_text = RENDER_FILE.read_text(encoding="utf-8", errors="ignore")
    config_text = APP_CONFIG_FILE.read_text(encoding="utf-8", errors="ignore")
    hardcoded_count = sum(1 for call in frontend_calls if call["base_url_source"] == "hardcoded_localhost")
    return "\n".join(
        [
            "# Environment and Deployment Audit",
            "",
            "## Backend / Web Deploy",
            "",
            "- `render.yaml` configures `gtex-web` with `GTE_API_BASE_URL=https://gtex-api.onrender.com` and `GTE_BACKEND_MODE=live`.",
            "- `render.yaml` configures `gtex-api` as the single backend origin for production traffic.",
            "",
            "## Flutter Runtime Config",
            "",
            "- `frontend/lib/app/gte_app_config.dart` uses `GTE_API_BASE_URL` and `GTE_BACKEND_MODE` as the canonical runtime inputs.",
            "- Fixture mode is intentionally gated to tests; live is the default runtime path.",
            "",
            "## Drift Risks",
            "",
            f"- Hardcoded localhost or alternate base-url defaults detected in frontend data files: **{hardcoded_count}**",
            "- These should be consolidated behind the shared runtime config before any destructive backend route cleanup.",
            "",
            "## Source Evidence",
            "",
            f"- `render.yaml` contains `GTE_API_BASE_URL`: {'GTE_API_BASE_URL' in render_text}",
            f"- `gte_app_config.dart` contains `GTE_API_BASE_URL`: {'GTE_API_BASE_URL' in config_text}",
        ]
    )


def _route_descriptor(route: dict) -> dict:
    return {
        "path": route["effective_paths"][0],
        "file": route["file"],
        "handler": route["handler"],
    }


def _canonical_reason(route: dict) -> str:
    if route["version"] == "v1":
        return "Only v1 route discovered for this signature; keep until a richer replacement exists."
    if route["module_mounts"]:
        return "Mounted through the newer module system and preferred over legacy api_v1 handlers."
    return "Highest-ranked non-v1 route for this signature."


def _legacy_reason(legacy: dict, canonical: dict) -> str:
    if legacy["version"] == "v1" or "api_v1" in legacy["module_path"]:
        return f"Legacy api_v1 surface shadowed by `{canonical['effective_paths'][0]}`."
    return f"Duplicate or lower-ranked surface shadowed by `{canonical['effective_paths'][0]}`."


def _route_rank(route: dict) -> tuple[int, int, int]:
    non_v1 = 0 if route["version"] == "v1" else 1
    canonical_mount = 1 if route["module_mounts"] else 0
    richer = 1 if route["response_shape"]["response_model"] else 0
    return (non_v1, canonical_mount, richer)


def _effective_paths(local_paths: list[str], mounts: list[ModuleMount]) -> list[str]:
    paths: list[str] = []
    for local_path in local_paths:
        if mounts:
            for mount in mounts:
                if mount.transform == "with_api_alias":
                    paths.extend([local_path, _join_paths("/api", local_path)])
                elif mount.transform == "api_only":
                    paths.append(_join_paths("/api", local_path))
                else:
                    paths.append(local_path)
        else:
            paths.append(local_path)
    return sorted(dict.fromkeys(_normalize_path(path) for path in paths))


def _router_prefix_paths(
    router_var: str,
    router_prefixes: dict[str, str],
    parent_routers: dict[str, list[str]],
) -> list[str]:
    prefixes = [_normalize_path(router_prefixes.get(router_var, ""))]
    for parent in parent_routers.get(router_var, []):
        parent_prefixes = _router_prefix_paths(parent, router_prefixes, parent_routers)
        current_prefix = _normalize_path(router_prefixes.get(router_var, ""))
        for parent_prefix in parent_prefixes:
            prefixes.append(_join_paths(parent_prefix, current_prefix))
    return sorted(dict.fromkeys(prefixes))


def _route_mounts(
    module_path: str,
    router_var: str,
    mount_lookup: dict[tuple[str, str], list[ModuleMount]],
    parent_routers: dict[str, list[str]],
) -> list[ModuleMount]:
    mounts: list[ModuleMount] = []
    mounts.extend(mount_lookup.get((module_path, router_var), []))
    for parent in parent_routers.get(router_var, []):
        mounts.extend(_route_mounts(module_path, parent, mount_lookup, parent_routers))
    deduped: dict[tuple[str, str, str], ModuleMount] = {}
    for mount in mounts:
        deduped[(mount.name, mount.router_path, mount.transform)] = mount
    return list(deduped.values())


def _normalize_path(path: str) -> str:
    raw = path.strip()
    if not raw:
        return "/"
    normalized = "/" + raw.strip("/")
    return normalized.replace("//", "/")


def _join_paths(prefix: str, path: str) -> str:
    prefix = _normalize_path(prefix) if prefix else ""
    path = _normalize_path(path)
    if not prefix or prefix == "/":
        return path
    if path == "/":
        return prefix
    return _normalize_path(prefix.rstrip("/") + "/" + path.lstrip("/"))


def _normalize_signature(path: str) -> str:
    return re.sub(r"/\{[^/]+\}", "/{}", path)


def _infer_request_shape(signature: str) -> dict:
    params = []
    for raw_param in signature.split(","):
        candidate = raw_param.strip()
        if not candidate or candidate in {"self", "cls"}:
            continue
        name = candidate.split(":")[0].split("=")[0].strip()
        if name:
            params.append(name)
    return {"parameters": params}


def _infer_domain(module_path: str, mounts: list[ModuleMount]) -> str:
    if mounts:
        return mounts[0].name.split("_")[0]
    leaf = module_path.split(".")[-2] if module_path.endswith(".router") else module_path.split(".")[-1]
    return leaf.split("_")[0]


def _infer_version(module_path: str, effective_paths: list[str]) -> str:
    if "api_v1" in module_path or any(path.startswith("/api/v1") for path in effective_paths):
        return "v1"
    return "canonical"


def _infer_expected_shape(text: str, start: int) -> str | None:
    window = text[start : start + 500]
    if re.search(r"_asMap|GteJson\.map|Map<String,\s*Object\?>", window):
        return "map/envelope"
    if re.search(r"_asList|List<", window):
        return "list"
    return None


def _infer_base_url_source(text: str) -> str:
    if "http://127.0.0.1:8000" in text:
        return "hardcoded_localhost"
    if "GTE_API_BASE_URL" in text or "resolveGteApiBaseUrl" in text:
        return "runtime_env"
    return "injected"


def _resolve_runtime_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if endpoint.startswith("/api/") and not endpoint.startswith("/api/v2/"):
        return "/api/v2/" + endpoint[len("/api/") :]
    if endpoint == "/api":
        return "/api/v2"
    if endpoint.startswith("/auth/"):
        return endpoint
    return endpoint


def _dedupe_calls(calls: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for call in calls:
        key = (
            call["file"],
            call["transport_call"],
            call["method"],
            call["endpoint"],
            call["base_url_source"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(call)
    return deduped


def _dedupe_dicts(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        key = json.dumps(item, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_markdown(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
