from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion.models import Country
from app.global_memory.models import NationalTeamCountryRanking
from app.models import Base
from app.models.competition import UserCompetition
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry
from app.models.user import User, UserRole
from app.national_team_engine.competition_lifecycle_service import (
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.schemas import NationalTeamCompetitionEntrySubmitRequest
from app.national_team_engine.tournament_service import NationalTeamTournamentService


def _build_session_factory(database_path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            UserCompetition.__table__,
            Country.__table__,
            NationalTeamCountryRanking.__table__,
            NationalTeamCompetition.__table__,
            NationalTeamCompetitionEntry.__table__,
        ],
    )
    return SessionLocal


def _create_user(session, *, suffix: int, role: UserRole = UserRole.USER) -> User:
    user = User(
        email=f"user{suffix}@example.com",
        username=f"user_{suffix}",
        display_name=f"User {suffix}",
        password_hash="not-used",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _seed_country(session, *, name: str, alpha2: str, fifa: str, confederation: str) -> None:
    session.add(
        Country(
            source_provider="test",
            provider_external_id=alpha2,
            name=name,
            alpha2_code=alpha2,
            fifa_code=fifa,
            confederation_code=confederation,
        )
    )


def _payload(
    country_code: str, country_name: str, ages: tuple[int, int], ratings: tuple[int, int]
) -> NationalTeamCompetitionEntrySubmitRequest:
    return NationalTeamCompetitionEntrySubmitRequest(
        country_code=country_code,
        country_name=country_name,
        squad=[
            {
                "player_name": f"{country_name} Player A",
                "age": ages[0],
                "overall_rating": ratings[0],
                "position": "fw",
            },
            {
                "player_name": f"{country_name} Player B",
                "age": ages[1],
                "overall_rating": ratings[1],
                "position": "cm",
            },
        ],
    )


def test_seed_default_competitions_expands_family_catalog(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "seed-defaults.db")
    with session_factory() as session:
        admin = _create_user(session, suffix=1, role=UserRole.ADMIN)
        service = NationalTeamTournamentService(session)

        payload = service.seed_default_competitions(actor=admin)

        keys = {item["key"] for item in payload}
        assert "gtex-world-cup" in keys
        assert "gtex-u17-afcon" in keys
        assert "gtex-u20-copa" in keys
        assert "gtex-euros" in keys
        afcon = next(item for item in payload if item["key"] == "gtex-u17-afcon")
        assert afcon["metadata_json"]["competition_family"] == "afcon"
        assert afcon["metadata_json"]["schedule_profile"]["preferred_cycle_week"] == 1


def test_lifecycle_engine_handles_age_locking_prequalifiers_qualifiers_and_tournament(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "lifecycle-engine.db")
    with session_factory() as session:
        users = [_create_user(session, suffix=index + 1) for index in range(6)]
        for name, alpha2, fifa in [
            ("Nigeria", "NG", "NGA"),
            ("Ghana", "GH", "GHA"),
            ("Ivory Coast", "CI", "CIV"),
            ("Egypt", "EG", "EGY"),
            ("Cameroon", "CM", "CMR"),
        ]:
            _seed_country(session, name=name, alpha2=alpha2, fifa=fifa, confederation="CAF")

        competition = NationalTeamCompetition(
            key="gtex-u17-afcon-test",
            title="GTEX U17 AFCON Test",
            season_label="2030",
            region_type="afcon",
            age_band="u17",
            format_type="cup",
            status="published",
            metadata_json={
                "competition_family": "afcon",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "competition_engine": {
                    "tournament_slots": 4,
                    "group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "qualifier_group_size": 3,
                    "preferred_cycle_week": 1,
                    "schedule_label": "Week 1 -> U17 AFCON",
                },
            },
            created_by_user_id=users[0].id,
        )
        session.add(competition)
        session.flush()

        service = NationalCompetitionLifecycleService(session)

        try:
            service.submit_entry(
                competition_id=competition.id,
                actor=users[0],
                payload=_payload("NG", "Nigeria", ages=(18, 16), ratings=(78, 74)),
            )
        except NationalCompetitionLifecycleError as exc:
            assert exc.reason == "invalid_squad_age"
        else:
            raise AssertionError("Expected invalid U17 squad submission to fail.")

        submissions = [
            (users[0], _payload("NG", "Nigeria", ages=(17, 16), ratings=(82, 80))),
            (users[1], _payload("NG", "Nigeria", ages=(17, 17), ratings=(79, 78))),
            (users[2], _payload("GH", "Ghana", ages=(16, 17), ratings=(76, 75))),
            (users[3], _payload("CI", "Ivory Coast", ages=(16, 16), ratings=(77, 74))),
            (users[4], _payload("EG", "Egypt", ages=(17, 16), ratings=(75, 75))),
            (users[5], _payload("CM", "Cameroon", ages=(17, 17), ratings=(74, 73))),
        ]
        for actor, payload in submissions:
            service.submit_entry(competition_id=competition.id, actor=actor, payload=payload)

        locked = service.lock_entries(competition_id=competition.id)
        assert locked["current_stage"] == "pre_qualifier"
        assert all(item["locked"] for item in locked["submitted_entries"])
        assert locked["schedule_plan"][0]["week"] == 1

        after_pre_qualifier = service.advance_lifecycle(competition_id=competition.id)
        assert after_pre_qualifier["current_stage"] == "qualifier"
        assert len(after_pre_qualifier["representative_entries"]) == 5
        assert "pre_qualifier" in after_pre_qualifier["stage_results"]

        after_qualifier = service.advance_lifecycle(competition_id=competition.id)
        assert after_qualifier["current_stage"] == "tournament"
        assert len(after_qualifier["qualified_entries"]) == 4
        assert "qualifier" in after_qualifier["stage_results"]

        completed = service.advance_lifecycle(competition_id=competition.id)
        assert completed["current_stage"] == "completed"
        assert completed["champion_entry_id"] is not None
        assert "tournament" in completed["stage_results"]
        assert [item["stage"] for item in completed["stage_history"]] == [
            "pre_qualifier",
            "qualifier",
            "tournament",
        ]
