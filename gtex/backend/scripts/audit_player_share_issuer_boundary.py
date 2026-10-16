from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

ISSUER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "issue_player_share_markets.py"
)


def inspect_issuer(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    violations: list[dict[str, Any]] = []
    ensure_calls: list[ast.Call] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "ensure_market"
        ):
            ensure_calls.append(node)

    issue_function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "issue_markets"
        ),
        None,
    )
    if issue_function is None:
        violations.append({"finding": "issuer_entrypoint_missing"})
    else:
        issue_lines = {
            node.lineno
            for node in ast.walk(issue_function)
            if hasattr(node, "lineno")
        }
        if any(call.lineno not in issue_lines for call in ensure_calls):
            violations.append(
                {"finding": "issuer_service_call_outside_issue_markets"}
            )

    source_lines = source.splitlines()
    ensure_lines = {call.lineno for call in ensure_calls}
    for line_no in ensure_lines:
        context = "\n".join(
            source_lines[max(0, line_no - 12) : min(len(source_lines), line_no + 2)]
        )
        if "if not dry_run" not in context:
            violations.append(
                {
                    "finding": "issuer_activation_guard_missing",
                    "line": line_no,
                }
            )

    if "--activate" not in source:
        violations.append({"finding": "explicit_activation_flag_missing"})
    if "dry_run = bool(args.dry_run or not args.activate)" not in source:
        violations.append({"finding": "default_dry_run_guard_missing"})

    return {
        "source": str(ISSUER),
        "contract": "bulk issuance is an explicit operational issuer; ordinary trade paths must not bootstrap markets",
        "ensure_market_calls": len(ensure_calls),
        "pass": not violations,
        "violations": violations,
        "read_only": True,
    }


def audit(path: Path = ISSUER) -> dict[str, Any]:
    return inspect_issuer(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the explicit player-share bulk issuer boundary."
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
