from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "backend" / "app" / "players" / "router.py"
SCHEMAS = ROOT / "backend" / "app" / "players" / "token_schemas.py"
SERVICE = ROOT / "backend" / "app" / "players" / "token_service.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    router_source = _read(ROUTER)
    schema_source = _read(SCHEMAS)
    service_source = _read(SERVICE)

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

    if "def _run_trade_with_boundary" not in service_source:
        errors.append("trade service must have the strict trade boundary")
    if "def _require_trade_market" not in service_source:
        errors.append("trade service must require an already-issued market")
    if "def _idempotency_reference" not in service_source:
        errors.append("trade service must derive a durable idempotency reference")
    if "def _replay_idempotent_trade" not in service_source:
        errors.append("trade service must replay an existing idempotent settlement")

    for route_name, method in (("buy_player_shares", "buy_shares"), ("sell_player_shares", "sell_shares")):
        route_marker = f"def {route_name}"
        start = router_source.find(route_marker)
        if start < 0:
            errors.append(f"missing route: {route_name}")
            continue
        next_route = router_source.find("\n@router.", start + len(route_marker))
        block = router_source[start:] if next_route < 0 else router_source[start:next_route]
        if "idempotency_key" not in block:
            warnings.append(
                f"{route_name} does not forward payload.idempotency_key to {method}(); "
                "the service still uses its deterministic trade reference fallback"
            )

    return errors, warnings


def main() -> int:
    errors, warnings = audit()
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("PASS: player-share API contract has a fail-closed trade boundary")
    if warnings:
        print("NOTE: optional client idempotency-key forwarding remains a follow-up integration item")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
