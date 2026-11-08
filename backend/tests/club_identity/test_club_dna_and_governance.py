from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base, generate_uuid
from app.models.club_dna import (
    DNAPhilosophy,
    PolicyAgeMode,
    PolicyNationalityMode,
    TransferStrategy,
)
from app.models.club_profile import ClubProfile, ClubType
from app.models.user import User, UserRole
from app.services.club_governance_policy import ClubGovernancePolicyService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def owner(session: Session) -> User:
    user = User(
        id=generate_uuid(),
        email="owner@gtex.local",
        username="ClubOwner",
        password_hash="test_password_hash_secure",  # pragma: allowlist secret
        role=UserRole.USER,
        display_name="Club Owner",
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def test_club(session: Session, owner: User) -> ClubProfile:
    club = ClubProfile(
        id=generate_uuid(),
        owner_user_id=owner.id,
        club_name="Olympique Nouvelle FC",
        short_name="ONFC",
        slug="olympique-nouvelle-fc",
        club_type=ClubType.PROFESSIONAL,
        primary_color="#1E3A8A",
        secondary_color="#FFFFFF",
        accent_color="#F59E0B",
        country_code="FRA",
        city_name="Lyon",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return club


def test_default_club_dna_policy(session: Session, test_club: ClubProfile) -> None:
    service = ClubGovernancePolicyService(session)
    policy = service.get_or_create_policy(test_club.id)

    assert policy.club_id == test_club.id
    assert policy.primary_philosophy == DNAPhilosophy.BALANCED.value
    assert policy.nationality_mode == PolicyNationalityMode.NONE.value
    assert policy.age_mode == PolicyAgeMode.NONE.value
    assert policy.allow_dual_nationality is True
    assert policy.allow_age_exceptions is True


def test_compound_club_philosophy_configuration(session: Session, test_club: ClubProfile) -> None:
    service = ClubGovernancePolicyService(session)
    updated = service.update_policy(
        test_club.id,
        {
            "primary_philosophy": DNAPhilosophy.ACADEMY_FIRST.value,
            "secondary_philosophies": [
                DNAPhilosophy.YOUTH_DEVELOPMENT.value,
                DNAPhilosophy.SELLING_CLUB.value,
            ],
            "transfer_strategy": TransferStrategy.BUY_YOUNG_DEVELOP_SELL.value,
            "club_vision_narrative": "French Academy-First Selling Club dedicated to developing top prospects.",
        },
    )

    assert updated.primary_philosophy == DNAPhilosophy.ACADEMY_FIRST.value
    assert updated.secondary_philosophies == [
        DNAPhilosophy.YOUTH_DEVELOPMENT.value,
        DNAPhilosophy.SELLING_CLUB.value,
    ]
    assert updated.transfer_strategy == TransferStrategy.BUY_YOUNG_DEVELOP_SELL.value
    assert "French Academy-First" in (updated.club_vision_narrative or "")


def test_exclusive_nationality_policy_enforcement(session: Session, test_club: ClubProfile) -> None:
    service = ClubGovernancePolicyService(session)
    service.update_policy(
        test_club.id,
        {
            "nationality_mode": PolicyNationalityMode.EXCLUSIVE.value,
            "target_nationalities": ["FRA"],
            "allow_dual_nationality": True,
        },
    )

    # 1. French player: eligible
    eval_french = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="player-french-1",
        player_name="Kylian Mbappé",
        nationality="FRA",
        age=25,
    )
    assert eval_french.is_eligible is True
    assert eval_french.policy_violated is None

    # 2. Non-French player (e.g. English): rejected
    eval_english = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="player-english-1",
        player_name="Harry Kane",
        nationality="ENG",
        age=30,
    )
    assert eval_english.is_eligible is False
    assert eval_english.policy_violated == "nationality"
    assert "strict exclusive nationality policy" in (eval_english.violation_reason or "")
    assert eval_english.exception_permitted is False

    # 3. Dual nationality player (e.g. DZA + FRA): eligible when allow_dual_nationality=True
    eval_dual = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="player-dual-1",
        player_name="Dual National Prospect",
        nationality="DZA",
        dual_nationalities=["FRA"],
        age=20,
    )
    assert eval_dual.is_eligible is True

    # 4. If dual nationality disabled: rejected
    service.update_policy(test_club.id, {"allow_dual_nationality": False})
    eval_dual_disabled = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="player-dual-1",
        player_name="Dual National Prospect",
        nationality="DZA",
        dual_nationalities=["FRA"],
        age=20,
    )
    assert eval_dual_disabled.is_eligible is False


