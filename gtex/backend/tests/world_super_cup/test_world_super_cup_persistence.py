from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.base import Base
from app.models.world_super_cup_authority import (
    WorldSuperCupCoefficient,
    WorldSuperCupCountdown,
    WorldSuperCupFixture,
    WorldSuperCupGroup,
    WorldSuperCupQualifiedClub,
    WorldSuperCupSettlement,
    WorldSuperCupStanding,
    WorldSuperCupTournament,
)
from app.world_super_cup.api.router import router
from app.world_super_cup.services.persistence import WorldSuperCupPersistenceService
from app.world_super_cup.services.tournament import WorldSuperCupService

_AUTHORITY_TABLES = (
    UserCompetition.__table__,
    CompetitionRound.__table__,
    CompetitionMatch.__table__,
    WorldSuperCupTournament.__table__,
    WorldSuperCupCountdown.__table__,
    WorldSuperCupCoefficient.__table__,
    WorldSuperCupQualifiedClub.__table__,
    WorldSuperCupGroup.__table__,
    WorldSuperCupFixture.__table__,
    WorldSuperCupStanding.__table__,
    WorldSuperCupSettlement.__table__,
)


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=_AUTHORITY_TABLES)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _demo_plan():
    return WorldSuperCupService().build_demo_tournament(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))


def test_world_super_cup_plan_persists_authoritative_snapshot_idempotently() -> None:
    SessionLocal = _session_factory()
    plan = _demo_plan()

    with SessionLocal() as session:
        service = WorldSuperCupPersistenceService(session)
        tournament = service.persist_plan(plan, tournament_id="wsc-2026")
        duplicate = service.persist_plan(plan, tournament_id="wsc-2026")
        session.commit()

        assert duplicate.id == tournament.id
        assert session.scalar(select(func.count(WorldSuperCupTournament.id))) == 1
        assert session.scalar(select(func.count(WorldSuperCupCoefficient.id))) == 48
        assert session.scalar(select(func.count(WorldSuperCupGroup.id))) == 8
        assert session.scalar(select(func.count(WorldSuperCupFixture.id))) == 71
        assert session.scalar(select(func.count(WorldSuperCupStanding.id))) == 32

        persisted = service.read_plan("wsc-2026")

    assert persisted is not None
    assert len(persisted.qualification.direct_qualifiers) == 24
    assert len(persisted.group_stage.groups) == 8
    assert [round_view.round_name for round_view in persisted.knockout.rounds] == [
        "round_of_16",
        "quarterfinal",
        "semifinal",
        "final",
    ]


def test_world_super_cup_settlement_hook_is_idempotent_and_rebuilds_group_table() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        service = WorldSuperCupPersistenceService(session)
        service.persist_plan(_demo_plan(), tournament_id="wsc-2026")
        fixture = next(item for item in service.fixtures("wsc-2026") if item.stage == "group")

        first = service.settle_fixture(
            tournament_id="wsc-2026",
            fixture_id=fixture.fixture_id,
            home_score=9,
            away_score=0,
            idempotency_key="settlement:wsc-2026:group-one",
        )
        replay = service.settle_fixture(
            tournament_id="wsc-2026",
            fixture_id=fixture.fixture_id,
            home_score=0,
            away_score=9,
            idempotency_key="settlement:wsc-2026:group-one",
        )
        session.commit()

        fixture_row = session.scalar(
            select(WorldSuperCupFixture).where(
                WorldSuperCupFixture.tournament_id == "wsc-2026",
                WorldSuperCupFixture.fixture_id == fixture.fixture_id,
            )
        )
        home_standing = session.scalar(
            select(WorldSuperCupStanding).where(
                WorldSuperCupStanding.tournament_id == "wsc-2026",
                WorldSuperCupStanding.group_name == fixture.group_name,
                WorldSuperCupStanding.club_id == fixture.home_club.club_id,
            )
        )

        assert replay.idempotency_key == first.idempotency_key
        assert replay.home_score == 9
        assert replay.away_score == 0
        assert session.scalar(select(func.count(WorldSuperCupSettlement.id))) == 1
        assert fixture_row is not None
        assert fixture_row.home_score == 9
        assert fixture_row.away_score == 0
        assert home_standing is not None
        assert home_standing.goals_for >= 9


