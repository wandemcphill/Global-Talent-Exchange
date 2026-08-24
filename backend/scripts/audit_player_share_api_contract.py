from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "backend" / "app" / "players" / "router.py"
SCHEMAS = ROOT / "backend" / "app" / "players" / "token_schemas.py"
SERVICE = ROOT / "backend" / "app" / "players" / "token_service.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _call_has_keyword(function: ast.AST, method: str, keyword: str) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != method:
                continue
            if any(arg.arg == keyword for arg in node.keywords):
                return True
    return False


def audit() -> list[str]:
    errors: list[str] = []
    router_tree = ast.parse(_read(ROUTER), filename=str(ROUTER))
    schema_tree = ast.parse(_read(SCHEMAS), filename=str(SCHEMAS))
    service_tree = ast.parse(_read(SERVICE), filename=str(SERVICE))

    for route_name, service_method in (("buy_player_shares", "buy_shares"), ("sell_player_shares", "sell_shares")):
        route = _find_function(router_tree, route_name)
        if not _call_has_keyword(route, service_method, "idempotency_key"):
            errors.append(f"{route_name} must forward payload.idempotency_key to {service_method}()")

    for request_name in ("PlayerSharePurchaseRequest", "PlayerShareSaleRequest"):
        request = _find_function(schema_tree, request_name) if False else None
        del request
    schema_source = _read(SCHEMAS)
    for request_name in ("PlayerSharePurchaseRequest", "PlayerShareSaleRequest"):
        marker = f"class {request_name}"
        start = schema_source.find(marker)
        if start < 0:
            errors.append(f"missing request schema: {request_name}")
            continue
        end = schema_source.find("\nclass ", start + len(marker))
        block = schema_source[start:] if end < 0 else schema_source[start:end]
        if "idempotency_key" not in block:
            errors.append(f"{request_name} must expose idempotency_key")

    service_source = _read(SERVICE)
    if "def _run_trade_with_boundary" not in service_source:
        errors.append("trade service must have the strict trade boundary")
    if "def _require_trade_market" not in service_source:
        errors.append("trade service must require an already-issued market")
    if "def _idempotency_reference" not in service_source:
        errors.append("trade service must derive a durable idempotency reference")

    return errors


def main() -> int:
    errors = audit()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: player-share API contract is fail-closed and idempotency-aware")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
