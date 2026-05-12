from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal
import os
from typing import Any

from sqlalchemy import Select, func, inspect, select
from sqlalchemy.orm import Session

from app.ingestion.models import Club, Competition, Player, PlayerImageMetadata
from app.models.admin_rules import AdminBetaAccessGrant, AdminFeatureFlag, AdminFeatureFlagAuditLog
from app.models.base import utcnow
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
from app.models.club_sponsorship_asset import ClubSponsorshipAsset
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.coin_trader import CoinTradeOrder, CoinTraderRate
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.dispute import Dispute, DisputeStatus
from app.models.event_backbone import CompetitionQueueRecord, EventOutbox
from app.models.fan_prediction import FanPredictionFixture, FanPredictionSubmission
from app.models.fan_war import FanWarPoint, FanWarProfile, FanbaseRanking
from app.models.federation import Federation, FederationMembership, FederationProposal, FederationSanction
from app.models.moderation_report import ModerationPriority, ModerationReport, ModerationReportStatus
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.policy import CountryFeaturePolicy, PolicyAcceptanceRecord, PolicyDocument, PolicyDocumentVersion
from app.models.player_cards import PlayerCard, PlayerCardListing
from app.models.real_world_hub import RealDataProvider, RealDataSyncJob, RealPlayer
from app.models.regen import RegenProfile, RegenVisualProfile
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.risk_ops import (
    AmlCase,
    AuditLog,
    FraudCase,
    RiskAction,
    RiskActionStatus,
    RiskCaseStatus,
    RiskSeverity,
    RiskSignal,
    SystemEvent,
    SystemEventSeverity,
)
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket
from app.models.transfer_market import TransferListing
from app.models.user import KycStatus, User, UserRole
from app.models.user_wallet import UserWallet, WalletTransactionRecord
from app.models.wallet import LedgerEntry
from app.notifications.service import NotificationEventMatrixService, NotificationServiceError
from app.operations_readiness.schemas import (
    OperationsLaunchGate,
    OperationsReadinessNotificationDispatch,
    OperationsReadinessMetric,
    OperationsReadinessQueue,
    OperationsReadinessSnapshot,
)


