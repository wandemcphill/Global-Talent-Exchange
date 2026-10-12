from __future__ import annotations

from app.ingestion.fm23_genie_scout import build_manifest
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


def test_build_manifest_normalizes_genie_scout_rows(tmp_path) -> None:
    source = tmp_path / "founding.csv"
    source.write_text(
        '"Name";"Nation";"Position";"Club";"Age";"Wage";"Value";"Sale Value";"Best Rating";"Best Pot Rating"\n'
        '"Messi, Lionel";"Argentina";"AM RC, F C";"Barcelona";"23";"350,000";"160,875,010";"193,474,400";"100.6% (FS)";"100.6% (FS)"\n',
        encoding="utf-8",
    )

    manifest = build_manifest(source)

    assert manifest["ingestion_source_version"].startswith("gtex.fm23-genie-scout.v1:")
    assert manifest["as_of"] == "2022-06-27T00:00:00+00:00"
    RealPlayerIngestionRequest.model_validate(manifest)
    player = manifest["players"][0]
    assert player["canonical_name"] == "Lionel Messi"
    assert player["source_name"] == "fm23_club_legends_v0"
    assert player["source_player_key"].startswith("fm23gs-")
    assert player["overall_rating"] == 99
    assert player["potential"] == 99
    assert player["current_real_world_club"] == "Barcelona"
