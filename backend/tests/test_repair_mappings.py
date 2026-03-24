from __future__ import annotations

import csv
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country
from app.ingestion.repair_mappings import main
from app.models.base import Base


PLAYER_HEADERS = [
    "player_id",
    "first_name",
    "last_name",
    "name",
    "last_season",
    "current_club_id",
    "player_code",
    "country_of_birth",
    "city_of_birth",
    "country_of_citizenship",
    "date_of_birth",
    "sub_position",
    "position",
    "foot",
    "height_in_cm",
    "contract_expiration_date",
    "agent_name",
    "image_url",
    "international_caps",
    "international_goals",
    "current_national_team_id",
    "url",
    "current_club_domestic_competition_id",
    "current_club_name",
    "market_value_in_eur",
    "highest_market_value_in_eur",
]


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _initialize_database(database_url: str):
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_canonical_entities(engine) -> None:
    with _session_factory(engine)() as session:
        country = Country(source_provider="seed", provider_external_id="NG", name="Nigeria", alpha2_code="NG")
        competition = Competition(
            source_provider="seed",
            provider_external_id="NG1",
            country=country,
            name="Test League",
            slug="test-league",
            competition_type="league",
            format_type="real_world",
            is_major=True,
            is_tradable=True,
        )
        club = Club(
            source_provider="seed",
            provider_external_id="100",
            country=country,
            current_competition=competition,
            name="Test FC",
            slug="test-fc",
            short_name="Test FC",
            is_tradable=True,
        )
        session.add_all([country, competition, club])
        session.commit()


def _csv_text(headers: list[str], rows: list[dict[str, str]]) -> str:
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(header, "")) for header in headers))
    return "\n".join(lines) + "\n"


def _write_archive(path: Path) -> Path:
    players = [
        {
            "player_id": "1",
            "first_name": "Alex",
            "last_name": "Ready",
            "name": "Alex Ready",
            "last_season": "2024",
            "current_club_id": "100",
            "player_code": "alex-ready",
            "country_of_birth": "Nigeria",
            "city_of_birth": "Lagos",
            "country_of_citizenship": "Nigeria",
            "date_of_birth": "2000-01-02 00:00:00",
            "sub_position": "Centre-Forward",
            "position": "Attack",
            "foot": "right",
            "height_in_cm": "180",
            "contract_expiration_date": "",
            "agent_name": "Agent",
            "image_url": "https://example.test/1.jpg",
            "international_caps": "",
            "international_goals": "",
            "current_national_team_id": "",
            "url": "https://example.test/player/1",
            "current_club_domestic_competition_id": "NG1",
            "current_club_name": "Test FC",
            "market_value_in_eur": "1000000",
            "highest_market_value_in_eur": "2000000",
        },
        {
            "player_id": "2",
            "first_name": "Ivory",
            "last_name": "NeedsMap",
            "name": "Ivory NeedsMap",
            "last_season": "2024",
            "current_club_id": "",
            "player_code": "ivory-needs-map",
            "country_of_birth": "Ivory Coast",
            "city_of_birth": "Abidjan",
            "country_of_citizenship": "Ivory Coast",
            "date_of_birth": "2000-01-02 00:00:00",
            "sub_position": "Centre-Forward",
            "position": "Attack",
            "foot": "right",
            "height_in_cm": "180",
            "contract_expiration_date": "",
            "agent_name": "Agent",
            "image_url": "https://example.test/2.jpg",
            "international_caps": "",
            "international_goals": "",
            "current_national_team_id": "",
            "url": "https://example.test/player/2",
            "current_club_domestic_competition_id": "",
            "current_club_name": "Unattached",
            "market_value_in_eur": "1000000",
            "highest_market_value_in_eur": "2000000",
        },
    ]
    clubs = [
        {
            "club_id": "100",
            "club_code": "test-fc",
            "name": "Test FC",
            "domestic_competition_id": "NG1",
            "total_market_value": "",
            "squad_size": "25",
            "average_age": "24.1",
            "foreigners_number": "5",
            "foreigners_percentage": "20.0",
            "national_team_players": "2",
            "stadium_name": "Test Ground",
            "stadium_seats": "12000",
            "net_transfer_record": "0",
            "coach_name": "",
            "last_season": "2024",
            "filename": "clubs.json.gz",
            "url": "https://example.test/club/test-fc",
        }
    ]
    competitions = [
        {
            "competition_id": "NG1",
            "competition_code": "test-league",
            "name": "Test League",
            "sub_type": "league",
            "type": "domestic_league",
            "country_id": "NG",
            "country_name": "Nigeria",
            "domestic_league_code": "NG1",
            "confederation": "caf",
            "url": "https://example.test/competition/ng1",
            "is_major_national_league": "true",
        }
    ]
    countries = [
        {
            "country_id": "NG",
            "country_name": "Nigeria",
            "country_code": "NG",
            "confederation": "caf",
            "total_clubs": "20",
            "total_players": "400",
            "average_age": "24.5",
            "url": "https://example.test/country/ng",
        }
    ]
    with ZipFile(path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("players.csv", _csv_text(PLAYER_HEADERS, players))
        archive.writestr(
            "clubs.csv",
            _csv_text(
                [
                    "club_id",
                    "club_code",
                    "name",
                    "domestic_competition_id",
                    "total_market_value",
                    "squad_size",
                    "average_age",
                    "foreigners_number",
                    "foreigners_percentage",
                    "national_team_players",
                    "stadium_name",
                    "stadium_seats",
                    "net_transfer_record",
                    "coach_name",
                    "last_season",
                    "filename",
                    "url",
                ],
                clubs,
            ),
        )
        archive.writestr(
            "competitions.csv",
            _csv_text(
                [
                    "competition_id",
                    "competition_code",
                    "name",
                    "sub_type",
                    "type",
                    "country_id",
                    "country_name",
                    "domestic_league_code",
                    "confederation",
                    "url",
                    "is_major_national_league",
                ],
                competitions,
            ),
        )
        archive.writestr(
            "countries.csv",
            _csv_text(
                [
                    "country_id",
                    "country_name",
                    "country_code",
                    "confederation",
                    "total_clubs",
                    "total_players",
                    "average_age",
                    "url",
                ],
                countries,
            ),
        )
        for dataset_name in ("national_teams.csv", "player_valuations.csv", "transfers.csv", "club_games.csv"):
            archive.writestr(dataset_name, "id,name\n")
    return path


def test_repair_mappings_scans_without_importing_and_writes_csv(tmp_path: Path, capsys, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "repair.db")
    engine = _initialize_database(database_url)
    try:
        _seed_canonical_entities(engine)
        archive_path = _write_archive(tmp_path / "2nd.zip")
        csv_path = tmp_path / "reports" / "unresolved.csv"
        monkeypatch.setattr("app.ingestion.repair_mappings.ensure_database_schema_current", lambda _engine: None)
        monkeypatch.setattr("backend.app.ingestion.repair_mappings.ensure_database_schema_current", lambda _engine: None)

        exit_code = main(
            [
                "--database-url",
                database_url,
                "--file",
                str(archive_path),
                "--csv-path",
                str(csv_path),
            ]
        )

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["selected_player_count"] == 2
        assert payload["resolved_row_count"] == 1
        assert payload["skipped_row_count"] == 0
        assert payload["unresolved_row_count"] == 1
        assert payload["unresolved_group_count"] == 1

        rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
        assert rows == [
            {
                "club_name": "Unattached",
                "country_name": "Ivory Coast",
                "count": "1",
                "examples": "Ivory NeedsMap",
            }
        ]
    finally:
        engine.dispose()
