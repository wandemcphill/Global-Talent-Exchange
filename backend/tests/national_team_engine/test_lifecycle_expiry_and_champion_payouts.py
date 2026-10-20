from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_admin, get_current_user, get_session
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
from app.models.notification_record import NotificationRecord
from app.models.player_contract import PlayerContract
from app.models.reward_settlement import RewardSettlement
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.national_team_engine.competition_lifecycle_service import (
    NATIONAL_CHAMPION_REWARD_SOURCE,
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.router import admin_router, national_router, router
from app.national_team_engine.schemas import NationalTeamCompetitionEntrySubmitRequest
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.national_team_engine.worker import NationalTeamLifecycleScheduler
from app.wallets.service import LedgerPosting, WalletService


def _build_session_factory(database_path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    return SessionLocal


def _create_user(
    session,
    prefix: str,
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
) -> User:
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"{prefix}_{uid}@gtex.test",
        username=f"{prefix}_{uid}",
        display_name=f"User {prefix}",
        full_name=f"User {prefix}",
        role=role,
        is_active=is_active,
        password_hash="mock_hash_1234567890",  # pragma: allowlist secret
    )
    session.add(user)
    session.flush()
    return user


def _fund_user(
    session,
    wallet_service: WalletService,
    user: User,
    amount: Decimal = Decimal("1000.0000"),
) -> None:
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform_account, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            LedgerPosting(account=user_account, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"test-funding:{user.id}:{uuid.uuid4().hex[:6]}",
        description="Test funding",
        actor=user,
    )


def _seed_country(
    session,
    *,
    name: str,
    alpha2: str,
    alpha3: str,
    fifa: str,
    confederation: str = "CAF",
) -> Country:
    country = Country(
        source_provider="test",
        provider_external_id=f"country-{alpha2.lower()}-{uuid.uuid4().hex[:6]}",
        name=name,
        alpha2_code=alpha2.upper(),
        alpha3_code=alpha3.upper(),
        fifa_code=fifa.upper(),
        confederation_code=confederation,
    )
    session.add(country)
    session.flush()
    return country


def _seed_club_and_player(
    session,
    *,
    owner: User,
    country: Country,
    club_name: str,
    player_name: str,
    position: str = "ST",
    gsi: int = 82,
) -> tuple[ClubProfile, Player, PlayerContract]:
    club = ClubProfile(
        owner_user_id=owner.id,
        club_name=club_name,
        short_name=club_name[:12],
        slug=f"{club_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        primary_color="#112233",
        secondary_color="#ddeeff",
        accent_color="#ffaa00",
        country_code=country.alpha2_code,
    )
    session.add(club)
    session.flush()

    player = Player(
        source_provider="test",
        provider_external_id=f"player-{uuid.uuid4().hex[:8]}",
        country_id=country.id,
        current_club_id=club.id,
        current_club_profile_id=club.id,
        real_world_club_name=club_name,
        full_name=player_name,
        canonical_display_name=player_name,
        position=position,
        normalized_position=position,
        date_of_birth=date(2000, 5, 14),
        is_tradable=True,
        is_real_player=False,
        market_value_eur=25_000_000.0,
        current_market_reference_value=25_000_000.0,
        dna_profile={"gsi": gsi, "regen_type": "club"},
    )
    session.add(player)
    session.flush()

    contract = PlayerContract(
        player_id=player.id,
        club_id=club.id,
        status="active",
        wage_amount=Decimal("250.00"),
        signed_on=date(2025, 1, 1),
        starts_on=date(2025, 1, 1),
        ends_on=date(2028, 12, 31),
    )
    session.add(contract)
    session.flush()
    return club, player, contract


def test_rental_expiry_boundary_future_start_and_owning_club_release(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "rental-boundary-release.db")
    wallet_service = WalletService()
    fixed_now = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        club_owner = _create_user(session, "club_owner")
        manager = _create_user(session, "national_manager")
        _fund_user(session, wallet_service, manager, Decimal("2000.0000"))

        nigeria = _seed_country(session, name="Nigeria", alpha2="NG", alpha3="NGA", fifa="NGA")
        club, boundary_player, boundary_player_contract = _seed_club_and_player(
            session,
            owner=club_owner,
            country=nigeria,
            club_name="Lagos Athletic FC",
            player_name="Victor Boundary",
            position="ST",
        )
        _, warning_player, _ = _seed_club_and_player(
            session,
            owner=club_owner,
            country=nigeria,
            club_name="Lagos Athletic FC",
            player_name="Kelechi Warning",
            position="CM",
        )
        _, future_player, _ = _seed_club_and_player(
            session,
            owner=club_owner,
            country=nigeria,
            club_name="Lagos Athletic FC",
            player_name="Samuel Future",
            position="GK",
        )

        competition = NationalTeamCompetition(
            key=f"boundary-cup-{uuid.uuid4().hex[:6]}",
            title="Boundary Nations Cup",
            season_label="2030",
            region_type="global",
            age_band="senior",
            format_type="cup",
            status="published",
            active=True,
            metadata_json={"minimum_squad_size": 1, "maximum_squad_size": 10},
            created_by_user_id=club_owner.id,
        )
        session.add(competition)
        session.flush()

        entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=manager.id,
            manager_user_id=manager.id,
        )
        session.add(entry)
        session.flush()

        tournament_service = NationalTeamTournamentService(session, wallet_service=wallet_service)
        for rented_player in (boundary_player, warning_player, future_player):
            tournament_service.rent_player(
                entry_id=entry.id,
                actor=manager,
                player_id=rented_player.id,
            )

        contracts_by_player = {
            item.player_id: item
            for item in session.scalars(select(RentalContract).where(RentalContract.entry_id == entry.id)).all()
        }
        assert len(contracts_by_player) == 3
        assert entry.squad_size == 3

        # Provenance recorded at rental time
        boundary_rental = contracts_by_player[boundary_player.id]
        assert boundary_rental.metadata_json["owning_club_id"] == club.id
        assert boundary_rental.metadata_json["owning_club_name"] == "Lagos Athletic FC"

        # 1) Exact expiry boundary: end_date == fixed_now
        boundary_rental.start_date = fixed_now - timedelta(days=2)
        boundary_rental.end_date = fixed_now
        # Simulate temporary rental lock on player & club contract while out on national duty
        boundary_player.current_club_id = None
        boundary_player.dna_profile = {
            **dict(boundary_player.dna_profile or {}),
            "national_rental_locked": True,
            "active_national_rental_contract_id": boundary_rental.id,
        }
        boundary_player_contract.status = "loan_locked"

        # 2) Expiring soon (within 24h warning window): start_date <= fixed_now < end_date <= fixed_now + 24h
        warning_rental = contracts_by_player[warning_player.id]
        warning_rental.start_date = fixed_now - timedelta(days=1)
        warning_rental.end_date = fixed_now + timedelta(hours=6)

        # 3) Future-start rental: start_date > fixed_now, even if end_date is within 24h
        future_rental = contracts_by_player[future_player.id]
        future_rental.start_date = fixed_now + timedelta(hours=4)
        future_rental.end_date = fixed_now + timedelta(hours=20)
        session.commit()

        # Squad submission at exact boundary must reject the boundary-expired player
        lifecycle_service = NationalCompetitionLifecycleService(session)
        with pytest.raises(NationalCompetitionLifecycleError) as exc_info:
            lifecycle_service.submit_entry(
                competition_id=competition.id,
                actor=manager,
                payload=NationalTeamCompetitionEntrySubmitRequest(
                    country_code="NG",
                    country_name="Nigeria",
                    squad=[
                        {
                            "player_id": boundary_player.id,
                            "player_name": boundary_player.full_name,
                            "overall_rating": 82,
                            "position": "ST",
                        }
                    ],
                ),
            )
        assert exc_info.value.reason == "player_not_rented"

    # Run cleanup in a brand-new session (simulating worker process / app restart with SQLite reload)
    with session_factory() as worker_session:
        worker_service = NationalTeamTournamentService(worker_session)
        cleanup_summary = worker_service.cleanup_expired_rentals(
            competition_id=competition.id,
            now=fixed_now,
        )
        worker_session.commit()

        assert cleanup_summary["released_contracts"] == 1
        assert cleanup_summary["released_player_ids"] == [boundary_player.id]
        assert cleanup_summary["expiring_notifications"] == 1
        assert cleanup_summary["affected_entries"] == [entry.id]

    # Verify DB state after cleanup and verify repeated worker execution is idempotent
    with session_factory() as verify_session:
        reloaded_boundary = verify_session.get(RentalContract, boundary_rental.id)
        reloaded_warning = verify_session.get(RentalContract, warning_rental.id)
        reloaded_future = verify_session.get(RentalContract, future_rental.id)
        reloaded_entry = verify_session.get(NationalTeamEntry, entry.id)
        reloaded_player = verify_session.get(Player, boundary_player.id)
        reloaded_club_contract = verify_session.get(PlayerContract, boundary_player_contract.id)

        assert reloaded_boundary is not None
        assert reloaded_boundary.status == RentalContractStatus.EXPIRED
        assert reloaded_boundary.metadata_json["player_released"] is True
        assert reloaded_boundary.metadata_json["release_reason"] == "rental_window_expired"
        assert reloaded_boundary.metadata_json["returned_to_club_id"] == club.id
        assert reloaded_boundary.metadata_json["returned_to_club_name"] == "Lagos Athletic FC"

        # Player returned to owning club and unlocked
        assert reloaded_player is not None
        assert reloaded_player.current_club_id == club.id
        assert reloaded_player.current_club_profile_id == club.id
        assert "national_rental_locked" not in (reloaded_player.dna_profile or {})
        assert reloaded_club_contract is not None
        assert reloaded_club_contract.status == "active"

        # Warning contract stayed active and notified once; future contract stayed untouched
        assert reloaded_warning is not None
        assert reloaded_warning.status == RentalContractStatus.ACTIVE
        assert reloaded_warning.metadata_json.get("expiring_notified_at") is not None
        assert reloaded_future is not None
        assert reloaded_future.status == RentalContractStatus.ACTIVE
        assert reloaded_future.metadata_json.get("expiring_notified_at") is None

        # Entry squad size updated from 3 -> 2
        assert reloaded_entry is not None
        assert reloaded_entry.squad_size == 2
        remaining_member_player_ids = set(
            verify_session.scalars(
                select(NationalTeamRentalSquadMember.player_id).where(
                    NationalTeamRentalSquadMember.entry_id == entry.id
                )
            ).all()
        )
        assert remaining_member_player_ids == {warning_player.id, future_player.id}

        # Re-running worker at the same timestamp produces zero duplicate writes or notifications
        second_summary = NationalTeamTournamentService(verify_session).cleanup_expired_rentals(
            competition_id=competition.id,
            now=fixed_now,
        )
        verify_session.commit()
        assert second_summary["released_contracts"] == 0
        assert second_summary["expiring_notifications"] == 0

        notification_count = int(
            verify_session.scalar(
                select(func.count(NotificationRecord.id)).where(
                    NotificationRecord.template_key == "RENTAL_EXPIRING",
                    NotificationRecord.competition_id == competition.id,
                )
            )
            or 0
        )
        assert notification_count == 1


