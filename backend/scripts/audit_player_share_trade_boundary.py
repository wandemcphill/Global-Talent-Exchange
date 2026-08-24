from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

TOKEN_SERVICE = Path(__file__).resolve().parents[1] / "app" / "players" / "token_service.py"
TRADE_METHODS = {"buy_shares", "sell_shares"}
FORBIDDEN_CALL = "ensure_market"


def inspect_trade_boundary(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in TRADE_METHODS:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            target = child.func
            if isinstance(target, ast.Attribute) and target.attr == FORBIDDEN_CALL:
                findings.append(
                    {
                        "method": node.name,
                        "line": child.lineno,
                        "forbidden_call": FORBIDDEN_CALL,
                    }
                )

    return {
        "source": str(TOKEN_SERVICE),
        "trade_methods": sorted(TRADE_METHODS),
        "forbidden_call": FORBIDDEN_CALL,
        "violations": findings,
        "pass": not findings,
        "read_only": True,
    }


def audit(path: Path = TOKEN_SERVICE) -> dict[str, Any]:
    return inspect_trade_boundary(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player-share buy/sell methods for implicit market issuance.")
    parser.add_argument("--strict", action="store_true", help="return non-zero when a trade method calls ensure_market")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