class OperationsReadinessService:
    """Builds a single admin snapshot without replacing existing GTEX engines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._inspector = inspect(session.get_bind())

    def snapshot(self) -> OperationsReadinessSnapshot:
        queues = [
            self._risk_compliance_queue(),
            self._moderation_disputes_queue(),
            self._policy_launch_queue(),
            self._data_diagnostics_queue(),
            self._ledger_worker_queue(),
        ]
        gates = self._launch_gates()
        status = self._overall_status(queues, gates)
        totals = {
            "queues": len(queues),
            "alerts": sum(len(queue.alerts) for queue in queues),
            "blocked_queues": sum(1 for queue in queues if queue.status == "blocked"),
            "attention_queues": sum(1 for queue in queues if queue.status == "attention"),
            "launch_gates": len(gates),
            "kill_switches": sum(1 for gate in gates if gate.kill_switch_enabled),
        }
        return OperationsReadinessSnapshot(
            generated_at=utcnow(),
            status=status,
            totals=totals,
            queues=queues,
            launch_gates=gates,
        )

    def notify_blockers(self, *, actor: User) -> OperationsReadinessNotificationDispatch:
        snapshot = self.snapshot()
        queues = [
            queue
            for queue in snapshot.queues
            if queue.status in {"blocked", "attention"} and queue.alerts
        ]
        if not queues or not self._notification_tables_available():
            return OperationsReadinessNotificationDispatch(
                status="skipped",
                notifications_created=0,
                queue_keys=[queue.key for queue in queues],
            )
        recipients = tuple(self._admin_user_ids() or [actor.id])
        service = NotificationEventMatrixService(self.session)
        created = 0
        queue_keys: list[str] = []
        for queue in queues:
            try:
                records = service.publish_event(
                    event_key="operations_readiness_blocked",
                    target_user_ids=recipients,
                    resource_id=queue.key,
                    message=self._notification_message(queue),
                    metadata_json={
                        "queue_key": queue.key,
                        "queue_title": queue.title,
                        "queue_status": queue.status,
                        "route": queue.route,
                        "owner": queue.owner,
                        "action_routes": queue.action_routes,
                        "alerts": queue.alerts,
                        "attention_metrics": [
                            {
                                "key": metric.key,
                                "value": metric.value,
                                "status": metric.status,
                            }
                            for metric in queue.metrics
                            if metric.status != "ok"
                        ][:8],
                        "triggered_by_admin_user_id": actor.id,
                    },
                )
            except NotificationServiceError:
                continue
            created += len(records)
            queue_keys.append(queue.key)
        return OperationsReadinessNotificationDispatch(
            status="sent" if created else "skipped",
            notifications_created=created,
            queue_keys=queue_keys,
        )

    def _risk_compliance_queue(self) -> OperationsReadinessQueue:
        pending_kyc = self._count(User, User.kyc_status == KycStatus.PENDING)
        rejected_kyc = self._count(User, User.kyc_status == KycStatus.REJECTED)
        open_aml = self._count(AmlCase, AmlCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))
        open_fraud = self._count(FraudCase, FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))
        high_fraud = self._count(
            FraudCase,
            FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]),
            FraudCase.severity.in_([RiskSeverity.HIGH, RiskSeverity.CRITICAL]),
        )
        active_actions = self._count(RiskAction, RiskAction.status == RiskActionStatus.ACTIVE)
        critical_events = self._count(SystemEvent, SystemEvent.severity == SystemEventSeverity.CRITICAL)
        risk_signals = self._count(RiskSignal)
        alerts: list[str] = []
        if high_fraud:
            alerts.append(f"{high_fraud} high-severity fraud case(s) require review.")
        if critical_events:
            alerts.append(f"{critical_events} critical system event(s) are open.")
        if active_actions:
            alerts.append(f"{active_actions} active user risk action(s) are in force.")
        status = "blocked" if critical_events else "attention" if alerts or pending_kyc or open_aml or open_fraud else "ok"
        return OperationsReadinessQueue(
            key="risk_compliance",
            title="Risk, KYC And Compliance",
            description="KYC review load, AML/fraud cases, risk actions, and system events.",
            status=status,
            route="/admin/risk-ops",
            owner="risk_ops_engine",
            action_routes=["/admin/risk-ops", "/admin/policies", "/admin/ops/audit"],
            alerts=alerts,
            metrics=[
                self._metric("pending_kyc", "Pending KYC", pending_kyc, status="attention" if pending_kyc else "ok"),
                self._metric("rejected_kyc", "Rejected KYC", rejected_kyc, status="attention" if rejected_kyc else "ok"),
                self._metric("open_aml_cases", "Open AML cases", open_aml, status="attention" if open_aml else "ok"),
                self._metric("open_fraud_cases", "Open fraud cases", open_fraud, status="attention" if open_fraud else "ok"),
                self._metric("active_risk_actions", "Active risk actions", active_actions, status="attention" if active_actions else "ok"),
                self._metric("risk_signals", "Risk signals", risk_signals),
            ],
        )

    def _moderation_disputes_queue(self) -> OperationsReadinessQueue:
        open_reports = self._count(
            ModerationReport,
            ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
        )
        critical_reports = self._count(
            ModerationReport,
            ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
            ModerationReport.priority == ModerationPriority.CRITICAL,
        )
        high_reports = self._count(
            ModerationReport,
            ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
            ModerationReport.priority == ModerationPriority.HIGH,
        )
        open_disputes = self._count(
            Dispute,
            Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.AWAITING_ADMIN, DisputeStatus.AWAITING_USER]),
        )
        awaiting_admin = self._count(Dispute, Dispute.status == DisputeStatus.AWAITING_ADMIN)
        alerts: list[str] = []
        if critical_reports:
            alerts.append(f"{critical_reports} critical moderation report(s) are waiting.")
        if awaiting_admin:
            alerts.append(f"{awaiting_admin} dispute(s) are waiting for admin response.")
        status = "blocked" if critical_reports else "attention" if open_reports or open_disputes else "ok"
        return OperationsReadinessQueue(
            key="moderation_disputes",
            title="Moderation And Disputes",
            description="Reports, escalations, wallet/order disputes, and support pressure.",
            status=status,
            route="/admin/moderation",
            owner="moderation_dispute_engine",
            action_routes=["/admin/moderation", "/admin/disputes"],
            alerts=alerts,
            metrics=[
                self._metric("open_reports", "Open reports", open_reports, status="attention" if open_reports else "ok"),
                self._metric("critical_reports", "Critical reports", critical_reports, status="blocked" if critical_reports else "ok"),
                self._metric("high_priority_reports", "High-priority reports", high_reports, status="attention" if high_reports else "ok"),
                self._metric("open_disputes", "Open disputes", open_disputes, status="attention" if open_disputes else "ok"),
                self._metric("awaiting_admin_disputes", "Awaiting admin", awaiting_admin, status="attention" if awaiting_admin else "ok"),
            ],
        )

    def _policy_launch_queue(self) -> OperationsReadinessQueue:
        active_documents = self._count(PolicyDocument, PolicyDocument.active.is_(True))
        published_versions = self._count(PolicyDocumentVersion, PolicyDocumentVersion.is_published.is_(True))
        acceptances = self._count(PolicyAcceptanceRecord)
        active_country_policies = self._count(CountryFeaturePolicy, CountryFeaturePolicy.active.is_(True))
        enabled_flags = self._count(AdminFeatureFlag, AdminFeatureFlag.enabled.is_(True))
        beta_flags = self._count(AdminFeatureFlag, AdminFeatureFlag.launch_state == "beta")
        maintenance_flags = self._count(AdminFeatureFlag, AdminFeatureFlag.launch_state == "maintenance")
        kill_switches = self._count(AdminFeatureFlag, AdminFeatureFlag.kill_switch_enabled.is_(True))
        active_beta_grants = self._count(AdminBetaAccessGrant, AdminBetaAccessGrant.active.is_(True))
        alerts: list[str] = []
        if kill_switches:
            alerts.append(f"{kill_switches} kill switch(es) are active.")
        if maintenance_flags:
            alerts.append(f"{maintenance_flags} module(s) are in maintenance.")
        status = "blocked" if kill_switches else "attention" if maintenance_flags else "ok"
        return OperationsReadinessQueue(
            key="policy_launch_control",
            title="Policy And Launch Control",
            description="Feature gates, country policy, beta access, policy versions, and rollout safety.",
            status=status,
            route="/admin/launch-control",
            owner="launch_control_policies",
            action_routes=["/admin/launch-control", "/admin/policies"],
            alerts=alerts,
            metrics=[
                self._metric("enabled_flags", "Enabled flags", enabled_flags),
                self._metric("beta_flags", "Beta flags", beta_flags, status="gated" if beta_flags else "ok"),
                self._metric("maintenance_flags", "Maintenance flags", maintenance_flags, status="attention" if maintenance_flags else "ok"),
                self._metric("kill_switches", "Kill switches", kill_switches, status="blocked" if kill_switches else "ok"),
                self._metric("active_policy_documents", "Active policy docs", active_documents),
                self._metric("published_policy_versions", "Published versions", published_versions),
                self._metric("policy_acceptances", "Policy acceptances", acceptances),
                self._metric("country_policies", "Country policies", active_country_policies),
                self._metric("active_beta_grants", "Beta grants", active_beta_grants, status="gated" if active_beta_grants else "ok"),
            ],
        )

    def _data_diagnostics_queue(self) -> OperationsReadinessQueue:
        players = self._count(Player)
        player_images = self._count(PlayerImageMetadata)
        real_players = self._count(RealPlayer)
        leagues = self._count(Competition)
        clubs = self._count(Club)
        regens = self._count(RegenProfile)
        regen_visuals = self._count(RegenVisualProfile)
        national_regen_seeds = self._count(NationalRegenSeed)
        academy_prospects = self._count(AcademyProspect)
        club_lifecycles = self._count(ClubLifecycleState)
        club_readiness = self._count(ClubReadinessStatus)
        squad_registrations = self._count(ClubSquadRegistration)
        locked_squad_registrations = self._count(ClubSquadRegistration, ClubSquadRegistration.locked_at.is_not(None))
        eligibility_flags = self._count(ClubEligibilityFlag)
        blocked_eligibility_flags = self._count(ClubEligibilityFlag, ClubEligibilityFlag.status != "clear")
        operating_statuses = self._count(ClubOperatingStatus)
        staff_profiles = self._count(ClubStaffProfile)
        active_staff_contracts = self._count(ClubStaffContract, ClubStaffContract.status == "active")
        active_staff_assignments = self._count(ClubStaffAssignment, ClubStaffAssignment.active.is_(True))
        academy_profiles = self._count(AcademyProfile)
        active_academy_training_plans = self._count(AcademyTrainingPlan, AcademyTrainingPlan.active.is_(True))
        academy_contract_offers = self._count(AcademyRegenContractOffer)
        academy_generation_runs = self._count(AcademyGenerationRun)
        sponsorship_packages = self._count(ClubSponsorshipPackage)
        active_sponsorship_packages = self._count(ClubSponsorshipPackage, ClubSponsorshipPackage.is_active.is_(True))
        active_sponsorship_contracts = self._count(ClubSponsorshipContract, ClubSponsorshipContract.status == "active")
        visible_sponsorship_assets = self._count(ClubSponsorshipAsset, ClubSponsorshipAsset.is_visible.is_(True))
        pending_sponsorship_payouts = self._count(ClubSponsorshipPayout, ClubSponsorshipPayout.status == "pending")
        federations = self._count(Federation)
        federation_memberships = self._count(FederationMembership)
        open_federation_proposals = self._count(FederationProposal, FederationProposal.status == "open")
        federation_sanctions = self._count(FederationSanction)
        fan_prediction_fixtures = self._count(FanPredictionFixture)
        fan_prediction_submissions = self._count(FanPredictionSubmission)
        fan_war_profiles = self._count(FanWarProfile)
        fan_war_points = self._count(FanWarPoint)
        fanbase_rankings = self._count(FanbaseRanking)
        broadcast_rights = self._count(BroadcastRight)
        broadcast_auctions = self._count(BroadcastRightsAuction)
        broadcast_access_grants = self._count(BroadcastAccessGrant)
        broadcast_view_sessions = self._count(ViewSession)
        clip_variants = self._count(ClipVariant)
        winning_clip_variants = self._count(ClipVariant, ClipVariant.is_winner.is_(True))
        sponsored_clips = self._count(SponsoredClip)
        active_sponsored_clips = self._count(SponsoredClip, SponsoredClip.is_active.is_(True))
        creator_clip_revenue_rows = self._count(CreatorClipRevenueAttribution)
        transfer_listings = self._count(TransferListing)
        active_transfer_listings = self._count(TransferListing, TransferListing.status == "open")
        coin_trader_orders = self._count(CoinTradeOrder)
        coin_trader_liquidity = self._sum(CoinTraderRate.available_liquidity, CoinTraderRate.is_active.is_(True))
        ticket_events = self._count(StadiumEvent)
        stadium_tickets = self._count(StadiumTicket)
        resale_tickets = self._count(
            StadiumTicket,
            StadiumTicket.status == "available",
            StadiumTicket.resale_listing_price.is_not(None),
        )
        player_cards = self._count(PlayerCard)
        player_card_listings = self._count(PlayerCardListing)
        active_player_card_listings = self._count(PlayerCardListing, PlayerCardListing.status == "open")
        notification_records = self._count(NotificationRecord)
        unread_notifications = self._count(NotificationRecord, NotificationRecord.read_at.is_(None))
        providers = self._count(RealDataProvider, RealDataProvider.is_active.is_(True))
        sportmonks_last_sync = self._sportmonks_last_sync()
        alerts: list[str] = []
        if players and player_images < players:
            alerts.append("Real-player image coverage is below player coverage.")
        if regens and regen_visuals < regens:
            alerts.append("Regen portrait coverage is below regen coverage.")
        if not providers and real_players:
            alerts.append("Real players exist but no active provider is recorded.")
        status = "attention" if alerts else "ok"
        return OperationsReadinessQueue(
            key="production_data_diagnostics",
            title="Production Data Diagnostics",
            description="Player, club, regen, image, market, academy, and provider coverage.",
            status=status,
            route="/admin/ops",
            owner="diagnostics",
            action_routes=["/admin/ops", "/admin/launch-control"],
            alerts=alerts,
            metrics=[
                self._metric("players", "Players", players),
                self._metric("player_images", "Player images", player_images, status="attention" if players and player_images < players else "ok"),
                self._metric("real_players", "Real players", real_players),
                self._metric("leagues", "Leagues", leagues),
                self._metric("clubs", "Clubs", clubs),
                self._metric("regens", "Regens", regens),
                self._metric("regen_visuals", "Regen portraits", regen_visuals, status="attention" if regens and regen_visuals < regens else "ok"),
                self._metric("national_regen_seeds", "National regen seeds", national_regen_seeds),
                self._metric("academy_prospects", "Academy prospects", academy_prospects),
                self._metric("club_lifecycles", "Club lifecycles", club_lifecycles),
                self._metric("club_readiness", "Club readiness", club_readiness),
                self._metric("squad_registrations", "Squad registrations", squad_registrations),
                self._metric("locked_squad_registrations", "Locked squads", locked_squad_registrations, status="live" if locked_squad_registrations else "ok"),
                self._metric("eligibility_flags", "Eligibility flags", eligibility_flags),
                self._metric("blocked_eligibility_flags", "Blocked eligibility flags", blocked_eligibility_flags, status="attention" if blocked_eligibility_flags else "ok"),
                self._metric("club_operating_statuses", "Club operating dashboards", operating_statuses),
                self._metric("staff_profiles", "Staff profiles", staff_profiles),
                self._metric("active_staff_contracts", "Active staff contracts", active_staff_contracts, status="live" if active_staff_contracts else "ok"),
                self._metric("active_staff_assignments", "Active staff assignments", active_staff_assignments, status="live" if active_staff_assignments else "ok"),
                self._metric("academy_profiles", "Academy profiles", academy_profiles),
                self._metric("active_academy_training_plans", "Active training plans", active_academy_training_plans, status="live" if active_academy_training_plans else "ok"),
                self._metric("academy_contract_offers", "Academy contract offers", academy_contract_offers, status="attention" if academy_contract_offers else "ok"),
                self._metric("academy_generation_runs", "Academy generation runs", academy_generation_runs),
                self._metric("sponsorship_packages", "Sponsorship packages", sponsorship_packages),
                self._metric("active_sponsorship_packages", "Active sponsorship packages", active_sponsorship_packages),
                self._metric("active_sponsorship_contracts", "Active sponsorship contracts", active_sponsorship_contracts, status="live" if active_sponsorship_contracts else "ok"),
                self._metric("visible_sponsorship_assets", "Visible sponsor assets", visible_sponsorship_assets),
                self._metric("pending_sponsorship_payouts", "Pending sponsor payouts", pending_sponsorship_payouts, status="attention" if pending_sponsorship_payouts else "ok"),
                self._metric("federations", "Federations", federations),
                self._metric("federation_memberships", "Federation memberships", federation_memberships),
                self._metric("open_federation_proposals", "Open federation votes", open_federation_proposals, status="attention" if open_federation_proposals else "ok"),
                self._metric("federation_sanctions", "Federation sanctions", federation_sanctions, status="attention" if federation_sanctions else "ok"),
                self._metric("fan_prediction_fixtures", "Prediction fixtures", fan_prediction_fixtures),
                self._metric("fan_prediction_submissions", "Prediction submissions", fan_prediction_submissions),
                self._metric("fan_war_profiles", "Fan war profiles", fan_war_profiles),
                self._metric("fan_war_points", "Fan war points", fan_war_points),
                self._metric("fanbase_rankings", "Fanbase rankings", fanbase_rankings),
                self._metric("broadcast_rights", "Broadcast rights", broadcast_rights),
                self._metric("broadcast_auctions", "Broadcast auctions", broadcast_auctions, status="live" if broadcast_auctions else "ok"),
                self._metric("broadcast_access_grants", "Broadcast grants", broadcast_access_grants),
                self._metric("broadcast_view_sessions", "Broadcast views", broadcast_view_sessions),
                self._metric("clip_variants", "Clip variants", clip_variants),
                self._metric("winning_clip_variants", "Winning clips", winning_clip_variants, status="live" if winning_clip_variants else "ok"),
                self._metric("sponsored_clips", "Sponsored clips", sponsored_clips),
                self._metric("active_sponsored_clips", "Active sponsored clips", active_sponsored_clips, status="live" if active_sponsored_clips else "ok"),
                self._metric("creator_clip_revenue_rows", "Clip revenue rows", creator_clip_revenue_rows),
                self._metric("transfer_listings", "Transfer listings", transfer_listings),
                self._metric("active_transfer_listings", "Active transfer listings", active_transfer_listings, status="live" if active_transfer_listings else "ok"),
                self._metric("coin_trader_orders", "Coin trader orders", coin_trader_orders),
                self._metric("coin_trader_liquidity", "Coin trader liquidity", coin_trader_liquidity, unit="coins"),
                self._metric("ticket_events", "Ticket events", ticket_events),
                self._metric("stadium_tickets", "Stadium tickets", stadium_tickets),
                self._metric("resale_tickets", "Resale tickets", resale_tickets, status="live" if resale_tickets else "ok"),
                self._metric("player_cards", "Player cards", player_cards),
                self._metric("player_card_listings", "Card listings", player_card_listings),
                self._metric("active_player_card_listings", "Active card listings", active_player_card_listings, status="live" if active_player_card_listings else "ok"),
                self._metric("notification_records", "Notification records", notification_records),
                self._metric("unread_notifications", "Unread notifications", unread_notifications, status="attention" if unread_notifications else "ok"),
                self._metric("active_real_data_providers", "Active providers", providers),
                self._metric(
                    "sportmonks_last_sync_seen",
                    "SportMonks last sync",
                    1 if sportmonks_last_sync else 0,
                    status="ok" if sportmonks_last_sync else "attention",
                    metadata={"last_sync_at": sportmonks_last_sync},
                ),
            ],
        )

    def _ledger_worker_queue(self) -> OperationsReadinessQueue:
        since = utcnow() - timedelta(hours=24)
        ledger_entries_24h = self._count(LedgerEntry, LedgerEntry.created_at >= since)
        user_wallets = self._count(UserWallet)
        wallet_transactions = self._count(WalletTransactionRecord)
        pending_wallet_transactions = self._count(WalletTransactionRecord, WalletTransactionRecord.status == "pending")
        pending_outbox = self._count(EventOutbox, EventOutbox.status == "pending")
        dead_outbox = self._count(EventOutbox, EventOutbox.status == "dead_lettered")
        queued_jobs = self._count(CompetitionQueueRecord, CompetitionQueueRecord.status == "queued")
        failed_jobs = self._count(CompetitionQueueRecord, CompetitionQueueRecord.status.in_(["failed", "dead_lettered"]))
        feature_flag_audits = self._count(AdminFeatureFlagAuditLog)
        audit_logs_24h = self._count(AuditLog, AuditLog.created_at >= since)
        running_sync_jobs = self._count(RealDataSyncJob, RealDataSyncJob.status == "running")
        failed_sync_jobs = self._count(RealDataSyncJob, RealDataSyncJob.status == "failed")
        build_commit = self._build_commit()
        alerts: list[str] = []
        if dead_outbox:
            alerts.append(f"{dead_outbox} dead-lettered outbox event(s) need inspection.")
        if failed_jobs:
            alerts.append(f"{failed_jobs} failed queue job(s) are present.")
        if failed_sync_jobs:
            alerts.append(f"{failed_sync_jobs} real-data sync job(s) failed.")
        if pending_wallet_transactions:
            alerts.append(f"{pending_wallet_transactions} wallet transaction(s) remain pending.")
        status = "blocked" if dead_outbox or failed_jobs else "attention" if pending_wallet_transactions or pending_outbox or failed_sync_jobs else "ok"
        return OperationsReadinessQueue(
            key="ledger_worker_health",
            title="Ledger And Worker Health",
            description="Wallet activity, ledger movement, event outbox, queue pressure, real-data workers, and build identity.",
            status=status,
            route="/admin/ops",
            owner="observability",
            action_routes=["/admin/ops", "/admin/ops/audit"],
            alerts=alerts,
            metrics=[
                self._metric("ledger_entries_24h", "Ledger entries 24h", ledger_entries_24h),
                self._metric("user_wallets", "User wallets", user_wallets),
                self._metric("wallet_transactions", "Wallet transactions", wallet_transactions),
                self._metric("pending_wallet_transactions", "Pending wallet tx", pending_wallet_transactions, status="attention" if pending_wallet_transactions else "ok"),
                self._metric("pending_outbox_events", "Pending outbox", pending_outbox, status="attention" if pending_outbox else "ok"),
                self._metric("dead_outbox_events", "Dead outbox", dead_outbox, status="blocked" if dead_outbox else "ok"),
                self._metric("queued_jobs", "Queued jobs", queued_jobs),
                self._metric("failed_jobs", "Failed jobs", failed_jobs, status="blocked" if failed_jobs else "ok"),
                self._metric("running_sync_jobs", "Running sync jobs", running_sync_jobs, status="live" if running_sync_jobs else "ok"),
                self._metric("failed_sync_jobs", "Failed sync jobs", failed_sync_jobs, status="attention" if failed_sync_jobs else "ok"),
                self._metric("feature_flag_audits", "Flag audits", feature_flag_audits),
                self._metric("audit_logs_24h", "Audit logs 24h", audit_logs_24h),
                self._metric(
                    "build_commit_present",
                    "Build commit",
                    1 if build_commit else 0,
                    status="ok" if build_commit else "attention",
                    metadata={"commit": build_commit},
                ),
            ],
        )

    def _launch_gates(self) -> list[OperationsLaunchGate]:
        if not self._has_table(AdminFeatureFlag):
            return []
        flags = list(
            self.session.scalars(
                select(AdminFeatureFlag).order_by(
                    AdminFeatureFlag.kill_switch_enabled.desc(),
                    AdminFeatureFlag.launch_state.asc(),
                    AdminFeatureFlag.feature_key.asc(),
                )
            ).all()
        )
        return [
            OperationsLaunchGate(
                feature_key=flag.feature_key,
                title=flag.title,
                enabled=flag.enabled,
                launch_state=flag.launch_state,
                audience=flag.audience,
                kill_switch_enabled=flag.kill_switch_enabled,
                maintenance_message=flag.maintenance_message,
                route=(flag.metadata_json or {}).get("route"),
            )
            for flag in flags
        ]

    def _overall_status(self, queues: Iterable[OperationsReadinessQueue], gates: Iterable[OperationsLaunchGate]) -> str:
        queue_statuses = {queue.status for queue in queues}
        if "blocked" in queue_statuses or any(gate.kill_switch_enabled for gate in gates):
            return "blocked"
        if "attention" in queue_statuses:
            return "attention"
        return "ok"

    def _metric(
        self,
        key: str,
        label: str,
        value: int | float | Decimal,
        *,
        unit: str | None = None,
        status: str = "ok",
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperationsReadinessMetric:
        numeric = float(value)
        return OperationsReadinessMetric(
            key=key,
            label=label,
            value=numeric,
            display_value=self._format_value(numeric, unit=unit),
            unit=unit,
            status=status,
            route=route,
            metadata=metadata or {},
        )

    def _format_value(self, value: float, *, unit: str | None = None) -> str:
        number = int(value) if value.is_integer() else round(value, 2)
        text = f"{number:,}" if isinstance(number, int) else f"{number:,.2f}"
        if unit:
            return f"{text} {unit}"
        return text

    def _count(self, model: type[Any], *criteria: Any) -> int:
        if not self._has_table(model):
            return 0
        stmt: Select[tuple[int]] = select(func.count()).select_from(model)
        for item in criteria:
            stmt = stmt.where(item)
        return int(self.session.scalar(stmt) or 0)

    def _sum(self, column: Any, *criteria: Any) -> float:
        model = column.class_
        if not self._has_table(model):
            return 0.0
        stmt: Select[Any] = select(func.coalesce(func.sum(column), 0))
        for item in criteria:
            stmt = stmt.where(item)
        return float(self.session.scalar(stmt) or 0)

    def _has_table(self, model: type[Any]) -> bool:
        table_name = getattr(model, "__tablename__", None)
        if not table_name:
            return False
        return bool(self._inspector.has_table(table_name))

    def _sportmonks_last_sync(self) -> str | None:
        if not self._has_table(RealDataProvider):
            return None
        provider = self.session.scalar(
            select(RealDataProvider)
            .where(func.lower(RealDataProvider.name).like("%sportmonks%"))
            .order_by(RealDataProvider.last_sync_at.desc().nullslast(), RealDataProvider.updated_at.desc())
        )
        if provider is None or provider.last_sync_at is None:
            return None
        return provider.last_sync_at.isoformat()

    @staticmethod
    def _notification_message(queue: OperationsReadinessQueue) -> str:
        detail = queue.alerts[0] if queue.alerts else queue.status
        return f"{queue.title}: {detail}"[:240]

    def _admin_user_ids(self) -> list[str]:
        if not self._has_table(User):
            return []
        statement = (
            select(User.id)
            .where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
            .order_by(User.created_at.asc())
        )
        return [item for item in self.session.scalars(statement).all() if item]

    def _notification_tables_available(self) -> bool:
        return self._has_table(NotificationRecord) and self._has_table(NotificationPreference)

    @staticmethod
    def _build_commit() -> str | None:
        for key in (
            "GTEX_BUILD_COMMIT",
            "RENDER_GIT_COMMIT",
            "VERCEL_GIT_COMMIT_SHA",
            "GITHUB_SHA",
            "COMMIT_SHA",
        ):
            value = os.getenv(key)
            if value and value.strip():
                return value.strip()[:12]
        return None
