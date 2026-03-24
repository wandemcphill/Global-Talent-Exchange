from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import app.models.real_player_import_batch  # noqa: F401
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country
from app.ingestion.second_zip_real_player_ops_service import (
    SecondZipEvaluationResult,
    SecondZipRealPlayerOpsService,
)
from app.ingestion.transfermarkt_second_zip import SECOND_ZIP_SOURCE_NAME
from app.models.base import Base
from app.models.real_player_import_batch import RealPlayerImportRow, RealPlayerImportRowStatus
from app.schemas.real_player_ingestion import RealPlayerIngestionItemResult


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
EXTRA_DATASET_HEADERS = {
    "national_teams.csv": ("id", "name"),
    "player_valuations.csv": ("id", "name"),
    "transfers.csv": ("id", "name"),
    "club_games.csv": ("id", "name"),
}


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _initialize_database(database_url: str):
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings(database_url: str):
    return load_settings(environ={"GTE_DATABASE_URL": database_url, "DATABASE_URL": database_url})


def _service(database_url: str, engine) -> SecondZipRealPlayerOpsService:
    return SecondZipRealPlayerOpsService(
        session_factory=_session_factory(engine),
        settings=_settings(database_url),
    )


def _player_row(
    player_id: int | str,
    *,
    club_id: str = "100",
    club_name: str = "Test FC",
    competition_id: str = "NG1",
    nationality: str = "Nigeria",
    last_season: str = "2024",
    date_of_birth: str = "2000-01-02 00:00:00",
    name: str | None = None,
) -> dict[str, str]:
    numeric_id = str(player_id)
    canonical_name = name or f"Player {numeric_id}"
    return {
        "player_id": numeric_id,
        "first_name": "Player",
        "last_name": numeric_id,
        "name": canonical_name,
        "last_season": last_season,
        "current_club_id": club_id,
        "player_code": f"player-{numeric_id}",
        "country_of_birth": nationality,
        "city_of_birth": "Lagos",
        "country_of_citizenship": nationality,
        "date_of_birth": date_of_birth,
        "sub_position": "Centre-Forward",
        "position": "Attack",
        "foot": "right",
        "height_in_cm": "180",
        "contract_expiration_date": "",
        "agent_name": "Agent",
        "image_url": f"https://img.example.test/{numeric_id}.jpg",
        "international_caps": "",
        "international_goals": "",
        "current_national_team_id": "",
        "url": f"https://example.test/player/{numeric_id}",
        "current_club_domestic_competition_id": competition_id,
        "current_club_name": club_name,
        "market_value_in_eur": "1000000",
        "highest_market_value_in_eur": "3000000",
    }


def _csv_text(headers: list[str] | tuple[str, ...], rows: list[dict[str, str]]) -> str:
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(header, "")) for header in headers))
    return "\n".join(lines) + "\n"


