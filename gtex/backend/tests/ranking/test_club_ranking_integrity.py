from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.security import TokenError, create_access_token, decode_access_token
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.enums.match_status import MatchStatus
from app.core.module import DomainModule
from app.models.auth_session import AuthSession
from app.models.club_profile import ClubProfile
from app.models.club_ranking_integrity import ClubRankingAbuseFlag, ClubRankingEvent
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import KycStatus, User, UserRole
from app.schemas.competition_lifecycle import CompetitionMatchResultRequest
from app.services.competition_orchestrator import CompetitionOrchestrator


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-ranking-integrity-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-ranking-integrity-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_INGESTION_PROVIDER": "mock",
        "GTE_REAL_PLAYER_IMPORT_PROVIDER": "mock",
        "GTE_RUN_STARTUP_SEEDING": "0",
        "GTE_TASK_QUEUE_ENABLED": "0",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}
    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield load_settings()
    finally:
        reset_settings_cache()
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_settings_cache()


@pytest.fixture(scope="module")
def app(test_settings):
    from app.main import create_app

    modules = (
        DomainModule("auth", router_path="app.auth.router:router"),
        DomainModule("competitions", router_path="app.routes.competitions:router"),
        DomainModule("ranking_integrity", router_path="app.ranking_integrity.router:router"),
    )
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(settings=test_settings, engine=engine, modules=modules, run_migration_check=True)
    yield application
    startup_thread = getattr(application.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    engine.dispose()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def app_session_factory(app, client):
    return app.state.session_factory


@pytest.fixture(autouse=True)
def _authenticated_routes(app, app_session_factory):
    def _resolve_user(request: Request) -> User:
        authorization = request.headers.get("authorization", "").strip()
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ", maxsplit=1)[1].strip()
        try:
            subject = decode_access_token(token).get("sub")
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        with app_session_factory() as session:
            user = session.get(User, subject)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
            return user

    def _current_admin(request: Request) -> User:
        user = _resolve_user(request)
        if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access is required.")
        return user

    app.dependency_overrides[get_current_user] = _resolve_user
    app.dependency_overrides[get_current_admin] = _current_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def user_factory(app_session_factory):
    def create_user(*, role: UserRole = UserRole.USER, suffix: str | None = None) -> dict[str, str]:
        user_id = str(uuid4())
        session_id = str(uuid4())
        token = uuid4().hex[:8]
        label = suffix or token
        email = f"ranking-{label}-{token}@example.com"
        username = f"ranking_{label}_{token}".replace("-", "_")[:64]
        with app_session_factory() as session:
            session.add(
                User(
                    id=user_id,
                    email=email,
                    username=username,
                    display_name=f"Ranking {label}",
                    full_name=f"Ranking {label}",
                    phone_number="1234567890",
                    password_hash="not-used",
                    role=role,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    last_login_at=datetime.now(timezone.utc),
                )
            )
            session.add(
                AuthSession(
                    id=session_id,
                    user_id=user_id,
                    refresh_token_hash=f"ranking-test-refresh-{session_id}",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                    last_used_at=datetime.now(timezone.utc),
                    device_id="ranking-tests",
                )
            )
            session.commit()
        access_token = create_access_token(user_id, claims={"sid": session_id, "role": role.value, "email": email})
        return {"user_id": user_id, "headers": {"Authorization": f"Bearer {access_token}"}}

    return create_user


def _create_club(session, *, owner_user_id: str, name: str | None = None, days_old: int = 30) -> ClubProfile:
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    club = ClubProfile(
        owner_user_id=owner_user_id,
        club_name=name or f"Integrity Club {suffix}",
        short_name=(name or f"Integrity {suffix}")[:20],
        slug=f"integrity-club-{suffix}",
        primary_color="#A6FF1A",
        secondary_color="#0B1210",
        accent_color="#58D5FF",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        created_at=now - timedelta(days=days_old),
        updated_at=now - timedelta(days=days_old),
    )
    session.add(club)
    session.flush()
    return club


def _seed_clean_history(session, *, club_id: str, competition_id: str, count: int = 5) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=30)
    for index in range(count):
        session.add(
            ClubRankingEvent(
                event_key=f"seed:{club_id}:{index}:{uuid4().hex}",
                event_kind="seed_history",
                club_id=club_id,
                competition_id=competition_id,
                result="win",
                base_points=Decimal("3.0000"),
                final_points_delta=Decimal("1.0000"),
                raw_points_delta=Decimal("1.0000"),
                integrity_status="clean",
                reason="seeded_established_history",
                created_at=old,
                updated_at=old,
            )
        )
    session.flush()


