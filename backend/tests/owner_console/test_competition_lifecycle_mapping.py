from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.owner_competition_lifecycle_mapping import (
    OwnerCompetitionLifecycleMapping,
    OwnerMatchLifecycleMapping,
)
from app.models.user import User
from app.owner_console.models import OwnerCompetition, OwnerMatch
from app.services.owner_competition_lifecycle_mapping_service import (
    OwnerCompetitionLifecycleMappingError,
    OwnerCompetitionLifecycleMappingService,
)


def _id() -> str:
    return str(uuid4())


def _canonical_competition(session, *, name: str = "Canonical Global Cup") -> UserCompetition:
    owner = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
    assert owner is not None
    competition = UserCompetition(
        host_user_id=owner.id,
        name=name,
        format="league",
        currency="coin",
        source_type="gtex_global",
        source_id=_id(),
        status="live",
        stage="live",
    )
    session.add(competition)
    session.flush()
    return competition


def test_competition_mapping_is_idempotent_and_one_to_one(app):
    with app.state.session_factory() as session:
        legacy = OwnerCompetition(name=f"Global Cup {_id()}", host_type="gtex")
        canonical = _canonical_competition(session)
        another_canonical = _canonical_competition(session, name="Another Canonical Cup")
        session.add(legacy)
        session.flush()

        service = OwnerCompetitionLifecycleMappingService(session)
        first = service.bind_competition(legacy.id, canonical.id)
        repeated = service.bind_competition(legacy.id, canonical.id)

        assert repeated.id == first.id
        assert repeated.canonical_competition_id == canonical.id

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_competition(legacy.id, another_canonical.id)
        assert exc_info.value.code == "legacy_competition_already_mapped"

        other_legacy = OwnerCompetition(name=f"Other Global Cup {_id()}", host_type="gtex")
        session.add(other_legacy)
        session.flush()
        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_competition(other_legacy.id, canonical.id)
        assert exc_info.value.code == "canonical_competition_already_mapped"

        session.flush()
        assert (
            session.scalar(
                select(OwnerCompetitionLifecycleMapping).where(
                    OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy.id
                )
            ).id
            == first.id
        )


def test_user_hosted_competition_cannot_be_bound_to_global_lifecycle(app):
    with app.state.session_factory() as session:
        legacy = OwnerCompetition(
            name=f"Friends Cup {_id()}",
            host_type="user",
            host_user_id=_id(),
        )
        canonical = _canonical_competition(session)
        session.add(legacy)
        session.flush()

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            OwnerCompetitionLifecycleMappingService(session).bind_competition(legacy.id, canonical.id)
        assert exc_info.value.code == "user_hosted_competition_uses_separate_lifecycle"


def test_only_matching_scheduled_fixtures_can_be_mapped_and_retried(app):
    with app.state.session_factory() as session:
        owner = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        assert owner is not None
        legacy_competition = OwnerCompetition(name=f"Global Cup {_id()}", host_type="gtex")
        canonical_competition = _canonical_competition(session)
        session.add(legacy_competition)
        session.flush()

        home_club_id, away_club_id = _id(), _id()
        legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_name="Home",
            away_name="Away",
            status="scheduled",
        )
        another_legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_name="Home",
            away_name="Away",
            status="scheduled",
        )
        round_row = CompetitionRound(
            competition_id=canonical_competition.id,
            round_number=1,
            stage="league",
            group_key="A",
            status="scheduled",
        )
        session.add_all([legacy_match, another_legacy_match, round_row])
        session.flush()

        canonical_match = CompetitionMatch(
            competition_id=canonical_competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            group_key="A",
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            status="scheduled",
        )
        mismatched_match = CompetitionMatch(
            competition_id=canonical_competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            group_key="A",
            home_club_id=away_club_id,
            away_club_id=home_club_id,
            status="scheduled",
        )
        session.add_all([canonical_match, mismatched_match])
        session.flush()

        service = OwnerCompetitionLifecycleMappingService(session)
        service.bind_competition(legacy_competition.id, canonical_competition.id)
        first = service.bind_scheduled_match(legacy_match.id, canonical_match.id)
        repeated = service.bind_scheduled_match(legacy_match.id, canonical_match.id)
        assert first.id == repeated.id
        assert service.canonical_match_for_legacy_match(legacy_match.id).id == canonical_match.id

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_scheduled_match(another_legacy_match.id, canonical_match.id)
        assert exc_info.value.code == "canonical_match_already_mapped"

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_scheduled_match(another_legacy_match.id, mismatched_match.id)
        assert exc_info.value.code == "fixture_club_identity_mismatch"

        # The mapping layer must not write score/event/history or settlement data.
        assert legacy_match.home_goals is None
        assert legacy_match.away_goals is None
        assert legacy_match.played_at is None
        assert canonical_match.home_score == 0
        assert canonical_match.away_score == 0
        assert canonical_match.completed_at is None
        assert session.scalar(
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.legacy_match_id == legacy_match.id
            )
        ).canonical_match_id == canonical_match.id