def test_worker_scheduler_recovers_after_restart_and_cleans_orphan_squad_members(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "worker-restart-recovery.db")
    now = datetime.now(UTC)

    with session_factory() as session:
        owner = _create_user(session, "owner")
        manager = _create_user(session, "manager")
        ghana = _seed_country(session, name="Ghana", alpha2="GH", alpha3="GHA", fifa="GHA")
        _, player_one, _ = _seed_club_and_player(
            session,
            owner=owner,
            country=ghana,
            club_name="Accra Hearts",
            player_name="Thomas Recovery",
            position="CM",
        )
        _, player_two, _ = _seed_club_and_player(
            session,
            owner=owner,
            country=ghana,
            club_name="Accra Hearts",
            player_name="Mohammed Orphan",
            position="AM",
        )
        competition = NationalTeamCompetition(
            key=f"recovery-cup-{uuid.uuid4().hex[:6]}",
            title="Recovery Cup",
            season_label="2030",
            region_type="global",
            age_band="senior",
            format_type="cup",
            status="published",
            active=True,
            created_by_user_id=owner.id,
        )
        session.add(competition)
        session.flush()

        entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="GH",
            country_name="Ghana",
            entry_owner_user_id=manager.id,
            manager_user_id=manager.id,
            squad_size=2,
        )
        session.add(entry)
        session.flush()

        # Contract 1: expired while app was down (still ACTIVE in DB)
        active_expired_contract = RentalContract(
            player_id=player_one.id,
            user_id=manager.id,
            tournament_id=competition.id,
            entry_id=entry.id,
            start_date=now - timedelta(days=3),
            end_date=now - timedelta(minutes=5),
            loan_price_coin=Decimal("25.0000"),
            status=RentalContractStatus.ACTIVE,
            metadata_json={"player_name": player_one.full_name},
        )
        # Contract 2: already marked EXPIRED before a simulated crash, but squad member remained
        crashed_contract = RentalContract(
            player_id=player_two.id,
            user_id=manager.id,
            tournament_id=competition.id,
            entry_id=entry.id,
            start_date=now - timedelta(days=4),
            end_date=now - timedelta(days=1),
            loan_price_coin=Decimal("25.0000"),
            status=RentalContractStatus.EXPIRED,
            metadata_json={"player_name": player_two.full_name},
        )
        session.add_all([active_expired_contract, crashed_contract])
        session.flush()

        session.add_all(
            [
                NationalTeamRentalSquadMember(
                    entry_id=entry.id,
                    rental_contract_id=active_expired_contract.id,
                    player_id=player_one.id,
                    player_name=player_one.full_name,
                    overall_rating=80,
                    shirt_number=8,
                    source_type="rental",
                    status="selected",
                ),
                NationalTeamRentalSquadMember(
                    entry_id=entry.id,
                    rental_contract_id=crashed_contract.id,
                    player_id=player_two.id,
                    player_name=player_two.full_name,
                    overall_rating=82,
                    shirt_number=10,
                    source_type="rental",
                    status="selected",
                ),
            ]
        )
        session.commit()

    scheduler = NationalTeamLifecycleScheduler(session_factory=session_factory, interval_seconds=60.0)
    first_run = scheduler.run_once()
    assert first_run["rental_cleanup"]["released_contracts"] == 1
    assert first_run["rental_cleanup"]["affected_entries"] == [entry.id]

    # Second run after recovery is a clean no-op
    second_run = scheduler.run_once()
    assert second_run["rental_cleanup"]["released_contracts"] == 0
    assert second_run["rental_cleanup"]["affected_entries"] == []

    with session_factory() as check_session:
        refreshed_entry = check_session.get(NationalTeamEntry, entry.id)
        assert refreshed_entry is not None
        assert refreshed_entry.squad_size == 0
        remaining_members = list(
            check_session.scalars(
                select(NationalTeamRentalSquadMember).where(NationalTeamRentalSquadMember.entry_id == entry.id)
            ).all()
        )
        assert remaining_members == []


