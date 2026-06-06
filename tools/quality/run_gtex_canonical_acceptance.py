from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib import error, parse, request

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "shared" / "api_contract.json"
GENERATED_FRONTEND_CONTRACT_PATH = REPO_ROOT / "frontend" / "lib" / "data" / "generated" / "gte_api_contract.g.dart"
FRONTEND_APP_ROUTER_PATH = REPO_ROOT / "frontend" / "lib" / "router" / "app_router.dart"
FRONTEND_ROUTE_CONSTANTS_PATH = REPO_ROOT / "frontend" / "lib" / "router" / "route_constants.dart"
FRONTEND_LEGACY_ROUTER_PATH = REPO_ROOT / "frontend" / "lib" / "navigation" / "app_router.dart"
FRONTEND_DESTINATIONS_PATH = REPO_ROOT / "frontend" / "lib" / "navigation" / "app_destinations.dart"
FRONTEND_ROUTE_COVERAGE_TEST_PATH = REPO_ROOT / "frontend" / "test" / "router" / "route_coverage_test.dart"
MATCH_SIMULATION_ENGINE_PATH = (
    REPO_ROOT / "frontend" / "lib" / "features" / "match_center" / "data" / "match" / "match_simulation_engine.dart"
)
PITCH_2D_TELEMETRY_PATH = (
    REPO_ROOT / "frontend" / "lib" / "features" / "match_center" / "widgets" / "pitch_2d_telemetry.dart"
)
REAL_MATCH_SCENE_DIRECTOR_PATH = (
    REPO_ROOT / "frontend" / "lib" / "features" / "match_center" / "presentation" / "real_match_scene_director.dart"
)

