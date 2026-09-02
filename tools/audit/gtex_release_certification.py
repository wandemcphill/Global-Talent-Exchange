from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]

CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("reality_audit", (sys.executable, "tools/audit/reality_audit.py")),
    (
        "player_share_release_audit",
        (sys.executable, "backend/scripts/audit_player_share_release.py"),
    ),
    (
        "player_share_lifecycle_audit",
        (sys.executable, "backend/scripts/audit_player_share_lifecycle.py"),
    ),
    (
        "player_share_trade_boundary_audit",
        (sys.executable, "backend/scripts/audit_player_share_trade_boundary.py"),
    ),
    (
        "player_share_api_contract_audit",
        (sys.executable, "backend/scripts/audit_player_share_api_contract.py"),
    ),
)


def _run(name: str, command: tuple[str, ...]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
        env=os.environ.copy(),
    )
    return {
        "name": name,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _git_state() -> dict[str, object]:
    status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    branch = subprocess.run(
        ("git", "branch", "--show-current"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return {
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "clean": not bool(status.stdout.strip()),
        "status": status.stdout.strip(),
    }


def main() -> int:
    results: list[dict[str, object]] = []
    for name, command in CHECKS:
        try:
            results.append(_run(name, command))
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "name": name,
                    "ok": False,
                    "returncode": None,
                    "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                    "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
                    "timeout": True,
                }
            )

    payload = {
        "certification": "GTEX local release certification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git": _git_state(),
        "checks": results,
        "github_actions": "unavailable_if_quota_exhausted",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if all(bool(item["ok"]) for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
