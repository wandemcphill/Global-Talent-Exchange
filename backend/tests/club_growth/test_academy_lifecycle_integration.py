from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.club_growth.router import router as club_growth_router
from app.club_growth.service import ClubGrowthService
from app.club_growth.schemas import (
    AcademyContractOfferRequest,
    AcademyContractResponseRequest,
    AcademyGenerateProspectsRequest,
)
from app.club_lifecycle.service import ClubLifecycleService
from app.ingestion.models import Player, PlayerImageMetadata, PlayerMatchStat, PlayerSeasonStat
from app.models.access_control import AccessAuditLog, Organization, OrganizationMembership
from app.models.base import Base, utcnow
from app.models.club_growth import (
    AcademyGenerationRun,
    AcademyProfile,
    AcademyPromotionHistory,
    AcademyProspect,
    AcademyRegenContractOffer,
    AcademyTrainingPlan,
    ClubGrowthAuditEvent,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffPerformanceLog,
    ClubStaffProfile,
)
from app.models.club_infra import ClubFacility, ClubStadium
from app.models.club_lifecycle import ClubLifecycleState, ClubSquadRegistration
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_asset import ClubSponsorshipAsset
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.club_squad_tier import ClubSquadTierMembership
from app.models.player_contract import PlayerContract
from app.models.player_injury_case import PlayerInjuryCase
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_token_market import PlayerShareMarket
from app.models.sponsorship_engine import SponsorshipLead
from app.models.transfer_bid import TransferBid
from app.models.user import KycStatus, User, UserRole
from app.services.player_lifecycle_service import PlayerLifecycleService
from app.squad_tiers.router import router as squad_tiers_router
from app.squad_tiers.service import SquadTierService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            ClubFacility.__table__,
            ClubStadium.__table__,
            Organization.__table__,
            OrganizationMembership.__table__,
            AccessAuditLog.__table__,
            Player.__table__,
            PlayerImageMetadata.__table__,
            PlayerMatchStat.__table__,
            PlayerSeasonStat.__table__,
            PlayerShareMarket.__table__,
            PlayerContract.__table__,
            ClubSquadTierMembership.__table__,
            ClubSquadRegistration.__table__,
            ClubLifecycleState.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            ClubStaffPerformanceLog.__table__,
            AcademyProfile.__table__,
            AcademyProspect.__table__,
            AcademyTrainingPlan.__table__,
            AcademyRegenContractOffer.__table__,
            AcademyPromotionHistory.__table__,
            AcademyGenerationRun.__table__,
            ClubGrowthAuditEvent.__table__,
            ClubSponsorshipPackage.__table__,
            ClubSponsorshipContract.__table__,
            ClubSponsorshipAsset.__table__,
            ClubSponsorshipPayout.__table__,
            SponsorshipLead.__table__,
            PlayerInjuryCase.__table__,
            PlayerLifecycleEvent.__table__,
            TransferBid.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-owner-1",
                    email="owner1@example.com",
                    username="owner1",
                    display_name="Owner 1",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-owner-2",
                    email="owner2@example.com",
                    username="owner2",
                    display_name="Owner 2",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-unauthorized",
                    email="unauthorized@example.com",
                    username="unauth",
                    display_name="Unauthorized",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
            ]
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(club_growth_router, prefix="/api")
    app.include_router(squad_tiers_router, prefix="/api")
    app.state.current_user_id = "user-owner-1"

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_user() -> User:
        user = session.get(User, app.state.current_user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as test_client:
        yield test_client


def _create_club(session: Session, *, club_id: str, owner_id: str, name: str) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner_id,
        club_name=name,
        short_name=name[:3].upper(),
        slug=f"{name.lower().replace(' ', '-')}-fc",
        primary_color="#112233",
        secondary_color="#FFFFFF",
        accent_color="#FFD700",
        home_venue_name=f"{name} Arena",
        country_code="NG",
    )
    session.add(club)
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_id)
    session.commit()
    return club


