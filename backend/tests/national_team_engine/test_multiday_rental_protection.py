from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.ingestion.models import Country, Player
from app.models import Base
from app.models.club_profile import ClubProfile
from app.models.national_team import (
    NationalTeamCompetition,
    NationalTeamCompetitionEntry,
    NationalTeamEntry,
)
from app.models.national_team_tournament import (
    NationalTeamRentalSquadMember,
    RentalContract,
    RentalContractStatus,
)
from app.models.player_contract import PlayerContract
from app.models.user import User, UserRole
from app.national_team_engine.tournament_service import (
    DEFAULT_RENTAL_DURATION_DAYS,
    NationalTeamTournamentService,
)
from app.wallets.service import WalletService


def _build_session_factory(database_path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    return SessionLocal


def test_multiday_tournament_protects_active_squad_from_deletion(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "multiday-rental.db")
    wallet_service = WalletService()
    t0 = datetime(2030, 7, 1, 10, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        # Create user & club
        owner = User(
            id=str(uuid.uuid4()),
            email="owner@gtex.test",
            username="owner_user",
            display_name="Owner User",
            full_name="Owner User",
            role=UserRole.USER,
            is_active=True,
            password_hash="pw_mock",
        )
        manager = User(
            id=str(uuid.uuid4()),
            email="manager@gtex.test",
            username="manager_user",
            display_name="Manager User",
            full_name="Manager User",
            role=UserRole.USER,
            is_active=True,
            password_hash="pw_mock",
        )
        session.add_all([owner, manager])
        session.flush()

        nigeria = Country(
            id=str(uuid.uuid4()),
            source_provider="test",
            provider_external_id=f"country-ng-{uuid.uuid4().hex[:6]}",
            name="Nigeria",
            alpha2_code="NG",
            alpha3_code="NGA",
            fifa_code="NGA",
        )
        session.add(nigeria)
        session.flush()

        club = ClubProfile(
            id=str(uuid.uuid4()),
            owner_user_id=owner.id,
            club_name="Super Stars FC",
            short_name="SSF",
            slug=f"super-stars-{uuid.uuid4().hex[:6]}",
            country_code=nigeria.alpha2_code,
            primary_color="#000000",
            secondary_color="#FFFFFF",
            accent_color="#FFD700",
        )
        session.add(club)
        session.flush()

        player = Player(
            id=str(uuid.uuid4()),
            source_provider="test",
            provider_external_id=f"player-{uuid.uuid4().hex[:8]}",
            first_name="Victor",
            last_name="Osimhen",
            full_name="Victor Osimhen",
            canonical_display_name="Victor Osimhen",
            short_name="Osimhen",
            position="ST",
            normalized_position="ST",
            date_of_birth=date(2000, 1, 1),
            country_id=nigeria.id,
            current_club_id=club.id,
            current_club_profile_id=club.id,
            real_world_club_name=club.club_name,
            is_tradable=True,
            is_real_player=False,
            market_value_eur=50_000_000.0,
            current_market_reference_value=50_000_000.0,
            dna_profile={"gsi": 88, "regen_type": "national"},
        )
        session.add(player)
        session.flush()

        player_contract = PlayerContract(
            id=str(uuid.uuid4()),
            player_id=player.id,
            club_id=club.id,
            signed_on=t0.date(),
            starts_on=t0.date(),
            ends_on=(t0 + timedelta(days=365)).date(),
            wage_amount=Decimal("5000.0000"),
            status="active",
        )
        session.add(player_contract)
        session.flush()

        # Multi-day competition scheduled for 5 days
        competition = NationalTeamCompetition(
            key=f"world-cup-stage-{uuid.uuid4().hex[:6]}",
            title="GTEX Nations Championship",
            season_label="2030",
            region_type="global",
            age_band="senior",
            format_type="cup",
            status="live",
            active=True,
            metadata_json={
                "scheduled_end_at": (t0 + timedelta(days=5)).isoformat(),
                "minimum_squad_size": 1,
                "maximum_squad_size": 23,
            },
            created_by_user_id=owner.id,
        )
        session.add(competition)
        session.flush()

        # Preliminary NationalTeamEntry
        prelim_entry = NationalTeamEntry(
            id=str(uuid.uuid4()),
            competition_id=competition.id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=manager.id,
            manager_user_id=manager.id,
        )
        session.add(prelim_entry)
        session.flush()

        # Active submitted entry for manager
        comp_entry = NationalTeamCompetitionEntry(
            id=str(uuid.uuid4()),
            competition_id=competition.id,
            user_id=manager.id,
            country_code="NG",
            country_name="Nigeria",
            squad_json=[{"player_id": player.id, "position": "ST", "overall_rating": 88}],
            locked=True,
            qualified=True,
            status="qualified",
        )
        session.add(comp_entry)
        session.flush()

        # Rental contract initially for 48h
        rental = RentalContract(
            id=str(uuid.uuid4()),
            tournament_id=competition.id,
            user_id=manager.id,
            player_id=player.id,
            entry_id=prelim_entry.id,
            start_date=t0,
            end_date=t0 + timedelta(days=DEFAULT_RENTAL_DURATION_DAYS),
            loan_price_coin=Decimal("50.0000"),
            status=RentalContractStatus.ACTIVE,
            metadata_json={
                "owning_club_id": club.id,
                "owning_club_name": club.club_name,
            },
        )
        session.add(rental)
        session.flush()

        squad_member = NationalTeamRentalSquadMember(
            id=str(uuid.uuid4()),
            entry_id=prelim_entry.id,
            rental_contract_id=rental.id,
            player_id=player.id,
            player_name=player.full_name,
            overall_rating=88,
            shirt_number=9,
            source_type="rental",
        )
        session.add(squad_member)
        session.commit()

        # Verify initial setup
        assert session.scalar(select(NationalTeamRentalSquadMember).where(NationalTeamRentalSquadMember.id == squad_member.id)) is not None

        # Day 3 (72 hours in): 48 hours have elapsed!
        # The competition is still live and ongoing.
        day_3_now = t0 + timedelta(days=3)
        service = NationalTeamTournamentService(session, wallet_service=wallet_service)
        cleanup_summary = service.cleanup_expired_rentals(competition_id=competition.id, now=day_3_now)
        session.commit()

        # CONTRACT MUST NOT BE RELEASED, AND SQUAD MEMBER MUST NOT BE DELETED!
        assert cleanup_summary["released_contracts"] == 0
        reloaded_member = session.scalar(select(NationalTeamRentalSquadMember).where(NationalTeamRentalSquadMember.id == squad_member.id))
        assert reloaded_member is not None, "Active tournament squad member was prematurely deleted!"

        reloaded_rental = session.get(RentalContract, rental.id)
        assert reloaded_rental.status == RentalContractStatus.ACTIVE
        # Contract end was extended to cover the tournament
        assert reloaded_rental.end_date >= day_3_now

        # Now simulate competition completion on Day 5
        day_5_now = t0 + timedelta(days=5)
        competition.status = "completed"
        competition.completed_at = day_5_now
        session.commit()

        # Run cleanup at completion
        completion_cleanup = service.cleanup_expired_rentals(competition_id=competition.id, now=day_5_now + timedelta(minutes=5))
        session.commit()

        # NOW contract should be released cleanly and member removed
        assert completion_cleanup["released_contracts"] == 1
        assert session.scalar(select(NationalTeamRentalSquadMember).where(NationalTeamRentalSquadMember.id == squad_member.id)) is None
        assert session.get(RentalContract, rental.id).status in (
            RentalContractStatus.RELEASED,
            RentalContractStatus.EXPIRED,
        )