def test_lifecycle_completion_releases_rentals_and_settles_champion_reward_idempotently(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "champion-payouts.db")
    wallet_service = WalletService()

    with session_factory() as session:
        admin = _create_user(session, "admin", role=UserRole.ADMIN)
        user_ng = _create_user(session, "ng_manager", role=UserRole.USER)
        user_gh = _create_user(session, "gh_manager", role=UserRole.USER)
        outsider = _create_user(session, "outsider", role=UserRole.USER)

        _fund_user(session, wallet_service, user_ng, Decimal("400.0000"))
        _fund_user(session, wallet_service, user_gh, Decimal("400.0000"))

        nigeria = _seed_country(session, name="Nigeria", alpha2="NG", alpha3="NGA", fifa="NGA")
        ghana = _seed_country(session, name="Ghana", alpha2="GH", alpha3="GHA", fifa="GHA")

        ng_club, ng_player, _ = _seed_club_and_player(
            session,
            owner=outsider,
            country=nigeria,
            club_name="Enyimba FC",
            player_name="Jay-Jay Star",
            position="AM",
            gsi=90,
        )
        gh_club, gh_player, _ = _seed_club_and_player(
            session,
            owner=outsider,
            country=ghana,
            club_name="Asante Kotoko",
            player_name="Abedi Star",
            position="AM",
            gsi=72,
        )

        competition = NationalTeamCompetition(
            key=f"afcon-payout-{uuid.uuid4().hex[:6]}",
            title="GTEX AFCON Finals",
            season_label="2030",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            active=True,
            metadata_json={
                "competition_family": "afcon",
                "minimum_squad_size": 1,
                "maximum_squad_size": 5,
                "champion_reward_coin": "500.0000",
                "auto_settle_champion_reward": False,
                "competition_engine": {
                    "tournament_slots": 2,
                    "group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "qualifier_group_size": 2,
                    "preferred_cycle_week": 1,
                },
            },
            created_by_user_id=admin.id,
        )
        session.add(competition)
        session.flush()

        ng_rental_entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=user_ng.id,
            manager_user_id=user_ng.id,
        )
        gh_rental_entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="GH",
            country_name="Ghana",
            entry_owner_user_id=user_gh.id,
            manager_user_id=user_gh.id,
        )
        session.add_all([ng_rental_entry, gh_rental_entry])
        session.flush()

        tournament_service = NationalTeamTournamentService(session, wallet_service=wallet_service)
        tournament_service.rent_player(entry_id=ng_rental_entry.id, actor=user_ng, player_id=ng_player.id)
        tournament_service.rent_player(entry_id=gh_rental_entry.id, actor=user_gh, player_id=gh_player.id)

        lifecycle_service = NationalCompetitionLifecycleService(session, wallet_service=wallet_service)
        lifecycle_service.submit_entry(
            competition_id=competition.id,
            actor=user_ng,
            payload=NationalTeamCompetitionEntrySubmitRequest(
                country_code="NG",
                country_name="Nigeria",
                squad=[
                    {
                        "player_id": ng_player.id,
                        "player_name": ng_player.full_name,
                        "overall_rating": 92,
                        "position": "AM",
                    }
                ],
            ),
        )
        lifecycle_service.submit_entry(
            competition_id=competition.id,
            actor=user_gh,
            payload=NationalTeamCompetitionEntrySubmitRequest(
                country_code="GH",
                country_name="Ghana",
                squad=[
                    {
                        "player_id": gh_player.id,
                        "player_name": gh_player.full_name,
                        "overall_rating": 72,
                        "position": "AM",
                    }
                ],
            ),
        )

        # Cannot settle before lifecycle is completed
        lifecycle_service.lock_entries(competition_id=competition.id)
        with pytest.raises(NationalCompetitionLifecycleError) as incomplete_exc:
            lifecycle_service.settle_champion_reward(competition_id=competition.id, actor=admin)
        assert incomplete_exc.value.reason == "lifecycle_not_completed"

        # Advance tournament to completion -> automatically releases active rentals
        completed = lifecycle_service.advance_lifecycle(competition_id=competition.id, actor=admin)
        assert completed["current_stage"] == "completed"
        assert completed["champion_entry_id"] is not None
        assert completed["rental_cleanup"] is not None
        assert completed["rental_cleanup"]["released_contracts"] == 2

        # Rentals are now RELEASED and returned to owning clubs
        active_rentals = list(
            session.scalars(
                select(RentalContract).where(
                    RentalContract.tournament_id == competition.id,
                    RentalContract.status == RentalContractStatus.ACTIVE,
                )
            ).all()
        )
        assert active_rentals == []
        released_contracts = list(
            session.scalars(select(RentalContract).where(RentalContract.tournament_id == competition.id)).all()
        )
        assert {item.metadata_json["returned_to_club_id"] for item in released_contracts} == {
            ng_club.id,
            gh_club.id,
        }

        # Non-admin user cannot trigger settlement
        with pytest.raises(NationalCompetitionLifecycleError) as forbidden_exc:
            lifecycle_service.settle_champion_reward(competition_id=competition.id, actor=user_ng)
        assert forbidden_exc.value.reason == "settlement_forbidden"

        # Read/preview calls must NEVER trigger a payout
        _ = lifecycle_service.get_lifecycle_payload(competition_id=competition.id)
        _ = tournament_service.build_competition_presentation_payload(competition_id=competition.id)
        _ = tournament_service.build_entry_detail_payload_for_actor(entry_id=ng_rental_entry.id, actor=user_ng)
        _ = tournament_service.build_rental_status_payload(entry_id=ng_rental_entry.id, actor=user_ng)
        assert (
            session.scalar(
                select(func.count(RewardSettlement.id)).where(
                    RewardSettlement.competition_key == f"national-competition:{competition.id}"
                )
            )
            == 0
        )

        champion_entry = session.get(NationalTeamCompetitionEntry, completed["champion_entry_id"])
        assert champion_entry is not None
        champion_user = session.get(User, champion_entry.user_id)
        assert champion_user is not None
        champion_account = wallet_service.get_user_account(session, champion_user, LedgerUnit.COIN)
        balance_before = wallet_service.get_balance(session, champion_account)

        # Admin settles champion reward
        first_settlement = lifecycle_service.settle_champion_reward(
            competition_id=competition.id,
            actor=admin,
        )
        session.commit()

        assert first_settlement["competition_id"] == competition.id
        assert first_settlement["champion_entry_id"] == champion_entry.id
        assert first_settlement["champion_user_id"] == champion_user.id
        assert first_settlement["reward_source"] == NATIONAL_CHAMPION_REWARD_SOURCE
        assert first_settlement["ledger_unit"] == LedgerUnit.COIN.value
        assert Decimal(str(first_settlement["gross_amount"])) == Decimal("400.0000")
        assert Decimal(str(first_settlement["net_amount"])) > Decimal("0.0000")
        assert first_settlement["ledger_transaction_id"] is not None

        balance_after_first = wallet_service.get_balance(session, champion_account)
        assert balance_after_first == balance_before + Decimal(str(first_settlement["net_amount"]))

        # Verify authoritative ledger entry semantics
        reward_ledger_entries = list(
            session.scalars(
                select(LedgerEntry).where(
                    LedgerEntry.transaction_id == first_settlement["ledger_transaction_id"],
                    LedgerEntry.account_id == champion_account.id,
                )
            ).all()
        )
        assert len(reward_ledger_entries) == 1
        assert reward_ledger_entries[0].unit == LedgerUnit.COIN
        assert reward_ledger_entries[0].reason == LedgerEntryReason.COMPETITION_REWARD
        assert reward_ledger_entries[0].source_tag == LedgerSourceTag.NATIONAL_COMPETITION_REWARD
        assert reward_ledger_entries[0].transaction_type == LedgerTransactionType.MATCH_REWARD

        # Duplicate / retry settlement attempt must be idempotent and never double-credit
        second_settlement = lifecycle_service.settle_champion_reward(
            competition_id=competition.id,
            actor=admin,
            gross_amount=Decimal("999.0000"),
        )
        session.commit()

        assert second_settlement["settlement_id"] == first_settlement["settlement_id"]
        assert second_settlement["ledger_transaction_id"] == first_settlement["ledger_transaction_id"]
        assert Decimal(str(second_settlement["gross_amount"])) == Decimal(str(first_settlement["gross_amount"]))
        assert wallet_service.get_balance(session, champion_account) == balance_after_first
        assert (
            session.scalar(
                select(func.count(RewardSettlement.id)).where(
                    RewardSettlement.competition_key == f"national-competition:{competition.id}"
                )
            )
            == 1
        )


