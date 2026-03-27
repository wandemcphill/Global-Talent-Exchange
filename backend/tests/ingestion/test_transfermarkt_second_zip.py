from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import zipfile

from app.ingestion.transfermarkt_second_zip import (
    PLAYER_SOURCE_TO_GTEX_FIELD_MAP,
    SECOND_ZIP_REQUIRED_FILES,
    TransfermarktSecondZipReader,
    map_player_row_to_contract,
    parse_optional_height_cm,
    normalize_optional_text,
    normalize_position_fields,
    normalize_preferred_foot,
    parse_optional_int,
    parse_source_date,
)


def test_player_source_to_gtex_field_map_is_first_pass_contract() -> None:
    assert PLAYER_SOURCE_TO_GTEX_FIELD_MAP == {
        "external_player_id": "player_id",
        "slug": "player_code",
        "code": "player_code",
        "full_name": "name",
        "first_name": "first_name",
        "last_name": "last_name",
        "date_of_birth": "date_of_birth",
        "nationality": "country_of_citizenship",
        "country_of_birth": "country_of_birth",
        "city_of_birth": "city_of_birth",
        "preferred_foot": "foot",
        "height_cm": "height_in_cm",
        "primary_position_group": "position",
        "primary_position": "sub_position",
        "current_club_id": "current_club_id",
        "current_club_name": "current_club_name",
        "domestic_competition_id": "current_club_domestic_competition_id",
        "current_market_value_eur": "market_value_in_eur",
        "peak_market_value_eur": "highest_market_value_in_eur",
        "image_url": "image_url",
        "source_url": "url",
        "last_season": "last_season",
        "is_real_player": True,
    }


def test_player_contract_maps_expected_first_pass_fields() -> None:
    row = {
        " player_id ": " 10 ",
        " player_code ": " miroslav-klose ",
        " name ": " Miroslav Klose ",
        " first_name ": " Miroslav ",
        " last_name ": " Klose ",
        " date_of_birth ": "1978-06-09 00:00:00",
        " country_of_citizenship ": " Germany ",
        " country_of_birth ": " Poland ",
        " city_of_birth ": " Opole ",
        " foot ": " right ",
        " height_in_cm ": "184",
        " position ": " Attack ",
        " sub_position ": " Centre-Forward ",
        " current_club_id ": "398",
        " current_club_name ": " Societa Sportiva Lazio S.p.A. ",
        " current_club_domestic_competition_id ": " IT1 ",
        " market_value_in_eur ": "1000000",
        " highest_market_value_in_eur ": "30000000",
        " image_url ": " https://img.example.test/player.jpg ",
        " url ": " https://www.transfermarkt.co.uk/miroslav-klose/profil/spieler/10 ",
        " last_season ": "2015",
    }

    contract = map_player_row_to_contract(row)

    assert contract.external_player_id == "10"
    assert contract.slug == "miroslav-klose"
    assert contract.code == "miroslav-klose"
    assert contract.full_name == "Miroslav Klose"
    assert contract.first_name == "Miroslav"
    assert contract.last_name == "Klose"
    assert contract.date_of_birth == date(1978, 6, 9)
    assert contract.nationality == "Germany"
    assert contract.country_of_birth == "Poland"
    assert contract.city_of_birth == "Opole"
    assert contract.preferred_foot == "right"
    assert contract.height_cm == 184
    assert contract.primary_position_group == "Attack"
    assert contract.primary_position == "Centre-Forward"
    assert contract.current_club_id == "398"
    assert contract.current_club_name == "Societa Sportiva Lazio S.p.A."
    assert contract.domestic_competition_id == "IT1"
    assert contract.current_market_value_eur == 1_000_000
    assert contract.peak_market_value_eur == 30_000_000
    assert contract.image_url == "https://img.example.test/player.jpg"
    assert contract.source_url == "https://www.transfermarkt.co.uk/miroslav-klose/profil/spieler/10"
    assert contract.last_season == 2015
    assert contract.is_real_player is True
    assert contract.raw_payload["player_id"] == "10"


def test_normalization_helpers_cover_nulls_dates_feet_and_positions() -> None:
    assert normalize_optional_text("  Left Winger  ") == "Left Winger"
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text(" NULL ") is None

    assert parse_source_date("1978-06-09 00:00:00") == date(1978, 6, 9)
    assert parse_source_date(datetime(2001, 9, 5, 12, 45, 0)) == date(2001, 9, 5)
    assert parse_source_date("not-a-date") is None

    assert normalize_preferred_foot(" Left Footed ") == "left"
    assert normalize_preferred_foot("ambidextrous") == "both"
    assert normalize_preferred_foot("") is None

    assert normalize_position_fields(" Defender ", " Center Back ") == ("Defender", "Centre-Back")
    assert normalize_position_fields(" Missing ", " ") == (None, None)

    assert parse_optional_int("184") == 184
    assert parse_optional_int("184.0") == 184
    assert parse_optional_int("") is None


