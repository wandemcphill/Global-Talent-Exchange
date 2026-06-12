"""GTEX release gate: runs the canonical certification checks and emits PASS/FAIL with evidence.

Usage:
    python tools/release/gtex_release_gate.py [--fast] [--json OUT.json]

--fast skips the slow pytest shards (startup/module registration) and runs
static + guard checks only. Exit code 0 = PASS, 1 = FAIL, 2 = gate error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable or "python"
FLUTTER = os.environ.get("GTEX_FLUTTER_BAT", r"C:\flutter\bin\flutter.bat")

# Minimal env to let create_app() compose standalone, mirroring backend/tests/conftest.py.
# Real values come from the deploy environment; these are inert defaults for the gate only.
_COMPOSE_DB = (REPO_ROOT / ".tmp_release_gate.db").as_posix()
COMPOSE_ENV = {
    "DATABASE_URL": f"sqlite+pysqlite:///{_COMPOSE_DB}",
    "GTE_DATABASE_URL": f"sqlite+pysqlite:///{_COMPOSE_DB}",
    "GTE_AUTH_SECRET": "release-gate-compose-secret",
    "GTE_MEDIA_SIGNING_SECRET": "release-gate-media-secret",
    "GTE_BOOTSTRAP_ADMIN_ENABLED": "0",
    "GTE_OUTBOX_RELAY_ENABLED": "0",
    "GTE_PROJECTION_WORKERS_ENABLED": "0",
    "GTE_RUN_STARTUP_SEEDING": "0",
    "GTE_TASK_QUEUE_ENABLED": "0",
}

# Shards chosen for signal-per-second: full backend suite is multi-hour.
PYTEST_SHARDS: dict[str, list[str]] = {
    "production_guards": ["backend/tests/ops/test_canonical_production_guards.py"],
    "websocket_contracts": [
        "backend/tests/realtime/test_websocket_route_contracts.py",
        "backend/tests/realtime/test_match_websocket_gateway.py",
        "backend/tests/realtime/test_wallet_websocket_gateway.py",
    ],
    "module_registration": ["backend/tests/app/test_module_registration.py"],
    "money_lane": ["backend/tests/trader/test_trader_service.py"],
}
SLOW_SHARDS = {"module_registration", "websocket_contracts"}


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration_s: float
    evidence: str
    skipped: bool = False


@dataclass
class GateReport:
    verdict: str = "FAIL"
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        status = "SKIP" if result.skipped else ("PASS" if result.passed else "FAIL")
        print(f"[{status}] {result.name} ({result.duration_s:.1f}s)")
        if not result.passed and not result.skipped:
            print(f"        {result.evidence[:500]}")


def _run(cmd: list[str], *, timeout: int, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None) -> tuple[bool, str]:
    run_env = None
    if env:
        run_env = {**os.environ, **env}
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=run_env
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError as exc:
        return False, f"NOT FOUND: {exc}"
    tail = (proc.stdout + proc.stderr)[-2000:]
    return proc.returncode == 0, tail


def _timed(name: str, fn) -> CheckResult:
    start = time.monotonic()
    passed, evidence = fn()
    return CheckResult(name=name, passed=passed, duration_s=time.monotonic() - start, evidence=evidence)


def check_guardrail_scan() -> tuple[bool, str]:
    return _run([PYTHON, "tools/guardrails/production_guardrail_scan.py"], timeout=300)


def check_api_contract() -> tuple[bool, str]:
    return _run([PYTHON, "tools/audit/check_api_contract_violations.py"], timeout=300)


def check_backend_import() -> tuple[bool, str]:
    # Proves the app composes: settings, container, all 117 routers import.
    code = "import app.main; app.main.create_app(run_migration_check=False); print('APP_COMPOSED')"
    return _run([PYTHON, "-c", code], timeout=900, cwd=REPO_ROOT / "backend", env=COMPOSE_ENV)


def check_routes_registered() -> tuple[bool, str]:
    code = (
        "import app.main\n"
        "a = app.main.create_app(run_migration_check=False)\n"
        "routes = [r.path for r in a.routes]\n"
        "required = ['/api/v2/auth/login', '/health']\n"
        "missing = [p for p in required if not any(p in r for r in routes)]\n"
        "assert not missing, f'missing routes: {missing}'\n"
        "print(f'ROUTES_OK count={len(routes)}')\n"
    )
    return _run([PYTHON, "-c", code], timeout=900, cwd=REPO_ROOT / "backend", env=COMPOSE_ENV)


def check_pytest_shard(paths: list[str]) -> tuple[bool, str]:
    cmd = [PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q", *paths]
    return _run(cmd, timeout=1800)


def check_flutter_analyze() -> tuple[bool, str]:
    if not Path(FLUTTER).exists():
        return False, f"flutter not found at {FLUTTER}"
    return _run([FLUTTER, "analyze", "--no-pub"], timeout=900, cwd=REPO_ROOT / "frontend")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="skip slow pytest shards")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--skip-flutter", action="store_true")
    args = parser.parse_args()

    report = GateReport()
    report.add(_timed("guardrail_scan", check_guardrail_scan))
    report.add(_timed("api_contract_violations", check_api_contract))
    report.add(_timed("backend_app_composes", check_backend_import))
    report.add(_timed("routes_registered", check_routes_registered))

    for shard_name, paths in PYTEST_SHARDS.items():
        if args.fast and shard_name in SLOW_SHARDS:
            report.add(CheckResult(shard_name, True, 0.0, "skipped (--fast)", skipped=True))
            continue
        report.add(_timed(f"pytest:{shard_name}", lambda p=paths: check_pytest_shard(p)))

    if args.skip_flutter:
        report.add(CheckResult("flutter_analyze", True, 0.0, "skipped (--skip-flutter)", skipped=True))
    else:
        report.add(_timed("flutter_analyze", check_flutter_analyze))

    hard_failures = [c for c in report.checks if not c.passed and not c.skipped]
    report.verdict = "PASS" if not hard_failures else "FAIL"

    print("\n" + "=" * 60)
    print(f"GTEX RELEASE GATE: {report.verdict}")
    if hard_failures:
        for c in hard_failures:
            print(f"  FAIL: {c.name}")
    print("=" * 60)

    if args.json:
        args.json.write_text(
            json.dumps({"verdict": report.verdict, "checks": [asdict(c) for c in report.checks]}, indent=2),
            encoding="utf-8",
        )
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
