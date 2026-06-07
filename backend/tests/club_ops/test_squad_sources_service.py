from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.clubs.service import ClubQueryService
from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole
from app.services.club_squad_sources_service import (
    PLAYER_CONTRACT_SOURCE,
    PLAYER_MEDICAL_AVAILABILITY_SOURCE,
    TEAM_CHEMISTRY_SOURCE,
    TEAM_MORALE_SOURCE,
    ClubSquadSourcesService,
)


def test_squad_roster_omits_source_fields_until_records_are_seeded(gtex_db_session) -> None:
    session = gtex_db_session
    club_id = _seed_club(session, player_count=1)

    roster = ClubQueryService(session).get_squad_roster(club_id)

    assert roster.selection_ready_count == 0
    assert roster.players[0].availability == "unknown"
    assert roster.players[0].medical_source is None
    assert roster.players[0].morale is None
    assert roster.players[0].chemistry_fit is None
    assert roster.players[0].contract_status is None
    assert ClubQueryService(session).get_chemistry_report(club_id).overall_score is None
    assert ClubQueryService(session).get_contracts(club_id).contracts == []


def test_squad_sources_make_roster_authoritative_and_selection_ready(gtex_db_session) -> None:
    session = gtex_db_session
    club_id = _seed_club(session, player_count=11)
    _seed_complete_sources(session, club_id=club_id, player_count=11)

    roster = ClubQueryService(session).get_squad_roster(club_id)
    first = roster.players[0]

    assert roster.selection_ready_count == 11
    assert first.availability == "available"
    assert first.medical_source == PLAYER_MEDICAL_AVAILABILITY_SOURCE
    assert first.morale is not None
    assert first.morale.score == 78
    assert first.morale.source == TEAM_MORALE_SOURCE
    assert first.chemistry_fit is not None
    assert first.chemistry_fit.overall_score == 82
    assert first.chemistry_fit.source == TEAM_CHEMISTRY_SOURCE
    assert first.contract_status is not None
    assert first.contract_status.status == "active"
    assert first.contract_status.source == PLAYER_CONTRACT_SOURCE
    assert ClubQueryService(session).get_chemistry_report(club_id).overall_score == 82
    assert len(ClubQueryService(session).get_contracts(club_id).contracts) == 11


def test_injury_and_missing_contract_block_selection_readiness(gtex_db_session) -> None:
    session = gtex_db_session
    club_id = _seed_club(session, player_count=11)
    _seed_complete_sources(session, club_id=club_id, player_count=10)
    service = ClubSquadSourcesService(session)
    service.upsert_medical_status(
        club_id=club_id,
        player_id="player-1",
        status="injured",
        detail="Hamstring",
        expected_return_at=date.today() + timedelta(days=21),
    )
    session.commit()

    roster = ClubQueryService(session).get_squad_roster(club_id)
    injured = next(player for player in roster.players if player.id == "player-1")
    missing_contract = next(player for player in roster.players if player.id == "player-11")

    assert injured.availability == "injured"
    assert injured.injury_detail is not None
    assert injured.selection_ready is False
    assert missing_contract.availability == "unknown"
    assert missing_contract.contract_status is None
    assert missing_contract.selection_ready is False
    assert roster.selection_ready_count == 9


def _seed_club(session: Session, *, player_count: int) -> str:
    owner = User(
        id="club-owner",
        email="club.owner@example.com",
        username="club-owner",
        display_name="Club Owner",
        password_hash="x",
        role=UserRole.USER,
    )
    club = ClubProfile(
        id="club-profile-squad-sources",
        owner_user_id=owner.id,
        club_name="Source FC",
        short_name="SFC",
        slug="source-fc",
        primary_color="#102030",
        secondary_color="#405060",
        accent_color="#d0e0f0",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    session.add_all([owner, club])
    for index in range(player_count):
        session.add(
            Player(
                id=f"player-{index + 1}",
                source_provider="club-squad-sources-test",
                provider_external_id=f"club-squad-sources-test-{index + 1}",
                full_name=f"Source Player {index + 1}",
                canonical_display_name=f"Source Player {index + 1}",
                position=_POSITIONS[index],
                normalized_position=_POSITIONS[index],
                current_club_profile_id=club.id,
            )
        )
    session.commit()
    return club.id


def _seed_complete_sources(session: Session, *, club_id: str, player_count: int) -> None:
    service = ClubSquadSourcesService(session)
    today = date.today()
    for index in range(player_count):
        player_id = f"player-{index + 1}"
        service.upsert_medical_status(club_id=club_id, player_id=player_id, status="cleared")
        service.upsert_player_sources(
            club_id=club_id,
            player_id=player_id,
            morale_score=78,
            morale_trend="stable",
            chemistry_overall_score=82,
            chemistry_position_fit=84,
            chemistry_team_fit=80,
            source_ref="test-seed",
        )
        service.upsert_contract(
            club_id=club_id,
            player_id=player_id,
            signed_on=today - timedelta(days=30),
            starts_on=today - timedelta(days=30),
            ends_on=today + timedelta(days=730),
            status="active",
        )
    session.commit()


_POSITIONS = (
    "goalkeeper",
    "defender",
    "defender",
    "defender",
    "defender",
    "midfielder",
    "midfielder",
    "midfielder",
    "forward",
    "forward",
    "forward",
)
