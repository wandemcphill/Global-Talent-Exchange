from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.real_player_import_ops import main


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _write_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "cli-batch.json"
    manifest_path.write_text(
        json.dumps(
            {
                "mode": "curated_seed",
                "ingestion_batch_id": "cli-batch",
                "ingestion_source_version": "ops-cli-v1",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "osimhen-001",
                        "canonical_name": "Victor Osimhen",
                        "known_aliases": ["V. Osimhen"],
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "date_of_birth": "1998-12-29",
                        "dominant_foot": "right",
                        "primary_position": "Striker",
                        "secondary_positions": ["Winger"],
                        "current_real_world_club": "Galatasaray",
                        "current_real_world_league": "Super Lig",
                        "competition_level": "top_flight",
                        "appearances": 31,
                        "minutes_played": 2410,
                        "goals": 19,
                        "assists": 4,
                        "current_market_reference_value": 60000000,
                        "market_reference_currency": "EUR",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_real_player_import_ops_cli_runs_and_lists_status(tmp_path: Path, capsys) -> None:
    database_url = _database_url(tmp_path / "cli-ops.db")
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "--database-url",
            database_url,
            "run",
            "--manifest-path",
            str(manifest_path),
            "--mode",
            "dry-run",
        ]
    )
    assert exit_code == 0
    run_payload = json.loads(capsys.readouterr().out)
    assert run_payload["batch_key"] == "cli-batch"
    assert run_payload["status"] == "completed"

    exit_code = main(
        [
            "--database-url",
            database_url,
            "status",
            "--batch-key",
            "cli-batch",
        ]
    )
    assert exit_code == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert len(status_payload) == 1
    assert status_payload[0]["batch_key"] == "cli-batch"
