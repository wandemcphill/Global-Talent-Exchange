from backend.app.models.academy_graduation_event import AcademyGraduationEvent
from backend.app.models.academy_player import AcademyPlayer
from backend.app.models.academy_player_progress import AcademyPlayerProgress
from backend.app.models.academy_program import AcademyProgram
from backend.app.models.academy_training_cycle import AcademyTrainingCycle
from backend.app.models.analytics_event import AnalyticsEvent
from backend.app.models.admin_rules import AdminCalendarRule, AdminFeatureFlag, AdminRewardRule
from backend.app.models.attachment import Attachment
from backend.app.models.calendar_engine import CalendarEvent, CalendarSeason, CompetitionLifecycleRun
from backend.app.models.base import Base
from backend.app.models.card_access import (
    CardLoanContract,
    CardLoanListing,
    CardLoanNegotiation,
    CardMarketplaceAuditEvent,
    CardSwapExecution,
    CardSwapListing,
    StarterSquadRental,
)
from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_budget_snapshot import ClubBudgetSnapshot
from backend.app.models.club_cashflow_summary import ClubCashflowSummary
from backend.app.models.club_cosmetic_catalog_item import ClubCosmeticCatalogItem
from backend.app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from backend.app.models.club_dynasty_progress import ClubDynastyProgress
from backend.app.models.club_finance_account import ClubFinanceAccount
from backend.app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry
from backend.app.models.club_hall_of_fame import ClubHallOfFameEntry
from backend.app.models.club_infra import ClubFacility, ClubStadium, ClubSupporterHolding, ClubSupporterToken, SupporterTokenStatus
from backend.app.models.club_identity_theme import ClubIdentityTheme
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_sale import (
    ClubSaleAuditEvent,
    ClubSaleInquiry,
    ClubSaleInquiryStatus,
    ClubSaleListing,
    ClubSaleListingStatus,
    ClubSaleOffer,
    ClubSaleOfferStatus,
    ClubSaleTransfer,
    ClubSaleTransferStatus,
    ClubValuationSnapshot,
)
from backend.app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from backend.app.models.club_social import (
    ChallengeShareEvent,
    ClubChallenge,
    ClubChallengeLink,
    ClubChallengeResponse,
    ClubIdentityMetrics,
    MatchReactionEvent,
    RivalryMatchHistory,
    RivalryProfile,
)
from backend.app.models.football_world import ClubWorldProfile, FootballCultureProfile, WorldNarrativeArc
from backend.app.models.club_sponsor import ClubSponsor, SponsorOffer, SponsorOfferRule
from backend.app.models.club_sponsorship_asset import ClubSponsorshipAsset
from backend.app.models.club_sponsorship_contract import ClubSponsorshipContract
from backend.app.models.club_sponsorship_package import ClubSponsorshipPackage
from backend.app.models.club_sponsorship_payout import ClubSponsorshipPayout
from backend.app.models.club_trophy import ClubTrophy
from backend.app.models.competition import Competition, UserCompetition
from backend.app.models.competition_autofill_rule import CompetitionAutofillRule
from backend.app.models.competition_entry import CompetitionEntry
from backend.app.models.competition_invite import CompetitionInvite
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_match_event import CompetitionMatchEvent
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_playoff import CompetitionPlayoff
from backend.app.models.competition_prize_rule import CompetitionPrizeRule
from backend.app.models.competition_reward import CompetitionReward
from backend.app.models.competition_reward_pool import CompetitionRewardPool
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_schedule_job import CompetitionScheduleJob
from backend.app.models.competition_seed_rule import CompetitionSeedRule
from backend.app.models.competition_visibility_rule import CompetitionVisibilityRule
from backend.app.models.competition_wallet_ledger import CompetitionWalletLedger
from backend.app.models.creator_campaign import CreatorCampaign
from backend.app.models.creator_monetization import (
    CreatorBroadcastModeConfig,
    CreatorBroadcastPurchase,
    CreatorMatchGiftEvent,
    CreatorRevenueSettlement,
    CreatorSeasonPass,
    CreatorStadiumControl,
    CreatorStadiumPlacement,
    CreatorStadiumPricing,
    CreatorStadiumProfile,
    CreatorStadiumTicketPurchase,
)
from backend.app.models.creator_share_market import (
    CreatorClubShareDistribution,
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
    CreatorClubSharePayout,
    CreatorClubSharePurchase,
)
from backend.app.models.creator_fan_engagement import (
    CreatorClubFollow,
    CreatorFanCompetition,
    CreatorFanCompetitionEntry,
    CreatorFanCompetitionStatus,
    CreatorFanGroup,
    CreatorFanGroupMembership,
    CreatorFanWallEvent,
    CreatorMatchChatMessage,
    CreatorMatchChatMessageVisibility,
    CreatorMatchChatRoom,
    CreatorMatchChatRoomStatus,
    CreatorMatchTacticalAdvice,
    CreatorRivalrySignalOutput,
    CreatorRivalrySignalStatus,
    CreatorRivalrySignalSurface,
    CreatorTacticalAdviceStatus,
    CreatorTacticalAdviceType,
)
from backend.app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier, CreatorLeagueTier
from backend.app.models.creator_application import CreatorApplication
from backend.app.models.creator_card import CreatorCard, CreatorCardListing, CreatorCardLoan, CreatorCardSale, CreatorCardSwap
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorClubProvisioning, CreatorRegen, CreatorSquad
from backend.app.models.streamer_tournament import (
    StreamerTournament,
    StreamerTournamentApprovalStatus,
    StreamerTournamentEntry,
    StreamerTournamentEntryStatus,
    StreamerTournamentInvite,
    StreamerTournamentInviteStatus,
    StreamerTournamentPolicy,
    StreamerTournamentQualificationType,
    StreamerTournamentReward,
    StreamerTournamentRewardGrant,
    StreamerTournamentRewardGrantStatus,
    StreamerTournamentRewardType,
    StreamerTournamentRiskSignal,
    StreamerTournamentRiskStatus,
    StreamerTournamentStatus,
    StreamerTournamentType,
)
from backend.app.models.community_engine import CompetitionWatchlist, LiveThread, LiveThreadMessage, MessageVisibility, PrivateMessage, PrivateMessageParticipant, PrivateMessageThread, PrivateMessageThreadStatus, LiveThreadStatus
from backend.app.models.discovery_engine import FeaturedRail, SavedSearch
from backend.app.models.dispute import Dispute, DisputeMessage, DisputeStatus
from backend.app.models.economy_config import GiftCatalogItem, ServicePricingRule
from backend.app.models.economy_burn_event import EconomyBurnEvent
from backend.app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from backend.app.models.gift_combo_event import GiftComboEvent
from backend.app.models.gift_combo_rule import GiftComboRule
from backend.app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
from backend.app.models.market_topup import MarketTopup, MarketTopupStatus
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_import import PlayerImportItem, PlayerImportItemStatus, PlayerImportJob, PlayerImportJobStatus
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.player_cards import (
    PlayerAlias,
    PlayerMoniker,
    PlayerCard,
    PlayerCardTier,
    PlayerCardSupplyBatch,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardOwnerHistory,
    PlayerCardEffect,
    PlayerCardFormBuff,
    PlayerCardMomentum,
    PlayerCardListing,
    PlayerCardSale,
    PlayerCardWatchlist,
    PlayerStatsSnapshot,
    PlayerMarketValueSnapshot,
)
from backend.app.models.real_world_football import (
    EventEffectRule,
    EventIngestionJob,
    PlayerDemandSignal,
    PlayerFormModifier,
    RealWorldFootballEvent,
    TrendingPlayerFlag,
)
from backend.app.models.referral_attribution import ReferralAttribution
from backend.app.models.referral_event import ReferralEvent
from backend.app.models.referral_reward import ReferralReward
from backend.app.models.referral_reward_ledger import ReferralRewardLedger
from backend.app.models.scout_assignment import ScoutAssignment
from backend.app.models.scouting_region import ScoutingRegion
from backend.app.models.share_code import ShareCode
from backend.app.models.manager_market import (
    ManagerAuditLog,
    ManagerCatalogEntry,
    ManagerCompetitionSetting,
    ManagerHolding,
    ManagerSettlementRecord,
    ManagerTeamAssignment,
    ManagerTradeListing,
    ManagerTradeRecord,
)
from backend.app.models.transfer_bid import TransferBid
from backend.app.models.transfer_window import TransferWindow
from backend.app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    PaymentMode,
    RateDirection,
    TreasuryAuditEvent,
    TreasuryBankAccount,
    TreasurySettings,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
    UserBankAccount,
)
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.models.user_region import UserRegionProfile
from backend.app.models.notification_center import NotificationPreference, NotificationSubscription, PlatformAnnouncement
from backend.app.models.notification_record import NotificationRecord
from backend.app.models.policy import CountryFeaturePolicy, PolicyAcceptanceRecord, PolicyDocument, PolicyDocumentVersion
from backend.app.models.fan_prediction import (
    FanPredictionFixture,
    FanPredictionFixtureStatus,
    FanPredictionLeaderboardScope,
    FanPredictionOutcome,
    FanPredictionRewardGrant,
    FanPredictionRewardType,
    FanPredictionSubmission,
    FanPredictionSubmissionStatus,
    FanPredictionTokenLedger,
    FanPredictionTokenReason,
)
from backend.app.models.fan_war import (
    CountryCreatorAssignment,
    FanWarPoint,
    FanWarProfile,
    FanbaseRanking,
    NationsCupEntry,
    NationsCupFanMetric,
)
from backend.app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
from backend.app.models.spending_control import SpendingControlAuditEvent, SpendingControlDecision
from backend.app.models.regen import (
    AcademyCandidate,
    AcademyIntakeBatch,
    CurrencyConversionQuote,
    MajorTransferAnnouncement,
    RegenDemandSignal,
    RegenGenerationEvent,
    RegenBigClubApproach,
    RegenLineageProfile,
    RegenMarketActivity,
    RegenContractOffer,
    RegenAward,
    RegenDiscoveryBadge,
    RegenLegacyRecord,
    RegenOnboardingFlag,
    RegenOfferVisibilityState,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenRelationshipTag,
    RegenRecommendationItem,
    RegenScoutReport,
    RegenTeamDynamicsEffect,
    RegenTransferFeeRule,
    RegenTransferPressureState,
    RegenTwinsGroup,
    RegenUnsettlingEvent,
    RegenValueSnapshot,
    RegenVisualProfile,
    TransferHeadlineMediaRecord,
)
from backend.app.models.scouting_intelligence import (
    AcademySupplySignal,
    HiddenPotentialEstimate,
    ManagerScoutingProfile,
    PlayerLifecycleProfile,
    ScoutMission,
    ScoutReport,
    ScoutingNetwork,
    ScoutingNetworkAssignment,
    TalentDiscoveryBadge,
)
from backend.app.models.revenue_share_rule import RevenueShareRule
from backend.app.models.risk_ops import AmlCase, AuditLog, FraudCase, RiskCaseStatus, RiskSeverity, SystemEvent, SystemEventSeverity
from backend.app.models.sponsorship_engine import SponsorshipLead
from backend.app.models.creator_campaign_engine import CreatorCampaignMetricSnapshot
from backend.app.models.governance_engine import GovernanceProposal, GovernanceProposalScope, GovernanceProposalStatus, GovernanceVote, GovernanceVoteChoice
from backend.app.models.highlight_share import HighlightShareAmplification, HighlightShareExport, HighlightShareTemplate
from backend.app.models.moderation_report import ModerationPriority, ModerationReport, ModerationReportStatus, ModerationResolutionAction
from backend.app.models.media_engine import MatchRevenueSnapshot, MatchView, PremiumVideoPurchase
from backend.app.models.national_team import NationalTeamCompetition, NationalTeamEntry, NationalTeamManagerHistory, NationalTeamSquadMember
from backend.app.models.story_feed import StoryFeedItem
from backend.app.models.daily_challenge import DailyChallenge, DailyChallengeClaim, DailyChallengeStatus
from backend.app.models.hosted_competition import CompetitionTemplate, HostedCompetitionSettlement, HostedCompetitionSettlementStatus, HostedCompetitionStanding, HostedCompetitionStatus, UserHostedCompetition, UserHostedCompetitionParticipant
from backend.app.models.integrity import IntegrityIncident, IntegrityScore
from backend.app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
    PayoutRequest,
    PayoutStatus,
)
from backend.app.models.withdrawal_review import WithdrawalReview
from backend.app.models.youth_pipeline_snapshot import YouthPipelineSnapshot
from backend.app.models.youth_prospect import YouthProspect
from backend.app.models.youth_prospect_report import YouthProspectReport

