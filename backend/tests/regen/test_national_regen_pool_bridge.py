from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import shutil

from alembic import command as alembic_command
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core import database as database_module
from app.ingestion.models import Country, Player
from app.models.national_team import NationalTeamCompetition
from app.models.regen_ecosystem import NationalRegenSeed
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.regen_universe.expansion_service import RegenUniverseExpansionService


POSITION_MINIMUMS = {
    "GK": 3,
    "CB": 5,
    "RB": 2,
    "LB": 2,
    "DM": 3,
    "CM": 5,
    "AM": 3,
    "RW": 2,
    "LW": 2,
    "ST": 3,
}


def _database_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


@pytest.fixture(scope="module")
def migrated_db_template(tmp_path_factory) -> Path:
    database_path = tmp_path_factory.mktemp("regen-phase-db") / "template.db"
    database_url = _database_url(database_path)
    config = database_module.build_alembic_config(database_url)
    alembic_command.upgrade(config, "head")
    return database_path


@pytest.fixture()
def migrated_session_factory(migrated_db_template: Path, tmp_path, request):
    database_path = tmp_path / f"{request.node.name}.db"
    shutil.copyfile(migrated_db_template, database_path)
    engine = create_engine(_database_url(database_path), connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


def _seed_country(
    session,
    *,
    provider_external_id: str,
    name: str,
    alpha2: str,
    alpha3: str,
    fifa: str,
    confederation: str,
) -> Country:
    country = Country(
        source_provider="test",
        provider_external_id=provider_external_id,
        name=name,
        alpha2_code=alpha2,
        alpha3_code=alpha3,
        fifa_code=fifa,
        confederation_code=confederation,
        is_enabled_for_universe=True,
    )
    session.add(country)
    session.flush()
    return country


def _create_competition(
    session,
    *,
    key: str,
    title: str,
    age_band: str,
    kickoff_at: datetime,
) -> NationalTeamCompetition:
    competition = NationalTeamCompetition(
        key=key,
        title=title,
        season_label="2030",
        region_type="global",
        age_band=age_band,
        format_type="cup",
        status="published",
        kickoff_at=kickoff_at,
        metadata_json={
            "entry_mode": "rental_only",
            "minimum_squad_size": 11,
            "maximum_squad_size": 23,
        },
    )
    session.add(competition)
    session.flush()
    return competition


def _create_player(
    session,
    *,
    provider_external_id: str,
    country_id: str,
    full_name: str,
    position: str,
    birth_date: date,
    gsi: int,
    market_value: int,
    is_real_player: bool,
) -> Player:
    player = Player(
        source_provider="test",
        provider_external_id=provider_external_id,
        country_id=country_id,
        full_name=full_name,
        canonical_display_name=full_name,
        position=position,
        normalized_position=position,
        date_of_birth=birth_date,
        current_market_reference_value=market_value,
        market_value_eur=market_value,
        is_tradable=True,
        is_real_player=is_real_player,
        dna_profile={"gsi": gsi, "regen_type": "real" if is_real_player else "club"},
    )
    session.add(player)
    session.flush()
    return player


def _seed_age_band(session, *, country_code: str, age_band: str) -> dict[str, object]:
    return RegenUniverseExpansionService(session).seed_preseeded_national_regens(
        country_codes=[country_code],
        age_band=age_band,
    )


def _position_counts(session, *, country_code: str, age_band: str) -> Counter[str]:
    rows = session.scalars(
        select(NationalRegenSeed.primary_position).where(
            NationalRegenSeed.country_code == country_code,
            NationalRegenSeed.age_band == age_band,
            NationalRegenSeed.status.in_(("active", "available")),
        )
    ).all()
    return Counter(rows)


def test_preseeded_national_regens_fill_u17_quota_gaps_and_remain_non_marketable(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        country = _seed_country(
            session,
            provider_external_id="country-ng",
            name="Nigeria",
            alpha2="NG",
            alpha3="NGA",
            fifa="NGA",
            confederation="CAF",
        )
        result = _seed_age_band(session, country_code="NG", age_band="u17")
        assert result["summary"]["created"] >= 30

        _create_player(
            session,
            provider_external_id="ng-u17-gk-real",
            country_id=country.id,
            full_name="Daniel Okoye",
            position="GK",
            birth_date=date(2014, 1, 5),
            gsi=79,
            market_value=14_000_000,
            is_real_player=True,
        )
        _create_player(
            session,
            provider_external_id="ng-u17-cb-real",
            country_id=country.id,
            full_name="Chisom Okafor",
            position="CB",
            birth_date=date(2013, 8, 12),
            gsi=81,
            market_value=16_000_000,
            is_real_player=True,
        )
        _create_player(
            session,
            provider_external_id="ng-u17-st-real",
            country_id=country.id,
            full_name="Tobi Adesina",
            position="ST",
            birth_date=date(2013, 11, 2),
            gsi=83,
            market_value=18_000_000,
            is_real_player=True,
        )
        competition = _create_competition(
            session,
            key="gtex-u17-world-cup-bridge",
            title="GTEX U17 World Cup Bridge",
            age_band="u17",
            kickoff_at=datetime(2030, 6, 1, tzinfo=timezone.utc),
        )

        service = NationalTeamTournamentService(session)
        squad = service.auto_build_squad(
            competition_id=competition.id,
            country_code="NG",
            budget_coin=Decimal("10000.0000"),
            tactic="balanced",
        )

        assert squad["complete"] is True
        assert squad["selected_count"] == 11
        assert squad["source_mix"]["real"] > 0
        assert squad["source_mix"]["preseeded"] > 0

        preseeded_players = [item for item in squad["players"] if item["source_bucket"] == "preseeded"]
        assert preseeded_players
        for item in preseeded_players:
            assert item["is_regen"] is True
            assert item["is_preseeded_national_regen"] is True
            assert item["market_eligible"] is False
            assert item["share_market_eligible"] is False
            assert item["tradable"] is False
            assert item["buyable"] is False
            assert item["transferable"] is False
            assert item["card_mint_eligible"] is False
            assert item["national_pool_only"] is True
            assert item["age"] <= 17


def test_real_players_are_ranked_ahead_of_preseeded_in_u20_pool(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        country = _seed_country(
            session,
            provider_external_id="country-gh",
            name="Ghana",
            alpha2="GH",
            alpha3="GHA",
            fifa="GHA",
            confederation="CAF",
        )
        _seed_age_band(session, country_code="GH", age_band="u20")
        for index, position in enumerate(("GK", "RB", "CB", "CB", "LB", "DM", "CM", "CM", "RW", "LW", "ST"), start=1):
            _create_player(
                session,
                provider_external_id=f"gh-u20-real-{index}",
                country_id=country.id,
                full_name=f"Ghana Real {index}",
                position=position,
                birth_date=date(2010, 1, min(index, 28)),
                gsi=78 + (index % 4),
                market_value=12_000_000 + (index * 500_000),
                is_real_player=True,
            )
        competition = _create_competition(
            session,
            key="gtex-u20-afcon-ordering",
            title="GTEX U20 AFCON Ordering",
            age_band="u20",
            kickoff_at=datetime(2030, 7, 1, tzinfo=timezone.utc),
        )

        payload = NationalTeamTournamentService(session).list_rental_players(
            competition_id=competition.id,
            country_code="GH",
            limit=15,
        )

        assert payload["total"] >= 11
        first_eleven = payload["items"][:11]
        assert len(first_eleven) == 11
        assert all(item["source_bucket"] == "real" for item in first_eleven)
        assert all(item["age"] is not None and item["age"] <= 20 for item in payload["items"])


def test_preseed_seeding_is_idempotent_and_u17_u20_position_filters_hold(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        _seed_country(
            session,
            provider_external_id="country-ci",
            name="Ivory Coast",
            alpha2="CI",
            alpha3="CIV",
            fifa="CIV",
            confederation="CAF",
        )
        service = RegenUniverseExpansionService(session)

        first_u17 = service.seed_preseeded_national_regens(country_codes=["CI"], age_band="u17")
        second_u17 = service.seed_preseeded_national_regens(country_codes=["CI"], age_band="u17")
        first_u20 = service.seed_preseeded_national_regens(country_codes=["CI"], age_band="u20")
        first_senior = service.seed_preseeded_national_regens(country_codes=["CI"], age_band="senior")

        assert first_u17["summary"]["created"] >= 30
        assert second_u17["summary"]["created"] == 0
        assert second_u17["summary"]["skipped_existing"] >= 30
        assert first_u20["summary"]["created"] >= 30
        assert first_senior["summary"]["created"] >= 30

        u17_counts = _position_counts(session, country_code="CI", age_band="u17")
        u20_counts = _position_counts(session, country_code="CI", age_band="u20")
        senior_counts = _position_counts(session, country_code="CI", age_band="senior")
        for position, minimum in POSITION_MINIMUMS.items():
            assert u17_counts[position] >= minimum
            assert u20_counts[position] >= minimum
            assert senior_counts[position] >= minimum

        u17_seed_keys = session.scalars(
            select(NationalRegenSeed.seed_key).where(
                NationalRegenSeed.country_code == "CI",
                NationalRegenSeed.age_band == "u17",
            )
        ).all()
        assert len(u17_seed_keys) == len(set(u17_seed_keys))

        u17_competition = _create_competition(
            session,
            key="gtex-u17-filter-ci",
            title="GTEX U17 Filter CI",
            age_band="u17",
            kickoff_at=datetime(2030, 6, 15, tzinfo=timezone.utc),
        )
        u20_competition = _create_competition(
            session,
            key="gtex-u20-filter-ci",
            title="GTEX U20 Filter CI",
            age_band="u20",
            kickoff_at=datetime(2030, 6, 15, tzinfo=timezone.utc),
        )

        tournament_service = NationalTeamTournamentService(session)
        u17_pool = tournament_service.list_rental_players(
            competition_id=u17_competition.id,
            country_code="CI",
            preseeded_only=True,
            limit=60,
        )
        u20_pool = tournament_service.list_rental_players(
            competition_id=u20_competition.id,
            country_code="CI",
            preseeded_only=True,
            limit=60,
        )

        assert u17_pool["items"]
        assert u20_pool["items"]
        assert all(item["source_bucket"] == "preseeded" for item in u17_pool["items"])
        assert all(item["source_bucket"] == "preseeded" for item in u20_pool["items"])
        assert all(item["age"] is not None and item["age"] <= 17 for item in u17_pool["items"])
        assert all(item["age"] is not None and 18 <= item["age"] <= 20 for item in u20_pool["items"])
        assert all(item["tradable"] is False and item["buyable"] is False for item in u17_pool["items"])
        assert all(item["tradable"] is False and item["buyable"] is False for item in u20_pool["items"])
