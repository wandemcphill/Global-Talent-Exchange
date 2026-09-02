from __future__ import annotations

"""Read-only static certification for the authoritative KYC boundary."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
IDENTITY_SERVICE = BACKEND / "app" / "identity" / "compliance_service.py"


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _direct_verified_writes(path: Path) -> list[str]:
    tree = _parse(path)
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute) or target.attr != "kyc_status":
                continue
            value = ast.unparse(node.value)
            if "KycStatus.VERIFIED" in value:
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: direct verified-state write")
    return violations


def _scan_application() -> list[str]:
    violations: list[str] = []
    for path in sorted((BACKEND / "app").rglob("*.py")):
        if path == IDENTITY_SERVICE or path.name == "__init__.py":
            continue
        try:
            violations.extend(_direct_verified_writes(path))
        except SyntaxError as exc:
            violations.append(f"{path.relative_to(ROOT)}:{exc.lineno}: syntax error: {exc.msg}")
    return violations


def main() -> int:
    violations = _scan_application()
    identity_source = IDENTITY_SERVICE.read_text(encoding="utf-8") if IDENTITY_SERVICE.exists() else ""
    required_markers = (
        "provider",
        "provider_subject",
        "decision",
        "verified_at",
        "AuditLog",
        "identity.kyc.verify",
    )
    missing = [marker for marker in required_markers if marker not in identity_source]
    if missing:
        violations.append("identity service missing required evidence markers: " + ", ".join(missing))

    report = {
        "read_only": True,
        "scanned_application_files": len(list((BACKEND / "app").rglob("*.py"))),
        "verified_projection_direct_write_violations": violations,
        "identity_service_present": IDENTITY_SERVICE.exists(),
        "passed": not violations and IDENTITY_SERVICE.exists(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