__all__ = [
    "AcademyGraduationEvent",
    "AcademyPlayer",
    "AcademyPlayerProgress",
    "AcademyProgram",
    "AcademyTrainingCycle",
    "AnalyticsEvent",
    "AdminCalendarRule",
    "AdminFeatureFlag",
    "AdminRewardRule",
    "Attachment",
    "CalendarEvent",
    "CalendarSeason",
    "CompetitionLifecycleRun",
    "Base",
    "CardLoanContract",
    "CardLoanListing",
    "CardLoanNegotiation",
    "CardMarketplaceAuditEvent",
    "CardSwapExecution",
    "CardSwapListing",
    "ClubBrandingAsset",
    "ClubBudgetSnapshot",
    "ClubCashflowSummary",
    "ClubCosmeticCatalogItem",
    "ClubCosmeticPurchase",
    "ClubDynastyProgress",
    "ClubFinanceAccount",
    "ClubFinanceLedgerEntry",
    "ClubFacility",
    "ClubStadium",
    "ClubSupporterHolding",
    "ClubSupporterToken",
    "ClubIdentityTheme",
    "ClubJerseyDesign",
    "ClubProfile",
    "ClubSaleAuditEvent",
    "ClubSaleInquiry",
    "ClubSaleInquiryStatus",
    "ClubSaleListing",
    "ClubSaleListingStatus",
    "ClubSaleOffer",
    "ClubSaleOfferStatus",
    "ClubSaleTransfer",
    "ClubSaleTransferStatus",
    "ClubValuationSnapshot",
    "ClubShowcaseSnapshot",
    "ChallengeShareEvent",
    "ClubChallenge",
    "ClubChallengeLink",
    "ClubChallengeResponse",
    "ClubIdentityMetrics",
    "MatchReactionEvent",
    "RivalryMatchHistory",
    "RivalryProfile",
    "ClubSponsor",
    "ClubSponsorshipAsset",
    "ClubSponsorshipContract",
    "ClubSponsorshipPackage",
    "ClubSponsorshipPayout",
    "ClubTrophy",
    "Competition",
    "UserCompetition",
    "CompetitionAutofillRule",
    "CompetitionEntry",
    "CompetitionInvite",
    "CompetitionMatch",
    "CompetitionMatchEvent",
    "CompetitionParticipant",
    "CompetitionPlayoff",
    "CompetitionPrizeRule",
    "CompetitionReward",
    "CompetitionRewardPool",
    "CompetitionRound",
    "CompetitionRuleSet",
    "CompetitionScheduleJob",
    "CompetitionSeedRule",
    "CompetitionVisibilityRule",
    "CompetitionWalletLedger",
    "CreatorCampaign",
    "CreatorBroadcastModeConfig",
    "CreatorBroadcastPurchase",
    "CreatorClubShareDistribution",
    "CreatorMatchGiftEvent",
    "CreatorClubShareHolding",
    "CreatorClubShareMarket",
    "CreatorClubShareMarketControl",
    "CreatorClubSharePayout",
    "CreatorClubSharePurchase",
    "CreatorRevenueSettlement",
    "CreatorSeasonPass",
    "CreatorLeagueConfig",
    "CreatorLeagueSeason",
    "CreatorLeagueSeasonTier",
    "CreatorLeagueTier",
    "CreatorApplication",
    "CreatorCard",
    "CreatorCardListing",
    "CreatorCardLoan",
    "CreatorCardSale",
    "CreatorCardSwap",
    "CreatorClubFollow",
    "CreatorFanCompetition",
    "CreatorFanCompetitionEntry",
    "CreatorFanCompetitionStatus",
    "CreatorFanGroup",
    "CreatorFanGroupMembership",
    "CreatorFanWallEvent",
    "CreatorMatchChatMessage",
    "CreatorMatchChatMessageVisibility",
    "CreatorMatchChatRoom",
    "CreatorMatchChatRoomStatus",
    "CreatorMatchTacticalAdvice",
    "CreatorClubProvisioning",
    "CreatorProfile",
    "CreatorRegen",
    "CreatorRivalrySignalOutput",
    "CreatorRivalrySignalStatus",
    "CreatorRivalrySignalSurface",
    "StreamerTournament",
    "StreamerTournamentApprovalStatus",
    "StreamerTournamentEntry",
    "StreamerTournamentEntryStatus",
    "StreamerTournamentInvite",
    "StreamerTournamentInviteStatus",
    "StreamerTournamentPolicy",
    "StreamerTournamentQualificationType",
    "StreamerTournamentReward",
    "StreamerTournamentRewardGrant",
    "StreamerTournamentRewardGrantStatus",
    "StreamerTournamentRewardType",
    "StreamerTournamentRiskSignal",
    "StreamerTournamentRiskStatus",
    "StreamerTournamentStatus",
    "StreamerTournamentType",
    "CreatorSquad",
    "CreatorTacticalAdviceStatus",
    "CreatorTacticalAdviceType",
    "CompetitionWatchlist",
    "LiveThread",
    "LiveThreadMessage",
    "LiveThreadStatus",
    "MessageVisibility",
    "PrivateMessage",
    "PrivateMessageParticipant",
    "PrivateMessageThread",
    "PrivateMessageThreadStatus",
    "Dispute",
    "FeaturedRail",
    "DisputeMessage",
    "DisputeStatus",
    "GiftCatalogItem",
    "EconomyBurnEvent",
    "FancoinPurchaseOrder",
    "PurchaseOrderStatus",
    "GiftComboEvent",
    "GiftComboRule",
    "NotificationPreference",
    "NotificationSubscription",
    "PlatformAnnouncement",
    "GiftTransaction",
    "GiftTransactionStatus",
    "KycStatus",
    "LedgerAccount",
    "LedgerAccountKind",
    "LedgerEntry",
    "LedgerEntryReason",
    "LedgerSourceTag",
    "LedgerUnit",
    "PaymentEvent",
    "PaymentProvider",
    "PaymentStatus",
    "PayoutRequest",
    "PayoutStatus",
    "MarketTopup",
    "MarketTopupStatus",
    "WithdrawalReview",
    "PlayerCareerEntry",
    "PlayerContract",
    "PlayerImportItem",
    "PlayerImportItemStatus",
    "PlayerImportJob",
    "PlayerImportJobStatus",
    "PlayerInjuryCase",
    "PlayerLifecycleEvent",
    "PlayerAlias",
    "PlayerMoniker",
    "PlayerCard",
    "PlayerCardTier",
    "PlayerCardSupplyBatch",
    "PlayerCardHolding",
    "PlayerCardHistory",
    "PlayerCardOwnerHistory",
    "PlayerCardEffect",
    "PlayerCardFormBuff",
    "PlayerCardMomentum",
    "PlayerCardListing",
    "PlayerCardSale",
    "PlayerCardWatchlist",
    "PlayerStatsSnapshot",
    "PlayerMarketValueSnapshot",
    "EventEffectRule",
    "EventIngestionJob",
    "PlayerDemandSignal",
    "PlayerFormModifier",
    "RealWorldFootballEvent",
    "TrendingPlayerFlag",
    "SponsorOffer",
    "SponsorOfferRule",
    "StarterSquadRental",
    "ReferralAttribution",
    "ReferralEvent",
    "ReferralReward",
    "ReferralRewardLedger",
    "ScoutAssignment",
    "ScoutingRegion",
    "ServicePricingRule",
    "RevenueShareRule",
    "SupporterTokenStatus",
    "SavedSearch",
    "ShareCode",
    "ManagerAuditLog",
    "ManagerCatalogEntry",
    "ManagerCompetitionSetting",
    "ManagerHolding",
    "ManagerSettlementRecord",
    "ManagerTeamAssignment",
    "ManagerTradeListing",
    "ManagerTradeRecord",
    "TransferBid",
    "TransferWindow",
    "DepositRequest",
    "DepositStatus",
    "KycProfile",
    "PaymentMode",
    "RateDirection",
    "TreasuryAuditEvent",
    "TreasuryBankAccount",
    "TreasurySettings",
    "TreasuryWithdrawalRequest",
    "TreasuryWithdrawalStatus",
    "UserBankAccount",
    "UserRegionProfile",
    "User",
    "UserRole",
    "NotificationRecord",
    "CountryFeaturePolicy",
    "PolicyAcceptanceRecord",
    "PolicyDocument",
    "PolicyDocumentVersion",
    "FanPredictionFixture",
    "FanPredictionFixtureStatus",
    "FanPredictionLeaderboardScope",
    "FanPredictionOutcome",
    "FanPredictionRewardGrant",
    "FanPredictionRewardType",
    "FanPredictionSubmission",
    "FanPredictionSubmissionStatus",
    "FanPredictionTokenLedger",
    "FanPredictionTokenReason",
    "CountryCreatorAssignment",
    "FanWarPoint",
    "FanWarProfile",
    "FanbaseRanking",
    "NationsCupEntry",
    "NationsCupFanMetric",
    "RewardSettlement",
    "RewardSettlementStatus",
    "SpendingControlAuditEvent",
    "SpendingControlDecision",
    "AcademyCandidate",
    "AcademyIntakeBatch",
    "CurrencyConversionQuote",
    "MajorTransferAnnouncement",
    "RegenDemandSignal",
    "RegenGenerationEvent",
    "RegenBigClubApproach",
    "RegenMarketActivity",
    "RegenContractOffer",
    "RegenOnboardingFlag",
    "RegenOfferVisibilityState",
    "RegenOriginMetadata",
    "RegenPersonalityProfile",
    "RegenProfile",
    "RegenRecommendationItem",
    "RegenScoutReport",
    "RegenTeamDynamicsEffect",
    "RegenTransferFeeRule",
    "RegenTransferPressureState",
    "RegenUnsettlingEvent",
    "RegenValueSnapshot",
    "RegenVisualProfile",
    "TransferHeadlineMediaRecord",
    "AcademySupplySignal",
    "HiddenPotentialEstimate",
    "ManagerScoutingProfile",
    "PlayerLifecycleProfile",
    "ScoutMission",
    "ScoutReport",
    "ScoutingNetwork",
    "ScoutingNetworkAssignment",
    "TalentDiscoveryBadge",
    "AmlCase",
    "AuditLog",
    "FraudCase",
    "RiskCaseStatus",
    "RiskSeverity",
    "SystemEvent",
    "SystemEventSeverity",
    "SponsorshipLead",
    "CreatorCampaignMetricSnapshot",
    "GovernanceProposal",
    "GovernanceProposalScope",
    "GovernanceProposalStatus",
    "GovernanceVote",
    "GovernanceVoteChoice",
    "HighlightShareExport",
    "HighlightShareTemplate",
    "ModerationPriority",
    "ModerationReport",
    "ModerationReportStatus",
    "ModerationResolutionAction",
    "MatchRevenueSnapshot",
    "MatchView",
    "PremiumVideoPurchase",
    "NationalTeamCompetition",
    "NationalTeamEntry",
    "NationalTeamManagerHistory",
    "NationalTeamSquadMember",
    "StoryFeedItem",
    "DailyChallenge",
    "DailyChallengeClaim",
    "DailyChallengeStatus",
    "CompetitionTemplate",
    "HostedCompetitionSettlement",
    "HostedCompetitionSettlementStatus",
    "HostedCompetitionStanding",
    "HostedCompetitionStatus",
    "UserHostedCompetition",
    "UserHostedCompetitionParticipant",
    "IntegrityIncident",
    "IntegrityScore",
    "YouthPipelineSnapshot",
    "YouthProspect",
    "YouthProspectReport",
]
