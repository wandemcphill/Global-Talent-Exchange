from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.canonical_countries import seed_canonical_countries
from app.ingestion.mapping_resolver import ClubResolutionContext, MappingResolver, normalize_string
from app.ingestion.models import Club, Competition, Country
from app.models.base import Base


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_normalize_string_strips_accents_punctuation_and_suffix_noise() -> None:
    assert normalize_string("Paris Saint-Germain FC") == "paris saint germain"
    assert normalize_string("Real Madrid CF") == "real madrid"
    assert normalize_string("Barcelona B") == "barcelona"
    assert normalize_string("Kayserispor Kulubu") == "kayserispor kulubu"


def test_resolve_club_uses_alias_registry_for_psg_and_man_utd() -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            france = Country(source_provider="seed", provider_external_id="FR", name="France", alpha2_code="FR")
            england = Country(source_provider="seed", provider_external_id="GB-ENG", name="England", alpha2_code="GB")
            ligue_1 = Competition(
                source_provider="seed",
                provider_external_id="fr1",
                country=france,
                name="Ligue 1",
                slug="ligue-1",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            premier_league = Competition(
                source_provider="seed",
                provider_external_id="eng1",
                country=england,
                name="Premier League",
                slug="premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            session.add_all(
                [
                    france,
                    england,
                    ligue_1,
                    premier_league,
                    Club(
                        source_provider="seed",
                        provider_external_id="psg",
                        country=france,
                        current_competition=ligue_1,
                        name="Paris Saint Germain",
                        slug="paris-saint-germain",
                        short_name="PSG",
                        is_tradable=True,
                    ),
                    Club(
                        source_provider="seed",
                        provider_external_id="manu",
                        country=england,
                        current_competition=premier_league,
                        name="Manchester United",
                        slug="manchester-united",
                        short_name="Man United",
                        is_tradable=True,
                    ),
                ]
            )
            session.commit()

        with session_factory() as session:
            psg = resolver.resolve_club(session, raw_name="PSG", context=ClubResolutionContext(competition_name="Ligue 1"))
            man_utd = resolver.resolve_club(
                session,
                raw_name="Man Utd",
                context=ClubResolutionContext(competition_name="Premier League"),
            )

            assert psg.status == "resolved"
            assert psg.canonical_name == "Paris Saint Germain"
            assert man_utd.status == "resolved"
            assert man_utd.canonical_name == "Manchester United"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("raw_name", "expected_canonical_name"),
    [
        ("Ivory Coast", "Côte d’Ivoire"),
        ("Cote d'Ivoire", "Côte d’Ivoire"),
        ("Cote dIvoire", "Côte d’Ivoire"),
        ("CÃ´te dâ€™Ivoire", "Côte d’Ivoire"),
        ("Curacao", "Curaçao"),
        ("Cape Verde", "Cabo Verde"),
        ("Congo", "Republic of the Congo"),
        ("DR Congo", "Democratic Republic of the Congo"),
        ("Congo DR", "Democratic Republic of the Congo"),
        ("Congo-Kinshasa", "Democratic Republic of the Congo"),
        ("The Gambia", "Gambia"),
    ],
)
def test_resolve_country_prefers_canonical_rows_for_aliases_and_variants(
    raw_name: str,
    expected_canonical_name: str,
) -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            session.add_all(
                [
                    Country(
                        source_provider="transfermarkt_2nd_zip",
                        provider_external_id="civ-raw",
                        name="Cote d'Ivoire",
                    ),
                    Country(
                        source_provider="transfermarkt_2nd_zip",
                        provider_external_id="cod-raw",
                        name="DR Congo",
                    ),
                    Country(
                        source_provider="transfermarkt_2nd_zip",
                        provider_external_id="cv-raw",
                        name="Cape Verde",
                    ),
                    Country(
                        source_provider="transfermarkt_2nd_zip",
                        provider_external_id="gm-raw",
                        name="The Gambia",
                    ),
                ]
            )
            seed_canonical_countries(session)
            session.commit()

        with session_factory() as session:
            resolution = resolver.resolve_country(session, raw_name=raw_name)
            assert resolution.status == "resolved"
            assert resolution.canonical_name == expected_canonical_name
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("raw_name", "expected_canonical_name"),
    [
        ("Antigua and Barbuda", "Antigua and Barbuda"),
        ("Benin", "Benin"),
        ("Burkina Faso", "Burkina Faso"),
        ("Central African Republic", "Central African Republic"),
        ("Equatorial Guinea", "Equatorial Guinea"),
        ("French Guiana", "French Guiana"),
        ("Gabon", "Gabon"),
        ("Guinea-Bissau", "Guinea-Bissau"),
        ("Haiti", "Haiti"),
        ("Madagascar", "Madagascar"),
        ("Martinique", "Martinique"),
        ("Mauritius", "Mauritius"),
        ("Bonaire", "Bonaire"),
        ("Sao Tome and Principe", "Sao Tome and Principe"),
        ("Saint-Martin", "Saint-Martin"),
        ("Sierra Leone", "Sierra Leone"),
        ("Palestine", "Palestine"),
        ("Syria", "Syria"),
        ("Tanzania", "Tanzania"),
        ("Togo", "Togo"),
        ("Turkmenistan", "Turkmenistan"),
        ("Zimbabwe", "Zimbabwe"),
    ],
)
def test_resolve_country_covers_additive_long_tail_seed_names(
    raw_name: str,
    expected_canonical_name: str,
) -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            seed_canonical_countries(session)
            session.commit()

        with session_factory() as session:
            resolution = resolver.resolve_country(session, raw_name=raw_name)
            assert resolution.status == "resolved"
            assert resolution.canonical_name == expected_canonical_name
    finally:
        engine.dispose()


