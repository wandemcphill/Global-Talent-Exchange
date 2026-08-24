from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "wallet_service": ROOT / "app" / "wallets" / "service.py",
    "rail_service": ROOT / "app" / "wallets" / "rail_service.py",
    "payment_gateway": ROOT / "app" / "services" / "payment_gateway_service.py",
    "admin_finance": ROOT / "app" / "admin_finance" / "service.py",
    "payment_router": ROOT / "app" / "integrations" / "payments" / "router.py",
    "finance_router": ROOT / "app" / "admin_finance" / "router.py",
    "treasury_service": ROOT / "app" / "treasury" / "service.py",
    "runtime_controls": ROOT / "app" / "services" / "runtime_control_service.py",
    "provider_registry": ROOT / "app" / "wallets" / "providers" / "registry.py",
}


def _source(key: str) -> str:
    return FILES[key].read_text(encoding="utf-8")


def _functions(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def audit() -> dict[str, object]:
    findings: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    wallet_functions = _functions(_source("wallet_service"))
    rail_functions = _functions(_source("rail_service"))
    treasury_functions = _functions(_source("treasury_service"))
    admin_functions = _functions(_source("admin_finance"))
    runtime_functions = _functions(_source("runtime_controls"))

    required = {
        "wallet.request_payout": (wallet_functions, "request_payout"),
        "wallet.complete_payout_request": (wallet_functions, "complete_payout_request"),
        "wallet.release_payout_request": (wallet_functions, "release_payout_request"),
        "wallet.create_payment_event": (wallet_functions, "create_payment_event"),
        "wallet.verify_payment_event": (wallet_functions, "verify_payment_event"),
        "rail.settle_purchase_order": (rail_functions, "settle_purchase_order"),
        "rail.handle_provider_event": (rail_functions, "handle_provider_event"),
        "treasury.create_withdrawal_batch": (treasury_functions, "create_withdrawal_batch"),
        "treasury.list_withdrawal_batches": (treasury_functions, "list_withdrawal_batches"),
        "treasury.review_withdrawal_status": (
            treasury_functions,
            "review_withdrawal_status",
        ),
        "admin.handle_korapay_webhook": (admin_functions, "handle_korapay_webhook"),
        "admin.handle_paystack_webhook": (admin_functions, "handle_paystack_webhook"),
        "admin.payment_reconciliation_summary": (
            admin_functions,
            "payment_reconciliation_summary",
        ),
        "runtime.wallet_transaction_lock": (
            runtime_functions,
            "acquire_wallet_transaction_lock",
        ),
    }
    for label, (names, function_name) in required.items():
        if function_name not in names:
            findings.append(
                {"finding": "missing_required_surface", "surface": label}
            )

    provider_registry = _source("provider_registry")
    if '"korapay": ProviderRegistration' not in provider_registry:
        findings.append(
            {"finding": "korapay_not_registered_live", "surface": "provider_registry"}
        )
    if "def paystack_enabled()" not in provider_registry or "return False" not in provider_registry:
        findings.append(
            {"finding": "paystack_not_fail_closed", "surface": "provider_registry"}
        )

    admin_source = _source("admin_finance")
    protected_checks = (
        "_verify_korapay_webhook",
        "_verify_paystack_webhook",
        "_signature_optional",
        "_is_protected_environment",
    )
    for check in protected_checks:
        if check not in admin_source:
            findings.append(
                {"finding": "missing_webhook_security_boundary", "surface": check}
            )

    rail_source = _source("rail_service")
    replay_markers = (
        'idempotency_key=f"purchase-order:{order.id}:settle"',
        "Duplicate provider reference detected",
        "provider_reference",
    )
    for marker in replay_markers:
        if marker not in rail_source:
            findings.append(
                {"finding": "missing_payment_replay_guard", "surface": marker}
            )

    reconciliation_markers = (
        "settled_purchase_order_missing_ledger",
        "verified_payment_event_missing_ledger",
        "confirmed_deposit_missing_ledger",
        "duplicate_provider_reference",
    )
    for marker in reconciliation_markers:
        if marker not in admin_source:
            findings.append(
                {"finding": "missing_reconciliation_mismatch", "surface": marker}
            )

    treasury_source = _source("treasury_service")
    batch_markers = (
        '"batch_id"',
        "TreasuryWithdrawalStatus.PROCESSING",
        "treasury.withdrawal.batch.created",
    )
    for marker in batch_markers:
        if marker not in treasury_source:
            findings.append(
                {"finding": "missing_withdrawal_batch_contract", "surface": marker}
            )

    finance_router = _source("finance_router")
    if "/korapay/webhook" not in finance_router:
        findings.append(
            {"finding": "missing_korapay_http_route", "surface": "finance_router"}
        )
    if "/paystack/webhook" not in finance_router:
        findings.append(
            {"finding": "missing_paystack_http_route", "surface": "finance_router"}
        )

    payment_router = _source("payment_router")
    if "acquire_wallet_transaction_lock" not in payment_router:
        findings.append(
            {"finding": "payment_order_missing_wallet_lock", "surface": "payment_router"}
        )
    if "release_wallet_transaction_lock" not in payment_router:
        findings.append(
            {"finding": "payment_order_lock_not_released", "surface": "payment_router"}
        )

    warnings.append(
        {
            "finding": "runtime_wallet_locks_are_process_scoped",
            "detail": (
                "Persistent row locks remain the database safety boundary; "
                "runtime controls provide an operator/request guard."
            ),
        }
    )

    return {
        "group": "wallet-payments-treasury",
        "contract": (
            "all live money movement must terminate in the authoritative ledger, "
            "be replay-safe, reconciliable, and operator-controllable"
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
