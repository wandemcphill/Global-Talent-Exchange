from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

ISSUER = Path(__file__).resolve().parents[1] / "scripts" / "issue_player_share_markets.py"
FORBIDDEN_CALL = "ensure_market"


def inspect_issuer(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute) and target.attr == FORBIDDEN_CALL:
            findings.append(
                {
                    "line": node.lineno,
                    "forbidden_call": FORBIDDEN_CALL,
                }
            )
    return {
        "source": str(ISSUER),
        "forbidden_call": FORBIDDEN_CALL,
        "violations": findings,
        "pass": not findings,
        "read_only": True,
    }


def audit(path: Path = ISSUER) -> dict[str, Any]:
    return inspect_issuer(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player-share bulk issuance for implicit market bootstrap.")
    parser.add_argument("--strict", action="store_true", help="return non-zero when the issuer calls ensure_market")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
