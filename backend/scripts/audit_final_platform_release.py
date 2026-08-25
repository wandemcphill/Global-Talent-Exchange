from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _guarded_fixture_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    factory_pattern = re.compile(r"factory\s+[A-Za-z0-9_]+\s*\.\s*fixture\s*\(")
    for match in factory_pattern.finditer(text):
        start = match.start()
        paren_start = match.end() - 1
        depth = 0
        in_string = False
        quote = ""
        escaped = False
        close_paren = None
        for index in range(paren_start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    in_string = False
                continue
            if char in ("'", '"'):
                in_string = True
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
        if close_paren is None:
            continue
        body_start = close_paren + 1
        while body_start < len(text) and text[body_start].isspace():
            body_start += 1
        if text.startswith("=>", body_start):
            end = text.find(";", body_start)
            if end != -1 and "assertFixtureFactoryAllowed" in text[start : end + 1]:
                ranges.append((start, end + 1))
            continue
        if body_start >= len(text) or text[body_start] != "{":
            continue
        brace_depth = 0
        in_string = False
        quote = ""
        escaped = False
        end = len(text)
        for index in range(body_start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    in_string = False
                continue
            if char in ("'", '"'):
                in_string = True
                quote = char
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    end = index + 1
                    break
        if "assertFixtureFactoryAllowed" in text[start:end]:
            ranges.append((start, end))
    return ranges


def _production_localhost_findings(frontend: Path) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    warnings: list[str] = []
    needles = ("localhost:8000", "127.0.0.1:8000")
    for path in frontend.rglob("*.dart"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        guarded = _guarded_fixture_ranges(text)
        for needle in needles:
            for match in re.finditer(re.escape(needle), text):
                if any(start <= match.start() < end for start, end in guarded):
                    continue
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                if "baseUrl =" in line and "GteBackendMode.live" in text[line_start : min(len(text), line_end + 240)]:
                    warnings.append(f"{path.relative_to(REPO)}:{needle}:injectable_ui_default")
                else:
                    violations.append(f"{path.relative_to(REPO)}:{needle}")
    return sorted(set(violations)), sorted(set(warnings))


def audit() -> dict[str, object]:
    violations: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    frontend = REPO / "frontend" / "lib"
    backend = REPO / "backend"

    localhost_violations, localhost_warnings = _production_localhost_findings(frontend)
    violations.extend({"finding": "production_frontend_localhost", "surface": finding} for finding in localhost_violations)
    warnings.extend({"finding": "injectable_ui_localhost_default", "surface": finding} for finding in localhost_warnings)

    repository_source = _read(frontend / "data" / "gte_api_repository.dart")
    if "liveThenFixture" in repository_source and "never enables a silent fixture fallback" not in repository_source:
        violations.append({"finding": "deprecated_backend_mode_contract_missing", "surface": "gte_api_repository.dart"})
    if "return gteFixtureApiBaseUrl" in repository_source:
        warnings.append({"finding": "fixture_url_symbol_present", "surface": "gte_api_repository.dart"})

    analysis = _read(REPO / "frontend" / "analysis_options.yaml")
    if "use_build_context_synchronously: ignore" in analysis:
        violations.append({"finding": "global_async_context_lint_suppressed", "surface": "frontend/analysis_options.yaml"})

    startup = _read(backend / "app" / "main.py") + _read(backend / "app" / "core" / "database.py")
    if "metadata.create_all" in startup:
        violations.append({"finding": "startup_schema_mutation", "surface": "backend startup/database"})

    workflow = " ".join(_read(REPO / ".github" / "workflows" / "phase-a-economic-regressions.yml").split())
    required_gates = (
        "test_player_share_release_audit.py",
        "audit_wallet_payments_treasury_release.py",
        "audit_admin_control_plane_release.py",
        "audit_match_engine_competition_economy_release.py",
    )
    for gate in required_gates:
        if gate not in workflow:
            violations.append({"finding": "economic_release_gate_missing", "surface": gate})

    payment_registry = _read(backend / "app" / "payments" / "provider_registry.py")
    if "Paystack" in payment_registry and "False" not in payment_registry:
        warnings.append({"finding": "verify_paystack_runtime_flag", "surface": "provider_registry"})

    tracker = _read(REPO / "AUDIT_REMEDIATION_TRACKER.md")
    if "## Phase A10" not in tracker:
        violations.append({"finding": "audit_tracker_incomplete", "surface": "AUDIT_REMEDIATION_TRACKER.md"})

    return {
        "group": "final-platform-certification",
        "contract": "shipping paths must be truthful, durable, fail-closed, authorized, and covered by the economic release gates",
        "violations": violations,
        "warnings": warnings,
        "pass": not violations,
        "read_only": True,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
