from __future__ import annotations

"""Single local certification entry point for the player-share economy.

The command is intentionally read-only. It combines static source-boundary
checks with the existing database audit scripts when a database URL is
available. It never creates markets, changes balances, or mutates production.
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
TOKEN_SERVICE = BACKEND / "app" / "players" / "token_service.py"
ISSUER = BACKEND / "scripts" / "issue_player_share_markets_strict.py"
LIFECYCLE_AUDIT = BACKEND / "scripts" / "audit_player_share_lifecycle.py"
TRADE_AUDIT = BACKEND / "scripts" / "audit_player_share_trade_boundary.py"


def _boundary_check() -> dict[str, object]:
    source = TOKEN_SERVICE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TOKEN_SERVICE))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in {"buy_shares", "sell_shares"}:
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr == "ensure_market":
                violations.append(f"{node.name} directly calls ensure_market()")
    issuer_source = ISSUER.read_text(encoding="utf-8")
    if "issue_market(" not in issuer_source:
        violations.append("strict issuer does not call issue_market()")
    if "ensure_market(" in issuer_source:
        violations.append("strict issuer references ensure_market()")
    return {"passed": not violations, "violations": violations}


def _run_audit(script: Path, database_url: str | None) -> dict[str, object]:
    command = [sys.executable, str(script)]
    if database_url:
        command.extend(["--database-url", database_url])
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    payload: object
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}
    return {"passed": completed.returncode == 0, "result": payload}


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify player-share economic release boundaries.")
    parser.add_argument("--database-url")
    args = parser.parse_args()

    report: dict[str, object] = {
        "read_only": True,
        "boundary": _boundary_check(),
        "database_audits": {},
    }
    if args.database_url:
        report["database_audits"] = {
            "lifecycle": _run_audit(LIFECYCLE_AUDIT, args.database_url),
            "trade_boundary": _run_audit(TRADE_AUDIT, args.database_url),
        }
    else:
        report["database_audits"] = {
            "status": "SKIPPED",
            "reason": "No --database-url supplied; static certification only.",
        }

    boundary_passed = bool(report["boundary"]["passed"])
    db = report["database_audits"]
    db_passed = all(
        bool(value.get("passed"))
        for value in db.values()
        if isinstance(value, dict) and "passed" in value
    )
    report["certified"] = boundary_passed and db_passed
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["certified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