def test_resolve_country_remains_unresolved_for_unknown_country() -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            seed_canonical_countries(session)
            session.commit()

        with session_factory() as session:
            resolution = resolver.resolve_country(session, raw_name="Atlantis Republic")
            assert resolution.status == "unresolved"
            assert resolution.reason_code == "country_not_found"
    finally:
        engine.dispose()


def test_resolve_club_returns_unresolved_for_unknown_names() -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            session.add(
                Club(
                    source_provider="seed",
                    provider_external_id="arsenal",
                    name="Arsenal",
                    slug="arsenal",
                    short_name="Arsenal",
                    is_tradable=True,
                )
            )
            session.commit()

        with session_factory() as session:
            resolution = resolver.resolve_club(session, raw_name="Completely Unknown Club")
            assert resolution.status == "unresolved"
            assert resolution.entity is None
    finally:
        engine.dispose()


def test_resolve_club_uses_context_to_break_exact_name_ties() -> None:
    engine, session_factory = _session_factory()
    try:
        resolver = MappingResolver()
        with session_factory() as session:
            portugal = Country(source_provider="seed", provider_external_id="PT", name="Portugal", alpha2_code="PT")
            spain = Country(source_provider="seed", provider_external_id="ES", name="Spain", alpha2_code="ES")
            liga_portugal = Competition(
                source_provider="seed",
                provider_external_id="pt1",
                country=portugal,
                name="Liga Portugal",
                slug="liga-portugal",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            la_liga = Competition(
                source_provider="seed",
                provider_external_id="es1",
                country=spain,
                name="La Liga",
                slug="la-liga",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            session.add_all(
                [
                    portugal,
                    spain,
                    liga_portugal,
                    la_liga,
                    Club(
                        source_provider="seed",
                        provider_external_id="avs-pt",
                        country=portugal,
                        current_competition=liga_portugal,
                        name="United",
                        slug="united-pt",
                        short_name="United",
                        is_tradable=True,
                    ),
                    Club(
                        source_provider="seed",
                        provider_external_id="united-es",
                        country=spain,
                        current_competition=la_liga,
                        name="United",
                        slug="united-es",
                        short_name="United",
                        is_tradable=True,
                    ),
                ]
            )
            session.commit()

        with session_factory() as session:
            no_context = resolver.resolve_club(session, raw_name="United")
            with_context = resolver.resolve_club(
                session,
                raw_name="United",
                context=ClubResolutionContext(competition_name="Liga Portugal"),
            )
            assert no_context.status == "unresolved"
            assert with_context.status == "resolved"
            assert with_context.canonical_id is not None
    finally:
        engine.dispose()