def test_world_super_cup_settlement_can_derive_idempotency_from_match_lifecycle() -> None:
    SessionLocal = _session_factory()
    completed_at = datetime(2026, 3, 12, 18, 45, tzinfo=timezone.utc)

    with SessionLocal() as session:
        service = WorldSuperCupPersistenceService(session)
        service.persist_plan(
            _demo_plan(),
            tournament_id="wsc-2026",
            competition_id="competition-os-wsc",
        )
        fixture = next(item for item in service.fixtures("wsc-2026") if item.stage == "group")
        session.add(
            CompetitionMatch(
                id=fixture.fixture_id,
                competition_id="competition-os-wsc",
                round_id="wsc-round-1",
                round_number=1,
                stage=fixture.group_name or fixture.stage,
                home_club_id=fixture.home_club.club_id,
                away_club_id=fixture.away_club.club_id,
                status="completed",
                home_score=2,
                away_score=1,
                winner_club_id=fixture.home_club.club_id,
                completed_at=completed_at,
            )
        )
        session.flush()

        first = service.settle_fixture(
            tournament_id="wsc-2026",
            competition_id="competition-os-wsc",
            match_id=fixture.fixture_id,
            fixture_id=fixture.fixture_id,
            home_score=2,
            away_score=1,
        )
        replay = service.settle_fixture(
            tournament_id="wsc-2026",
            competition_id="competition-os-wsc",
            match_id=fixture.fixture_id,
            fixture_id=fixture.fixture_id,
            home_score=5,
            away_score=0,
        )
        session.commit()

        assert first.idempotency_key.startswith("competition-os:match-completed:competition-os-wsc:")
        assert replay.idempotency_key == first.idempotency_key
        assert replay.home_score == 2
        assert first.lifecycle_match_id == fixture.fixture_id
        assert first.lifecycle_competition_id == "competition-os-wsc"
        assert first.idempotency_source == "competition_match_lifecycle"
        assert session.scalar(select(func.count(WorldSuperCupSettlement.id))) == 1


def test_world_super_cup_routes_read_from_persisted_authority_without_demo_flag(monkeypatch) -> None:
    monkeypatch.delenv("GTE_ENABLE_WORLD_SUPER_CUP_DEMO", raising=False)
    SessionLocal = _session_factory()
    with SessionLocal() as session:
        WorldSuperCupPersistenceService(session).persist_plan(
            _demo_plan(),
            tournament_id="wsc-2026",
            competition_id="competition-os-wsc",
        )
        session.commit()

    app = FastAPI()
    app.state.settings = SimpleNamespace(app_env="test")
    app.state.session_factory = SessionLocal
    app.include_router(router)
    client = TestClient(app)

    countdown = client.get("/world-super-cup/countdown", params={"tournament_id": "wsc-2026"})
    fixtures = client.get("/world-super-cup/fixtures", params={"tournament_id": "wsc-2026"})

    assert countdown.status_code == 200, countdown.text
    countdown_payload = countdown.json()
    assert countdown_payload["tournament_name"] == "GTEX World Super Cup"
    assert countdown_payload["source_of_truth"] == "persisted_backend_authority"
    assert countdown_payload["authority"] == "competition_os"
    assert countdown_payload["no_demo_data"] is True
    assert countdown_payload["competition_id"] == "competition-os-wsc"
    assert fixtures.status_code == 200, fixtures.text
    fixtures_payload = fixtures.json()
    assert fixtures_payload["source_of_truth"] == "persisted_backend_authority"
    assert fixtures_payload["authority"] == "competition_os"
    assert fixtures_payload["no_demo_data"] is True
    assert fixtures_payload["competition_id"] == "competition-os-wsc"
    assert "demo" not in fixtures_payload
    assert len(fixtures_payload["fixtures"]) == 71

    with SessionLocal() as session:
        assert session.scalar(select(func.count(WorldSuperCupTournament.id))) == 1
        assert session.scalar(select(func.count(WorldSuperCupFixture.id))) == 71
