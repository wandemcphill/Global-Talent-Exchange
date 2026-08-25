from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "godmode_router": ROOT / "app" / "admin_godmode" / "router.py",
    "godmode_service": ROOT / "app" / "admin_godmode" / "service.py",
    "capabilities": ROOT / "app" / "admin" / "capabilities.py",
    "finance_router": ROOT / "app" / "admin_finance" / "router.py",
    "finance_service": ROOT / "app" / "admin_finance" / "service.py",
    "runtime_controls": ROOT / "app" / "services" / "runtime_control_service.py",
    "runtime_state": ROOT / "app" / "models" / "admin_runtime_state.py",
}

REQUIRED_GODMODE_MUTATIONS = {
    "update_roles": "MANAGE_ADMIN_ROLES",
    "update_commissions": "MANAGE_COMMISSIONS",
    "update_payment_rails": "MANAGE_PAYMENT_RAILS",
    "update_withdrawal_controls": "MANAGE_WITHDRAWALS",
    "update_competition_controls": "MANAGE_COMPETITIONS",
    "create_liquidity_intervention": "MANAGE_LIQUIDITY_DESK",
    "update_withdrawal": "MANAGE_WITHDRAWALS",
    "create_treasury_withdrawal": "MANAGE_TREASURY_WITHDRAWALS",
}

REQUIRED_RUNTIME_CONTROLS = (
    "upsert_price_override",
    "remove_price_override",
    "upsert_account_control",
    "clear_account_control",
    "set_match_kill_switch",
    "acquire_wallet_transaction_lock",
    "release_wallet_transaction_lock",
)

REQUIRED_AUDIT_MARKERS = (
    "_append_audit(",
    "_log_admin_override(",
)


def _source(key: str) -> str:
    return FILES[key].read_text(encoding="utf-8")


def _tree(key: str) -> ast.Module:
    return ast.parse(_source(key))


def _functions(key: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = _tree(key)
    return {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _add(findings: list[dict[str, str]], finding: str, surface: str) -> None:
    findings.append({"finding": finding, "surface": surface})


def _has_capability_dependency(node: ast.FunctionDef | ast.AsyncFunctionDef, capability: str) -> bool:
    """Verify the FastAPI Depends(require_admin_capability(...)) boundary."""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Name) or child.func.id != "Depends" or not child.args:
            continue
        dependency = child.args[0]
        if not isinstance(dependency, ast.Call):
            continue
        if not isinstance(dependency.func, ast.Name) or dependency.func.id != "require_admin_capability":
            continue
        if not dependency.args:
            continue
        capability_arg = dependency.args[0]
        if (
            isinstance(capability_arg, ast.Attribute)
            and isinstance(capability_arg.value, ast.Name)
            and capability_arg.value.id == "AdminCapability"
            and capability_arg.attr == capability
        ):
            return True
    return False


def audit() -> dict[str, object]:
    findings: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    router_functions = _functions("godmode_router")
    for function_name, capability in REQUIRED_GODMODE_MUTATIONS.items():
        node = router_functions.get(function_name)
        if node is None:
            _add(findings, "missing_admin_mutation_route", function_name)
            continue
        if not _has_capability_dependency(node, capability):
            _add(
                findings,
                "mutation_missing_capability_gate",
                f"{function_name}:{capability}",
            )

    capability_source = _source("capabilities")
    for capability in (
        "MANAGE_ADMIN_ROLES",
        "MANAGE_COMMISSIONS",
        "MANAGE_PAYMENT_RAILS",
        "MANAGE_WITHDRAWALS",
        "MANAGE_TREASURY_WITHDRAWALS",
        "MANAGE_LIQUIDITY_DESK",
        "MANAGE_COMPETITIONS",
        "VIEW_AUDIT_LOG",
    ):
        if f"{capability} =" not in capability_source:
            _add(findings, "missing_admin_capability", capability)
    if "def require_admin_capability(" not in capability_source:
        _add(
            findings,
            "capability_authorization_boundary_missing",
            "require_admin_capability",
        )
    if "def assert_admin_capability(" not in capability_source:
        _add(findings, "capability_assertion_missing", "assert_admin_capability")

    godmode_service = _source("godmode_service")
    for marker in REQUIRED_AUDIT_MARKERS:
        if marker not in godmode_service:
            _add(findings, "missing_admin_audit_sink", marker)
    for marker in (
        "confirm liquidity action",
        "outside the allowed bounded range",
        "Completed withdrawals are append-only",
        "Rejected or failed withdrawals are terminal",
        "generate_uuid()",
    ):
        if marker not in godmode_service:
            _add(findings, "missing_high_risk_integrity_guard", marker)

    finance_router = _source("finance_router")
    for marker in (
        'prefix="/api/admin/finance"',
        "get_current_admin",
        "control-tower",
        "wallet-protection",
        "reconciliation",
    ):
        if marker not in finance_router:
            _add(findings, "missing_finance_control_surface", marker)

    finance_service = _source("finance_service")
    for marker in (
        "get_control_tower_snapshot",
        "wallet_protection_summary",
        "payment_reconciliation_summary",
        "handle_korapay_webhook",
        "handle_paystack_webhook",
    ):
        if marker not in finance_service:
            _add(findings, "missing_finance_service_surface", marker)

    runtime_source = _source("runtime_controls")
    for marker in REQUIRED_RUNTIME_CONTROLS:
        if f"def {marker}(" not in runtime_source:
            _add(findings, "missing_runtime_control", marker)

    runtime_state_source = _source("runtime_state")
    if "class AdminRuntimeState" not in runtime_state_source or "state_key" not in runtime_state_source:
        _add(findings, "missing_persistent_admin_runtime_state", "admin_runtime_states")

    warnings.append(
        {
            "finding": "runtime_wallet_locks_have_process_local_operator_guard",
            "detail": "Database row locks remain the authoritative economic safety boundary.",
        }
    )

    return {
        "group": "admin-control-plane",
        "contract": (
            "every high-risk admin mutation must be capability-gated, bounded, "
            "audited, and connected to authoritative finance/economic services"
        ),
        "violations": findings,
        "warnings": warnings,
        "pass": not findings,
        "read_only": True,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
