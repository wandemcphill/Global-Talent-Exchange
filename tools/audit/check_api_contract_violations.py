from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "shared" / "api_contract.json"
REPORT_PATH = REPO_ROOT / "docs" / "CONTRACT_VIOLATIONS.md"
FRONTEND_ROOT = REPO_ROOT / "frontend" / "lib"
INTERNAL_ROUTE_RE = re.compile(r"['\"](/(?:api|auth|ws)[^'\"\s]*)['\"]")
EXCLUDED_FILE_FRAGMENTS = (
    "generated/gte_api_contract.g.dart",
    "frontend/lib/data/gte_api_contract.dart",
    "frontend/lib/data/gte_http_transport.dart",
    "frontend/lib/features/shared/data/gte_feature_support.dart",
)


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    allowed_patterns = _compile_allowed_patterns(contract)
    violations: list[dict[str, str]] = []

    for file_path in FRONTEND_ROOT.rglob("*.dart"):
        rel = file_path.relative_to(REPO_ROOT).as_posix()
        if any(fragment in rel for fragment in EXCLUDED_FILE_FRAGMENTS):
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for match in INTERNAL_ROUTE_RE.finditer(text):
            endpoint = match.group(1)
            normalized_endpoint = endpoint.split("?", 1)[0]
            if endpoint.startswith("/api/v1"):
                violations.append(
                    {
                        "file": rel,
                        "endpoint": endpoint,
                        "issue": "Deprecated /api/v1 usage remains in source.",
                    }
                )
                continue
            if normalized_endpoint in {"/api/v2", "/api/v2/"}:
                continue
            if normalized_endpoint.startswith(("/api/", "/auth/", "/ws/")) and not _matches_allowed_pattern(
                normalized_endpoint,
                allowed_patterns,
            ):
                violations.append(
                    {
                        "file": rel,
                        "endpoint": endpoint,
                        "issue": "Endpoint is not declared in shared/api_contract.json.",
                    }
                )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(violations), encoding="utf-8")
    if violations:
        print(f"[api-contract] Found {len(violations)} contract violation(s).")
        return 1
    print("[api-contract] No contract violations detected.")
    return 0


def _render_report(violations: list[dict[str, str]]) -> str:
    lines = [
        "# Contract Violations",
        "",
        f"- Violations detected: **{len(violations)}**",
        "",
    ]
    if not violations:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for violation in violations[:500]:
        lines.append(f"- `{violation['file']}` -> `{violation['endpoint']}`: {violation['issue']}")
    if len(violations) > 500:
        lines.append(f"- ... and {len(violations) - 500} more")
    return "\n".join(lines) + "\n"


def _compile_allowed_patterns(contract: dict) -> list[re.Pattern[str]]:
    aliases = set(contract.get("canonical_paths", {}).keys())
    aliases.update((contract.get("deprecated_aliases") or {}).keys())
    return [_route_pattern(alias) for alias in sorted(aliases)]


def _matches_allowed_pattern(endpoint: str, patterns: list[re.Pattern[str]]) -> bool:
    normalized = endpoint.replace(r"\$", "$")
    return any(pattern.fullmatch(normalized) for pattern in patterns)


def _route_pattern(path: str) -> re.Pattern[str]:
    escaped = re.escape(path)
    escaped = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", escaped)
    escaped = re.sub(r"\\\$\{[^}]+\}", r"[^/]+", escaped)
    escaped = re.sub(r"\\\$[A-Za-z_][A-Za-z0-9_]*", r"[^/]+", escaped)
    return re.compile(escaped)


if __name__ == "__main__":
    raise SystemExit(main())
