from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TOKEN_SERVICE = BACKEND_ROOT / "app" / "players" / "token_service.py"
PLAYER_ROUTER = BACKEND_ROOT / "app" / "players" / "router.py"
TRADE_BOUNDARY = BACKEND_ROOT / "app" / "players" / "trade_boundary.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports_production_service(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.players.token_service":
            names = {alias.name for alias in node.names}
            if "PlayerTokenMarketService" in names:
                return True
    return False


def _trade_methods_call_ensure_market(tree: ast.Module) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in {"buy_shares", "sell_shares"}:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr == "ensure_market":
                    violations.append(
                        {
                            "method": node.name,
                            "line": child.lineno,
                            "rule": "trade_methods_must_not_call_ensure_market",
                        }
                    )
    return violations


def inspect_repository() -> dict[str, Any]:
    token_tree = _parse(TOKEN_SERVICE)
    router_tree = _parse(PLAYER_ROUTER)
    boundary_tree = _parse(TRADE_BOUNDARY)

    violations = _trade_methods_call_ensure_market(token_tree)
    production_service_wired = _imports_production_service(router_tree)
    boundary_class_present = any(
        isinstance(node, ast.ClassDef) and node.name == "PlayerShareTradeBoundary"
        for node in ast.walk(boundary_tree)
    )
    context_vars_present = {
        "trade_reference": "_trade_reference" in ast.unparse(token_tree),
        "trade_market_override": "_trade_market_override" in ast.unparse(token_tree),
    }

    gates = {
        "production_router_uses_trade_service": production_service_wired,
        "trade_boundary_class_present": boundary_class_present,
        "trade_methods_do_not_call_ensure_market": not violations,
        "trade_reference_is_request_scoped": context_vars_present["trade_reference"],
        "trade_market_override_is_request_scoped": context_vars_present["trade_market_override"],
    }
    return {
        "gate": "player-share-release",
        "read_only": True,
        "gates": gates,
        "violations": violations,
        "pass": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Static release gate for the player-share trade boundary.")
    parser.parse_args()
    report = inspect_repository()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
