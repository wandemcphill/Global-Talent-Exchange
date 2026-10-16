from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

FORBIDDEN_FIELD_NAMES = {"demo", "fixture", "mock", "synthetic"}


def _load_harness() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    harness_path = repo_root / "tools" / "load" / "strict_live_runtime_load.py"
    spec = importlib.util.spec_from_file_location("strict_live_runtime_load", harness_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PHASE2_LIVE_RESPONSE_CASES: tuple[dict[str, Any], ...] = (
    {
        "surface": "profile/bootstrap",
        "method": "GET",
        "endpoint": "/api/session/bootstrap",
        "status_code": 200,
        "payload": {
            "roles": ["club_owner"],
            "permissions": ["manage_club"],
            "runtime": {
                "strict_live": True,
                "backend_mode": "live",
                "payments": {
                    "korapay_enabled": True,
                    "paystack_enabled": False,
                },
            },
            "source_of_truth": "persisted_backend_authority",
        },
    },
    {
        "surface": "admin rejection",
        "method": "GET",
        "endpoint": "/api/admin/operations-readiness",
        "status_code": 403,
        "payload": {
            "detail": "Admin privileges are required for operations readiness.",
            "error_code": "admin_forbidden",
            "required_permission": "manage_admin_console",
        },
    },
    {
        "surface": "club snapshot/no-club",
        "method": "GET",
        "endpoint": "/api/club/current",
        "status_code": 404,
        "payload": {
            "detail": "No active club is registered for this account.",
            "club": None,
            "has_club": False,
        },
    },
    {
        "surface": "national rental",
        "method": "GET",
        "endpoint": "/api/national/competitions/{competition_id}/rental-pool",
        "status_code": 200,
        "payload": {
            "competition_id": "nations-live-2026",
            "total": 1,
            "items": [
                {
                    "player_id": "player-live-9",
                    "player_name": "K. Adeyemi",
                    "country_code": "NG",
                    "source_bucket": "sportmonks",
                    "eligibility": {
                        "eligible": True,
                        "reasons": [],
                        "checks": {
                            "persisted_player": True,
                            "age_band": True,
                            "squad_limit": True,
                        },
                    },
                },
            ],
        },
    },
    {
        "surface": "competition/world-super-cup runtime",
        "method": "GET",
        "endpoint": "/api/competitions/runtime/world-super-cup",
        "status_code": 200,
        "payload": {
            "code": "world-super-cup",
            "status": "mounted",
            "source_of_truth": "persisted_backend_authority",
            "authority": "competition_os",
        },
    },
    {
        "surface": "competition/world-super-cup bracket",
        "method": "GET",
        "endpoint": "/api/world-super-cup/knockout/bracket",
        "status_code": 200,
        "payload": {
            "rounds": [
                {
                    "name": "Final",
                    "matches": [
                        {
                            "fixture_id": "wsc-final-1",
                            "home_club": "club-live-1",
                            "away_club": "club-live-2",
                            "status": "scheduled",
                        },
                    ],
                },
            ],
            "source_of_truth": "persisted_backend_authority",
        },
    },
    {
        "surface": "realtime auth/provenance",
        "method": "WS",
        "endpoint": "/realtime/stream",
        "status_code": 101,
        "payload": {
            "type": "wallet_update",
            "topic": "wallet:user-live-1",
            "source_of_truth": "persisted_backend_authority",
            "runtime_source": "persisted_backend_authority",
            "data": {
                "user_id": "user-live-1",
                "ledger_cursor": 42,
            },
            "realtime_provenance": {
                "transport": "websocket",
                "source_of_truth": "persisted_backend_authority",
                "topics": ["wallet:user-live-1"],
            },
        },
    },
    {
        "surface": "treasury invalid-claim",
        "method": "POST",
        "endpoint": "/api/admin/treasury/withdrawals/{withdrawal_id}/status",
        "status_code": 404,
        "payload": {
            "detail": "Withdrawal claim could not be matched to a live treasury request.",
            "error_code": "treasury_claim_invalid",
            "claim_valid": False,
            "source_of_truth": "ledger_authority",
        },
    },
)


SYNTHETIC_REJECTION_CASES: tuple[tuple[str, dict[str, Any], str], ...] = (
    (
        "profile/bootstrap demo source",
        {"runtime_source": "demo_bootstrap"},
        "synthetic_source:$.runtime_source",
    ),
    (
        "admin rejection mock field",
        {"mock": True, "detail": "Admin privileges are required."},
        "synthetic_field:$.mock",
    ),
    (
        "club snapshot fixture field",
        {"fixture": True, "detail": "No active club."},
        "synthetic_field:$.fixture",
    ),
    (
        "national rental fixture source",
        {"items": [{"source": "fixture_repository"}]},
        "synthetic_source:$.items[0].source",
    ),
    (
        "competition synthetic mode",
        {"mode": "synthetic_projection"},
        "synthetic_source:$.mode",
    ),
    (
        "realtime mock provenance",
        {"data": {"source": "mock_socket"}},
        "synthetic_source:$.data.source",
    ),
    (
        "treasury synthetic field",
        {"synthetic": True, "error_code": "treasury_claim_invalid"},
        "synthetic_field:$.synthetic",
    ),
)


def test_phase2_live_response_contracts_do_not_expose_synthetic_markers() -> None:
    harness = _load_harness()

    for case in PHASE2_LIVE_RESPONSE_CASES:
        assert case["method"]
        assert case["endpoint"]
        assert case["status_code"] in {101, 200, 403, 404}
        assert harness._walk_forbidden_payload(case["payload"]) == "", case["surface"]
        assert _forbidden_field_paths(case["payload"]) == [], case["surface"]


def test_phase2_synthetic_response_contracts_are_rejected() -> None:
    harness = _load_harness()

    for label, payload, expected_reason in SYNTHETIC_REJECTION_CASES:
        assert harness._walk_forbidden_payload(payload) == expected_reason, label


def _forbidden_field_paths(value: Any, *, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        failures: list[str] = []
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            next_path = f"{path}.{normalized_key}"
            if normalized_key in FORBIDDEN_FIELD_NAMES:
                failures.append(next_path)
            failures.extend(_forbidden_field_paths(item, path=next_path))
        return failures
    if isinstance(value, list):
        failures: list[str] = []
        for index, item in enumerate(value):
            failures.extend(_forbidden_field_paths(item, path=f"{path}[{index}]"))
        return failures
    return []
