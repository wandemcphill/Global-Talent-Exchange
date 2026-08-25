from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def python_has_dependency(
    path: Path, function_name: str, dependency_name: str
) -> bool:
    tree = ast.parse(read(path))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == dependency_name:
                    return True
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr == dependency_name:
                    return True
        source = ast.get_source_segment(read(path), node) or ""
        return dependency_name in source
    return False


def check() -> dict[str, object]:
    violations: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, object] = {}

    production_env = read(ROOT / ".env.production.example")
    k8s_secret = read(ROOT / "ops/k8s/base/secret.example.yaml")
    render_build = read(ROOT / "ops/render/build-frontend.sh")
    players_router = BACKEND / "app/players/router.py"
    hosted_router = read(BACKEND / "app/hosted_competition_engine/router.py")
    hosted_invite_tests = (
        BACKEND / "tests/hosted_competition_engine/test_invites.py"
    )
    admin_service = read(BACKEND / "app/admin_godmode/service.py")
    market_repo = read(BACKEND / "app/market/repositories.py")
    market_service = read(BACKEND / "app/market/service.py")
    deploy_workflow = read(ROOT / ".github/workflows/deploy-production.yml")

    required_korapay = (
        "GTE_KORAPAY_SECRET_KEY",
        "GTE_KORAPAY_WEBHOOK_SECRET",
        "GTE_KORAPAY_REDIRECT_URL",
        "GTE_KORAPAY_NOTIFICATION_URL",
    )
    evidence["korapay_env_contract"] = {
        key: key in production_env and key in k8s_secret for key in required_korapay
    }
    for key in required_korapay:
        if key not in production_env or key not in k8s_secret:
            violations.append(f"missing_korapay_env_contract:{key}")
    if "/integrations/payments/korapay/webhook" not in production_env:
        violations.append("korapay_notification_route_contract_missing")

    evidence["frontend_live_boot_guarded"] = (
        ': "${GTE_API_BASE_URL:?' in render_build
    )
    if not evidence["frontend_live_boot_guarded"]:
        violations.append("frontend_release_missing_live_api_guard")

    evidence["player_trade_dependency_guard"] = {
        "buy": python_has_dependency(
            players_router, "buy_player_shares", "get_current_trading_user"
        ),
        "sell": python_has_dependency(
            players_router, "sell_player_shares", "get_current_trading_user"
        ),
    }
    if not all(evidence["player_trade_dependency_guard"].values()):
        violations.append(
            "player_share_trade_routes_missing_trading_compliance_dependency"
        )

    evidence["hosted_invites"] = {
        "router": any(token in hosted_router for token in ("invite", "invites")),
        "tests": hosted_invite_tests.exists(),
    }
    if (
        not evidence["hosted_invites"]["router"]
        or not evidence["hosted_invites"]["tests"]
    ):
        violations.append("hosted_competition_invite_surface_incomplete")

    evidence["admin_db_state"] = {
        "model": "AdminRuntimeState" in admin_service,
        "session_load": "_load_state_in_session" in admin_service,
        "session_save": "_save_state_record" in admin_service,
    }
    if not all(evidence["admin_db_state"].values()):
        violations.append("admin_runtime_state_not_database_backed")
    if "_save_file_state" in admin_service:
        warnings.append("legacy_file_state_fallback_retained_for_non_database_bootstrap")

    evidence["market_discovery"] = {
        "sql_tradable_filter": "Player.is_tradable.is_(True)" in market_repo,
        "service_pagination": "next_cursor" in market_service
        and "has_more" in market_service,
        "full_python_filter_marker": "filtered_records = [" in market_service,
    }
    if evidence["market_discovery"]["full_python_filter_marker"]:
        warnings.append(
            "market_discovery_still_performs_post-load_python_filtering; "
            "large-market_sql_optimization remains open"
        )

    evidence["unity_gate"] = {
        "workflow_present": "unity-windows-build:" in deploy_workflow,
        "license_failure_classified": "No valid Unity Editor license found"
        in deploy_workflow,
    }
    if not evidence["unity_gate"]["workflow_present"]:
        violations.append("unity_windows_release_gate_missing")
    if not evidence["unity_gate"]["license_failure_classified"]:
        warnings.append("unity_license_failure_is_not_explicitly_classified")

    evidence["runtime_inputs_required"] = [
        "canonical production backend URL",
        "bootstrap admin secret in staging/production vault",
        "live KoraPay credentials and public callbacks",
        "5000+ real-player import and issuance cohort",
        "production Unity runner license",
    ]

    return {
        "group": "group-6-production-readiness-marathon",
        "pass": not violations,
        "violations": sorted(set(violations)),
        "warnings": sorted(set(warnings)),
        "evidence": evidence,
        "read_only": True,
        "runtime_inputs_required": evidence["runtime_inputs_required"],
    }


def main() -> int:
    report = check()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
