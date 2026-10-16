from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.clubs.ownership_cap import (
    MAX_OWNED_CLUBS,
    ClubOwnershipCapError,
    assert_can_acquire_club,
    count_owned_clubs,
)
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.ownership_groups.service import OwnershipGroupError, OwnershipGroupService


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal()


def _make_user(session, *, email: str, username: str) -> User:
    user = User(email=email, username=username, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _make_club(session, *, owner_user_id: str, name: str, slug: str) -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner_user_id,
        club_name=name,
        short_name=name[:4].upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=slug,
        primary_color="#0F766E",
        secondary_color="#F8FAFC",
        accent_color="#14B8A6",
    )
    session.add(club)
    session.flush()
    return club


def test_assert_can_acquire_club_blocks_at_three() -> None:
    engine, session = _session()
    try:
        user = _make_user(session, email="cap@example.com", username="cap-owner")
        for index in range(MAX_OWNED_CLUBS):
            _make_club(
                session,
                owner_user_id=user.id,
                name=f"Cap Club {index}",
                slug=f"cap-club-{index}",
            )
        session.commit()
        assert count_owned_clubs(session, user.id) == MAX_OWNED_CLUBS
        try:
            assert_can_acquire_club(session, user.id)
            raised = False
        except ClubOwnershipCapError as exc:
            raised = True
            assert exc.owned == MAX_OWNED_CLUBS
            assert exc.limit == MAX_OWNED_CLUBS
        assert raised
    finally:
        session.close()
        engine.dispose()


def test_ownership_group_rejects_fourth_club() -> None:
    engine, session = _session()
    try:
        user = _make_user(session, email="empire@example.com", username="empire-owner")
        clubs = [
            _make_club(
                session,
                owner_user_id=user.id,
                name=f"Empire Club {index}",
                slug=f"empire-club-{index}",
            )
            for index in range(4)
        ]
        session.commit()

        class _Payload:
            name = "Test Empire"
            club_ids = [clubs[0].id, clubs[1].id]
            budget_pool = Decimal("1000")
            philosophy = "control"
            shared_budget_enabled = True

        service = OwnershipGroupService(session)
        group = service.create_group(actor=user, payload=_Payload())
        service.add_club(actor=user, group_id=group.id, club_id=clubs[2].id)
        session.flush()
        assert len(list(group.clubs_json or [])) == 3

        try:
            service.add_club(actor=user, group_id=group.id, club_id=clubs[3].id)
            raised = False
        except OwnershipGroupError as exc:
            raised = True
            assert "3 clubs" in str(exc)
        assert raised
    finally:
        session.close()
        engine.dispose()
