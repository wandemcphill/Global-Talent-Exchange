"""Shared fixtures for the Talent Exchange tests.

The suite runs against an in-memory SQLite database built from the ORM metadata
and a minimal FastAPI app carrying only the talent routers, mirroring the
pattern already used by `tests/players/test_real_player_universe_routes.py`.
That keeps these tests fast and independent of the full application startup
while still exercising the real routers, real dependencies and real SQL.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Match, Player, PlayerMatchStat
from app.models.base import Base
from app.models.user import User, UserRole
from app.talent.constants import AvailabilityStatus, VisibilityState
from app.talent.models import TalentProfile
from app.talent.router import admin_router, require_talent_admin, router as talent_router
from app.talent.service import TalentExchangeService

REFERENCE_TODAY = date(2026, 8, 1)


# Tables these tests write to, in delete order (children first). Building the
# full ORM metadata costs several seconds, so the schema is created once per
# session and only the touched tables are cleared between tests.
TRUNCATE_ORDER = (
    "talent_moderation_actions",
    "talent_shortlist_entries",
    "talent_shortlists",
    "talent_verification_records",
    "talent_signal_records",
    "talent_ranking_snapshots",
    "talent_profiles",
    "player_injury_cases",
    "ingestion_player_match_stats",
    "ingestion_matches",
    "ingestion_players",
    "ingestion_clubs",
    "ingestion_competitions",
    "ingestion_countries",
    "users",
)


@pytest.fixture(scope="session")
def _engine():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session_factory(_engine) -> Iterator[sessionmaker[Session]]:
    factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    yield factory
    with _engine.begin() as connection:
        for table_name in TRUNCATE_ORDER:
            connection.execute(text(f"DELETE FROM {table_name}"))


@pytest.fixture(scope="function")
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


class _Identity:
    """Mutable holder so a test can change who is calling mid-test."""

    def __init__(self) -> None:
        self.user: User | None = None
        self.admin: User | None = None


@pytest.fixture(scope="function")
def identity() -> _Identity:
    return _Identity()


@pytest.fixture(scope="function")
def client(session_factory: sessionmaker[Session], identity: _Identity) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(talent_router)
    app.include_router(admin_router)

    def _session_override() -> Iterator[Session]:
        db_session = session_factory()
        try:
            yield db_session
        finally:
            db_session.close()

    def _optional_user() -> User | None:
        return identity.user

    def _required_user() -> User:
        if identity.user is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return identity.user

    def _talent_admin() -> User:
        if identity.admin is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return identity.admin

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_optional_current_user] = _optional_user
    app.dependency_overrides[get_current_user] = _required_user
    app.dependency_overrides[require_talent_admin] = _talent_admin

    with TestClient(app) as test_client:
        yield test_client


# ----------------------------------------------------------------------
# Seeding helpers
# ----------------------------------------------------------------------


def make_user(
    session: Session,
    *,
    username: str,
    role: UserRole = UserRole.USER,
) -> User:
    user = User(
        email=f"{username}@talent.test",
        username=username,
        full_name=username.replace("_", " ").title(),
        password_hash="not-a-real-hash",  # pragma: allowlist secret
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def make_competition(
    session: Session,
    *,
    key: str,
    strength: float | None = 80.0,
    is_major: bool = False,
    age_bracket: str | None = None,
) -> Competition:
    country = Country(
        source_provider="test",
        provider_external_id=f"country-{key}",
        name=f"Country {key}",
        alpha3_code=key[:3].upper(),
        fifa_code=key[:3].upper(),
    )
    session.add(country)
    session.flush()
    competition = Competition(
        source_provider="test",
        provider_external_id=f"comp-{key}",
        country_id=country.id,
        name=f"Competition {key}",
        slug=f"competition-{key}",
        competition_strength=strength,
        is_major=is_major,
        age_bracket=age_bracket,
    )
    session.add(competition)
    session.flush()
    return competition


def make_club(session: Session, *, key: str, competition: Competition) -> Club:
    club = Club(
        source_provider="test",
        provider_external_id=f"club-{key}",
        name=f"Club {key}",
        slug=f"club-{key}",
        current_competition_id=competition.id,
    )
    session.add(club)
    session.flush()
    return club


def make_player(
    session: Session,
    *,
    key: str,
    full_name: str,
    position: str = "CM",
    date_of_birth: date = date(2002, 3, 14),
    club: Club | None = None,
    country: Country | None = None,
) -> Player:
    player = Player(
        source_provider="test",
        provider_external_id=f"player-{key}",
        full_name=full_name,
        canonical_display_name=full_name,
        position=position,
        normalized_position=position,
        secondary_positions_json=[],
        date_of_birth=date_of_birth,
        preferred_foot="right",
        current_club_id=club.id if club else None,
        country_id=country.id if country else None,
    )
    session.add(player)
    session.flush()
    return player


def make_match(
    session: Session,
    *,
    key: str,
    competition: Competition,
    home_club: Club,
    away_club: Club,
    kickoff: datetime,
    stage: str | None = None,
) -> Match:
    match = Match(
        source_provider="test",
        provider_external_id=f"match-{key}",
        competition_id=competition.id,
        home_club_id=home_club.id,
        away_club_id=away_club.id,
        kickoff_at=kickoff,
        status="completed",
        stage=stage,
    )
    session.add(match)
    session.flush()
    return match


def make_match_stat(
    session: Session,
    *,
    key: str,
    player: Player,
    match: Match,
    minutes: int = 90,
    rating: float | None = 7.0,
    goals: int = 0,
    assists: int = 0,
) -> PlayerMatchStat:
    stat = PlayerMatchStat(
        source_provider="test",
        provider_external_id=f"stat-{key}",
        player_id=player.id,
        match_id=match.id,
        competition_id=match.competition_id,
        appearances=1,
        starts=1,
        minutes=minutes,
        rating=rating,
        goals=goals,
        assists=assists,
    )
    session.add(stat)
    session.flush()
    return stat


def seed_talent(
    session: Session,
    *,
    key: str,
    display_name: str,
    position_code: str = "CM",
    composite_score: float = 60.0,
    form_score: float = 50.0,
    competition_level_score: float = 60.0,
    age_years: int = 22,
    nationality_code: str = "NGA",
    location_country_code: str = "NGA",
    location_region: str = "Lagos",
    location_city: str = "Ikeja",
    availability_status: str = AvailabilityStatus.OPEN_TO_OFFERS.value,
    verification_tier: str = "unverified",
    visibility_state: str = VisibilityState.PUBLISHED.value,
    tactical_roles: list[str] | None = None,
    secondary_positions: list[str] | None = None,
    signal_codes: list[str] | None = None,
    owner_user_id: str | None = None,
    experience_years: float = 4.0,
    ranking_confidence: float = 0.6,
    ranking_sample_size: int = 12,
    is_featured: bool = False,
    portfolio: list[dict[str, Any]] | None = None,
    internal_notes: str | None = None,
    preferred_foot: str = "right",
) -> TalentProfile:
    """Insert a ready-made discovery row without running the pipeline.

    Search, pagination and privacy tests care about the projection and the
    query, not about how the score was produced; ranking tests exercise the
    pipeline directly.
    """

    player = make_player(session, key=key, full_name=display_name, position=position_code)
    profile = TalentProfile(
        player_id=player.id,
        owner_user_id=owner_user_id,
        display_name=display_name,
        headline=f"{display_name} headline",
        position_code=position_code,
        secondary_positions_json=list(secondary_positions or []),
        tactical_roles_json=list(tactical_roles or []),
        preferred_foot=preferred_foot,
        date_of_birth=date(REFERENCE_TODAY.year - age_years, 5, 1),
        age_years=age_years,
        nationality_code=nationality_code,
        nationality_name="Nigeria",
        location_country_code=location_country_code,
        location_region=location_region,
        location_city=location_city,
        availability_status=availability_status,
        experience_years=experience_years,
        verification_tier=verification_tier,
        visibility_state=visibility_state,
        composite_score=composite_score,
        form_score=form_score,
        competition_level_score=competition_level_score,
        ranking_confidence=ranking_confidence,
        ranking_sample_size=ranking_sample_size,
        active_signal_codes_json=list(signal_codes or []),
        is_featured=is_featured,
        portfolio_json=list(portfolio or []),
        internal_notes=internal_notes,
        technical_attributes_json={"passing": 70.0, "first_touch": 68.0},
        tactical_attributes_json={"vision": 72.0},
        physical_attributes_json={"stamina": 74.0},
    )
    session.add(profile)
    session.flush()
    TalentExchangeService(session, today=REFERENCE_TODAY).refresh_indexes(profile)
    session.commit()
    return profile


@pytest.fixture(scope="function")
def make_service() -> Callable[[Session], TalentExchangeService]:
    def factory(db_session: Session) -> TalentExchangeService:
        return TalentExchangeService(db_session, today=REFERENCE_TODAY)

    return factory


def days_before(days: int) -> datetime:
    return datetime.combine(REFERENCE_TODAY, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=days)


__all__ = [
    "REFERENCE_TODAY",
    "days_before",
    "make_club",
    "make_competition",
    "make_match",
    "make_match_stat",
    "make_player",
    "make_user",
    "seed_talent",
]