def test_e2e_academy_lifecycle_intake_to_selection_and_registration(client: TestClient, session: Session) -> None:
    club = _create_club(session, club_id="club-alpha", owner_id="user-owner-1", name="Alpha FC")
    owner = session.get(User, "user-owner-1")
    assert owner is not None

    # Step 1: Academy intake (prospect generation)
    gen_resp = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 2, "seed": "lifecycle-e2e-seed"},
    )
    assert gen_resp.status_code == 200, gen_resp.text
    prospects = gen_resp.json()
    assert len(prospects) == 2
    prospect_id = prospects[0]["id"]
    assert prospects[0]["status"] == "discovered"

    # Step 2: Contract offer
    offer_resp = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 1500, "duration_months": 24},
    )
    assert offer_resp.status_code == 200, offer_resp.text
    offer = offer_resp.json()
    assert offer["status"] == "offered"
    assert offer["wage_minor"] == 1500
    assert offer["duration_months"] == 24
    offer_id = offer["id"]

    # Verify prospect state is now contract_offered
    prospect_in_db = session.get(AcademyProspect, prospect_id)
    assert prospect_in_db is not None
    assert prospect_in_db.status == "contract_offered"

    # Step 3: Accepted youth contract
    accept_resp = client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offer_id}/respond",
        json={"accepted": True, "reason": "E2E accepted youth terms"},
    )
    assert accept_resp.status_code == 200, accept_resp.text
    assert accept_resp.json()["status"] == "accepted"

    session.refresh(prospect_in_db)
    assert prospect_in_db.status == "youth_signed"
    # Ensure age is at least 16 for promotion
    if prospect_in_db.age < 16:
        prospect_in_db.age = 16
        session.commit()

    # Step 4: Academy promotion
    promote_resp = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert promote_resp.status_code == 200, promote_resp.text
    promoted = promote_resp.json()
    assert promoted["status"] == "promoted_to_senior"
    senior_player_id = promoted["senior_player_id"]
    assert senior_player_id is not None

    # Step 5: Verify ONE canonical senior Player identity
    players = session.scalars(
        select(Player).where(
            Player.source_provider == "gtex_academy_regen",
            Player.provider_external_id == f"academy:{prospect_id}",
        )
    ).all()
    assert len(players) == 1
    player = players[0]
    assert player.id == senior_player_id
    assert player.current_club_profile_id == club.id
    assert player.is_real_player is False
    assert player.dna_profile["academyProspectId"] == prospect_id
    assert player.dna_profile["academyClubId"] == club.id

    # Step 6: Verify canonical active PlayerContract
    contracts = session.scalars(
        select(PlayerContract).where(
            PlayerContract.player_id == player.id,
            PlayerContract.club_id == club.id,
        )
    ).all()
    assert len(contracts) == 1
    contract = contracts[0]
    assert contract.status == "active"
    assert contract.wage_amount == Decimal("1500.00")
    assert contract.signed_on == utcnow().date()
    assert contract.starts_on == utcnow().date()
    assert contract.ends_on == utcnow().date() + timedelta(days=24 * 30)

    # Step 7: Verify canonical SquadTierService membership in reserve
    squad_memberships = session.scalars(
        select(ClubSquadTierMembership).where(
            ClubSquadTierMembership.player_id == player.id,
            ClubSquadTierMembership.club_id == club.id,
        )
    ).all()
    assert len(squad_memberships) == 1
    membership = squad_memberships[0]
    assert membership.status == "active"
    assert membership.tier == "reserve"
    assert membership.source == "academy"

    # Step 8: Verify downstream SquadTierService visibility
    squad_tiers_view = SquadTierService(session).list_squad(club.id)
    reserve_ids = [m.player_id for m in squad_tiers_view.reserve]
    assert player.id in reserve_ids

    academy_intake_view = SquadTierService(session).academy_intake(club.id)
    youth_ids = [m.player_id for m in academy_intake_view.youth]
    assert player.id in youth_ids

    # Step 9: Manager promotes youth player to first_team via SquadTierService
    assigned = SquadTierService(session).assign_tier(
        club_id=club.id,
        player_id=player.id,
        tier="first_team",
        actor_user_id=owner.id,
    )
    assert assigned.tier == "first_team"

    squad_tiers_updated = SquadTierService(session).list_squad(club.id)
    first_team_ids = [m.player_id for m in squad_tiers_updated.first_team]
    assert player.id in first_team_ids

    # Step 10: Verify match selection visibility via PlayerLifecycleService.list_club_squad_status
    lifecycle_service = PlayerLifecycleService(session)
    squad_records = lifecycle_service.list_club_squad_status(club.id)
    matching_records = [r for r in squad_records if r.player.id == player.id]
    assert len(matching_records) == 1
    record = matching_records[0]
    assert record.available is True
    assert record.contract.status == "active"
    assert record.contract.club_id == club.id

    # Step 11: Verify season squad registration visibility via ClubLifecycleService
    club_lifecycle = ClubLifecycleService(session)
    squad_players = club_lifecycle._squad_players(club.id)
    assert any(p.id == player.id for p in squad_players)