def _write_second_zip(
    archive_path: Path,
    *,
    players: list[dict[str, str]],
    clubs: list[dict[str, str]] | None = None,
    competitions: list[dict[str, str]] | None = None,
    countries: list[dict[str, str]] | None = None,
) -> Path:
    clubs = clubs or [
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
    competitions = competitions or [
        {
            "competition_id": "NG1",
            "competition_code": "nigeria-premier-league",
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
    countries = countries or [
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

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
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
        for dataset_name, headers in EXTRA_DATASET_HEADERS.items():
            archive.writestr(dataset_name, ",".join(headers) + "\n")
    return archive_path


def _stub_evaluator(states_by_key: dict[str, str]):
    def _evaluate(candidates):
        results = {}
        for candidate in candidates:
            source_key = candidate.seed_input.source_player_key
            state = states_by_key.get(source_key, "publish_ready")
            mapping_status = "ready"
            publish_ready = False
            row_status = RealPlayerImportRowStatus.MATCHED.value
            review_status = "resolved"
            review_reason = None
            errors: list[str] = []
            if state == "publish_ready":
                publish_ready = True
            elif state == "mapped_partial":
                mapping_status = "partial"
                row_status = RealPlayerImportRowStatus.SKIPPED.value
                review_status = "needs_review"
                review_reason = "mapped_partial"
            elif state == "unresolved":
                mapping_status = "unresolved"
                row_status = RealPlayerImportRowStatus.SKIPPED.value
                review_status = "needs_review"
                review_reason = "unresolved_mapping"
            else:
                row_status = RealPlayerImportRowStatus.FAILED.value
                review_status = "needs_review"
                review_reason = "failed"
                errors = ["simulated failure"]

            results[(candidate.seed_input.source_name, source_key)] = SecondZipEvaluationResult(
                source_player_key=source_key,
                canonical_name=candidate.seed_input.canonical_name,
                match_action="create_new",
                gtex_player_id=None,
                row_status=row_status,
                review_status=review_status,
                review_reason=review_reason,
                normalized_payload_json={"real_player_tier": "core"},
                validation_errors=errors,
                candidate_players=[],
                audit_findings=[],
                mapping_status=mapping_status,
                mapping_summary={
                    "country": {"status": "resolved"},
                    "competition": {"status": "resolved" if mapping_status == "ready" else mapping_status},
                    "club": {"status": "resolved" if mapping_status == "ready" else mapping_status},
                },
                publish_ready=publish_ready,
                free_agent_fallback=False,
                fallback_valued=False,
                pricing_preview_ready=publish_ready,
                state=state,
            )
        return results

    return _evaluate


def _stub_publisher(calls: list[str]):
    def _publish(*, batch_key: str, row: RealPlayerImportRow) -> RealPlayerIngestionItemResult:
        calls.append(row.source_player_key)
        sequence = len(calls)
        return RealPlayerIngestionItemResult(
            source_name=row.source_name,
            source_player_key=row.source_player_key,
            gtex_player_id=f"player-{sequence}",
            action="created",
            pricing_snapshot_id=f"snapshot-{sequence}",
            authoritative_price_credits=120.0,
            identity_confidence_score=0.94,
        )

    return _publish


def _seed_canonical_entities(engine) -> None:
    with _session_factory(engine)() as session:
        country = Country(
            source_provider=SECOND_ZIP_SOURCE_NAME,
            provider_external_id="NG",
            name="Nigeria",
            alpha2_code="NG",
        )
        competition = Competition(
            source_provider=SECOND_ZIP_SOURCE_NAME,
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
            source_provider=SECOND_ZIP_SOURCE_NAME,
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


def test_import_archive_supports_2000_row_dry_run(tmp_path: Path, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "2ndzip-2000.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: _stub_evaluator({})(candidates),
    )
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[_player_row(index) for index in range(1, 2506)],
    )

    report = service.import_archive(archive_path=archive_path, batch_size=1000, limit=2000)

    assert report.status == "completed"
    assert report.counts.total_rows_read == 2000
    assert report.counts.eligible_rows == 2000
    assert report.counts.mapped_ready == 2000
    assert report.counts.publish_ready == 2000
    assert report.counts.published == 0
    assert report.read_exhausted is False
    assert report.scope_complete is True
    with _session_factory(engine)() as session:
        assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 2000
    engine.dispose()


def test_import_archive_is_idempotent_for_second_run_same_scope(tmp_path: Path, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "2ndzip-idempotent.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: _stub_evaluator({})(candidates),
    )
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[_player_row(index) for index in range(1, 4)],
    )

    first = service.import_archive(archive_path=archive_path, batch_size=2, limit=3)
    second = service.import_archive(archive_path=archive_path, batch_size=2, limit=3)

    assert second.run_id == first.run_id
    assert second.counts.to_dict() == first.counts.to_dict()
    with _session_factory(engine)() as session:
        assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 3
    engine.dispose()


def test_resume_run_continues_after_interruption(tmp_path: Path, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "2ndzip-resume.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[_player_row(index) for index in range(1, 3)],
    )
    calls = {"count": 0}

    def flaky_evaluator(candidates):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("simulated interruption")
        return _stub_evaluator({})(candidates)

    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: flaky_evaluator(candidates),
    )
    interrupted = service.import_archive(archive_path=archive_path, batch_size=1, limit=2)

    assert interrupted.status == "failed"
    assert interrupted.counts.total_rows_read == 1
    assert interrupted.next_resume_row_number == 2

    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: _stub_evaluator({})(candidates),
    )
    resumed = service.resume_run(run_id=interrupted.run_id)

    assert resumed.status == "completed"
    assert resumed.counts.total_rows_read == 2
    assert resumed.counts.publish_ready == 2
    with _session_factory(engine)() as session:
        assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 2
    engine.dispose()


def test_publish_excludes_invalid_and_partial_rows(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "2ndzip-publish.db")
    engine = _initialize_database(database_url)
    _seed_canonical_entities(engine)
    service = _service(database_url, engine)
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[
            _player_row(1, name="Ready Player"),
            _player_row(2, name="Partial Player", club_id="", club_name="", competition_id=""),
        ],
    )

    imported = service.import_archive(archive_path=archive_path, batch_size=10, limit=2)
    assert imported.counts.publish_ready == 1
    assert imported.counts.mapped_partial == 1

    published = service.publish_run(run_id=imported.run_id, limit=10)

    assert published.selected_row_count == 1
    assert published.counts.published == 1
    assert published.counts.publish_ready == 0
    assert published.counts.mapped_partial == 1
    with _session_factory(engine)() as session:
        rows = list(
            session.scalars(
                select(RealPlayerImportRow)
                .where(RealPlayerImportRow.batch_id == imported.run_id)
                .order_by(RealPlayerImportRow.row_number.asc())
            )
        )
        assert rows[0].status == RealPlayerImportRowStatus.IMPORTED.value
        assert rows[1].status == RealPlayerImportRowStatus.SKIPPED.value
    engine.dispose()