def test_age_policy_and_governance_exceptions(session: Session, test_club: ClubProfile, owner: User) -> None:
    service = ClubGovernancePolicyService(session)
    service.update_policy(
        test_club.id,
        {
            "age_mode": PolicyAgeMode.STRICT.value,
            "preferred_max_age": 23,
            "allow_age_exceptions": True,
        },
    )

    # Under-23 player: eligible
    eval_young = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="young-star-1",
        player_name="Young Prospect",
        age=21,
    )
    assert eval_young.is_eligible is True

    # Over-23 player: restricted, but exception permitted
    eval_veteran = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="veteran-star-1",
        player_name="Experienced Veteran",
        age=30,
    )
    assert eval_veteran.is_eligible is False
    assert eval_veteran.policy_violated == "age"
    assert eval_veteran.exception_permitted is True
    assert eval_veteran.has_approved_exception is False

    # Owner approves governance exception
    exception = service.approve_exception(
        test_club.id,
        player_id="veteran-star-1",
        player_name="Experienced Veteran",
        policy_type="age",
        reason="Exceptional leadership profile to mentor youth academy graduates in top flight.",
        user_id=owner.id,
        player_age=30,
    )
    assert exception.status == "approved"
    assert exception.approved_by_user_id == owner.id

    # Now veteran player is eligible via approved exception
    eval_veteran_after = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="veteran-star-1",
        player_name="Experienced Veteran",
        age=30,
    )
    assert eval_veteran_after.is_eligible is True
    assert eval_veteran_after.has_approved_exception is True
    assert eval_veteran_after.exception_id == exception.id

    # Check exception listing
    exceptions = service.list_exceptions(test_club.id)
    assert len(exceptions) == 1
    assert exceptions[0].player_id == "veteran-star-1"
    assert "leadership profile" in exceptions[0].reason


def test_strict_age_policy_without_exceptions(session: Session, test_club: ClubProfile) -> None:
    service = ClubGovernancePolicyService(session)
    service.update_policy(
        test_club.id,
        {
            "age_mode": PolicyAgeMode.STRICT.value,
            "preferred_max_age": 21,
            "allow_age_exceptions": False,
        },
    )

    eval_over_21 = service.evaluate_player_recruitment_eligibility(
        test_club.id,
        player_id="player-25",
        player_name="Mid-Career Player",
        age=25,
    )
    assert eval_over_21.is_eligible is False
    assert eval_over_21.exception_permitted is False
    assert "strictly prohibits signings over age 21" in (eval_over_21.violation_reason or "")


def test_squad_dna_recommendations(session: Session, test_club: ClubProfile) -> None:
    service = ClubGovernancePolicyService(session)
    service.update_policy(
        test_club.id,
        {
            "primary_philosophy": "academy_first",
            "secondary_philosophies": ["selling_club"],
            "nationality_mode": "exclusive",
            "target_nationalities": ["FRA"],
            "age_mode": "strict",
            "preferred_max_age": 23,
        },
    )
    recs = service.generate_squad_dna_recommendations(test_club.id)
    assert recs["club_id"] == test_club.id
    assert recs["recommended_formation"] == "4-3-3"
    assert recs["target_u21_minutes_share_pct"] == 45
    assert recs["academy_promotion_quota"] == 4
    assert any("FRA" in d for d in recs["scouting_directives"])
    assert any("showcase" in d.lower() for d in recs["tactical_directives"])
