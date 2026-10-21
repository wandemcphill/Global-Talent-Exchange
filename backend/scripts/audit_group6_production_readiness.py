from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def python_has_dependency(path: Path, function_name: str, dependency_name: str) -> bool:
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
    hosted_invite_tests = BACKEND / "tests/hosted_competition_engine/test_invites.py"
    admin_service = read(BACKEND / "app/admin_godmode/service.py")
    market_repo = read(BACKEND / "app/market/repositories.py")
    market_service = read(BACKEND / "app/market/service.py")
    deploy_workflow = read(ROOT / ".github/workflows/deploy-production.yml")
    staging_workflow = read(ROOT / ".github/workflows/ci-staging.yml")

    required_korapay = (
        "GTE_KORAPAY_SECRET_KEY",
        "GTE_KORAPAY_WEBHOOK_SECRET",
        "GTE_KORAPAY_REDIRECT_URL",
        "GTE_KORAPAY_NOTIFICATION_URL",
    )
    evidence["korapay_env_contract"] = {key: key in production_env and key in k8s_secret for key in required_korapay}
    for key in required_korapay:
        if key not in production_env or key not in k8s_secret:
            violations.append(f"missing_korapay_env_contract:{key}")
    if "/integrations/payments/korapay/webhook" not in production_env:
        violations.append("korapay_notification_route_contract_missing")

    evidence["frontend_live_boot_guarded"] = ': "${GTE_API_BASE_URL:?' in render_build
    if not evidence["frontend_live_boot_guarded"]:
        violations.append("frontend_release_missing_live_api_guard")

    evidence["player_trade_dependency_guard"] = {
        "buy": python_has_dependency(players_router, "buy_player_shares", "get_current_trading_user"),
        "sell": python_has_dependency(players_router, "sell_player_shares", "get_current_trading_user"),
    }
    if not all(evidence["player_trade_dependency_guard"].values()):
        violations.append("player_share_trade_routes_missing_trading_compliance_dependency")

    evidence["hosted_invites"] = {
        "router": any(token in hosted_router for token in ("invite", "invites")),
        "tests": hosted_invite_tests.exists(),
    }
    if not evidence["hosted_invites"]["router"] or not evidence["hosted_invites"]["tests"]:
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
        "service_pagination": "next_cursor" in market_service and "has_more" in market_service,
        "full_python_filter_marker": "filtered_records = [" in market_service,
    }
    if evidence["market_discovery"]["full_python_filter_marker"]:
        warnings.append(
            "market_discovery_still_performs_post-load_python_filtering; " "large-market_sql_optimization remains open"
        )

    evidence["unity_gate"] = {
        "workflow_present": "unity-windows-build:" in deploy_workflow,
        "license_failure_classified": "No valid Unity Editor license found" in deploy_workflow,
    }
    if not evidence["unity_gate"]["workflow_present"]:
        violations.append("unity_windows_release_gate_missing")
    if not evidence["unity_gate"]["license_failure_classified"]:
        warnings.append("unity_license_failure_is_not_explicitly_classified")

    issuance_policy = BACKEND / "config/player_share_issuance.toml"
    issuance_script = BACKEND / "scripts/issue_player_share_markets.py"
    issuance_strict_script = BACKEND / "scripts/issue_player_share_markets_strict.py"
    evidence["player_share_issuance_contract"] = {
        "policy_toml": issuance_policy.exists(),
        "issuer_script": issuance_script.exists(),
        "strict_issuer_script": issuance_strict_script.exists(),
    }
    if not all(evidence["player_share_issuance_contract"].values()):
        violations.append("player_share_issuance_contract_incomplete")

    unity_root = ROOT / "Gtex_Test_Migration/Assets/Code"
    match_controller = read(unity_root / "GTEX/Engine/GtexMatchController.cs")
    runtime_bootstrap = read(unity_root / "GTEX/Core/GtexRuntimeBootstrap.cs")
    stadium_atmosphere = read(unity_root / "GTEX/GtexStadiumAtmosphere.cs")
    startup_overlay = read(unity_root / "GTEX/Core/GtexLiveStartupOverlay.cs")
    build_tools = read(unity_root / "Editor/GtexBuildTools.cs")
    render_config = read(unity_root / "GTEX/Core/GtexRenderConfig.cs")
    render_repair = read(unity_root / "Editor/GtexRenderPipelineRepairTools.cs")
    pitch_presentation = read(unity_root / "GTEX/Presentation/GtexLivePitchPresentation.cs")
    isolation_guard = read(unity_root / "GTEX/Presentation/GtexLivePlaybackIsolationGuard.cs")
    metrics_source = read(BACKEND / "app/observability/metrics.py")
    live_dashboard = read(ROOT / "ops/observability/grafana/dashboards/gtex-live-playback.json")
    live_alerts = read(ROOT / "ops/observability/prometheus/rules/gtex-alerts.yml")
    rollback_runbook = read(ROOT / "ops/gtex-live-playback-rollback-runbook.md")
    unblock_checklist = read(ROOT / "docs/GTEX_P6_UNBLOCK_CHECKLIST.md")
    gap_backlog = read(ROOT / "docs/reports/GTEX_P6_PRODUCTION_GAP_BACKLOG.md")

    p6_gates: dict[str, bool] = {
        "p6_01_unity_windows_ci_gate": (
            "unity-windows-build:" in deploy_workflow
            and "unity-windows-build:" in staging_workflow
            and "BuildWindows64ProductionFromCommandLine" in deploy_workflow
            and "BuildWindows64ProductionFromCommandLine" in staging_workflow
            and "backend-live-playback-tests:" in deploy_workflow
            and (ROOT / "tools/run_gtex_windows_production_build.ps1").exists()
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_01_UNITY_WINDOWS_CI_GATE.md")
        ),
        "p6_02_current_engine_ownership": (
            "GtexEngineOwnershipMode.LegacyBootstrap" in match_controller
            and "PublishLiveState" in match_controller
            and "GtexMatchController" in runtime_bootstrap
            and "GtexMatchController.MatchManagerAdapter.FieldSize" in stadium_atmosphere
            and (ROOT / "docs/GTEX_P6_02_CURRENT_ENGINE_OWNERSHIP_AUDIT.md").exists()
        ),
        "p6_03_full_session_playback_validation": (
            (ROOT / "tools/run_gtex_full_session_validation.ps1").exists()
            and (ROOT / "tools/gtex_live_full_session_mock_server.py").exists()
            and (unity_root / "Editor/Gtex3DFullSessionVerifier.cs").exists()
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md")
        ),
        "p6_04_release_path_no_debug_overlay": (
            "Application.isEditor || GtexConfig.IsDev" in startup_overlay
            and "BuildWindows64ProductionFromCommandLine" in build_tools
            and "`P6-04` is now `PASSED`." in read(ROOT / "docs/GTEX_P6_04_RELEASE_PATH_AUDIT.md")
        ),
        "p6_05_staging_soak_run": (
            (ROOT / "tools/run_gtex_staging_soak.ps1").exists()
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_05_STAGING_SOAK_RUN.md")
        ),
        "p6_06_hosted_live_verification": (
            (ROOT / "tools/run_gtex_hosted_live_verification.ps1").exists()
            and (ROOT / "tools/provision_gtex_live_match.py").exists()
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_06_HOSTED_LIVE_VERIFICATION.md")
        ),
        "p6_07_live_observability": (
            "gtex_unity_live_access_total" in metrics_source
            and "gtex_unity_live_payload_total" in metrics_source
            and "gtex_unity_live_websocket_events_total" in metrics_source
            and "gtex_unity_live_generated_match_total" in metrics_source
            and "GTEX Live Playback" in live_dashboard
            and "GTexUnityLiveStaleStateDetected" in live_alerts
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_07_LIVE_OBSERVABILITY.md")
        ),
        "p6_08_rollback_operator_workflow": (
            "Trigger R1" in rollback_runbook
            and "Trigger R5" in rollback_runbook
            and "Post-Rollback Verification" in rollback_runbook
        ),
        "p6_09_render_content_signoff": (
            "ApplyForCurrentMode" in render_config
            and "Mobile_RPAsset.asset" in render_repair
            and "PC_RPAsset.asset" in render_repair
            and "HideLegacyPitchRenderers" in pitch_presentation
            and "GtexLivePlaybackIsolationGuard" in isolation_guard
            and "BuildAndroidApkFromCommandLine" in build_tools
            and "ExportAndroidLibraryFromCommandLine" in build_tools
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_09_RENDER_CONTENT_SIGNOFF.md")
        ),
        "p6_10_runtime_resilience_verification": (
            (ROOT / "tools/run_gtex_live_resilience_smoke.ps1").exists()
            and (ROOT / "tools/gtex_live_resilience_mock_server.py").exists()
            and "Current status: `PASSED`" in read(ROOT / "docs/GTEX_P6_10_RUNTIME_RESILIENCE_VERIFICATION.md")
        ),
        "p6_11_final_gate_review": (
            "## Final Gate Review Note (`P6-11`)" in unblock_checklist
            and "## P6-11 Repo-Side Verification & Final Gate Review Note" in gap_backlog
            and all(
                any(
                    line.startswith(f"| P6-{idx:02d} |") and line.endswith("| `PASSED` |")
                    for line in unblock_checklist.splitlines()
                )
                for idx in range(1, 12)
            )
        ),
    }
    evidence["p6_current_engine_hardening"] = p6_gates
    for gate_name, passed in p6_gates.items():
        if not passed:
            violations.append(f"p6_gate_incomplete:{gate_name}")

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
