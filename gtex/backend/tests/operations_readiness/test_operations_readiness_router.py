from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_session
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.ingestion.models import Player
from app.models.admin_rules import AdminBetaAccessGrant, AdminFeatureFlag, AdminFeatureFlagAuditLog
from app.models.base import Base, utcnow
from app.models.broadcast_rights import BroadcastAccessGrant, BroadcastRight, BroadcastRightsAuction, ViewSession
from app.models.clip_variant import ClipVariant
from app.models.club_growth import (
    AcademyGenerationRun,
    AcademyProfile,
    AcademyProspect,
    AcademyRegenContractOffer,
    AcademyTrainingPlan,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_lifecycle import (
    ClubEligibilityFlag,
    ClubLifecycleState,
    ClubOperatingStatus,
    ClubReadinessStatus,
    ClubSquadRegistration,
)
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_asset import ClubSponsorshipAsset
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.dispute import Dispute, DisputeStatus
from app.models.event_backbone import CompetitionQueueRecord, EventOutbox
from app.models.fan_prediction import FanPredictionFixture, FanPredictionFixtureStatus, FanPredictionSubmission
from app.models.fan_war import FanWarPoint, FanWarProfile, FanbaseRanking
from app.models.federation import Federation, FederationMembership, FederationProposal, FederationSanction
from app.models.moderation_report import ModerationPriority, ModerationReport, ModerationReportStatus
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.policy import CountryFeaturePolicy, PolicyAcceptanceRecord, PolicyDocument, PolicyDocumentVersion
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardTier
from app.models.risk_ops import (
    AmlCase,
    AuditLog,
    FraudCase,
    RiskAction,
    RiskActionStatus,
    RiskActionType,
    RiskCaseStatus,
    RiskSeverity,
    RiskSignal,
    RiskSignalType,
    SystemEvent,
    SystemEventSeverity,
)
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket
from app.models.user import KycStatus, User, UserRole
from app.models.user_wallet import UserWallet, WalletTransactionRecord
from app.operations_readiness.router import router as operations_readiness_router


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
            AdminFeatureFlag.__table__,
            AdminFeatureFlagAuditLog.__table__,
            AdminBetaAccessGrant.__table__,
            AmlCase.__table__,
            FraudCase.__table__,
            RiskSignal.__table__,
            RiskAction.__table__,
            SystemEvent.__table__,
            AuditLog.__table__,
            ModerationReport.__table__,
            Dispute.__table__,
            PolicyDocument.__table__,
            PolicyDocumentVersion.__table__,
            PolicyAcceptanceRecord.__table__,
            CountryFeaturePolicy.__table__,
            EventOutbox.__table__,
            CompetitionQueueRecord.__table__,
            UserWallet.__table__,
            WalletTransactionRecord.__table__,
            ClubProfile.__table__,
            ClubLifecycleState.__table__,
            ClubReadinessStatus.__table__,
            ClubSquadRegistration.__table__,
            ClubEligibilityFlag.__table__,
            ClubOperatingStatus.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            AcademyProfile.__table__,
            AcademyProspect.__table__,
            AcademyTrainingPlan.__table__,
            AcademyRegenContractOffer.__table__,
            AcademyGenerationRun.__table__,
            ClubSponsorshipPackage.__table__,
            ClubSponsorshipContract.__table__,
            ClubSponsorshipAsset.__table__,
            ClubSponsorshipPayout.__table__,
            UserCompetition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            Federation.__table__,
            FederationMembership.__table__,
            FederationProposal.__table__,
            FederationSanction.__table__,
            FanPredictionFixture.__table__,
            FanPredictionSubmission.__table__,
            FanWarProfile.__table__,
            FanWarPoint.__table__,
            FanbaseRanking.__table__,
            BroadcastRight.__table__,
            BroadcastRightsAuction.__table__,
            BroadcastAccessGrant.__table__,
            ViewSession.__table__,
            ClipVariant.__table__,
            SponsoredClip.__table__,
            Player.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerCardListing.__table__,
            StadiumEvent.__table__,
            StadiumTicket.__table__,
            NotificationPreference.__table__,
            NotificationRecord.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        _seed(db_session)
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(operations_readiness_router, prefix="/api")

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_admin() -> User:
        user = session.get(User, "user-admin")
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = override_current_admin
    with TestClient(app) as test_client:
        yield test_client


def test_operations_readiness_requires_admin(session: Session) -> None:
    app = FastAPI()
    app.include_router(operations_readiness_router, prefix="/api")

    def override_session() -> Iterator[Session]:
        yield session

    def deny_admin() -> None:
        raise HTTPException(status_code=403, detail="admin required")

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = deny_admin
    with TestClient(app) as test_client:
        response = test_client.get("/api/admin/operations-readiness")

    assert response.status_code == 403


def test_operations_readiness_combines_ops_queues(client: TestClient) -> None:
    response = client.get("/api/admin/operations-readiness")

    assert response.status_code == 200, response.text
    payload = response.json()
    queues = {item["key"]: item for item in payload["queues"]}
    assert payload["status"] == "blocked"
    assert set(queues) == {
        "risk_compliance",
        "moderation_disputes",
        "policy_launch_control",
        "infrastructure_payment_rails",
        "production_data_diagnostics",
        "ledger_worker_health",
    }
    assert _metric(queues["risk_compliance"], "pending_kyc") == 1
    assert _metric(queues["risk_compliance"], "open_fraud_cases") == 1
    assert queues["risk_compliance"]["status"] == "blocked"
    assert _metric(queues["moderation_disputes"], "critical_reports") == 1
    assert _metric(queues["moderation_disputes"], "open_disputes") == 1
    assert _metric(queues["policy_launch_control"], "kill_switches") == 1
    assert _metric(queues["infrastructure_payment_rails"], "worker_broker_configured") == 0
    assert _metric(queues["infrastructure_payment_rails"], "pending_outbox_events") == 1
    assert _metric(queues["infrastructure_payment_rails"], "dead_outbox_events") == 1
    assert _metric(queues["infrastructure_payment_rails"], "failed_jobs") == 1
    assert _metric(queues["infrastructure_payment_rails"], "payment_provider_stubbed_count") >= 1
    assert _metric(queues["production_data_diagnostics"], "academy_prospects") == 1
    assert _metric(queues["production_data_diagnostics"], "club_lifecycles") == 1
    assert _metric(queues["production_data_diagnostics"], "club_readiness") == 1
    assert _metric(queues["production_data_diagnostics"], "squad_registrations") == 1
    assert _metric(queues["production_data_diagnostics"], "locked_squad_registrations") == 1
    assert _metric(queues["production_data_diagnostics"], "blocked_eligibility_flags") == 1
    assert _metric(queues["production_data_diagnostics"], "club_operating_statuses") == 1
    assert _metric(queues["production_data_diagnostics"], "staff_profiles") == 1
    assert _metric(queues["production_data_diagnostics"], "active_staff_contracts") == 1
    assert _metric(queues["production_data_diagnostics"], "active_staff_assignments") == 1
    assert _metric(queues["production_data_diagnostics"], "academy_profiles") == 1
    assert _metric(queues["production_data_diagnostics"], "active_academy_training_plans") == 1
    assert _metric(queues["production_data_diagnostics"], "academy_contract_offers") == 1
    assert _metric(queues["production_data_diagnostics"], "academy_generation_runs") == 1
    assert _metric(queues["production_data_diagnostics"], "sponsorship_packages") == 1
    assert _metric(queues["production_data_diagnostics"], "active_sponsorship_packages") == 1
    assert _metric(queues["production_data_diagnostics"], "active_sponsorship_contracts") == 1
    assert _metric(queues["production_data_diagnostics"], "visible_sponsorship_assets") == 1
    assert _metric(queues["production_data_diagnostics"], "pending_sponsorship_payouts") == 1
    assert _metric(queues["production_data_diagnostics"], "federations") == 1
    assert _metric(queues["production_data_diagnostics"], "federation_memberships") == 1
    assert _metric(queues["production_data_diagnostics"], "open_federation_proposals") == 1
    assert _metric(queues["production_data_diagnostics"], "federation_sanctions") == 1
    assert _metric(queues["production_data_diagnostics"], "fan_prediction_fixtures") == 1
    assert _metric(queues["production_data_diagnostics"], "fan_prediction_submissions") == 1
    assert _metric(queues["production_data_diagnostics"], "fan_war_profiles") == 1
    assert _metric(queues["production_data_diagnostics"], "fan_war_points") == 1
    assert _metric(queues["production_data_diagnostics"], "fanbase_rankings") == 1
    assert _metric(queues["production_data_diagnostics"], "broadcast_rights") == 1
    assert _metric(queues["production_data_diagnostics"], "broadcast_auctions") == 1
    assert _metric(queues["production_data_diagnostics"], "broadcast_access_grants") == 1
    assert _metric(queues["production_data_diagnostics"], "broadcast_view_sessions") == 1
    assert _metric(queues["production_data_diagnostics"], "clip_variants") == 1
    assert _metric(queues["production_data_diagnostics"], "winning_clip_variants") == 1
    assert _metric(queues["production_data_diagnostics"], "sponsored_clips") == 1
    assert _metric(queues["production_data_diagnostics"], "active_sponsored_clips") == 1
    assert _metric(queues["production_data_diagnostics"], "ticket_events") == 1
    assert _metric(queues["production_data_diagnostics"], "resale_tickets") == 1
    assert _metric(queues["production_data_diagnostics"], "player_cards") == 1
    assert _metric(queues["production_data_diagnostics"], "active_player_card_listings") == 1
    assert _metric(queues["production_data_diagnostics"], "notification_records") == 1
    assert _metric(queues["ledger_worker_health"], "dead_outbox_events") == 1
    gates = {item["feature_key"]: item for item in payload["launch_gates"]}
    assert gates["broadcast"]["kill_switch_enabled"] is True
    assert gates["broadcast"]["launch_state"] == "maintenance"
    assert gates["fan_coin"]["launch_state"] == "beta"


def test_operations_readiness_can_notify_admins_about_blockers(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post("/api/admin/operations-readiness/notify-blockers")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "sent"
    assert {
        "risk_compliance",
        "moderation_disputes",
        "policy_launch_control",
        "ledger_worker_health",
    }.issubset(set(payload["queue_keys"]))
    records = list(
        session.scalars(
            select(NotificationRecord).where(NotificationRecord.resource_type == "operations_readiness_blocked")
        ).all()
    )
    assert len(records) == payload["notifications_created"]
    assert any(record.resource_id == "risk_compliance" for record in records)
    assert all(record.user_id == "user-admin" for record in records)
    assert all(record.metadata_json["deep_link_route"] == "/admin/ops" for record in records)


def _metric(queue: dict[str, object], key: str) -> float:
    metrics = {item["key"]: item["value"] for item in queue["metrics"]}
    return metrics[key]


def _seed(session: Session) -> None:
    now = utcnow()
    today = date.today()
    session.add_all(
        [
            User(
                id="user-admin",
                email="admin@example.com",
                username="admin",
                display_name="Admin",
                password_hash="x",
                role=UserRole.ADMIN,
                kyc_status=KycStatus.FULLY_VERIFIED,
            ),
            User(
                id="user-review",
                email="review@example.com",
                username="review",
                display_name="Review User",
                password_hash="x",
                role=UserRole.USER,
                kyc_status=KycStatus.PENDING,
            ),
        ]
    )
    session.add_all(
        [
            ClubProfile(
                id="club-ops-home",
                owner_user_id="user-review",
                club_name="Ops Home FC",
                short_name="OHF",
                slug="ops-home",
                primary_color="#0B6E4F",
                secondary_color="#FFFFFF",
                accent_color="#F7C948",
                country_code="NG",
                city_name="Lagos",
            ),
            ClubProfile(
                id="club-ops-away",
                owner_user_id="user-review",
                club_name="Ops Away FC",
                short_name="OAF",
                slug="ops-away",
                primary_color="#155EEF",
                secondary_color="#FFFFFF",
                accent_color="#D92D20",
                country_code="NG",
                city_name="Abuja",
            ),
            ClubLifecycleState(
                id="club-lifecycle-ops",
                club_id="club-ops-home",
                state="competition_ready",
                previous_state="squad_ready",
                readiness_score=92,
                advanced_by_user_id="user-admin",
            ),
            ClubReadinessStatus(
                id="club-readiness-ops",
                club_id="club-ops-home",
                readiness_score=92,
                checklist_json={"wallet_funded": True, "squad_registered": True},
                blockers_json=[],
                recommended_state="competition_ready",
                competition_eligible=True,
            ),
            ClubSquadRegistration(
                id="club-squad-registration-ops",
                club_id="club-ops-home",
                season_label="launch",
                status="locked",
                player_ids_json=["player-diagnostics"],
                position_summary_json={"CM": 1},
                submitted_at=now - timedelta(hours=3),
                locked_at=now - timedelta(hours=2),
                locked_by_user_id="user-admin",
            ),
            ClubEligibilityFlag(
                id="club-eligibility-ops",
                club_id="club-ops-away",
                flag_key="squad_shortfall",
                status="blocked",
                detail="Away club still needs a registered goalkeeper.",
            ),
            ClubOperatingStatus(
                id="club-operating-ops",
                club_id="club-ops-home",
                operating_state="active",
                dashboard_json={"next_step": "enter_competition"},
            ),
            ClubStaffProfile(
                id="staff-profile-ops",
                market_key="agent-ops-elite",
                display_name="Adaeze Nwosu",
                staff_type="agent",
                rarity="elite",
                skills_json=["negotiation", "contract_handling"],
                salary_minor=12000,
                commission_bps=450,
                rating=88,
                active=True,
            ),
            ClubStaffContract(
                id="staff-contract-ops",
                club_id="club-ops-home",
                staff_profile_id="staff-profile-ops",
                status="active",
                salary_minor=12000,
                commission_bps=450,
                duration_days=180,
                role_scope="transfers",
                exclusive=True,
                started_at=now - timedelta(days=1),
                accepted_at=now - timedelta(days=1),
                ends_at=now + timedelta(days=179),
            ),
            ClubStaffAssignment(
                id="staff-assignment-ops",
                club_id="club-ops-home",
                staff_contract_id="staff-contract-ops",
                role_key="lead_agent",
                active=True,
            ),
            AcademyProfile(
                id="academy-profile-ops",
                club_id="club-ops-home",
                level=3,
                investment_minor=50000,
            ),
            AcademyProspect(
                id="academy-prospect-ops",
                club_id="club-ops-home",
                academy_profile_id="academy-profile-ops",
                display_name="Kelechi Okoro",
                nationality="NG",
                position="ST",
                age=16,
                current_ability=41,
                potential=82,
                portrait_asset_ref="newgen/ng/kelechi-okoro.png",
                status="contract_offered",
            ),
            AcademyTrainingPlan(
                id="academy-training-plan-ops",
                club_id="club-ops-home",
                focus="finishing",
                intensity="normal",
                active=True,
            ),
            AcademyRegenContractOffer(
                id="academy-contract-offer-ops",
                club_id="club-ops-home",
                prospect_id="academy-prospect-ops",
                status="offered",
                wage_minor=3000,
                duration_months=24,
            ),
            AcademyGenerationRun(
                id="academy-generation-run-ops",
                club_id="club-ops-home",
                run_seed="ops-seed-20260511",
                prospects_created=1,
                status="completed",
            ),
            ClubSponsorshipPackage(
                id="sponsorship-package-ops",
                code="front-shirt-ops",
                name="Front Shirt Sponsor",
                asset_type=SponsorshipAssetType.JERSEY_FRONT,
                base_amount_minor=100000,
                currency="CREDITS",
                default_duration_months=2,
                payout_schedule="monthly",
                description="Launch-ready front shirt sponsorship package.",
                is_active=True,
            ),
            ClubSponsorshipContract(
                id="sponsorship-contract-ops",
                club_id="club-ops-home",
                package_id="sponsorship-package-ops",
                asset_type=SponsorshipAssetType.JERSEY_FRONT,
                sponsor_name="Ops Sponsor Bank",
                status=SponsorshipStatus.ACTIVE,
                contract_amount_minor=100000,
                currency="CREDITS",
                duration_months=2,
                payout_schedule="monthly",
                start_at=now - timedelta(days=1),
                end_at=now + timedelta(days=59),
                moderation_required=False,
                moderation_status="approved",
                settled_amount_minor=25000,
                outstanding_amount_minor=75000,
            ),
            ClubSponsorshipAsset(
                id="sponsorship-asset-ops",
                club_id="club-ops-home",
                contract_id="sponsorship-contract-ops",
                asset_type=SponsorshipAssetType.JERSEY_FRONT,
                slot_code="shirt_front",
                is_visible=True,
                moderation_required=False,
                moderation_status="approved",
                rendered_text="Ops Sponsor Bank",
            ),
            ClubSponsorshipPayout(
                id="sponsorship-payout-ops",
                contract_id="sponsorship-contract-ops",
                due_at=now + timedelta(days=1),
                amount_minor=75000,
                status="pending",
            ),
            UserCompetition(
                id="competition-ops-final",
                host_user_id="user-admin",
                name="Operations Continental Final",
                description="Diagnostics competition for fan economy, broadcast, and governance readiness.",
                format="single_elimination",
                visibility="public",
                status="active",
                start_mode="scheduled",
                currency="CREDIT",
            ),
            CompetitionRound(
                id="round-ops-final",
                competition_id="competition-ops-final",
                round_number=1,
                stage="final",
                name="Final",
                status="scheduled",
            ),
            CompetitionMatch(
                id="match-ops-final",
                competition_id="competition-ops-final",
                round_id="round-ops-final",
                round_number=1,
                stage="final",
                home_club_id="club-ops-home",
                away_club_id="club-ops-away",
                scheduled_at=now + timedelta(hours=4),
                match_date=today,
                status="scheduled",
            ),
            Federation(
                id="federation-ops",
                name="Operations Federation",
                owner_user_id="user-admin",
                ranking_score=77.0,
                reputation_score=68.0,
                audience_size=42000,
                is_public=True,
                default_reality_mode="hybrid",
            ),
            FederationMembership(
                id="federation-membership-ops",
                federation_id="federation-ops",
                club_id="club-ops-home",
                user_id="user-review",
                status="active",
            ),
            FederationProposal(
                id="federation-proposal-ops",
                federation_id="federation-ops",
                proposer_user_id="user-review",
                title="Launch verified cup policy",
                summary="Require verified squads before continental finals.",
                status="open",
                voting_starts_at=now - timedelta(hours=2),
                voting_ends_at=now + timedelta(days=2),
            ),
            FederationSanction(
                id="federation-sanction-ops",
                federation_id="federation-ops",
                club_id="club-ops-away",
                applied_by_user_id="user-admin",
                sanction_type="fine",
                reason="Fixture rule violation.",
                fine_amount=Decimal("25.0000"),
                status="active",
            ),
            FanPredictionFixture(
                id="prediction-fixture-ops",
                match_id="match-ops-final",
                competition_id="competition-ops-final",
                home_club_id="club-ops-home",
                away_club_id="club-ops-away",
                created_by_user_id="user-admin",
                title="Ops final prediction",
                description="Prediction queue coverage for launch diagnostics.",
                status=FanPredictionFixtureStatus.OPEN,
                opens_at=now - timedelta(hours=1),
                locks_at=now + timedelta(hours=3),
                token_cost=1,
                promo_pool_fancoin=Decimal("30.0000"),
            ),
            FanPredictionSubmission(
                id="prediction-submission-ops",
                fixture_id="prediction-fixture-ops",
                user_id="user-review",
                leaderboard_week_start=today,
                winner_club_id="club-ops-home",
                first_goal_scorer_player_id="player-diagnostics",
                total_goals=2,
                mvp_player_id="player-diagnostics",
                tokens_spent=1,
            ),
            FanWarProfile(
                id="fan-war-ops",
                profile_type="club",
                entity_key="club:ops-home",
                display_name="Ops Home Supporters",
                slug="ops-home-supporters",
                club_id="club-ops-home",
                country_code="NG",
                country_name="Nigeria",
                tagline="Supporter energy coverage.",
                prestige_points=90,
            ),
            FanWarPoint(
                id="fan-war-point-ops",
                profile_id="fan-war-ops",
                actor_user_id="user-review",
                competition_id="competition-ops-final",
                source_type="prediction",
                source_ref="prediction-submission-ops",
                base_points=10,
                weighted_points=14,
                dedupe_key="prediction-submission-ops",
            ),
            FanbaseRanking(
                id="fanbase-ranking-ops",
                board_type="club",
                period_type="weekly",
                window_start=today,
                window_end=today + timedelta(days=7),
                profile_id="fan-war-ops",
                profile_type="club",
                rank=1,
                points_total=14,
                event_count=1,
                unique_supporters=1,
            ),
            BroadcastRight(
                id="broadcast-right-ops",
                competition_id="competition-ops-final",
                owner_id="user-review",
                acquisition_price=Decimal("100.0000"),
                revenue_share_percentage=Decimal("12.50"),
                exclusivity=True,
                start_date=today,
                end_date=today + timedelta(days=30),
            ),
            BroadcastRightsAuction(
                id="broadcast-auction-ops",
                competition_id="competition-ops-final",
                seller_owner_id="user-review",
                reserve_price=Decimal("75.0000"),
                revenue_share_percentage=Decimal("10.00"),
                exclusivity=False,
                start_date=today,
                end_date=today + timedelta(days=30),
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=1),
                status="open",
            ),
            BroadcastAccessGrant(
                id="broadcast-grant-ops",
                broadcast_right_id="broadcast-right-ops",
                user_id="user-review",
                granted_by_user_id="user-admin",
                expires_at=now + timedelta(days=30),
            ),
            ViewSession(
                id="view-session-ops",
                user_id="user-review",
                match_id="match-ops-final",
                competition_id="competition-ops-final",
                paid_amount=Decimal("3.0000"),
            ),
            ClipVariant(
                variant_id="clip-ops-vertical",
                base_clip_id="clip-ops",
                format_type="vertical",
                view_count=900,
                watch_time=1800.0,
                viral_score=82.0,
                promotion_status="trending",
                is_winner=True,
            ),
            SponsoredClip(
                id="sponsored-clip-ops",
                advertiser_id="brand-ops",
                clip_id="clip-ops",
                budget=Decimal("200.0000"),
                bid_cpm=Decimal("5.0000"),
                target_formats_json=["vertical"],
                target_regions_json=["NG"],
                impressions_served=500,
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(days=3),
                is_active=True,
            ),
        ]
    )
    session.add_all(
        [
            AdminFeatureFlag(
                feature_key="broadcast",
                title="Broadcast",
                enabled=True,
                audience="internal",
                launch_state="maintenance",
                kill_switch_enabled=True,
                maintenance_message="Rights worker review.",
                metadata_json={"route": "/broadcast"},
            ),
            AdminFeatureFlag(
                feature_key="fan_coin",
                title="Fan Coin",
                enabled=True,
                audience="beta",
                launch_state="beta",
                beta_only=True,
                metadata_json={"route": "/app/community"},
            ),
            AdminBetaAccessGrant(
                id="grant-1",
                feature_key="fan_coin",
                user_id="user-review",
                active=True,
                granted_by_user_id="user-admin",
            ),
            AdminFeatureFlagAuditLog(
                id="flag-audit-1",
                feature_key="broadcast",
                action="kill_switch_enabled",
                previous_json={"kill_switch_enabled": False},
                next_json={"kill_switch_enabled": True},
                actor_user_id="user-admin",
            ),
        ]
    )
    document = PolicyDocument(
        id="policy-1",
        document_key="terms",
        title="GTEX Terms",
        active=True,
        is_mandatory=True,
    )
    version = PolicyDocumentVersion(
        id="policy-version-1",
        policy_document_id=document.id,
        version_label="2026.05",
        body_markdown="Terms.",
        is_published=True,
    )
    session.add_all(
        [
            document,
            version,
            PolicyAcceptanceRecord(
                id="acceptance-1",
                user_id="user-review",
                policy_document_version_id=version.id,
            ),
            CountryFeaturePolicy(
                id="country-policy-1",
                country_code="NG",
                bucket_type="default",
                active=True,
            ),
        ]
    )
    session.add_all(
        [
            AmlCase(
                id="aml-1",
                user_id="user-review",
                case_key="aml-1",
                title="AML review",
                description="Review wallet pattern.",
                severity=RiskSeverity.MEDIUM,
                status=RiskCaseStatus.OPEN,
            ),
            FraudCase(
                id="fraud-1",
                user_id="user-review",
                case_key="fraud-1",
                fraud_type="gift_farming",
                title="Gift farming",
                description="Suspicious reward loop.",
                severity=RiskSeverity.HIGH,
                status=RiskCaseStatus.IN_REVIEW,
                confidence_score=Decimal("91.00"),
            ),
            RiskSignal(
                id="risk-signal-1",
                user_id="user-review",
                signal_type=RiskSignalType.TRANSACTION_PATTERN,
                signal_key="wallet_velocity",
                signal_value="high",
                source="test",
            ),
            RiskAction(
                id="risk-action-1",
                user_id="user-review",
                action_type=RiskActionType.BLOCK_WITHDRAWAL,
                status=RiskActionStatus.ACTIVE,
                reason="Manual review",
                created_by_user_id="user-admin",
            ),
            SystemEvent(
                id="system-event-1",
                event_key="critical-worker-event",
                event_type="worker",
                severity=SystemEventSeverity.CRITICAL,
                title="Worker paused",
                body="Queue worker paused.",
            ),
            AuditLog(
                id="audit-1",
                actor_user_id="user-admin",
                action_key="risk.review",
                resource_type="risk_case",
                resource_id="fraud-1",
                detail="Reviewed case.",
            ),
        ]
    )
    session.add_all(
        [
            ModerationReport(
                id="moderation-1",
                reporter_user_id="user-review",
                target_type="clip",
                target_id="clip-1",
                reason_code="rights",
                description="Clip rights issue.",
                status=ModerationReportStatus.OPEN,
                priority=ModerationPriority.CRITICAL,
            ),
            Dispute(
                id="dispute-1",
                user_id="user-review",
                admin_user_id="user-admin",
                resource_type="order",
                resource_id="order-1",
                reference="order-1",
                status=DisputeStatus.AWAITING_ADMIN,
                subject="Escrow check",
            ),
        ]
    )
    session.add_all(
        [
            UserWallet(
                id="wallet-1",
                user_id="user-review",
                balance=Decimal("100.00"),
                currency="credit",
                compliance_status="review",
            ),
            WalletTransactionRecord(
                id="wallet-tx-1",
                user_id="user-review",
                type="withdrawal",
                amount=Decimal("25.00"),
                status="pending",
                reference="wallet-tx-1",
            ),
            EventOutbox(
                id="outbox-1",
                event_id="event-1",
                event_type="wallet.pending",
                status="pending",
            ),
            EventOutbox(
                id="outbox-2",
                event_id="event-2",
                event_type="wallet.failed",
                status="dead_lettered",
            ),
            CompetitionQueueRecord(
                id="queue-1",
                queue_name="matchday",
                job_name="settlement",
                idempotency_key="settlement-1",
                status="failed",
                published_at=now,
            ),
            PlayerCardTier(
                id="tier-diagnostics",
                code="diagnostic",
                name="Diagnostic",
                rarity_rank=9,
                max_supply=100,
                supply_multiplier=Decimal("1.0000"),
                base_mint_price_credits=Decimal("1.0000"),
                is_active=True,
            ),
            PlayerCard(
                id="card-diagnostics",
                player_id="player-diagnostics",
                tier_id="tier-diagnostics",
                edition_code="ops",
                display_name="Diagnostics Midfielder Ops",
                supply_total=10,
                supply_available=5,
                is_active=True,
            ),
            PlayerCardListing(
                id="card-listing-diagnostics-row",
                listing_id="card-listing-diagnostics",
                player_card_id="card-diagnostics",
                seller_user_id="user-review",
                quantity=1,
                price_per_card_credits=Decimal("5.0000"),
                status="open",
                is_negotiable=False,
            ),
            StadiumEvent(
                id="stadium-event-diagnostics",
                stadium_id="stadium-diagnostics",
                match_id="match-diagnostics",
                title="Diagnostics Derby",
                venue_name="GTEX Ops Arena",
                event_type="league",
                event_status="on_sale",
                capacity=100,
                tier_distribution_json={"regular": 100},
                base_price_json={"regular": "5.0000"},
            ),
            StadiumTicket(
                id="ticket-diagnostics",
                event_id="stadium-event-diagnostics",
                user_id="user-review",
                match_id="match-diagnostics",
                seat_tier="regular",
                seat_code="REG-1",
                price=Decimal("5.0000"),
                original_price=Decimal("5.0000"),
                status="available",
                resale_listing_price=Decimal("6.0000"),
                listed_at=now,
            ),
            NotificationRecord(
                id="notification-diagnostics",
                user_id="user-review",
                topic="club",
                template_key="club.readiness.complete",
                resource_type="club_readiness_complete",
                resource_id="club-diagnostics",
                message="Club readiness is complete.",
            ),
        ]
    )
    session.commit()
