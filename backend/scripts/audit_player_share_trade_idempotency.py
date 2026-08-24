from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

TOKEN_SERVICE = Path(__file__).resolve().parents[1] / "app" / "players" / "token_service.py"
TRADE_ROUTER = Path(__file__).resolve().parents[1] / "app" / "players" / "router.py"
TRADE_METHODS = {"buy_shares", "sell_shares"}
TRADE_ENDPOINTS = {"buy_player_shares", "sell_player_shares"}


def inspect_trade_idempotency(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    findings: list[dict[str, Any]] = []
    methods: dict[str, dict[str, Any]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in TRADE_METHODS:
            parameters = {arg.arg for arg in node.args.args + node.args.kwonlyargs}
            methods[node.name] = {
                "has_idempotency_key": "idempotency_key" in parameters,
                "has_boundary_runner": any(
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "_run_trade_with_boundary"
                    for child in ast.walk(node)
                ),
            }
    for method in sorted(TRADE_METHODS):
        state = methods.get(method, {})
        if not state.get("has_idempotency_key"):
            findings.append({"method": method, "finding": "missing_idempotency_key_parameter"})
        if not state.get("has_boundary_runner"):
            findings.append({"method": method, "finding": "missing_trade_boundary"})

    has_idempotency_reference = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_idempotency_reference"
        for node in ast.walk(tree)
    )
    if not has_idempotency_reference:
        findings.append({"finding": "missing_idempotency_reference_builder"})

    return {
        "source": str(TOKEN_SERVICE),
        "trade_methods": sorted(TRADE_METHODS),
        "methods": methods,
        "violations": findings,
        "pass": not findings,
        "read_only": True,
        "contract": "trade retries must use caller-provided idempotency material and a durable ledger reference",
    }


def inspect_router(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    findings: list[dict[str, Any]] = []
    endpoints: dict[str, bool] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in TRADE_ENDPOINTS:
            continue
        endpoints[node.name] = False
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
                continue
            if child.func.attr not in TRADE_METHODS:
                continue
            if any(keyword.arg == "idempotency_key" for keyword in child.keywords):
                endpoints[node.name] = True
        if not endpoints[node.name]:
            findings.append({"endpoint": node.name, "finding": "idempotency_key_not_forwarded"})

    return {
        "source": str(TRADE_ROUTER),
        "endpoints": endpoints,
        "violations": findings,
        "pass": not findings,
        "read_only": True,
    }


def audit(
    token_service_path: Path = TOKEN_SERVICE,
    router_path: Path = TRADE_ROUTER,
) -> dict[str, Any]:
    service_report = inspect_trade_idempotency(token_service_path.read_text(encoding="utf-8"))
    router_report = inspect_router(router_path.read_text(encoding="utf-8"))
    violations = service_report["violations"] + router_report["violations"]
    return {
        "service": service_report,
        "router": router_report,
        "violations": violations,
        "pass": not violations,
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player-share trade settlement for retry-safe idempotency.")
    parser.add_argument("--strict", action="store_true", help="return non-zero when the trade boundary is incomplete")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and not report["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
