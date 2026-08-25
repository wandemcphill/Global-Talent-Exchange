from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _scan(root: Path, suffixes: tuple[str, ...], needles: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    if not root.exists():
        return findings
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in needles:
            if needle in text:
                findings.append(f"{path.relative_to(REPO)}:{needle}")
    return findings


def audit() -> dict[str, object]:
    violations: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    frontend = REPO / "frontend" / "lib"
    backend = REPO / "backend"

    # Live frontend paths must not silently substitute fixture data or localhost.
    for finding in _scan(
        frontend,
        (".dart",),
        ("liveThenFixture", "localhost:8000", "127.0.0.1:8000"),
    ):
        violations.append({"finding": "production_frontend_fallback_or_localhost", "surface": finding})

    # Globally suppressed async-context lint is a release blocker because it hides lifecycle bugs.
    analysis = _read(REPO / "frontend" / "analysis_options.yaml")
    if "use_build_context_synchronously: ignore" in analysis:
        violations.append({"finding": "global_async_context_lint_suppressed", "surface": "frontend/analysis_options.yaml"})

    # Schema evolution must remain Alembic-only.
    startup = _read(backend / "app" / "main.py") + _read(backend / "app" / "core" / "database.py")
    if "metadata.create_all" in startup:
        violations.append({"finding": "startup_schema_mutation", "surface": "backend startup/database"})

    # Existing release certification gates must remain in the Phase A workflow.
    workflow = _read(REPO / ".github" / "workflows" / "phase-a-economic-regressions.yml")
    required_gates = (
        "audit_player_share_release_audit.py",
        "audit_wallet_payments_treasury_release.py",
        "audit_admin_control_plane_release.py",
        "audit_match_engine_competition_economy_release.py",
    )
    for gate in required_gates:
        if gate not in workflow:
            violations.append({"finding": "economic_release_gate_missing", "surface": gate})

    # Sensitive admin/payment routes must retain explicit capability/provider controls.
    payment_registry = _read(backend / "app" / "payments" / "provider_registry.py")
    if "Paystack" in payment_registry and "False" not in payment_registry:
        warnings.append({"finding": "verify_paystack_runtime_flag", "surface": "provider_registry"})

    # Release docs must not advertise the old placeholder/fixture fallback architecture.
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
