from __future__ import annotations

import os

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Player, PlayerImageMetadata
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.ingestion.transfermarkt_second_zip import SECOND_ZIP_SOURCE_NAME
from app.models.base import Base
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.models.real_player_import_batch import RealPlayerImportRow
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_reference_mapping import RealPlayerReferenceMapping, RealPlayerUnresolvedReference
from app.models.real_player_source_link import RealPlayerSourceLink
from app.player_cards.service import PlayerCardMarketService
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings(*, auto_create_mappings: bool = False):
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "1" if auto_create_mappings else "0",
        }
    )


def _curated_request(*, mode: str, as_of: str, osimhen_club: str = "Launch Club A") -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": mode,
            "as_of": as_of,
            "ingestion_source_version": "launch-pack-v1",
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
                    "current_real_world_club": osimhen_club,
                    "current_real_world_league": "Launch League Elite",
                    "competition_level": "elite",
                    "appearances": 31,
                    "minutes_played": 2410,
                    "goals": 19,
                    "assists": 4,
                    "current_market_reference_value": 60000000,
                    "market_reference_currency": "EUR",
                },
                {
                    "source_name": "curated-feed",
                    "source_player_key": "iwobi-001",
                    "canonical_name": "Alex Iwobi",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1996-05-03",
                    "dominant_foot": "right",
                    "primary_position": "Winger",
                    "secondary_positions": ["Attacking Midfielder"],
                    "current_real_world_club": "Launch Club B",
                    "current_real_world_league": "Launch League Premier",
                    "competition_level": "top_flight",
                    "appearances": 29,
                    "minutes_played": 2280,
                    "goals": 6,
                    "assists": 7,
                    "current_market_reference_value": 18000000,
                    "market_reference_currency": "EUR",
                },
                {
                    "source_name": "curated-feed",
                    "source_player_key": "bassey-001",
                    "canonical_name": "Calvin Bassey",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "birth_year": 1999,
                    "dominant_foot": "left",
                    "primary_position": "Centre-Back",
                    "secondary_positions": ["Full-Back"],
                    "current_real_world_club": "Launch Club C",
                    "current_real_world_league": "Launch League Premier",
                    "competition_level": "top_flight",
                    "appearances": 30,
                    "minutes_played": 2550,
                    "goals": 1,
                    "assists": 2,
                    "clean_sheets": 11,
                    "current_market_reference_value": 22000000,
                    "market_reference_currency": "EUR",
                },
            ],
        }
    )


def _seed_curated_canonical_entities(session) -> None:
    nigeria = Country(
        source_provider="football_data",
        provider_external_id="NG",
        name="Nigeria",
        alpha2_code="NG",
    )
    league_elite = Competition(
        source_provider="football_data",
        provider_external_id="launch-elite",
        country=nigeria,
        name="Launch League Elite",
        slug="launch-league-elite",
        competition_type="league",
        format_type="real_world",
        is_major=True,
        is_tradable=True,
    )
    league_premier = Competition(
        source_provider="football_data",
        provider_external_id="launch-premier",
        country=nigeria,
        name="Launch League Premier",
        slug="launch-league-premier",
        competition_type="league",
        format_type="real_world",
        is_major=True,
        is_tradable=True,
    )
    session.add_all(
        [
            nigeria,
            league_elite,
            league_premier,
            Club(
                source_provider="football_data",
                provider_external_id="launch-club-a",
                country=nigeria,
                current_competition=league_elite,
                name="Launch Club A",
                slug="launch-club-a",
                short_name="Launch Club A",
                is_tradable=True,
            ),
            Club(
                source_provider="football_data",
                provider_external_id="launch-club-b",
                country=nigeria,
                current_competition=league_premier,
                name="Launch Club B",
                slug="launch-club-b",
                short_name="Launch Club B",
                is_tradable=True,
            ),
            Club(
                source_provider="football_data",
                provider_external_id="launch-club-c",
                country=nigeria,
                current_competition=league_premier,
                name="Launch Club C",
                slug="launch-club-c",
                short_name="Launch Club C",
                is_tradable=True,
            ),
            Club(
                source_provider="football_data",
                provider_external_id="launch-club-z",
                country=nigeria,
                current_competition=league_elite,
                name="Launch Club Z",
                slug="launch-club-z",
                short_name="Launch Club Z",
                is_tradable=True,
            ),
        ]
    )
    session.commit()


