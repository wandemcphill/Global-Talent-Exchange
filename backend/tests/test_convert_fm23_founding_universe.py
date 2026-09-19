from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.scripts.convert_fm23_founding_universe import convert


def test_fm23_converter_deduplicates_exact_rows_and_preserves_game_semantics(tmp_path: Path) -> None:
    source = tmp_path / "fm23.csv"
    output = tmp_path / "fm23.jsonl"
    source.write_text(
        (
            'Name;"Nation";"Position";"Club";"Age";"Wage";"Value";"Sale Value";"Best Rating";"Best Pot Rating"\n'
            'Example One;"Brazil";"AM RLC, F C";"Example Club";"24";"150,000";"25,000,000";"40,000,000";"91.2% (FS)";"94.2% (FS)"\n'
            'Example One;"Brazil";"AM RLC, F C";"Example Club";"24";"150,000";"25,000,000";"40,000,000";"91.2% (FS)";"94.2% (FS)"\n'
        ),
        encoding="cp1252",
    )

    report = convert(source, output, source_version="fm23-test-v1")

    assert report["source_row_count"] == 2
    assert report["emitted_row_count"] == 1
    assert report["exact_duplicate_rows_collapsed"] == 1
    assert report["identity_collision_count"] == 0

    row = json.loads(output.read_text(encoding="utf-8").strip())
    assert row["source_name"] == "football_manager"
    assert row["source_player_key"].startswith("fm23:")
    assert "age" not in row
    assert "current_market_reference_value" not in row
    assert "current_real_world_club" not in row
    assert row["is_verified_real_player"] is False
    metadata = row["source_metadata"]
    assert metadata["fm23_age"] == 24
    assert metadata["fm23_value"] == 25000000
    assert metadata["fm23_sale_value"] == 40000000
    assert metadata["fm23_position"] == "AM RLC, F C"
    assert metadata["fm23_best_rating"]["percent"] == pytest.approx(91.2)
    assert metadata["semantics"]["value"].startswith("FM game value")


def test_fm23_converter_fails_closed_on_non_identical_identity_collisions(tmp_path: Path) -> None:
    source = tmp_path / "fm23.csv"
    output = tmp_path / "fm23.jsonl"
    source.write_text(
        (
            'Name;"Nation";"Position";"Club";"Age";"Wage";"Value";"Sale Value";"Best Rating";"Best Pot Rating"\n'
            'Same Name;"England";"ST";"Example Club";"24";"10,000";"1,000,000";"2,000,000";"70.0% (TS)";"75.0% (TS)"\n'
            'Same Name;"England";"ST";"Example Club";"24";"20,000";"1,500,000";"3,000,000";"72.0% (TS)";"77.0% (TS)"\n'
        ),
        encoding="cp1252",
    )

    with pytest.raises(ValueError, match="share the same provisional identity tuple"):
        convert(source, output, source_version="fm23-test-v1")
