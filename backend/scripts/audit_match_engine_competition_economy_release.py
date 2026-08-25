from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "simulation": ROOT / "app" / "match_engine" / "simulation" / "event_generator.py",
    "strength": ROOT / "app" / "match_engine" / "simulation" / "strength.py",
    "events": ROOT / "app" / "match_engine" / "simulation" / "event_generator.py",
    "competition": ROOT / "app" / "services" / "competition_match_service.py",
    "economy": ROOT / "app" / "economy" / "match_economy_engine.py",
}


def source(key: str) -> str:
    return FILES[key].read_text(encoding="utf-8")


def functions(key: str) -> set[str]:
    tree = ast.parse(source(key))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def audit() -> dict[str, object]:
    violations: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if "simulate" not in functions("simulation"):
        violations.append(
            {
                "finding": "simulation_entrypoint_missing",
                "surface": "event_generator.simulate",
            }
        )

    strength_source = source("strength").lower()
    for marker in (
        "form",
        "morale",
        "motivation",
        "fatigue",
        "chemistry",
        "coach",
        "tactical",
        "adaptability",
    ):
        if marker not in strength_source:
            violations.append(
                {"finding": "strength_factor_missing", "surface": marker}
            )

    events_source = source("events").lower()
    for marker in ("goal", "card", "substitution", "injury"):
        if marker not in events_source:
            violations.append(
                {"finding": "event_family_missing", "surface": marker}
            )

    competition_source = source("competition")
    competition_functions = functions("competition")
    for function_name in ("complete_match", "_apply_match_result"):
        if function_name not in competition_functions:
            violations.append(
                {
                    "finding": "competition_settlement_boundary_missing",
                    "surface": function_name,
                }
            )
    for marker in (
        "is_terminal",
        "stats_applied",
        "already settled",
        "cannot be re-settled",
    ):
        if marker not in competition_source:
            violations.append(
                {"finding": "settlement_guard_missing", "surface": marker}
            )

    economy_source = source("economy")
    economy_functions = functions("economy")
    for function_name in (
        "join_match",
        "fund_gtex_match",
        "record_match_volume",
        "run_lottery",
    ):
        if function_name not in economy_functions:
            violations.append(
                {"finding": "match_economy_surface_missing", "surface": function_name}
            )
    for marker in (
        "idempotency_key=idempotency_key",
        "EconomyGovernorService",
        "SpendingControlService",
        "RewardSettlement",
        "PLATFORM_COMPETITION_REWARD",
    ):
        if marker not in economy_source:
            violations.append(
                {"finding": "match_economy_control_missing", "surface": marker}
            )

    return {
        "group": "match-engine-competition-economy",
        "contract": (
            "match simulation must remain layered and reproducible; terminal matches must settle exactly once; "
            "match-funded rewards must flow through authoritative ledger/economic controls"
        ),
        "violations": violations,
        "warnings": warnings,
        "pass": not violations,
        "read_only": True,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