def test_academy_contract_rejection_and_reoffer_lifecycle(client: TestClient, session: Session) -> None:
    club = _create_club(session, club_id="club-beta", owner_id="user-owner-1", name="Beta FC")

    # Generate prospect
    gen_resp = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 1, "seed": "reject-test-seed"},
    )
    assert gen_resp.status_code == 200
    prospect_id = gen_resp.json()[0]["id"]

    # Offer low-wage contract
    offer_1 = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 200, "duration_months": 12},
    ).json()

    # Reject offer
    reject_resp = client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offer_1['id']}/respond",
        json={"accepted": False, "reason": "Salary is below market expectations"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    prospect = session.get(AcademyProspect, prospect_id)
    assert prospect is not None
    assert prospect.status == "contract_rejected"

    # Attempting to promote a rejected prospect must fail
    promote_blocked = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert promote_blocked.status_code == 409
    assert "prospect_not_promotable" in promote_blocked.json()["detail"]

    # Re-offer improved terms to the rejected prospect
    offer_2 = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 2500, "duration_months": 36},
    )
    assert offer_2.status_code == 200
    assert offer_2.json()["wage_minor"] == 2500

    # Accept the improved terms
    accept_2 = client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offer_2.json()['id']}/respond",
        json={"accepted": True, "reason": "Satisfied with improved contract terms"},
    )
    assert accept_2.status_code == 200
    assert accept_2.json()["status"] == "accepted"

    session.refresh(prospect)
    assert prospect.status == "youth_signed"
    if prospect.age < 16:
        prospect.age = 16
        session.commit()

    # Now promotion succeeds with the new accepted terms
    promote_ok = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert promote_ok.status_code == 200
    senior_player_id = promote_ok.json()["senior_player_id"]

    # Verify the created contract uses the accepted offer wage of 2500
    active_contract = session.scalar(
        select(PlayerContract).where(
            PlayerContract.player_id == senior_player_id,
            PlayerContract.club_id == club.id,
            PlayerContract.status == "active",
        )
    )
    assert active_contract is not None
    assert active_contract.wage_amount == Decimal("2500.00")


def test_academy_promotion_eligibility_enforced(client: TestClient, session: Session) -> None:
    club = _create_club(session, club_id="club-gamma", owner_id="user-owner-1", name="Gamma FC")

    # Generate prospect (status: discovered)
    gen = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 1, "seed": "eligibility-seed"},
    ).json()
    prospect_id = gen[0]["id"]

    # 1. Promote directly from discovered -> BLOCKED
    r1 = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert r1.status_code == 409
    assert "prospect_not_promotable" in r1.json()["detail"]

    # 2. Promote from contract_offered (pending) -> BLOCKED
    offer = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 1000, "duration_months": 24},
    ).json()
    r2 = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert r2.status_code == 409
    assert "prospect_not_promotable" in r2.json()["detail"]

    # Accept contract offer -> status: youth_signed
    client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offer['id']}/respond",
        json={"accepted": True, "reason": "OK"},
    )

    # 3. Underage prospect (< 16) -> BLOCKED
    prospect = session.get(AcademyProspect, prospect_id)
    assert prospect is not None
    prospect.age = 15
    session.commit()
    r3 = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert r3.status_code == 409
    assert "academy_player_too_young_to_promote" in r3.json()["detail"]

    # 4. Status is youth_signed, but accepted contract offer is deleted/missing -> BLOCKED
    prospect.age = 17
    # Delete the accepted offer to simulate corrupted / missing youth contract
    offer_db = session.get(AcademyRegenContractOffer, offer["id"])
    assert offer_db is not None
    session.delete(offer_db)
    session.commit()

    r4 = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert r4.status_code == 409
    assert "accepted_youth_contract_required" in r4.json()["detail"]