def test_champion_eligibility_validation_and_router_authorization(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path / "champion-router-authz.db")

    with session_factory() as session:
        admin = _create_user(session, "admin", role=UserRole.ADMIN)
        user_one = _create_user(session, "user1", role=UserRole.USER)
        user_two = _create_user(session, "user2", role=UserRole.USER)

        _seed_country(session, name="Nigeria", alpha2="NG", alpha3="NGA", fifa="NGA")
        _seed_country(session, name="Ghana", alpha2="GH", alpha3="GHA", fifa="GHA")

        competition = NationalTeamCompetition(
            key=f"router-payout-{uuid.uuid4().hex[:6]}",
            title="Router Payout Cup",
            season_label="2031",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            active=True,
            metadata_json={
                "competition_family": "afcon",
                "minimum_squad_size": 1,
                "maximum_squad_size": 3,
                "champion_reward_coin": "300.0000",
                "auto_settle_champion_reward": False,
                "competition_engine": {
                    "tournament_slots": 2,
                    "group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "qualifier_group_size": 2,
                    "preferred_cycle_week": 1,
                },
            },
            created_by_user_id=admin.id,
        )
        session.add(competition)
        session.commit()

    auth_state: dict[str, User | None] = {"user": user_one, "is_admin": False}
    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_router)
    app.include_router(national_router)

    def override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user():
        if auth_state["user"] is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return auth_state["user"]

    def override_get_current_admin():
        user = override_get_current_user()
        if not auth_state["is_admin"]:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    with TestClient(app) as client:
        for actor, code, name, rating in (
            (user_one, "NG", "Nigeria", 88),
            (user_two, "GH", "Ghana", 74),
        ):
            auth_state["user"] = actor
            auth_state["is_admin"] = False
            resp = client.post(
                f"/national-team-engine/competitions/{competition.id}/entries",
                json={
                    "country_code": code,
                    "country_name": name,
                    "squad": [{"player_name": f"{name} Captain", "age": 24, "overall_rating": rating}],
                },
            )
            assert resp.status_code == 200, resp.text

        auth_state["user"] = admin
        auth_state["is_admin"] = True
        lock_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/entries/lock")
        assert lock_resp.status_code == 200, lock_resp.text

        advance_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/lifecycle/advance")
        assert advance_resp.status_code == 200, advance_resp.text
        champion_entry_id = advance_resp.json()["champion_entry_id"]
        assert champion_entry_id is not None

        # 1. Anonymous user cannot settle champion reward -> 401
        auth_state["user"] = None
        auth_state["is_admin"] = False
        anon_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/champion-reward/settle")
        assert anon_resp.status_code == 401, anon_resp.text

        # 2. Authenticated non-admin user cannot settle champion reward -> 403
        auth_state["user"] = user_one
        auth_state["is_admin"] = False
        user_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/champion-reward/settle")
        assert user_resp.status_code == 403, user_resp.text

        # 3. Read endpoints have zero payout side effects
        lifecycle_read = client.get(f"/national-team-engine/competitions/{competition.id}/lifecycle")
        assert lifecycle_read.status_code == 200
        assert lifecycle_read.json()["champion_reward_settlement"] is None
        presentation_read = client.get(f"/national-team-engine/competitions/{competition.id}/presentation")
        assert presentation_read.status_code == 200

        # 4. Tampered / non-eligible champion entry is rejected (409 champion_not_eligible)
        with session_factory() as tamper_session:
            champ_row = tamper_session.get(NationalTeamCompetitionEntry, champion_entry_id)
            assert champ_row is not None
            champ_row.status = "eliminated"
            tamper_session.commit()

        auth_state["user"] = admin
        auth_state["is_admin"] = True
        ineligible_resp = client.post(
            f"/admin/national-team-engine/competitions/{competition.id}/champion-reward/settle"
        )
        assert ineligible_resp.status_code == 409, ineligible_resp.text
        assert ineligible_resp.json()["detail"] == "champion_not_eligible"

        # Restore champion status and settle via admin endpoint
        with session_factory() as restore_session:
            champ_row = restore_session.get(NationalTeamCompetitionEntry, champion_entry_id)
            assert champ_row is not None
            champ_row.status = "champion"
            restore_session.commit()

        settle_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/champion-reward/settle")
        assert settle_resp.status_code == 200, settle_resp.text
        settled_body = settle_resp.json()
        assert settled_body["champion_entry_id"] == champion_entry_id
        assert Decimal(str(settled_body["gross_amount"])) == Decimal("300.0000")

        # Calling the admin endpoint a second time is idempotent
        repeat_resp = client.post(f"/admin/national-team-engine/competitions/{competition.id}/champion-reward/settle")
        assert repeat_resp.status_code == 200, repeat_resp.text
        assert repeat_resp.json()["settlement_id"] == settled_body["settlement_id"]
        assert repeat_resp.json()["ledger_transaction_id"] == settled_body["ledger_transaction_id"]

        # Lifecycle read now reflects the completed settlement without re-settling
        lifecycle_after = client.get(f"/national-team-engine/competitions/{competition.id}/lifecycle")
        assert lifecycle_after.status_code == 200
        assert lifecycle_after.json()["champion_reward_settlement"]["settlement_id"] == settled_body["settlement_id"]