def _seed_match_fixture(
    session,
    *,
    host_user_id: str,
    home_club: ClubProfile,
    away_club: ClubProfile,
    is_ranked: bool = True,
    competition_type: str = "league",
    competition_mode: str = "competition",
    source_type: str | None = None,
    host_label: str = "User Hosted Ladder",
) -> tuple[Competition, CompetitionMatch]:
    competition = Competition(
        host_user_id=host_user_id,
        name=f"{host_label} {uuid4().hex[:6]}",
        competition_type=competition_type,
        competition_mode=competition_mode,
        source_type=source_type,
        format=CompetitionFormat.LEAGUE.value,
        visibility=CompetitionVisibility.PUBLIC.value,
        status=CompetitionStatus.LIVE.value,
        stage="league",
        currency="credit",
        entry_fee_minor=0,
        platform_fee_bps=2000,
        is_ranked=is_ranked,
    )
    session.add(competition)
    session.flush()
    session.add(
        CompetitionRuleSet(
            competition_id=competition.id,
            format=CompetitionFormat.LEAGUE.value,
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for"],
            league_home_away=False,
            group_stage_enabled=False,
        )
    )
    session.add_all(
        [
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=home_club.id,
                user_id=home_club.owner_user_id,
            ),
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=away_club.id,
                user_id=away_club.owner_user_id,
            ),
        ]
    )
    round_row = CompetitionRound(
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="scheduled",
    )
    session.add(round_row)
    session.flush()
    match = CompetitionMatch(
        competition_id=competition.id,
        round_id=round_row.id,
        round_number=1,
        stage="league",
        home_club_id=home_club.id,
        away_club_id=away_club.id,
        status=MatchStatus.SCHEDULED.value,
    )
    session.add(match)
    session.commit()
    return competition, match


def _complete_match(session, competition: Competition, match: CompetitionMatch, *, result_type: str = "played"):
    payload = CompetitionMatchResultRequest(
        home_score=2,
        away_score=0,
        winner_club_id=match.home_club_id,
        result_type=result_type,
        forfeit_reason="opponent_forfeit" if result_type == "forfeit" else None,
    )
    return CompetitionOrchestrator(session).complete_match(competition.id, match.id, payload)


def test_ranked_match_creates_ranking_events_and_leaderboard(client, app_session_factory, user_factory) -> None:
    host = user_factory(suffix="ranked-host")
    away_owner = user_factory(suffix="ranked-away")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"], name="Clean Ladder FC")
        away = _create_club(session, owner_user_id=away_owner["user_id"], name="Clean Opponent FC")
        competition, match = _seed_match_fixture(
            session,
            host_user_id=host["user_id"],
            home_club=home,
            away_club=away,
        )
        _seed_clean_history(session, club_id=home.id, competition_id=competition.id)
        _seed_clean_history(session, club_id=away.id, competition_id=competition.id)
        _complete_match(session, competition, match)
        events = session.scalars(
            select(ClubRankingEvent).where(ClubRankingEvent.competition_id == competition.id)
        ).all()
        match_events = [event for event in events if event.event_kind == "match_result"]
        assert len(match_events) == 2
        winner_event = next(event for event in match_events if event.club_id == home.id)
        assert winner_event.result == "win"
        assert winner_event.integrity_status == "clean"
        assert winner_event.final_points_delta > 0

    leaderboard = client.get("/api/competitions/leaderboard/clubs")
    assert leaderboard.status_code == 200, leaderboard.text
    assert any(item["club_id"] == home.id for item in leaderboard.json()["entries"])

    audit_response = client.get(f"/api/clubs/{home.id}/ranking-events")
    assert audit_response.status_code == 200, audit_response.text
    assert any(item["event_kind"] == "match_result" for item in audit_response.json()["events"])


def test_unranked_and_national_competitions_do_not_create_events(app_session_factory, user_factory) -> None:
    host = user_factory(suffix="skip-host")
    away_owner = user_factory(suffix="skip-away")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"])
        away = _create_club(session, owner_user_id=away_owner["user_id"])
        unranked, unranked_match = _seed_match_fixture(
            session,
            host_user_id=host["user_id"],
            home_club=home,
            away_club=away,
            is_ranked=False,
            host_label="Unranked",
        )
        national, national_match = _seed_match_fixture(
            session,
            host_user_id=host["user_id"],
            home_club=home,
            away_club=away,
            competition_type="national_team",
            competition_mode="national_team",
            host_label="National",
        )
        _complete_match(session, unranked, unranked_match)
        _complete_match(session, national, national_match)
        count = session.scalar(
            select(ClubRankingEvent).where(ClubRankingEvent.competition_id.in_([unranked.id, national.id]))
        )
        assert count is None