def test_academy_repeated_promotion_is_idempotent(client: TestClient, session: Session) -> None:
    club = _create_club(session, club_id="club-delta", owner_id="user-owner-1", name="Delta FC")

    gen = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 1, "seed": "idempotent-seed"},
    ).json()
    prospect_id = gen[0]["id"]
    prospect = session.get(AcademyProspect, prospect_id)
    assert prospect is not None
    prospect.age = 17
    session.commit()

    offer = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/offer-contract",
        json={"wage_minor": 1800, "duration_months": 24},
    ).json()
    client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/{offer['id']}/respond",
        json={"accepted": True, "reason": "Agreed"},
    )

    # First promotion
    first_resp = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert first_resp.status_code == 200
    first_data = first_resp.json()
    senior_player_id = first_data["senior_player_id"]
    assert senior_player_id is not None

    # Count initial rows
    player_count_1 = len(
        session.scalars(select(Player).where(Player.provider_external_id == f"academy:{prospect_id}")).all()
    )
    contract_count_1 = len(
        session.scalars(select(PlayerContract).where(PlayerContract.player_id == senior_player_id)).all()
    )
    squad_count_1 = len(
        session.scalars(
            select(ClubSquadTierMembership).where(ClubSquadTierMembership.player_id == senior_player_id)
        ).all()
    )
    history_count_1 = len(
        session.scalars(select(AcademyPromotionHistory).where(AcademyPromotionHistory.prospect_id == prospect_id)).all()
    )

    assert player_count_1 == 1
    assert contract_count_1 == 1
    assert squad_count_1 == 1
    assert history_count_1 == 1

    # Second promotion (exact repeated call)
    second_resp = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/{prospect_id}/promote")
    assert second_resp.status_code == 200
    second_data = second_resp.json()
    assert second_data["senior_player_id"] == senior_player_id

    # Third promotion (repeated call via service layer)
    owner = session.get(User, "user-owner-1")
    assert owner is not None
    service_result = ClubGrowthService(session).promote_prospect(
        actor=owner,
        club_id=club.id,
        prospect_id=prospect_id,
    )
    assert service_result.senior_player_id == senior_player_id

    # Verify NO duplicate rows created
    player_count_2 = len(
        session.scalars(select(Player).where(Player.provider_external_id == f"academy:{prospect_id}")).all()
    )
    contract_count_2 = len(
        session.scalars(select(PlayerContract).where(PlayerContract.player_id == senior_player_id)).all()
    )
    squad_count_2 = len(
        session.scalars(
            select(ClubSquadTierMembership).where(ClubSquadTierMembership.player_id == senior_player_id)
        ).all()
    )
    history_count_2 = len(
        session.scalars(select(AcademyPromotionHistory).where(AcademyPromotionHistory.prospect_id == prospect_id)).all()
    )

    assert player_count_2 == 1
    assert contract_count_2 == 1
    assert squad_count_2 == 1
    assert history_count_2 == 1


def test_academy_mismatched_club_and_contract_state_blocked(client: TestClient, session: Session) -> None:
    club_1 = _create_club(session, club_id="club-match-1", owner_id="user-owner-1", name="Match Club 1")
    club_2 = _create_club(session, club_id="club-match-2", owner_id="user-owner-2", name="Match Club 2")

    # Generate 3 prospects for Club 1
    gen = client.post(
        f"/api/clubs/{club_1.id}/growth/academy/generate-prospects",
        json={"count": 3, "seed": "mismatch-seed"},
    ).json()
    p1_id, p2_id, p3_id = gen[0]["id"], gen[1]["id"], gen[2]["id"]

    for pid in [p1_id, p2_id, p3_id]:
        p = session.get(AcademyProspect, pid)
        assert p is not None
        p.age = 18
        offer = client.post(
            f"/api/clubs/{club_1.id}/growth/academy/prospects/{pid}/offer-contract",
            json={"wage_minor": 1000, "duration_months": 24},
        ).json()
        client.post(
            f"/api/clubs/{club_1.id}/growth/academy/contracts/{offer['id']}/respond",
            json={"accepted": True, "reason": "Agreed"},
        )
    session.commit()

    # 1. Club 2 cannot promote Club 1's prospect
    client.app.state.current_user_id = "user-owner-2"
    cross_club_resp = client.post(f"/api/clubs/{club_2.id}/growth/academy/prospects/{p1_id}/promote")
    assert cross_club_resp.status_code == 404
    assert "academy_prospect_not_found" in cross_club_resp.json()["detail"]

    client.app.state.current_user_id = "user-owner-1"

    # 2. Player already exists with current_club_profile_id set to Club 2
    stolen_player = Player(
        id="player-stolen-by-club-2",
        source_provider="gtex_academy_regen",
        provider_external_id=f"academy:{p1_id}",
        current_club_profile_id=club_2.id,
        full_name="Stolen Player 1",
        short_name="Stolen1",
        position="ST",
        date_of_birth=date(2008, 1, 1),
    )
    session.add(stolen_player)
    session.commit()

    mismatch_player_resp = client.post(f"/api/clubs/{club_1.id}/growth/academy/prospects/{p1_id}/promote")
    assert mismatch_player_resp.status_code == 409
    assert "player_club_mismatch" in mismatch_player_resp.json()["detail"]

    # 3. Player has active PlayerContract belonging to Club 2
    competing_player = Player(
        id="player-contract-at-club-2",
        source_provider="gtex_academy_regen",
        provider_external_id=f"academy:{p2_id}",
        current_club_profile_id=club_1.id,
        full_name="Contract Conflict Player",
        short_name="Conflict2",
        position="CM",
        date_of_birth=date(2008, 1, 1),
    )
    competing_contract = PlayerContract(
        id="competing-contract-2",
        player_id=competing_player.id,
        club_id=club_2.id,
        status="active",
        wage_amount=Decimal("5000.00"),
        signed_on=date.today(),
        starts_on=date.today(),
        ends_on=date.today() + timedelta(days=365),
    )
    session.add_all([competing_player, competing_contract])
    session.commit()

    mismatch_contract_resp = client.post(f"/api/clubs/{club_1.id}/growth/academy/prospects/{p2_id}/promote")
    assert mismatch_contract_resp.status_code == 409
    assert "player_contract_club_mismatch" in mismatch_contract_resp.json()["detail"]

    # 4. Player has active squad tier membership belonging to Club 2
    squad_player = Player(
        id="player-squad-at-club-2",
        source_provider="gtex_academy_regen",
        provider_external_id=f"academy:{p3_id}",
        current_club_profile_id=club_1.id,
        full_name="Squad Conflict Player",
        short_name="Conflict3",
        position="CB",
        date_of_birth=date(2008, 1, 1),
    )
    competing_squad = ClubSquadTierMembership(
        id="competing-squad-3",
        player_id=squad_player.id,
        club_id=club_2.id,
        tier="reserve",
        source="academy",
        status="active",
        joined_club_at=utcnow(),
        joined_tier_at=utcnow(),
    )
    session.add_all([squad_player, competing_squad])
    session.commit()

    mismatch_squad_resp = client.post(f"/api/clubs/{club_1.id}/growth/academy/prospects/{p3_id}/promote")
    assert mismatch_squad_resp.status_code == 409
    assert "player_squad_club_mismatch" in mismatch_squad_resp.json()["detail"]


