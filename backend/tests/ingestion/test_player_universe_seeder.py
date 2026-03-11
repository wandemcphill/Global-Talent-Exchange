from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from backend.app.ingestion.models import Competition, Country, Player, PlayerClubTenure, PlayerVerification
from backend.app.ingestion.player_universe_seeder import (
    COUNTRY_SPECS,
    PHASE_THREE_PROVIDER_NAME,
    PHASE_THREE_REFERENCE_DATE,
    VerifiedPlayerUniverseSeeder,
)


def _age_on(reference_date: date, birth_date: date) -> int:
    years = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def test_phase_three_universe_seeder_hits_100k_distribution_requirements(session) -> None:
    seeder = VerifiedPlayerUniverseSeeder(session)

    summary = seeder.seed(
        target_player_count=100_000,
        provider_name=PHASE_THREE_PROVIDER_NAME,
        random_seed=20260311,
        batch_size=5_000,
    )
    session.commit()

    assert summary.players_created == 100_000
    assert summary.verifications_created == 100_000
    assert summary.tenures_created == 100_000
    assert summary.all_players_tradable is True
    assert summary.all_players_verified is True
    assert summary.duplicate_identity_count == 0
    assert summary.youth_players_under_24 >= 65_000
    assert summary.academy_reserve_pathway_players >= 20_000
    assert summary.priority_country_players >= 77_000

    total_players = session.scalar(select(func.count()).select_from(Player))
    tradable_players = session.scalar(select(func.count()).select_from(Player).where(Player.is_tradable.is_(True)))
    total_verifications = session.scalar(select(func.count()).select_from(PlayerVerification))
    total_verified = session.scalar(
        select(func.count()).select_from(PlayerVerification).where(PlayerVerification.status == "verified")
    )
    total_tenures = session.scalar(select(func.count()).select_from(PlayerClubTenure))
    distinct_names = session.scalar(select(func.count(func.distinct(Player.full_name))).select_from(Player))

    assert total_players == 100_000
    assert tradable_players == 100_000
    assert total_verifications == 100_000
    assert total_verified == 100_000
    assert total_tenures == 100_000
    assert distinct_names == 100_000

    birth_dates = list(session.scalars(select(Player.date_of_birth)))
    youth_count = sum(1 for birth_date in birth_dates if birth_date is not None and _age_on(PHASE_THREE_REFERENCE_DATE, birth_date) < 24)
    assert youth_count == summary.youth_players_under_24

    coverage_rows = session.execute(
        select(Country.name, Competition.domestic_level, func.count(Player.id))
        .join(Competition, Competition.country_id == Country.id)
        .join(Player, Player.current_competition_id == Competition.id)
        .where(Country.name.in_(("France", "Spain", "Belgium", "England", "Germany", "Italy")))
        .where(Competition.domestic_level.is_not(None))
        .group_by(Country.name, Competition.domestic_level)
    ).all()
    coverage = {(country, level): count for country, level, count in coverage_rows}
    required_pairs = {
        ("France", 1), ("France", 2), ("France", 3), ("France", 4),
        ("Spain", 1), ("Spain", 2), ("Spain", 3), ("Spain", 4),
        ("Belgium", 1), ("Belgium", 2), ("Belgium", 3),
        ("England", 1), ("England", 2), ("England", 3),
        ("Germany", 1), ("Germany", 2), ("Germany", 3),
        ("Italy", 1), ("Italy", 2), ("Italy", 3),
    }
    assert required_pairs.issubset(coverage.keys())
    assert all(coverage[pair] > 0 for pair in required_pairs)


def test_phase_three_universe_seeder_replaces_provider_slice_without_duplicates(session) -> None:
    seeder = VerifiedPlayerUniverseSeeder(session)

    seeder.seed(target_player_count=1_200, provider_name="phase3-test-provider", random_seed=11, batch_size=400)
    session.commit()
    first_count = session.scalar(select(func.count()).select_from(Player).where(Player.source_provider == "phase3-test-provider"))
    assert first_count == 1_200

    seeder.seed(target_player_count=2_000, provider_name="phase3-test-provider", random_seed=22, batch_size=400)
    session.commit()
    second_count = session.scalar(select(func.count()).select_from(Player).where(Player.source_provider == "phase3-test-provider"))
    second_verifications = session.scalar(
        select(func.count()).select_from(PlayerVerification).join(Player, Player.id == PlayerVerification.player_id).where(Player.source_provider == "phase3-test-provider")
    )
    distinct_names = session.scalar(
        select(func.count(func.distinct(Player.full_name))).select_from(Player).where(Player.source_provider == "phase3-test-provider")
    )

    assert second_count == 2_000
    assert second_verifications == 2_000
    assert distinct_names == 2_000


def test_phase_three_country_specs_flag_priority_export_markets() -> None:
    priority_countries = {spec.name for spec in COUNTRY_SPECS if spec.priority_youth_export}

    assert {"France", "Spain", "Belgium", "Brazil", "Argentina", "Nigeria", "Senegal"}.issubset(priority_countries)