def test_real_player_ingestion_seeds_curated_batch_without_duplicate_identities() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_curated_canonical_entities(session)
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        result = service.ingest(_curated_request(mode="curated_seed", as_of="2026-03-22T12:00:00+00:00"))

        assert result.players_processed == 3
        assert result.players_created == 3
        assert result.players_updated == 0
        assert result.authoritative_snapshots_seeded == 3

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerSummaryReadModel)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerMarketValueSnapshot)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerStatsSnapshot)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerImageMetadata)) == 0

            summary = session.scalar(
                select(PlayerSummaryReadModel)
                .join(Player, Player.id == PlayerSummaryReadModel.player_id)
                .where(Player.full_name == "Victor Osimhen")
            )
            assert summary is not None
            assert summary.summary_json["formation_ready"] is True
            assert summary.summary_json["real_player_profile"]["is_real_player"] is True
            assert summary.summary_json["real_player_profile"]["pricing_snapshot_id"]
            assert summary.summary_json["market_visibility"]["eligible"] is True

            listed = PlayerCardMarketService(session).list_players(search="Osimhen", limit=5)
            assert listed
            assert listed[0]["latest_value_credits"] is not None
            assert listed[0]["avatar"]["seed_token"]
    finally:
        engine.dispose()


def test_real_player_ingestion_refresh_updates_existing_players_without_creating_duplicates() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_curated_canonical_entities(session)
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        first = service.ingest(_curated_request(mode="curated_seed", as_of="2026-03-22T12:00:00+00:00"))
        second = service.ingest(
            _curated_request(
                mode="refresh_existing",
                as_of="2026-03-23T12:00:00+00:00",
                osimhen_club="Launch Club Z",
            )
        )

        assert set(first.player_ids) == set(second.player_ids)
        assert second.players_created == 0
        assert second.players_updated == 3

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 3

            refreshed_player = session.scalar(select(Player).where(Player.full_name == "Victor Osimhen"))
            assert refreshed_player is not None
            assert refreshed_player.real_world_club_name == "Launch Club Z"

            refreshed_profile = session.scalar(
                select(RealPlayerProfile).where(RealPlayerProfile.canonical_name == "Victor Osimhen")
            )
            assert refreshed_profile is not None
            assert refreshed_profile.current_club_name == "Launch Club Z"
            assert refreshed_profile.pricing_snapshot_id is not None
    finally:
        engine.dispose()


def test_real_player_ingestion_attaches_to_existing_canonical_entities() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            nigeria = Country(
                source_provider="football_data",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            england = Country(
                source_provider="football_data",
                provider_external_id="ENG",
                name="England",
                alpha3_code="ENG",
                fifa_code="ENG",
            )
            premier_league = Competition(
                source_provider="football_data",
                provider_external_id="pl",
                country=england,
                name="Premier League",
                slug="premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            fulham = Club(
                source_provider="football_data",
                provider_external_id="fulham",
                country=england,
                current_competition=premier_league,
                name="Fulham",
                slug="fulham",
                short_name="Fulham",
                is_tradable=True,
            )
            session.add_all([nigeria, england, premier_league, fulham])
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "iwobi-fulham-001",
                        "canonical_name": "Alex Iwobi",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "date_of_birth": "1996-05-03",
                        "primary_position": "Winger",
                        "current_real_world_club": "Fulham",
                        "current_real_world_league": "Premier League",
                        "competition_level": "elite",
                        "appearances": 29,
                        "minutes_played": 2280,
                        "goals": 6,
                        "assists": 7,
                        "current_market_reference_value": 18000000,
                        "market_reference_currency": "EUR",
                    }
                ],
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        report = service.write_batch(request)
        assert report.players_processed == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.full_name == "Alex Iwobi"))
            assert player is not None
            assert player.country_id == nigeria.id
            assert player.current_competition_id == premier_league.id
            assert player.current_club_id == fulham.id

            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player.id))
            assert profile is not None
            assert profile.metadata_json["canonical_mapping"]["country"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["competition"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["club"]["status"] == "resolved"

            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference)) == 0
    finally:
        engine.dispose()


