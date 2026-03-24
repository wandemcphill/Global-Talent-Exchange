from __future__ import annotations

from pathlib import Path

from app.ingestion.unresolved_logger import UnresolvedMappingLogger


def test_unresolved_logger_aggregates_counts_and_caps_examples(tmp_path: Path) -> None:
    logger = UnresolvedMappingLogger(csv_path=tmp_path / "report.csv")

    logger.record(
        raw_club_name="Unattached",
        raw_country_name="Cote d'Ivoire",
        competition_name="liga-portugal-bwin",
        player_name="Player One",
    )
    logger.record(
        raw_club_name="Unattached",
        raw_country_name="Cote d'Ivoire",
        competition_name="liga-portugal-bwin",
        player_name="Player Two",
    )
    logger.record(
        raw_club_name="Unattached",
        raw_country_name="Cote d'Ivoire",
        competition_name="liga-portugal-bwin",
        player_name="Player Three",
    )
    logger.record(
        raw_club_name="Unattached",
        raw_country_name="Cote d'Ivoire",
        competition_name="liga-portugal-bwin",
        player_name="Player Four",
    )

    summary = logger.summary()
    assert len(summary) == 1
    assert summary[0].occurrence_count == 4
    assert summary[0].sample_player_names == ("Player One", "Player Two", "Player Three")


def test_unresolved_logger_writes_sorted_csv(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "unresolved.csv"
    logger = UnresolvedMappingLogger(csv_path=path)
    logger.record(raw_club_name="Club B", raw_country_name="Country B", player_name="Bravo")
    logger.record(raw_club_name="Club A", raw_country_name="Country A", player_name="Alpha")
    logger.record(raw_club_name="Club A", raw_country_name="Country A", player_name="Another")

    written_path = logger.write_csv()

    lines = written_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "club_name,country_name,count,examples"
    assert lines[1].startswith("Club A,Country A,2,")
    assert lines[2].startswith("Club B,Country B,1,")