def test_publish_tier_filter_uses_second_zip_publish_tiers(tmp_path: Path, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "2ndzip-publish-tier.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: _stub_evaluator({})(candidates),
    )
    publish_calls: list[str] = []
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_publish_candidate",
        lambda self, *, batch_key, row: _stub_publisher(publish_calls)(batch_key=batch_key, row=row),
    )
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[_player_row(1), _player_row(2)],
    )

    imported = service.import_archive(archive_path=archive_path, batch_size=10, limit=2)
    with _session_factory(engine)() as session:
        fallback_row = session.scalar(
            select(RealPlayerImportRow).where(
                RealPlayerImportRow.batch_id == imported.run_id,
                RealPlayerImportRow.source_player_key == "2",
            )
        )
        assert fallback_row is not None
        metadata = dict(fallback_row.import_metadata_json or {})
        metadata["second_zip"] = {
            **dict(metadata.get("second_zip") or {}),
            "free_agent_fallback": True,
            "publish_ready": True,
            "published": False,
            "state": "publish_ready",
        }
        fallback_row.import_metadata_json = metadata
        session.commit()

    published = service.publish_run(run_id=imported.run_id, limit=10, tier="tier_1")

    assert published.selected_row_count == 1
    assert publish_calls == ["1"]
    assert published.counts.published == 1
    assert published.counts.publish_ready == 1
    engine.dispose()


def test_reporting_counts_remain_coherent(tmp_path: Path, monkeypatch) -> None:
    database_url = _database_url(tmp_path / "2ndzip-report.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_evaluate_candidates",
        lambda self, candidates: _stub_evaluator(
            {
                "2": "mapped_partial",
                "3": "unresolved",
                "4": "failed",
            }
        )(candidates),
    )
    publish_calls: list[str] = []
    monkeypatch.setattr(
        SecondZipRealPlayerOpsService,
        "_publish_candidate",
        lambda self, *, batch_key, row: _stub_publisher(publish_calls)(batch_key=batch_key, row=row),
    )
    archive_path = _write_second_zip(
        tmp_path / "2nd.zip",
        players=[
            _player_row(1),
            _player_row(2, club_id="", club_name="", competition_id=""),
            _player_row(3),
            _player_row(4),
            _player_row(5, last_season="2023"),
        ],
    )

    imported = service.import_archive(archive_path=archive_path, batch_size=10, limit=5)
    assert imported.counts.total_rows_read == 5
    assert imported.counts.eligible_rows == 4
    assert imported.counts.publish_ready == 1
    assert imported.counts.mapped_partial == 1
    assert imported.counts.unresolved == 1
    assert imported.counts.failed == 1

    service.publish_run(run_id=imported.run_id, limit=5)
    reported = service.report_run(run_id=imported.run_id)

    assert publish_calls == ["1"]
    assert reported.counts.total_rows_read == 5
    assert reported.counts.eligible_rows == 4
    assert reported.counts.mapped_ready == 2
    assert reported.counts.mapped_partial == 1
    assert reported.counts.unresolved == 1
    assert reported.counts.failed == 1
    assert reported.counts.publish_ready == 0
    assert reported.counts.published == 1
    engine.dispose()
