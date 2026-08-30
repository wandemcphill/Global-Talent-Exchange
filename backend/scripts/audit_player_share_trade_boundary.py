from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

TOKEN_SERVICE = Path(__file__).resolve().parents[1] / "app" / "players" / "token_service.py"
TRADE_TEST = Path(__file__).resolve().parents[1] / "tests" / "players" / "test_player_share_trade_boundary_behavior.py"
TRADE_METHODS = {"buy_shares", "sell_shares"}
FORBIDDEN_CALL = "ensure_market"
REPO_ROOT = Path(__file__).resolve().parents[1]


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


def run_behavioral_gate(*, timeout_seconds: int = 300) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "tests/players/test_player_share_trade_boundary_behavior.py", "-q"]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "pass": False,
            "timed_out": True,
            "returncode": None,
            "stdout": (exc.stdout or "")[-4000:],
            "stderr": (exc.stderr or "")[-4000:],
        }

    return {
        "command": command,
        "pass": completed.returncode == 0,
        "timed_out": False,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def audit(path: Path = TOKEN_SERVICE, *, behavioral: bool = False) -> dict[str, Any]:
    report = inspect_trade_boundary(path.read_text(encoding="utf-8"))
    if behavioral:
        behavior = run_behavioral_gate()
        report["behavioral"] = behavior
        report["pass"] = bool(report["pass"] and behavior["pass"])
        report["contract"] = (
            "strict mode requires both structural trade-boundary inspection and real end-to-end rejection "
            "of buy/sell against an unissued market"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player-share buy/sell methods for implicit market issuance.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when the trade-boundary contract is incomplete",
    )
    parser.add_argument(
        "--behavioral",
        action="store_true",
        help="execute the real player-share trade-boundary regression suite in addition to source checks",
    )
    args = parser.parse_args()
    report = audit(behavioral=args.behavioral or args.strict)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
