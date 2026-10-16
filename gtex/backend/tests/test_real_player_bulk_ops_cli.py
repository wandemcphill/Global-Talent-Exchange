from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.import_real_players_bulk import main as import_main
from backend.scripts.report_real_player_import import main as report_main


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "real_player_bulk_import_sample.json"


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def test_bulk_ops_cli_import_and_report(tmp_path: Path, capsys) -> None:
    database_url = _database_url(tmp_path / "bulk-ops-cli.db")
    fixture_path = tmp_path / "bulk-ops-cli.json"
    fixture_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    exit_code = import_main(
        [
            "--database-url",
            database_url,
            "--file",
            str(fixture_path),
            "--provider",
            "bulk-fixture",
            "--batch-size",
            "2",
        ]
    )
    assert exit_code == 0
    import_payload = json.loads(capsys.readouterr().out)
    run_id = import_payload["run"]["id"]
    assert import_payload["operation"] == "import"
    assert import_payload["run"]["processed_rows"] == 4

    exit_code = report_main(
        [
            "--database-url",
            database_url,
            "--run-id",
            run_id,
        ]
    )
    assert exit_code == 0
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["operation"] == "report"
    assert report_payload["run"]["id"] == run_id
    assert "processing_state_distribution" in report_payload["run"]