def test_parse_optional_height_cm_nulls_impossible_values() -> None:
    assert parse_optional_height_cm("184") == 184
    assert parse_optional_height_cm("18") is None
    assert parse_optional_height_cm("251") is None
    assert parse_optional_height_cm("") is None
    assert parse_optional_height_cm(None) is None


def test_player_contract_uses_height_hygiene_for_bad_source_values() -> None:
    base_row = {
        "player_id": "10",
        "name": "Test Player",
        "date_of_birth": "2004-01-10 00:00:00",
        "country_of_citizenship": "Scotland",
        "position": "Defender",
        "sub_position": "Centre-Back",
    }

    too_small = map_player_row_to_contract({**base_row, "height_in_cm": "19"})
    too_large = map_player_row_to_contract({**base_row, "height_in_cm": "300"})
    blank = map_player_row_to_contract({**base_row, "height_in_cm": ""})
    missing = map_player_row_to_contract(base_row)

    assert too_small.height_cm is None
    assert too_large.height_cm is None
    assert blank.height_cm is None
    assert missing.height_cm is None


def test_reader_supports_required_second_zip_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "players.csv",
            (
                " player_id , player_code , name , first_name , last_name , date_of_birth , country_of_citizenship ,"
                " country_of_birth , city_of_birth , foot , height_in_cm , position , sub_position , current_club_id ,"
                " current_club_name , current_club_domestic_competition_id , market_value_in_eur ,"
                " highest_market_value_in_eur , image_url , url , last_season \n"
                "1,test-player, Test Player ,Test,Player,2001-01-02 00:00:00,Nigeria,Nigeria,Lagos,right,180,"
                "Attack,Centre-Forward,100, Test FC ,NG1,250000,500000,https://img.test/a.jpg,"
                "https://example.test/player,2024\n"
            ),
        )
        archive.writestr("clubs.csv", " club_id , club_code , name \n100,test-fc, Test FC \n")
        archive.writestr(
            "competitions.csv",
            " competition_id , competition_code , name \nNG1,nigeria-premier-league, Nigeria Premier League \n",
        )
        archive.writestr("countries.csv", " country_id , country_name \nNG, Nigeria \n")

    reader = TransfermarktSecondZipReader(archive_path)

    reader.validate()
    player_rows = list(reader.iter_players())
    club_rows = list(reader.iter_clubs())
    competition_rows = list(reader.iter_competitions())
    country_rows = list(reader.iter_countries())
    player_contracts = list(reader.iter_player_contracts())

    assert SECOND_ZIP_REQUIRED_FILES == ("players.csv", "clubs.csv", "competitions.csv", "countries.csv")
    assert player_rows == [
        {
            "player_id": "1",
            "player_code": "test-player",
            "name": "Test Player",
            "first_name": "Test",
            "last_name": "Player",
            "date_of_birth": "2001-01-02 00:00:00",
            "country_of_citizenship": "Nigeria",
            "country_of_birth": "Nigeria",
            "city_of_birth": "Lagos",
            "foot": "right",
            "height_in_cm": "180",
            "position": "Attack",
            "sub_position": "Centre-Forward",
            "current_club_id": "100",
            "current_club_name": "Test FC",
            "current_club_domestic_competition_id": "NG1",
            "market_value_in_eur": "250000",
            "highest_market_value_in_eur": "500000",
            "image_url": "https://img.test/a.jpg",
            "url": "https://example.test/player",
            "last_season": "2024",
        }
    ]
    assert club_rows == [{"club_id": "100", "club_code": "test-fc", "name": "Test FC"}]
    assert competition_rows == [
        {
            "competition_id": "NG1",
            "competition_code": "nigeria-premier-league",
            "name": "Nigeria Premier League",
        }
    ]
    assert country_rows == [{"country_id": "NG", "country_name": "Nigeria"}]

    assert len(player_contracts) == 1
    assert player_contracts[0].external_player_id == "1"
    assert player_contracts[0].full_name == "Test Player"
    assert player_contracts[0].primary_position_group == "Attack"
    assert player_contracts[0].primary_position == "Centre-Forward"
