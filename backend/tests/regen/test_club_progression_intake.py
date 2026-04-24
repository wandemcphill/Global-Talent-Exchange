from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import app.models  # noqa: F401
from app.market.player_eligibility_policy import is_buy_cta_allowed, is_preseeded_national_regen
from app.models.base import Base
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.regen import AcademyCandidate, AcademyIntakeBatch, RegenProfile
from app.models.regen_ecosystem import CareerEvent, NationalRegenSeed, YouthAcademy
from app.models.user import KycStatus, User, UserRole
from app.ingestion.models import Player
from app.regen_universe.models import RegenSeason
from app.services.regen_ecosystem_service import RegenEcosystemService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def _create_user(session, *, suffix: str) -> User:
    user = User(
        id=f"user-{suffix}",
        email=f"{suffix}@example.com",
        username=f"user-{suffix}",
        full_name=f"User {suffix.title()}",
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    session.add(user)
    session.flush()
    return user


def _create_club(session, *, owner: User, suffix: str, country_code: str = "NG") -> ClubProfile:
    club = ClubProfile(
        id=f"club-{suffix}",
        owner_user_id=owner.id,
        club_name=f"{suffix.title()} FC",
        short_name=suffix[:10].upper(),
        slug=f"{suffix}-fc",
        primary_color="#0057B8",
        secondary_color="#FFFFFF",
        accent_color="#F5B400",
        country_code=country_code,
        region_name="Lagos",
        city_name="Lagos",
    )
    session.add(club)
    session.flush()
    return club


def _create_academy(session, *, club: ClubProfile, level: int, capacity: int = 24) -> YouthAcademy:
    academy = YouthAcademy(
        club_user_id=club.owner_user_id,
        club_id=club.id,
        level=level,
        scouting_regions_json=["Lagos", club.country_code or "NG"],
        capacity=capacity,
        upgrade_cost=100_000,
    )
    session.add(academy)
    session.add(
        ClubFacility(
            club_id=club.id,
            training_level=level,
            academy_level=level,
            medical_level=max(1, level),
            branding_level=max(1, level),
        )
    )
    session.flush()
    return academy


def _create_season(session, *, suffix: str, season_number: int) -> RegenSeason:
    season = RegenSeason(
        id=f"season-{suffix}",
        season_number=season_number,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_active=True,
        metadata_json={"season_label": "2026/2027"},
    )
    session.add(season)
    session.flush()
    return season


def _batch_for(session, *, club_id: str, season_id: str, reason: str) -> AcademyIntakeBatch:
    batch = session.scalar(
        select(AcademyIntakeBatch).where(
            AcademyIntakeBatch.club_id == club_id,
            AcademyIntakeBatch.season_id == season_id,
            AcademyIntakeBatch.trigger_reason == reason,
        )
    )
    assert batch is not None
    return batch


def _regens_for_batch(session, *, batch_id: str) -> list[RegenProfile]:
    return list(
        session.scalars(
            select(RegenProfile)
            .join_from(RegenProfile, AcademyCandidate, RegenProfile.id == AcademyCandidate.regen_profile_id)
            .where(AcademyCandidate.batch_id == batch_id)
            .order_by(RegenProfile.generated_at.asc(), RegenProfile.id.asc())
        )
    )


def test_season_rollover_generates_once_and_is_auditable(session) -> None:
    owner = _create_user(session, suffix="rollover")
    club = _create_club(session, owner=owner, suffix="rollover")
    _create_academy(session, club=club, level=2)
    season = _create_season(session, suffix="rollover", season_number=1)
    service = RegenEcosystemService(session)

    first = service.generate_club_progression_intake(
        club.id,
        "season_rollover",
        season.id,
        "progression-rollover-1",
    )
    session.flush()
    second = service.generate_club_progression_intake(
        club.id,
        "season_rollover",
        season.id,
        "progression-rollover-2",
    )
    session.flush()

    batch = _batch_for(session, club_id=club.id, season_id=season.id, reason="season_rollover")
    assert first.batch_id == second.batch_id == batch.id
    assert first.generated_count == second.generated_count
    assert first.generated_count in {2, 3}
    assert session.scalar(select(func.count()).select_from(AcademyIntakeBatch)) == 1
    assert batch.metadata_json["source"] == "club_progression"
    assert batch.metadata_json["reason"] == "season_rollover"
    assert batch.metadata_json["season_id"] == season.id
    assert batch.metadata_json["idempotency_key"] == "progression-rollover-1"
    assert (
        session.scalar(
            select(func.count()).select_from(CareerEvent).where(CareerEvent.type == "club_progression_intake")
        )
        == first.generated_count
    )

    for regen in _regens_for_batch(session, batch_id=batch.id):
        player = session.get(Player, regen.player_id)
        assert player is not None
        assert player.current_club_profile_id == club.id
        assert player.is_tradable is False
        assert is_buy_cta_allowed(player) is False
        assert regen.metadata_json["source"] == "club_progression"
        assert regen.metadata_json["trigger_reason"] == "season_rollover"


def test_higher_academy_level_creates_more_and_better_candidates(session) -> None:
    low_owner = _create_user(session, suffix="academy-low")
    high_owner = _create_user(session, suffix="academy-high")
    low_club = _create_club(session, owner=low_owner, suffix="academy-low")
    high_club = _create_club(session, owner=high_owner, suffix="academy-high")
    _create_academy(session, club=low_club, level=1)
    _create_academy(session, club=high_club, level=4)
    low_season = _create_season(session, suffix="academy-low", season_number=1)
    high_season = _create_season(session, suffix="academy-high", season_number=2)
    service = RegenEcosystemService(session)

    low_result = service.generate_club_progression_intake(
        low_club.id, "academy_level_up", low_season.id, "academy-low-key"
    )
    high_result = service.generate_club_progression_intake(
        high_club.id, "academy_level_up", high_season.id, "academy-high-key"
    )
    session.flush()

    low_batch = _batch_for(session, club_id=low_club.id, season_id=low_season.id, reason="academy_level_up")
    high_batch = _batch_for(session, club_id=high_club.id, season_id=high_season.id, reason="academy_level_up")
    low_regens = _regens_for_batch(session, batch_id=low_batch.id)
    high_regens = _regens_for_batch(session, batch_id=high_batch.id)
    low_avg_potential = sum(
        int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) for regen in low_regens
    ) / len(low_regens)
    high_avg_potential = sum(
        int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) for regen in high_regens
    ) / len(high_regens)

    assert low_result.generated_count in {1, 2}
    assert high_result.generated_count in {5, 6, 7, 8}
    assert high_result.generated_count > low_result.generated_count
    assert high_batch.academy_quality_score > low_batch.academy_quality_score
    assert high_avg_potential >= low_avg_potential