def test_real_player_ingestion_resolves_seeded_country_alias_when_club_exists() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            england = Country(
                source_provider="football_data",
                provider_external_id="ENG",
                name="England",
                alpha3_code="ENG",
                fifa_code="ENG",
            )
            premier_league = Competition(
                source_provider="football_data",
                provider_external_id="pl",
                country=england,
                name="Premier League",
                slug="premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            fulham = Club(
                source_provider="football_data",
                provider_external_id="fulham",
                country=england,
                current_competition=premier_league,
                name="Fulham",
                slug="fulham",
                short_name="Fulham",
                is_tradable=True,
            )
            session.add_all([england, premier_league, fulham])
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "gambia-001",
                        "canonical_name": "Gambia Example",
                        "nationality": "The Gambia",
                        "date_of_birth": "1999-01-01",
                        "primary_position": "Winger",
                        "current_real_world_club": "Fulham",
                        "current_real_world_league": "Premier League",
                        "competition_level": "elite",
                        "appearances": 20,
                        "minutes_played": 1800,
                        "goals": 8,
                        "assists": 4,
                        "current_market_reference_value": 20000000,
                        "market_reference_currency": "EUR",
                    }
                ],
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        report = service.write_batch(request)
        assert report.players_processed == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.full_name == "Gambia Example"))
            assert player is not None
            assert player.country is not None
            assert player.country.name == "Gambia"
            assert player.current_club_id == fulham.id

            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player.id))
            assert profile is not None
            assert profile.metadata_json["canonical_mapping"]["country"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["country"]["canonical_name"] == "Gambia"

            assert session.scalar(select(func.count()).select_from(RealPlayerUnresolvedReference)) == 0
    finally:
        engine.dispose()


def test_real_player_ingestion_surfaces_and_persists_unresolved_mappings_without_auto_create() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            session.add(
                Country(
                    source_provider="football_data",
                    provider_external_id="NG",
                    name="Nigeria",
                    alpha2_code="NG",
                )
            )
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "osimhen-unresolved-001",
                        "canonical_name": "Victor Osimhen",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "date_of_birth": "1998-12-29",
                        "primary_position": "Striker",
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
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        dry_run = service.validate(request)
        assert {issue.issue_type for issue in dry_run.issues} >= {
            "unresolved_competition_mapping",
            "unresolved_club_mapping",
        }

        report = service.write_batch(request)
        assert report.players_processed == 0

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 0

            import_row = session.scalar(select(RealPlayerImportRow))
            assert import_row is not None
            assert import_row.status == "skipped"
            assert import_row.review_reason == "unresolved_mapping"
            assert import_row.import_metadata_json["mapping_summary"]["country"]["status"] == "resolved"
            assert import_row.import_metadata_json["mapping_summary"]["competition"]["status"] == "unresolved"
            assert import_row.import_metadata_json["mapping_summary"]["club"]["status"] == "unresolved"

            unresolved_rows = list(session.scalars(select(RealPlayerUnresolvedReference)))
            assert len(unresolved_rows) == 2
            assert {row.entity_type for row in unresolved_rows} == {"competition", "club"}
            assert session.scalar(select(func.count()).select_from(Competition)) == 0
            assert session.scalar(select(func.count()).select_from(Club)) == 0
    finally:
        engine.dispose()


def test_real_player_ingestion_resolves_aliases_without_breaking_idempotency() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            france = Country(
                source_provider="football_data",
                provider_external_id="FR",
                name="France",
                alpha2_code="FR",
            )
            premier_league = Competition(
                source_provider="football_data",
                provider_external_id="eng1",
                name="Premier League",
                slug="premier-league",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            psg = Club(
                source_provider="football_data",
                provider_external_id="psg",
                country=france,
                name="Paris Saint Germain",
                slug="paris-saint-germain",
                short_name="PSG",
                is_tradable=True,
            )
            session.add_all([france, premier_league, psg])
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "psg-alias-001",
                        "canonical_name": "Alias Player",
                        "nationality": "France",
                        "nationality_code": "FR",
                        "date_of_birth": "1999-01-01",
                        "primary_position": "Winger",
                        "current_real_world_club": "PSG",
                        "current_real_world_league": "Premier League",
                        "competition_level": "elite",
                        "appearances": 20,
                        "minutes_played": 1800,
                        "goals": 8,
                        "assists": 4,
                        "current_market_reference_value": 20000000,
                        "market_reference_currency": "EUR",
                    }
                ],
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        first = service.ingest(request)
        second = service.ingest(request)

        assert first.players_processed == 1
        assert second.players_processed == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.full_name == "Alias Player"))
            assert player is not None
            assert player.current_club_id == psg.id
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 1
    finally:
        engine.dispose()