OWNED_PREFIXES = ("scripts/", "tools/")
CANONICAL_PRODUCTION_APP_PATHS = {
    "/app/world",
    "/app/market",
    "/app/club",
    "/app/compete",
    "/app/capital",
    "/app/community",
    "/app/creator",
    "/app/admin",
}
REQUIRED_CORE_PATHS = {"/health", "/ready", "/openapi.json"}
REQUIRED_CANONICAL_PATHS = {
    "/api/v2/match-viewer/{match_key}",
    "/api/v2/match-viewer/{match_key}/session",
    "/api/v2/matches/{match_id}/spectate",
}
REQUIRED_CANONICAL_WEBSOCKET_PATHS = {
    "/api/v2/matches/{match_id}/stream",
}
FORBIDDEN_PAYSTACK_TOKEN = "paystack"
FORBIDDEN_PUBLIC_3D_ROUTE_RE = re.compile(
    r"(?i)(/matches?/[^'\"\s,)]*3d|/match-?3d|/3d-match|unity-access|legacy-runtime-access|unity_match_3d)"
)
FORBIDDEN_PRODUCTION_3D_TOKENS = (
    "GtexMatch3dScreen",
    "MatchNative3d",
    "NativeMatch3dSurface",
    "match_3d/",
    "widgets/match_3d",
)
ALLOWED_3D_FRAGMENTS = (
    "/internal/dev/match-runtime",
    "/internal/dev/native-match-runtime",
)
FORBIDDEN_NONCANONICAL_PAYMENT_RAIL_RE = re.compile(
    r"\b(?:flutterwave|paypal|monnify|opay|coinbase|"
    r"mobile\s+money|m-?pesa)\b|"
    r"\b(?:payment|provider|checkout|gateway|rail)s?\b[^\n]{0,48}\b"
    r"(?:stripe|crypto(?:currency)?)\b|"
    r"\b(?:stripe|crypto(?:currency)?)\b[^\n]{0,48}\b"
    r"(?:payment|provider|checkout|gateway|rail)s?\b",
    re.IGNORECASE,
)
FORBIDDEN_FAKE_AUTHORITY_RE = re.compile(
    r"\b(?:fake|mock|dummy|sample|hardcoded|synthetic|"
    r"client[- ]generated|client[- ]side|local[- ]only|fallback)\s+"
    r"(?:balances?|scores?|bids?|rankings?|fixtures?)\b|"
    r"\b(?:balances?|scores?|bids?|rankings?|fixtures?)\s+"
    r"(?:fake|mock|dummy|sample|hardcoded|synthetic|"
    r"client[- ]generated|client[- ]side|local[- ]only|fallback)\b",
    re.IGNORECASE,
)
FORBIDDEN_FIXTURE_MODE_ACTIVATION_RE = re.compile(
    r"\b(?:kFixtureMode|GtexFixtureMode|fixtureMode|"
    r"enableFixtureMode|enableCapitalFixtures)\b\s*[:=]\s*true\b|"
    r"\b(?:mode|backendMode)\s*:\s*GteBackendMode\.fixture\b|"
    r"\ballowFixtureMode\s*\?\s*GteBackendMode\.fixture\b|"
    r"\bbool\.fromEnvironment\([^\n)]*(?:fixtureMode|FixtureMode|"
    r"GtexFixtureMode|kFixtureMode)[^\n)]*defaultValue\s*:\s*true",
    re.IGNORECASE,
)
PAYMENT_RAIL_SCAN_PATHS = (
    REPO_ROOT / "backend" / "app" / "admin_finance",
    REPO_ROOT / "backend" / "app" / "services" / "payment_gateway_service.py",
    REPO_ROOT / "backend" / "app" / "wallets",
    REPO_ROOT / "frontend" / "lib" / "features" / "capital",
    REPO_ROOT / "frontend" / "lib" / "features" / "navigation",
    REPO_ROOT / "frontend" / "lib" / "screens" / "admin",
)
PRODUCTION_AUTHORITY_SCAN_PATHS = (
    REPO_ROOT / "frontend" / "lib" / "app",
    REPO_ROOT / "frontend" / "lib" / "data",
    REPO_ROOT / "frontend" / "lib" / "features" / "app_routes",
    REPO_ROOT / "frontend" / "lib" / "features" / "capital",
    REPO_ROOT / "frontend" / "lib" / "features" / "compete",
    REPO_ROOT / "frontend" / "lib" / "features" / "match_center",
    REPO_ROOT / "frontend" / "lib" / "shared",
)
WORKFLOW_OPS_SCAN_PATHS = (
    REPO_ROOT / ".github" / "workflows",
    REPO_ROOT / "ops",
    REPO_ROOT / "tools" / "run_gtex_hosted_live_verification.ps1",
    REPO_ROOT / "tools" / "run_gtex_staging_soak.ps1",
    REPO_ROOT / "tools" / "run_gtex_canonical_acceptance.ps1",
)
FORBIDDEN_OPS_PROMOTION_RE = re.compile(
    r"\bpaystack\b|unity[-_ ]?access|legacy-runtime-access|verify[_-]?unity|"
    r"RENDER_[A-Z0-9_]*UNITY|GTEX_UNITY|UNITY_EDITOR|unity\s+(?:live|route|verifier)",
    re.IGNORECASE,
)
SCAN_TEXT_SUFFIXES = {".dart", ".json", ".md", ".ps1", ".py", ".sh", ".yaml", ".yml"}
PAYMENT_RAIL_PREFILTER_TOKENS = (
    "flutterwave",
    "paypal",
    "monnify",
    "opay",
    "coinbase",
    "mobile",
    "m-pesa",
    "mpesa",
    "payment",
    "provider",
    "checkout",
    "gateway",
    "rail",
    "stripe",
    "crypto",
)
OPS_PROMOTION_PREFILTER_TOKENS = (
    "paystack",
    "unity",
    "legacy-runtime-access",
    "verify_unity",
    "verify-unity",
)
FAKE_AUTHORITY_PREFILTER_TOKENS = (
    "fake",
    "mock",
    "dummy",
    "sample",
    "hardcoded",
    "synthetic",
    "client-generated",
    "client generated",
    "client-side",
    "client side",
    "local-only",
    "local only",
    "fallback",
    "balance",
    "score",
    "bid",
    "ranking",
    "fixture",
)
FIXTURE_ACTIVATION_PREFILTER_TOKENS = (
    "fixture",
    "kfixturemode",
    "gtexfixturemode",
    "fixturemode",
    "enablefixturemode",
    "enablecapitalfixtures",
    "gtebackendmode.fixture",
    "allowfixturemode",
    "bool.fromenvironment",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


class AcceptanceFailure(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Thread 8 GTEX canonicalization acceptance guardrails.",
    )
    parser.add_argument(
        "--live-url",
        default="",
        help="Optional local backend base/health URL. When provided, /health and /openapi.json are checked.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=15, help="HTTP timeout for --live-url checks.")
    parser.add_argument(
        "--diff-base",
        default="HEAD",
        help="Base git ref for diff hygiene. Use an empty string to skip the git diff check.",
    )
    parser.add_argument(
        "--diff-head",
        default="",
        help="Optional head git ref. When omitted, checks the working tree against --diff-base.",
    )
    parser.add_argument(
        "--strict-diff",
        action="store_true",
        help="Fail if the selected diff contains files outside scripts/** and tools/**.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of line-oriented output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []

    contract = load_contract()
    results.append(check_no_paystack_canonical_exposure(contract))
    results.append(check_payment_rails_are_korapay_manual_only())
    results.append(check_ops_workflows_no_paystack_or_unity_promotion())
    results.append(check_no_production_3d_route_promotion())
    results.append(check_no_fake_authority_or_fixture_mode())
    results.append(check_canonical_route_health(contract))
    results.append(check_2d_match_direction())
    results.append(check_diff_hygiene(args.diff_base, args.diff_head, strict=args.strict_diff))
    if args.live_url.strip():
        results.append(check_live_route_health(args.live_url, timeout_seconds=args.timeout_seconds))

    failures = [result for result in results if result.status == "fail"]
    if args.json:
        print(
            json.dumps(
                {
                    "status": "fail" if failures else "ok",
                    "results": [result.__dict__ for result in results],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            print(f"[gtex-canonical] {result.status.upper():>4} {result.name}: {result.detail}")

    return 1 if failures else 0


def load_contract() -> dict[str, Any]:
    try:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AcceptanceFailure(f"Missing API contract: {CONTRACT_PATH.relative_to(REPO_ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceFailure(f"API contract is not valid JSON: {exc}") from exc


def check_no_paystack_canonical_exposure(contract: dict[str, Any]) -> CheckResult:
    exposed: list[str] = []
    for label, value in _public_contract_strings(contract):
        if FORBIDDEN_PAYSTACK_TOKEN in value.lower():
            exposed.append(f"{label}: {value}")

    if GENERATED_FRONTEND_CONTRACT_PATH.is_file():
        generated = read_text(GENERATED_FRONTEND_CONTRACT_PATH)
        for line_number, line in enumerate(generated.splitlines(), start=1):
            if FORBIDDEN_PAYSTACK_TOKEN in line.lower():
                exposed.append(
                    f"{GENERATED_FRONTEND_CONTRACT_PATH.relative_to(REPO_ROOT).as_posix()}:{line_number}: {line.strip()}"
                )

    if exposed:
        return fail(
            "no_paystack_canonical_exposure",
            "Paystack appears on public canonical route surfaces: " + "; ".join(exposed[:8]),
        )
    return passed(
        "no_paystack_canonical_exposure", "Public route contract and generated frontend contract are provider-neutral."
    )


def check_payment_rails_are_korapay_manual_only() -> CheckResult:
    exposed: list[str] = []
    for path, line_number, line in _iter_source_lines(PAYMENT_RAIL_SCAN_PATHS):
        lower_line = line.lower()
        if not _has_any_token(lower_line, PAYMENT_RAIL_PREFILTER_TOKENS):
            continue
        if FORBIDDEN_NONCANONICAL_PAYMENT_RAIL_RE.search(line):
            exposed.append(f"{repo_relative_path(path)}:{line_number}: {line.strip()}")

    if exposed:
        return fail(
            "payment_rails_are_korapay_manual_only",
            "Unsupported payment rail/provider references: " + "; ".join(exposed[:10]),
        )
    return passed(
        "payment_rails_are_korapay_manual_only",
        "Production payment rail source names only KoraPay/manual bank transfer options.",
    )


def check_ops_workflows_no_paystack_or_unity_promotion() -> CheckResult:
    exposed: list[str] = []
    current_script_path = Path(__file__).resolve()
    for path, line_number, line in _iter_source_lines(WORKFLOW_OPS_SCAN_PATHS):
        if path == current_script_path:
            continue
        lower_line = line.lower()
        if not _has_any_token(lower_line, OPS_PROMOTION_PREFILTER_TOKENS):
            continue
        if FORBIDDEN_OPS_PROMOTION_RE.search(line):
            exposed.append(f"{repo_relative_path(path)}:{line_number}: {line.strip()}")

    if exposed:
        return fail(
            "ops_workflows_no_paystack_or_unity_promotion",
            "Ops/workflow files expose forbidden provider or Unity promotion tokens: " + "; ".join(exposed[:10]),
        )
    return passed(
        "ops_workflows_no_paystack_or_unity_promotion",
        "Ops/workflow files avoid Paystack rails/secrets/selectors and Unity route promotion.",
    )


def check_no_production_3d_route_promotion() -> CheckResult:
    app_router = read_text(FRONTEND_APP_ROUTER_PATH)
    route_constants = read_text(FRONTEND_ROUTE_CONSTANTS_PATH)
    legacy_router = read_text(FRONTEND_LEGACY_ROUTER_PATH)
    destinations = read_text(FRONTEND_DESTINATIONS_PATH)
    route_test = read_text(FRONTEND_ROUTE_COVERAGE_TEST_PATH)

    production_paths = set(re.findall(r"['\"](/app/[^'\"]+)['\"]", app_router + "\n" + route_constants))
    if production_paths != CANONICAL_PRODUCTION_APP_PATHS:
        return fail(
            "no_production_3d_route_promotion",
            "Canonical app paths changed: "
            f"missing={sorted(CANONICAL_PRODUCTION_APP_PATHS - production_paths)}, "
            f"extra={sorted(production_paths - CANONICAL_PRODUCTION_APP_PATHS)}",
        )

    scanned_files = {
        FRONTEND_APP_ROUTER_PATH: app_router,
        FRONTEND_ROUTE_CONSTANTS_PATH: route_constants,
        FRONTEND_LEGACY_ROUTER_PATH: legacy_router,
        FRONTEND_DESTINATIONS_PATH: destinations,
    }
    promoted_routes: list[str] = []
    for path, text in scanned_files.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = FORBIDDEN_PUBLIC_3D_ROUTE_RE.search(line)
            has_forbidden_token = any(token in line for token in FORBIDDEN_PRODUCTION_3D_TOKENS)
            if match is None and not has_forbidden_token:
                continue
            if any(fragment in line for fragment in ALLOWED_3D_FRAGMENTS):
                continue
            promoted_routes.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{line_number}: {line.strip()}")

    required_quarantine_markers = (
        "legacy match rendering URLs are not production-mounted",
        "Route unavailable",
        "findsNothing",
        "/matches/${'3d'}/live-match-001",
    )
    missing_markers = [marker for marker in required_quarantine_markers if marker not in route_test]
    if promoted_routes or missing_markers:
        detail = []
        if promoted_routes:
            detail.append("public 3D route fragments: " + "; ".join(promoted_routes[:8]))
        if missing_markers:
            detail.append("route coverage test markers missing: " + ", ".join(missing_markers))
        return fail("no_production_3d_route_promotion", "; ".join(detail))

    return passed(
        "no_production_3d_route_promotion",
        "Production shell paths stay canonical and legacy 3D route coverage remains quarantined.",
    )


def check_no_fake_authority_or_fixture_mode() -> CheckResult:
    fake_hits: list[str] = []
    fixture_hits: list[str] = []
    for path, line_number, line in _iter_source_lines(PRODUCTION_AUTHORITY_SCAN_PATHS):
        lower_line = line.lower()
        if (
            _has_any_token(lower_line, FAKE_AUTHORITY_PREFILTER_TOKENS)
            and FORBIDDEN_FAKE_AUTHORITY_RE.search(line)
            and not _is_disabled_authority_reference(line)
        ):
            relative = repo_relative_path(path)
            fake_hits.append(f"{relative}:{line_number}: {line.strip()}")
        if (
            _has_any_token(
                lower_line,
                FIXTURE_ACTIVATION_PREFILTER_TOKENS,
            )
            and FORBIDDEN_FIXTURE_MODE_ACTIVATION_RE.search(line)
            and not _is_test_only_fixture_activation(path, line_number, line)
        ):
            relative = repo_relative_path(path)
            fixture_hits.append(f"{relative}:{line_number}: {line.strip()}")

    problems = []
    if fake_hits:
        problems.append("fake authority data: " + "; ".join(fake_hits[:10]))
    if fixture_hits:
        problems.append("production fixture activation: " + "; ".join(fixture_hits[:10]))
    if problems:
        return fail("no_fake_authority_or_fixture_mode", " | ".join(problems))
    return passed(
        "no_fake_authority_or_fixture_mode",
        "No fake balance/score/bid/ranking/fixture authority or fixture-mode activation found.",
    )


def check_canonical_route_health(contract: dict[str, Any]) -> CheckResult:
    core_paths = set(_contract_public_paths(contract))
    canonical_paths = _canonical_paths(contract)
    generated_contract = read_text(GENERATED_FRONTEND_CONTRACT_PATH)

    missing_core_paths = sorted(REQUIRED_CORE_PATHS - core_paths)
    required_contract_paths = REQUIRED_CANONICAL_PATHS | REQUIRED_CANONICAL_WEBSOCKET_PATHS
    missing_canonical_paths = sorted(required_contract_paths - canonical_paths)
    missing_generated_paths = sorted(path for path in required_contract_paths if path not in generated_contract)
    non_v2_canonical_api_paths = sorted(
        path for path in canonical_paths if path.startswith("/api/") and not path.startswith("/api/v2/")
    )

    problems = []
    if missing_core_paths:
        problems.append(f"missing core paths: {missing_core_paths}")
    if missing_canonical_paths:
        problems.append(f"missing canonical route paths: {missing_canonical_paths}")
    if missing_generated_paths:
        problems.append(f"generated frontend contract missing: {missing_generated_paths}")
    if non_v2_canonical_api_paths:
        problems.append(f"non-v2 canonical API paths: {non_v2_canonical_api_paths[:10]}")

    if problems:
        return fail("canonical_route_health", "; ".join(problems))
    return passed(
        "canonical_route_health",
        f"{len(canonical_paths)} canonical paths parsed; required health, match-viewer, and realtime routes are present.",
    )


def check_2d_match_direction() -> CheckResult:
    simulation_engine = read_text(MATCH_SIMULATION_ENGINE_PATH)
    pitch_2d_telemetry = read_text(PITCH_2D_TELEMETRY_PATH)
    scene_director = read_text(REAL_MATCH_SCENE_DIRECTOR_PATH)
    required_simulation_markers = (
        "Canonical match state must come from backend-authored realtime payloads.",
        "Local match event generation is disabled for the canonical match center.",
    )
    required_pitch_markers = (
        "frame.possessionSide == MatchViewerSide.home",
        "? frame.homeAttacksRight",
        ": !frame.homeAttacksRight",
        "attacksRight: attacksRight",
    )
    required_director_markers = (
        "static bool _attacksRight",
        "side == MatchViewerSide.home",
        "? frame.homeAttacksRight",
        ": !frame.homeAttacksRight",
    )
    missing = [marker for marker in required_simulation_markers if marker not in simulation_engine]
    missing.extend(f"pitch:{marker}" for marker in required_pitch_markers if marker not in pitch_2d_telemetry)
    missing.extend(f"director:{marker}" for marker in required_director_markers if marker not in scene_director)

    if missing:
        return fail("two_d_match_direction", "Direction markers missing: " + ", ".join(missing))
    return passed(
        "two_d_match_direction",
        "Local simulation is disabled and 2D pitch/director movement stays driven by backend homeAttacksRight truth.",
    )


def check_diff_hygiene(diff_base: str, diff_head: str, *, strict: bool) -> CheckResult:
    base = diff_base.strip()
    head = diff_head.strip()
    if not base:
        return skipped("diff_hygiene", "Skipped because --diff-base was empty.")

    try:
        changed = git_changed_files(base=base, head=head or None)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return fail("diff_hygiene", f"Unable to inspect git diff: {exc}")

    outside_owned = sorted(path for path in changed if not path.startswith(OWNED_PREFIXES))
    if outside_owned and strict:
        return fail(
            "diff_hygiene",
            f"{len(outside_owned)} changed file(s) outside scripts/** and tools/**: {outside_owned[:12]}",
        )
    if outside_owned:
        return warning(
            "diff_hygiene",
            f"{len(outside_owned)} outside-owner changed file(s) observed in shared worktree; pass --strict-diff in a clean PR diff.",
        )
    return passed("diff_hygiene", "Selected diff is confined to scripts/** and tools/**.")


def check_live_route_health(raw_url: str, *, timeout_seconds: int) -> CheckResult:
    base_url = derive_base_url(raw_url)
    health = fetch_json(f"{base_url}/health", timeout_seconds=timeout_seconds)
    if not isinstance(health, dict):
        return fail("live_route_health", f"/health returned an unexpected payload from {base_url}.")

    openapi = fetch_json(f"{base_url}/openapi.json", timeout_seconds=timeout_seconds)
    paths = openapi.get("paths") if isinstance(openapi, dict) else None
    if not isinstance(paths, dict):
        return fail("live_route_health", f"/openapi.json did not include a paths object from {base_url}.")

    missing = sorted(path for path in REQUIRED_CANONICAL_PATHS if path not in paths)
    forbidden = sorted(
        path for path in paths if "paystack" in str(path).lower() or FORBIDDEN_PUBLIC_3D_ROUTE_RE.search(str(path))
    )
    if missing or forbidden:
        return fail("live_route_health", f"missing={missing}, forbidden={forbidden[:8]}")
    return passed("live_route_health", f"Live route health passed for {base_url}.")


def _public_contract_strings(contract: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for path in _contract_public_paths(contract):
        values.append(("core_paths", path))
    for alias, canonical in (contract.get("canonical_paths") or {}).items():
        values.append(("canonical_paths.key", str(alias)))
        values.append(("canonical_paths.value", str(canonical)))
    for alias, canonical in (contract.get("deprecated_aliases") or {}).items():
        values.append(("deprecated_aliases.key", str(alias)))
        values.append(("deprecated_aliases.value", str(canonical)))
    for group_name, group in (contract.get("routes") or {}).items():
        if not isinstance(group, dict):
            continue
        for route_name, entry in group.items():
            if not isinstance(entry, dict):
                continue
            values.append((f"routes.{group_name}.{route_name}", str(route_name)))
            for key in ("canonical_path", "handler", "response_model"):
                raw = entry.get(key)
                if isinstance(raw, str):
                    values.append((f"routes.{group_name}.{route_name}.{key}", raw))
            for alias in _list_string_values(entry.get("aliases")):
                values.append((f"routes.{group_name}.{route_name}.aliases", alias))
    for socket_name, entry in (contract.get("websockets") or {}).items():
        if not isinstance(entry, dict):
            continue
        values.append((f"websockets.{socket_name}", str(socket_name)))
        for key in ("canonical_path", "handler", "response_model"):
            raw = entry.get(key)
            if isinstance(raw, str):
                values.append((f"websockets.{socket_name}.{key}", raw))
        for alias in _list_string_values(entry.get("aliases")):
            values.append((f"websockets.{socket_name}.aliases", alias))
    return values


def _canonical_paths(contract: dict[str, Any]) -> set[str]:
    paths = set(str(path) for path in (contract.get("canonical_paths") or {}).keys())
    for group in (contract.get("routes") or {}).values():
        if not isinstance(group, dict):
            continue
        for entry in group.values():
            if isinstance(entry, dict) and isinstance(entry.get("canonical_path"), str):
                paths.add(str(entry["canonical_path"]))
    for entry in (contract.get("websockets") or {}).values():
        if isinstance(entry, dict) and isinstance(entry.get("canonical_path"), str):
            paths.add(str(entry["canonical_path"]))
    return paths


def _contract_public_paths(contract: dict[str, Any]) -> list[str]:
    return [
        *_list_string_values(contract.get("core_paths")),
        *_list_string_values(contract.get("public_exempt_paths")),
    ]


def _list_string_values(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw if isinstance(item, str)]
    if isinstance(raw, tuple):
        return [str(item) for item in raw if isinstance(item, str)]
    if isinstance(raw, set):
        return [str(item) for item in raw if isinstance(item, str)]
    return []


def git_changed_files(*, base: str, head: str | None) -> list[str]:
    if head:
        command = ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}..{head}", "--"]
    else:
        command = ["git", "diff", "--name-only", "--diff-filter=ACMRT", base, "--"]
    diff = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, check=True, text=True)
    files = {normalize_path(line) for line in diff.stdout.splitlines() if line.strip()}
    if head is None:
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "scripts", "tools"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
        )
        files.update(normalize_path(line) for line in untracked.stdout.splitlines() if line.strip())
    return sorted(files)


def derive_base_url(raw_url: str) -> str:
    parsed = parse.urlparse(raw_url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise AcceptanceFailure(f"Invalid --live-url value: {raw_url!r}")
    path = parsed.path.rstrip("/")
    for suffix in ("/api/health", "/health"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
    return parse.urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", "")).rstrip("/")


def fetch_json(url: str, *, timeout_seconds: int) -> Any:
    try:
        req = request.Request(url=url, method="GET", headers={"Accept": "application/json"})
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 0) or response.getcode())
            if status >= 400:
                raise AcceptanceFailure(f"{url} returned HTTP {status}.")
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        raise AcceptanceFailure(f"{url} returned HTTP {exc.code}.") from exc
    except error.URLError as exc:
        raise AcceptanceFailure(f"{url} could not be reached: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceFailure(f"{url} returned invalid JSON.") from exc


def _iter_source_lines(paths: tuple[Path, ...]) -> list[tuple[Path, int, str]]:
    lines: list[tuple[Path, int, str]] = []
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        for path in files:
            if path.suffix.lower() not in SCAN_TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lines.extend((path, index, line) for index, line in enumerate(text.splitlines(), start=1))
    return lines


def _is_disabled_authority_reference(line: str) -> bool:
    lower_line = line.lower()
    if not any(token in lower_line for token in ("fake", "mock", "fixture", "fallback")):
        return False
    return any(
        marker in lower_line
        for marker in (
            " disabled",
            " is disabled",
            "disabled.",
            "blocked",
            "reject",
            "never ",
            " no ",
            " not ",
            "without ",
            "removed",
        )
    )


def _is_test_only_fixture_activation(path: Path, line_number: int, line: str) -> bool:
    relative = repo_relative_path(path)
    if relative == "frontend/lib/app/gte_app_config.dart" and "allowFixtureMode ? GteBackendMode.fixture" in line:
        text = read_text(path)
        return "allowFixtureMode: isFlutterTestRuntime" in text

    text = read_text(path)
    lines = text.splitlines()
    prior_context = "\n".join(lines[max(0, line_number - 30) : line_number])

    if "enableCapitalFixtures: true" in line:
        return "factory GteMockApi.capitalFixtures" in prior_context

    if "GteBackendMode.fixture" not in line:
        return False
    if not (relative.startswith("frontend/lib/data/") or relative.startswith("frontend/lib/features/")):
        return False
    return ".fixture(" in prior_context or "factory " in prior_context


@lru_cache(maxsize=None)
def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError as exc:
        raise AcceptanceFailure(f"Missing required file: {repo_relative_path(path)}") from exc


@lru_cache(maxsize=None)
def repo_relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _has_any_token(lower_line: str, tokens: tuple[str, ...]) -> bool:
    return any(token in lower_line for token in tokens)


def normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def passed(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="pass", detail=detail)


def warning(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="warn", detail=detail)


def skipped(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="skip", detail=detail)


def fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="fail", detail=detail)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceFailure as exc:
        print(f"[gtex-canonical] FAIL acceptance: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