def test_academy_unauthorized_attempts_rejected_server_side(client: TestClient, session: Session) -> None:
    club = _create_club(session, club_id="club-auth-test", owner_id="user-owner-1", name="Auth FC")
    unauth_user = session.get(User, "user-unauthorized")
    assert unauth_user is not None

    # Authenticated as user-unauthorized (not owner of club-auth-test)
    client.app.state.current_user_id = "user-unauthorized"

    # 1. Unauthorized generate prospects
    r1 = client.post(
        f"/api/clubs/{club.id}/growth/academy/generate-prospects",
        json={"count": 1, "seed": "unauth-seed"},
    )
    assert r1.status_code == 403
    assert r1.json()["detail"] == "club_owner_required"

    # 2. Unauthorized offer contract
    r2 = client.post(
        f"/api/clubs/{club.id}/growth/academy/prospects/fake-prospect-id/offer-contract",
        json={"wage_minor": 1000, "duration_months": 24},
    )
    assert r2.status_code == 403
    assert r2.json()["detail"] == "club_owner_required"

    # 3. Unauthorized respond to contract
    r3 = client.post(
        f"/api/clubs/{club.id}/growth/academy/contracts/fake-offer-id/respond",
        json={"accepted": True, "reason": "Hack"},
    )
    assert r3.status_code == 403
    assert r3.json()["detail"] == "club_owner_required"

    # 4. Unauthorized promote prospect
    r4 = client.post(f"/api/clubs/{club.id}/growth/academy/prospects/fake-prospect-id/promote")
    assert r4.status_code == 403
    assert r4.json()["detail"] == "club_owner_required"

    # 5. Direct service-level invocation with unauthorized actor must raise PermissionError
    service = ClubGrowthService(session)
    with pytest.raises(PermissionError) as exc_info:
        service.generate_prospects(
            actor=unauth_user,
            club_id=club.id,
            payload=AcademyGenerateProspectsRequest(count=1),
        )
    assert "club_owner_required" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        service.offer_prospect_contract(
            actor=unauth_user,
            club_id=club.id,
            prospect_id="fake-prospect-id",
            payload=AcademyContractOfferRequest(wage_minor=1000, duration_months=24),
        )
    assert "club_owner_required" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        service.respond_to_prospect_contract(
            actor=unauth_user,
            club_id=club.id,
            offer_id="fake-offer-id",
            payload=AcademyContractResponseRequest(accepted=True),
        )
    assert "club_owner_required" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        service.promote_prospect(
            actor=unauth_user,
            club_id=club.id,
            prospect_id="fake-prospect-id",
        )
    assert "club_owner_required" in str(exc_info.value)
