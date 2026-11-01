from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user, get_session
from app.common.enums.match_status import MatchStatus
from app.models import Base
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.owner_competition_lifecycle_mapping import (
    OwnerCompetitionLifecycleMapping,
    OwnerMatchLifecycleMapping,
)
from app.models.user import User, UserRole
from app.owner_console.models import (
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerMatch,
)
from app.owner_console.router import router as owner_router


def test_dashboard_surfaces_canonical_match_and_standings_projection(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'dashboard_test.db'}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    app = FastAPI()
    app.include_router(owner_router)

    now = datetime.now(UTC)
    with SessionLocal() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="owner@gtex.test",
            username="clubowner1",
            display_name="Club Owner 1",
            role=UserRole.USER,
            is_active=True,
            password_hash="pw_mock",
        )
        session.add(user)
        session.flush()

        home_club = ClubProfile(
            id=str(uuid.uuid4()),
            owner_user_id=user.id,
            club_name="Apex Stars FC",
            short_name="APX",
            slug=f"apex-{uuid.uuid4().hex[:6]}",
            country_code="NGA",
            city_name="Lagos",
            primary_color="#10B981",
            secondary_color="#047857",
            accent_color="#F59E0B",
        )
        away_club = ClubProfile(
            id=str(uuid.uuid4()),
            owner_user_id=str(uuid.uuid4()),
            club_name="Dynamo Delta FC",
            short_name="DYN",
            slug=f"dynamo-{uuid.uuid4().hex[:6]}",
            country_code="NGA",
            city_name="Warri",
            primary_color="#3B82F6",
            secondary_color="#1D4ED8",
            accent_color="#F59E0B",
        )
        session.add_all([home_club, away_club])
        session.flush()

        club_state = OwnerClubState(
            club_id=home_club.id,
            owner_user_id=user.id,
            club_name=home_club.club_name,
            stage="competition",
            world_day=10,
        )
        session.add(club_state)

        # Legacy owner competition
        legacy_comp = OwnerCompetition(
            id=str(uuid.uuid4()),
            name="GTEX Global Championship",
            host_type="gtex",
            format="league",
            status="running",
            current_round=1,
            max_clubs=4,
        )
        session.add(legacy_comp)
        session.flush()

        legacy_entry = OwnerCompetitionEntry(
            competition_id=legacy_comp.id,
            club_id=home_club.id,
            club_name=home_club.club_name,
            owner_user_id=user.id,
        )
        session.add(legacy_entry)

        # Canonical competition
        canonical_comp = UserCompetition(
            id=str(uuid.uuid4()),
            host_user_id=user.id,
            name="GTEX Global Championship",
            format="league",
            source_type="gtex",
            status="in_progress",
            currency="USD",
            scheduled_start_at=now - timedelta(days=1),
        )
        session.add(canonical_comp)
        session.flush()

        rule_set = CompetitionRuleSet(
            id=str(uuid.uuid4()),
            competition_id=canonical_comp.id,
            format="league",
            min_participants=2,
            max_participants=4,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for"],
        )
        session.add(rule_set)

        participant_home = CompetitionParticipant(
            id=str(uuid.uuid4()),
            competition_id=canonical_comp.id,
            club_id=home_club.id,
            status="joined",
            played=1,
            wins=1,
            draws=0,
            losses=0,
            goals_for=3,
            goals_against=1,
            goal_diff=2,
            points=3,
        )
        participant_away = CompetitionParticipant(
            id=str(uuid.uuid4()),
            competition_id=canonical_comp.id,
            club_id=away_club.id,
            status="joined",
            played=1,
            wins=0,
            draws=0,
            losses=1,
            goals_for=1,
            goals_against=3,
            goal_diff=-2,
            points=0,
        )
        session.add_all([participant_home, participant_away])

        canonical_round = CompetitionRound(
            id=str(uuid.uuid4()),
            competition_id=canonical_comp.id,
            round_number=1,
            stage="league",
            status="completed",
        )
        session.add(canonical_round)
        session.flush()

        # Canonical match completed: 3 - 1
        canonical_match = CompetitionMatch(
            id=str(uuid.uuid4()),
            competition_id=canonical_comp.id,
            round_id=canonical_round.id,
            round_number=1,
            stage="league",
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=now.date(),
            scheduled_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
            status=MatchStatus.COMPLETED.value,
            home_score=3,
            away_score=1,
        )
        session.add(canonical_match)
        session.flush()

        # Legacy match placeholder (unplayed in legacy table)
        legacy_match = OwnerMatch(
            id=str(uuid.uuid4()),
            competition_id=legacy_comp.id,
            round_number=1,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_name=home_club.club_name,
            away_name=away_club.club_name,
            status="scheduled",
            home_goals=None,
            away_goals=None,
            played_at=None,
        )
        session.add(legacy_match)
        session.flush()

        # Reconcile competition and match mappings
        comp_mapping = OwnerCompetitionLifecycleMapping(
            id=str(uuid.uuid4()),
            legacy_competition_id=legacy_comp.id,
            canonical_competition_id=canonical_comp.id,
            mapping_status="active",
            metadata_json={},
        )
        match_mapping = OwnerMatchLifecycleMapping(
            id=str(uuid.uuid4()),
            legacy_match_id=legacy_match.id,
            competition_mapping_id=comp_mapping.id,
            legacy_competition_id=legacy_comp.id,
            canonical_match_id=canonical_match.id,
            mapping_status="active",
            metadata_json={},
        )
        session.add_all([comp_mapping, match_mapping])
        session.commit()

        user_id = user.id

    def override_session():
        with SessionLocal() as s:
            yield s

    def override_user():
        with SessionLocal() as s:
            return s.get(User, user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user

    client = TestClient(app)
    with client:
        res = client.get("/owner/control-center")
        assert res.status_code == 200, res.text
        data = res.json()

        # 1. Matches are mapped: canonical completed match appears under recent, not upcoming
        assert len(data["fixtures"]["recent"]) == 1
        assert len(data["fixtures"]["upcoming"]) == 0
        recent = data["fixtures"]["recent"][0]
        assert recent["status"] == MatchStatus.COMPLETED.value
        assert recent["home_goals"] == 3
        assert recent["away_goals"] == 1
        assert recent["execution_model"] == "canonical"

        # 2. Board standings project canonical standings
        assert len(data["board"]) == 1
        board_entry = data["board"][0]
        standings = board_entry["standings"]
        assert len(standings) == 2
        # Home club top of the table with 3 points, GD +2
        top_club = standings[0]
        assert top_club["club_id"] == home_club.id
        assert top_club["points"] == 3
        assert top_club["gf"] == 3
        assert top_club["ga"] == 1
        assert top_club["gf"] - top_club["ga"] == 2
        assert top_club["played"] == 1
