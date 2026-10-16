from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from backend.app.ingestion.real_player_batch_runner import RealPlayerBatchRunner


def _render_table(headers: list[str], rows: list[list[object]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider_line = "-+-".join("-" * width for width in widths)
    body_lines = [
        " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, divider_line, *body_lines]) if body_lines else "\n".join([header_line, divider_line, "(none)"])


def _finding_rows(findings: list[dict[str, object]]) -> list[list[object]]:
    rows: list[list[object]] = []
    for finding in findings:
        rows.append(
            [
                finding["finding_type"],
                finding["normalized_key"],
                ",".join(finding.get("gtex_player_ids", [])) or "-",
                ",".join(finding.get("source_keys", [])) or "-",
                finding.get("resolution_status", "-"),
                finding.get("required_action", "-") or "-",
            ]
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the controlled first-batch real-player ingestion flow.")
    parser.add_argument("mode", choices=["dry-run", "write"], help="Dry-run rolls back the outer transaction; write commits only if the audit stays clean.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL.",
    )
    parser.add_argument(
        "--batch-path",
        default=str((ROOT_DIR / "backend" / "data" / "real_player_batches" / "first_batch.json").resolve()),
        help="Path to the first-batch JSON payload.",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path for the machine-readable JSON report.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    runner = RealPlayerBatchRunner(
        database_url=args.database_url,
        batch_path=args.batch_path,
    )
    report = runner.run(mode=args.mode)
    payload = report.to_dict()

    print(f"Real Player Batch Mode: {report.runner_mode}")
    print(f"Batch Path: {report.batch_path}")
    print(f"Database URL: {report.database_url}")
    print(f"Verdict: {report.verdict}")
    print(f"Ambiguous Matches: {report.ambiguous_matches}")
    print(f"Missing Pricing Snapshots: {report.missing_pricing_snapshots}")
    print(f"Hard Failures: {report.hard_failures}")
    print()
    print("Preflight Result Table")
    print(
        _render_table(
            ["source_key", "canonical_name", "resolved_action", "gtex_player_id", "confidence", "audit_status"],
            [
                [
                    row["source_name"] + ":" + row["source_player_key"],
                    row["canonical_name"],
                    row["resolved_action"],
                    row["gtex_player_id"] or "-",
                    row["confidence_score"],
                    row["audit_status"],
                ]
                for row in payload["preflight_rows"]
            ],
        )
    )
    print()
    print("Execution Result Table")
    print(
        _render_table(
            ["source_key", "canonical_name", "resolved_action", "gtex_player_id", "confidence", "pricing_snapshot_id", "pricing_status", "audit_status", "commit_status"],
            [
                [
                    row["source_name"] + ":" + row["source_player_key"],
                    row["canonical_name"],
                    row["resolved_action"],
                    row["gtex_player_id"] or "-",
                    row["confidence_score"],
                    row["pricing_snapshot_id"] or "-",
                    row["pricing_status"],
                    row["audit_status"],
                    row["commit_status"],
                ]
                for row in payload["execution_rows"]
            ],
        )
    )
    print()
    print("Duplicate Findings Table")
    print(
        _render_table(
            ["finding_type", "normalized_key", "gtex_player_ids", "source_keys", "status", "required_action"],
            _finding_rows(payload["duplicate_findings"]),
        )
    )
    print()
    print("Ambiguous Findings Table")
    print(
        _render_table(
            ["finding_type", "normalized_key", "gtex_player_ids", "source_keys", "status", "required_action"],
            _finding_rows(payload["ambiguous_findings"]),
        )
    )
    if payload["pricing_findings"]:
        print()
        print("Pricing Findings Table")
        print(
            _render_table(
                ["finding_type", "normalized_key", "gtex_player_ids", "source_keys", "status", "required_action"],
                _finding_rows(payload["pricing_findings"]),
            )
        )
    if payload["stability_findings"]:
        print()
        print("Stability Findings Table")
        print(
            _render_table(
                ["finding_type", "normalized_key", "gtex_player_ids", "source_keys", "status", "required_action"],
                _finding_rows(payload["stability_findings"]),
            )
        )
    print()
    print("JSON Report")
    print(json.dumps(payload, indent=2))

    if args.json_output:
        output_path = Path(args.json_output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return 0 if report.verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