def test_repeated_same_opponent_matches_decay_and_block(app_session_factory, user_factory) -> None:
    host = user_factory(suffix="repeat-host")
    away_owner = user_factory(suffix="repeat-away")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"])
        away = _create_club(session, owner_user_id=away_owner["user_id"])
        statuses: list[str] = []
        deltas: list[Decimal] = []
        for index in range(7):
            competition, match = _seed_match_fixture(
                session,
                host_user_id=host["user_id"],
                home_club=home,
                away_club=away,
                host_label=f"Repeat {index}",
            )
            _complete_match(session, competition, match)
            event = session.scalar(
                select(ClubRankingEvent).where(ClubRankingEvent.event_key == f"match:{match.id}:{home.id}")
            )
            statuses.append(event.integrity_status)
            deltas.append(event.final_points_delta)

        assert any(status in {"reduced", "provisional"} for status in statuses)
        assert statuses[-1] == "blocked"
        assert deltas[-1] == Decimal("0.0000")
        assert deltas[3] < deltas[0]


def test_same_host_and_same_owner_flags_are_created(client, app_session_factory, user_factory) -> None:
    host = user_factory(suffix="same-host")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"])
        away = _create_club(session, owner_user_id=host["user_id"])
        competition, match = _seed_match_fixture(
            session,
            host_user_id=host["user_id"],
            home_club=home,
            away_club=away,
            host_label="Same Owner",
        )
        _complete_match(session, competition, match)
        event = session.scalar(
            select(ClubRankingEvent).where(ClubRankingEvent.event_key == f"match:{match.id}:{home.id}")
        )
        assert event.integrity_status == "blocked"
        assert event.final_points_delta == Decimal("0.0000")

    admin = user_factory(role=UserRole.SUPER_ADMIN, suffix="ranking-admin")
    flags = client.get("/api/admin/ranking/flags", headers=admin["headers"])
    assert flags.status_code == 200, flags.text
    assert any(flag["flag_type"] == "same_owner_or_ownership_group" for flag in flags.json()["flags"])


def test_forfeit_heavy_and_low_quality_matches_are_reduced(app_session_factory, user_factory) -> None:
    host = user_factory(suffix="forfeit-host")
    away_owner = user_factory(suffix="forfeit-away")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"])
        away = _create_club(session, owner_user_id=away_owner["user_id"])
        events = []
        for index in range(3):
            competition, match = _seed_match_fixture(
                session,
                host_user_id=host["user_id"],
                home_club=home,
                away_club=away,
                host_label=f"Forfeit {index}",
            )
            _complete_match(session, competition, match, result_type="forfeit")
            events.append(
                session.scalar(
                    select(ClubRankingEvent).where(ClubRankingEvent.event_key == f"match:{match.id}:{home.id}")
                )
            )
        assert all("forfeit" in event.reason for event in events)
        assert events[-1].integrity_status in {"reduced", "review", "blocked"}
        assert events[-1].final_points_delta <= events[0].final_points_delta


def test_duplicate_result_does_not_double_award(app_session_factory, user_factory) -> None:
    host = user_factory(suffix="duplicate-host")
    away_owner = user_factory(suffix="duplicate-away")
    with app_session_factory() as session:
        home = _create_club(session, owner_user_id=host["user_id"])
        away = _create_club(session, owner_user_id=away_owner["user_id"])
        competition, match = _seed_match_fixture(
            session,
            host_user_id=host["user_id"],
            home_club=home,
            away_club=away,
            host_label="Duplicate",
        )
        _complete_match(session, competition, match)
        first_total = session.scalar(
            select(ClubRankingEvent.final_points_delta).where(
                ClubRankingEvent.event_key == f"match:{match.id}:{home.id}"
            )
        )
        _complete_match(session, competition, match)
        events = session.scalars(
            select(ClubRankingEvent).where(
                ClubRankingEvent.competition_id == competition.id,
                ClubRankingEvent.event_kind == "match_result",
            )
        ).all()
        flags = session.scalars(
            select(ClubRankingAbuseFlag).where(
                ClubRankingAbuseFlag.competition_id == competition.id,
                ClubRankingAbuseFlag.flag_type == "duplicate_settlement",
            )
        ).all()
        assert len(events) == 2
        assert first_total == session.scalar(
            select(ClubRankingEvent.final_points_delta).where(
                ClubRankingEvent.event_key == f"match:{match.id}:{home.id}"
            )
        )
        assert flags
