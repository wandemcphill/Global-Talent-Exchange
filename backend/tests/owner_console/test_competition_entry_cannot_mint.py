"""Owner-hosted competitions are free to enter and cannot mint prize coin."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.owner_console import competitions as comps
from app.owner_console import ledger, service
from app.owner_console.models import LedgerEvent, OwnerCompetition, OwnerSquadPlayer
from app.owner_console.service import OwnerError

_FORBIDDEN_ENTRY_EVENTS = ("competition_entry_fee", "competition_entry_grant")


def _formed_club(session, owner_user_id: str, club_name: str) -> str:
    club = ClubProfile(
        owner_user_id=owner_user_id,
        club_name=club_name,
        short_name="TFC",
        slug=f"club-{uuid4().hex[:8]}",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        visibility="public",
        primary_color="#0F766E",
        secondary_color="#FFFFFF",
        accent_color="#EA580C",
        country_code="NG",
        continent_code="AF",
        city_name="Lagos",
    )
    session.add(club)
    session.flush()
    state = service.start_activation(session, owner_user_id, club.id)
    for index in range(service.MIN_SQUAD):
        session.add(
            OwnerSquadPlayer(
                club_id=club.id,
                player_ref=f"{club.id[:8]}-{index}",
                name=f"{club_name} {index}",
                position="goalkeeper" if index == 0 else "midfielder",
                status="active",
                rating=65,
                morale=70,
                potential=75,
                is_regen=True,
                personality_json={"squad_status": "first_team" if index < 11 else "reserve"},
            )
        )
    state.stage = "active"
    session.flush()
    assert service.get_club_formation_status(session, club.id)["is_formed"] is True
    return club.id


def _forbidden_entry_events(session, *club_ids: str, competition_id: str | None = None) -> list[LedgerEvent]:
    rows = session.scalars(select(LedgerEvent).where(LedgerEvent.event_type.in_(_FORBIDDEN_ENTRY_EVENTS))).all()
    club_id_set = set(club_ids)
    return [
        row
        for row in rows
        if row.club_id in club_id_set or (competition_id is not None and row.related_object_id == competition_id)
    ]


def test_hosting_with_entry_fee_stores_zero(app_session_factory, auth_user_factory) -> None:
    user = auth_user_factory(suffix=f"host-fee-{uuid4().hex[:8]}")
    with app_session_factory() as session:
        comp = comps.host_competition(
            session,
            user["user_id"],
            {
                "name": "Friday Night Derby",
                "format": "league",
                "entry_fee": 500,
                "max_clubs": 4,
                "allow_same_owner": True,
            },
        )
        assert comp.entry_fee == Decimal("0")
        assert comp.allow_same_owner is False
        assert comp.prize_sensitive is False
        assert comp.host_type == "user"
        assert comp.description == "One club per owner."

        comp.entry_fee = Decimal("500")
        comp.allow_same_owner = True
        session.flush()
        view = comps.comp_dict(session, comp, user["user_id"])
        assert view["entry_fee"] == "0"
        assert view["allow_same_owner"] is False
        session.rollback()


def test_entering_does_not_create_competition_entry_fee_or_grant(app_session_factory, auth_user_factory) -> None:
    user = auth_user_factory(suffix=f"enter-free-{uuid4().hex[:8]}")
    with app_session_factory() as session:
        club_id = _formed_club(session, user["user_id"], "Free Entry FC")
        hosted = comps.host_competition(
            session,
            user["user_id"],
            {"name": "Free Friends Cup", "entry_fee": 500, "allow_same_owner": True, "max_clubs": 4},
        )
        legacy = OwnerCompetition(
            name="Legacy Paid Cup",
            host_type="user",
            host_user_id=user["user_id"],
            format="league",
            tier="Friends",
            entry_fee=Decimal("500"),
            max_clubs=4,
            allow_same_owner=True,
            prize_sensitive=True,
            status="open",
        )
        session.add(legacy)
        session.flush()

        balance_before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        hosted_pot_before = ledger.balance(session, comps.comp_account(hosted.id), ledger.GTEX)
        legacy_pot_before = ledger.balance(session, comps.comp_account(legacy.id), ledger.GTEX)

        comps.enter_competition(session, user["user_id"], hosted.id, club_id)
        comps.enter_competition(session, user["user_id"], legacy.id, club_id)

        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == balance_before
        assert ledger.balance(session, comps.comp_account(hosted.id), ledger.GTEX) == hosted_pot_before
        assert ledger.balance(session, comps.comp_account(legacy.id), ledger.GTEX) == legacy_pot_before
        assert _forbidden_entry_events(session, club_id, competition_id=hosted.id) == []
        assert _forbidden_entry_events(session, club_id, competition_id=legacy.id) == []
        session.rollback()


def test_two_clubs_of_one_owner_are_rejected_even_if_allow_same_owner_requested(
    app_session_factory, auth_user_factory
) -> None:
    user = auth_user_factory(suffix=f"same-owner-{uuid4().hex[:8]}")
    with app_session_factory() as session:
        first_club_id = _formed_club(session, user["user_id"], "Sister One FC")
        second_club_id = _formed_club(session, user["user_id"], "Sister Two FC")
        comp = comps.host_competition(
            session,
            user["user_id"],
            {
                "name": "Common Ownership Cup",
                "entry_fee": 500,
                "allow_same_owner": True,
                "max_clubs": 4,
            },
        )
        assert comp.allow_same_owner is False
        comps.enter_competition(session, user["user_id"], comp.id, first_club_id)

        with pytest.raises(OwnerError) as requested:
            comps.enter_competition(session, user["user_id"], comp.id, second_club_id)
        assert requested.value.code == "same_owner_bracket_blocked"

        comp.allow_same_owner = True
        comp.entry_fee = Decimal("500")
        session.flush()
        with pytest.raises(OwnerError) as stored:
            comps.enter_competition(session, user["user_id"], comp.id, second_club_id)
        assert stored.value.code == "same_owner_bracket_blocked"
        assert _forbidden_entry_events(session, first_club_id, second_club_id, competition_id=comp.id) == []
        session.rollback()