def test_progression_regens_stay_distinct_from_preseeded_national_regens(session) -> None:
    owner = _create_user(session, suffix="distinct")
    club = _create_club(session, owner=owner, suffix="distinct")
    _create_academy(session, club=club, level=3)
    season = _create_season(session, suffix="distinct", season_number=1)
    session.add(
        NationalRegenSeed(
            seed_key="seed:ng:u20:st:1",
            display_name="Chinedu Okeke",
            age=18,
            age_band="u20",
            country_code="NG",
            country_name="Nigeria",
            confederation_code="CAF",
            seed_type="preseeded_national_pool",
            generation_index=1,
            primary_position="ST",
            secondary_positions_json=["RW"],
            current_rating=61,
            potential_rating=79,
            growth_curve=0.7,
            personality_seed_json={"ambition": 74},
            rarity_tier="rare",
            status="available",
            preseed_batch="test-batch",
            metadata_json={"source_bucket": "preseeded"},
        )
    )
    session.flush()
    service = RegenEcosystemService(session)

    result = service.generate_club_progression_intake(
        club.id,
        "youth_tournament_performance",
        season.id,
        "tournament-key",
    )
    session.flush()

    batch = _batch_for(session, club_id=club.id, season_id=season.id, reason="youth_tournament_performance")
    regens = _regens_for_batch(session, batch_id=batch.id)

    assert result.generated_count in {3, 4, 5}
    assert session.scalar(select(func.count()).select_from(NationalRegenSeed)) == 1
    assert all(regen.generation_source == "club_progression_intake" for regen in regens)
    assert all(is_preseeded_national_regen(regen) is False for regen in regens)
    assert all((regen.metadata_json or {}).get("source") == "club_progression" for regen in regens)
    assert all((regen.metadata_json or {}).get("national_pool_only") is not True for regen in regens)