def test_real_player_ingestion_resolves_cyrillic_club_names_via_provider_id_fallback() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            russia = Country(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="141",
                name="Russia",
                alpha3_code="RUS",
            )
            premier_liga = Competition(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="RU1",
                country=russia,
                name="premier-liga",
                slug="premier-liga",
                competition_type="league",
                format_type="real_world",
                is_major=True,
                is_tradable=True,
            )
            lokomotiv = Club(
                source_provider=SECOND_ZIP_SOURCE_NAME,
                provider_external_id="932",
                country=russia,
                current_competition=premier_liga,
                name='Футбольный клуб "Локомотив" Москва',
                slug="lokomotiv-moskau",
                short_name="Lokomotiv Moskva",
                is_tradable=True,
            )
            session.add_all([russia, premier_liga, lokomotiv])
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-23T12:00:00+00:00",
                "ingestion_source_version": "2ndzip-cyrillic-provider-fallback",
                "players": [
                    {
                        "source_name": SECOND_ZIP_SOURCE_NAME,
                        "source_player_key": "932-player",
                        "canonical_name": "Dmitriy Vorobyov",
                        "nationality": "Russia",
                        "nationality_code": "141",
                        "date_of_birth": "1997-10-10",
                        "dominant_foot": "right",
                        "primary_position": "Centre-Forward",
                        "current_real_world_club": 'Футбольный клуб "Локомотив" Москва',
                        "current_real_world_club_key": "932",
                        "current_real_world_league": "premier-liga",
                        "current_real_world_league_key": "RU1",
                        "competition_level": "top_flight",
                        "appearances": 25,
                        "minutes_played": 1800,
                        "goals": 8,
                        "assists": 3,
                        "height_cm": 187,
                        "current_market_reference_value": 4000000,
                        "market_reference_currency": "EUR",
                    }
                ],
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        result = service.ingest(request)

        assert result.players_processed == 1
        assert result.players_created == 1

        with session_factory() as session:
            player = session.scalar(select(Player).where(Player.source_provider == SECOND_ZIP_SOURCE_NAME))
            profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_name == SECOND_ZIP_SOURCE_NAME))
            unresolved_clubs = list(
                session.scalars(
                    select(RealPlayerUnresolvedReference).where(
                        RealPlayerUnresolvedReference.entity_type == "club"
                    )
                )
            )

            assert player is not None
            assert profile is not None
            assert player.current_club_id == lokomotiv.id
            assert profile.metadata_json["canonical_mapping"]["club"]["status"] == "resolved"
            assert profile.metadata_json["canonical_mapping"]["club"]["resolution_method"] == "provider_exact_fallback"
            assert unresolved_clubs == []
    finally:
        engine.dispose()


def test_real_player_ingestion_re_raises_fatal_match_database_errors_without_reusing_session(monkeypatch) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_curated_canonical_entities(session)
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        upsert_calls: list[str] = []
        original_upsert_import_row = RealPlayerIngestionService._upsert_import_row

        def tracked_upsert_import_row(self, *args, **kwargs):
            payload = kwargs["payload"]
            upsert_calls.append(payload.source_player_key)
            return original_upsert_import_row(self, *args, **kwargs)

        def fatal_match_error(session, payload, normalized_identity=None):
            session.connection().invalidate()
            raise SQLAlchemyError("simulated primary db failure")

        monkeypatch.setattr(RealPlayerIngestionService, "_upsert_import_row", tracked_upsert_import_row)
        monkeypatch.setattr(service.identity_matcher, "match", fatal_match_error)

        with pytest.raises(SQLAlchemyError, match="simulated primary db failure"):
            service.validate(_curated_request(mode="curated_seed", as_of="2026-03-22T12:00:00+00:00"))

        assert upsert_calls == []
    finally:
        engine.dispose()
