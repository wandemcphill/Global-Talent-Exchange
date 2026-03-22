import 'package:gte_frontend/data/gte_models.dart';

class CreatorClubShareMarketControl {
  const CreatorClubShareMarketControl({
    required this.id,
    required this.controlKey,
    required this.maxSharesPerClub,
    required this.maxSharesPerFan,
    required this.shareholderRevenueShareBps,
    required this.issuanceEnabled,
    required this.purchaseEnabled,
    required this.maxPrimaryPurchaseValueCoin,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String controlKey;
  final int maxSharesPerClub;
  final int maxSharesPerFan;
  final int shareholderRevenueShareBps;
  final bool issuanceEnabled;
  final bool purchaseEnabled;
  final double maxPrimaryPurchaseValueCoin;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubShareMarketControl.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share market control');
    return CreatorClubShareMarketControl(
      id: GteJson.string(json, <String>['id']),
      controlKey: GteJson.string(json, <String>['control_key', 'controlKey']),
      maxSharesPerClub: GteJson.integer(
        json,
        <String>['max_shares_per_club', 'maxSharesPerClub'],
      ),
      maxSharesPerFan: GteJson.integer(
        json,
        <String>['max_shares_per_fan', 'maxSharesPerFan'],
      ),
      shareholderRevenueShareBps: GteJson.integer(
        json,
        <String>[
          'shareholder_revenue_share_bps',
          'shareholderRevenueShareBps',
        ],
      ),
      issuanceEnabled: GteJson.boolean(
        json,
        <String>['issuance_enabled', 'issuanceEnabled'],
      ),
      purchaseEnabled: GteJson.boolean(
        json,
        <String>['purchase_enabled', 'purchaseEnabled'],
      ),
      maxPrimaryPurchaseValueCoin: GteJson.number(
        json,
        <String>[
          'max_primary_purchase_value_coin',
          'maxPrimaryPurchaseValueCoin',
        ],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class CreatorClubShareHolding {
  const CreatorClubShareHolding({
    required this.id,
    required this.marketId,
    required this.clubId,
    required this.userId,
    required this.shareCount,
    required this.totalSpentCoin,
    required this.revenueEarnedCoin,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String marketId;
  final String clubId;
  final String userId;
  final int shareCount;
  final double totalSpentCoin;
  final double revenueEarnedCoin;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubShareHolding.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share holding');
    return CreatorClubShareHolding(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      shareCount: GteJson.integer(json, <String>['share_count', 'shareCount']),
      totalSpentCoin:
          GteJson.number(json, <String>['total_spent_coin', 'totalSpentCoin']),
      revenueEarnedCoin: GteJson.number(
        json,
        <String>['revenue_earned_coin', 'revenueEarnedCoin'],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class CreatorClubShareBenefit {
  const CreatorClubShareBenefit({
    required this.shareholder,
    required this.shareCount,
    required this.hasPriorityChatVisibility,
    required this.hasEarlyTicketAccess,
    required this.hasCosmeticVotingRights,
    required this.tournamentQualificationMethod,
    required this.cosmeticVotePower,
  });

  final bool shareholder;
  final int shareCount;
  final bool hasPriorityChatVisibility;
  final bool hasEarlyTicketAccess;
  final bool hasCosmeticVotingRights;
  final String? tournamentQualificationMethod;
  final int cosmeticVotePower;

  factory CreatorClubShareBenefit.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share benefit');
    return CreatorClubShareBenefit(
      shareholder: GteJson.boolean(json, <String>['shareholder']),
      shareCount: GteJson.integer(json, <String>['share_count', 'shareCount']),
      hasPriorityChatVisibility: GteJson.boolean(
        json,
        <String>[
          'has_priority_chat_visibility',
          'hasPriorityChatVisibility',
        ],
      ),
      hasEarlyTicketAccess: GteJson.boolean(
        json,
        <String>['has_early_ticket_access', 'hasEarlyTicketAccess'],
      ),
      hasCosmeticVotingRights: GteJson.boolean(
        json,
        <String>[
          'has_cosmetic_voting_rights',
          'hasCosmeticVotingRights',
        ],
      ),
      tournamentQualificationMethod: GteJson.stringOrNull(
        json,
        <String>[
          'tournament_qualification_method',
          'tournamentQualificationMethod',
        ],
      ),
      cosmeticVotePower: GteJson.integer(
        json,
        <String>['cosmetic_vote_power', 'cosmeticVotePower'],
      ),
    );
  }
}

class CreatorClubGovernancePolicy {
  const CreatorClubGovernancePolicy({
    required this.governanceMode,
    required this.voteWeightModel,
    required this.antiTakeoverEnabled,
    required this.maxHolderBps,
    required this.ownerApprovalThresholdBps,
    required this.proposalShareThreshold,
    required this.quorumShareBps,
    required this.shareholderRightsPreservedOnSale,
  });

  final String governanceMode;
  final String voteWeightModel;
  final bool antiTakeoverEnabled;
  final int maxHolderBps;
  final int ownerApprovalThresholdBps;
  final int proposalShareThreshold;
  final int quorumShareBps;
  final bool shareholderRightsPreservedOnSale;

  factory CreatorClubGovernancePolicy.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator governance policy');
    return CreatorClubGovernancePolicy(
      governanceMode:
          GteJson.string(json, <String>['governance_mode', 'governanceMode']),
      voteWeightModel: GteJson.string(
          json, <String>['vote_weight_model', 'voteWeightModel']),
      antiTakeoverEnabled: GteJson.boolean(
        json,
        <String>['anti_takeover_enabled', 'antiTakeoverEnabled'],
      ),
      maxHolderBps:
          GteJson.integer(json, <String>['max_holder_bps', 'maxHolderBps']),
      ownerApprovalThresholdBps: GteJson.integer(
        json,
        <String>[
          'owner_approval_threshold_bps',
          'ownerApprovalThresholdBps',
        ],
      ),
      proposalShareThreshold: GteJson.integer(
        json,
        <String>['proposal_share_threshold', 'proposalShareThreshold'],
      ),
      quorumShareBps:
          GteJson.integer(json, <String>['quorum_share_bps', 'quorumShareBps']),
      shareholderRightsPreservedOnSale: GteJson.boolean(
        json,
        <String>[
          'shareholder_rights_preserved_on_sale',
          'shareholderRightsPreservedOnSale',
        ],
      ),
    );
  }
}

class CreatorClubOwnershipLedgerEntry {
  const CreatorClubOwnershipLedgerEntry({
    required this.entryType,
    required this.entryReferenceId,
    required this.userId,
    required this.shareDelta,
    required this.ownershipBps,
    required this.createdAt,
    required this.summary,
    required this.metadata,
  });

  final String entryType;
  final String entryReferenceId;
  final String? userId;
  final int shareDelta;
  final int ownershipBps;
  final DateTime createdAt;
  final String summary;
  final Map<String, Object?> metadata;

  factory CreatorClubOwnershipLedgerEntry.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator ownership ledger entry');
    return CreatorClubOwnershipLedgerEntry(
      entryType: GteJson.string(json, <String>['entry_type', 'entryType']),
      entryReferenceId: GteJson.string(
        json,
        <String>['entry_reference_id', 'entryReferenceId'],
      ),
      userId: GteJson.stringOrNull(json, <String>['user_id', 'userId']),
      shareDelta: GteJson.integer(json, <String>['share_delta', 'shareDelta']),
      ownershipBps:
          GteJson.integer(json, <String>['ownership_bps', 'ownershipBps']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      summary: GteJson.string(json, <String>['summary']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class CreatorClubOwnershipLedger {
  const CreatorClubOwnershipLedger({
    required this.currentOwnerUserId,
    required this.totalGovernanceShares,
    required this.shareholderCount,
    required this.circulatingShareCount,
    required this.lastTransferId,
    required this.lastTransferAt,
    required this.recentEntries,
  });

  final String currentOwnerUserId;
  final int totalGovernanceShares;
  final int shareholderCount;
  final int circulatingShareCount;
  final String? lastTransferId;
  final DateTime? lastTransferAt;
  final List<CreatorClubOwnershipLedgerEntry> recentEntries;

  factory CreatorClubOwnershipLedger.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator ownership ledger');
    return CreatorClubOwnershipLedger(
      currentOwnerUserId: GteJson.string(
        json,
        <String>['current_owner_user_id', 'currentOwnerUserId'],
      ),
      totalGovernanceShares: GteJson.integer(
        json,
        <String>['total_governance_shares', 'totalGovernanceShares'],
      ),
      shareholderCount: GteJson.integer(
          json, <String>['shareholder_count', 'shareholderCount']),
      circulatingShareCount: GteJson.integer(
        json,
        <String>['circulating_share_count', 'circulatingShareCount'],
      ),
      lastTransferId: GteJson.stringOrNull(
        json,
        <String>['last_transfer_id', 'lastTransferId'],
      ),
      lastTransferAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_transfer_at', 'lastTransferAt'],
      ),
      recentEntries: GteJson.typedList(
        json,
        <String>['recent_entries', 'recentEntries'],
        CreatorClubOwnershipLedgerEntry.fromJson,
      ),
    );
  }
}

class CreatorClubShareMarket {
  const CreatorClubShareMarket({
    required this.id,
    required this.clubId,
    required this.creatorUserId,
    required this.issuedByUserId,
    required this.status,
    required this.sharePriceCoin,
    required this.maxSharesIssued,
    required this.sharesSold,
    required this.sharesRemaining,
    required this.maxSharesPerFan,
    required this.creatorControlledShares,
    required this.creatorControlBps,
    required this.shareholderRevenueShareBps,
    required this.shareholderCount,
    required this.totalPurchaseVolumeCoin,
    required this.totalRevenueDistributedCoin,
    required this.metadata,
    required this.governancePolicy,
    required this.ownershipLedger,
    required this.createdAt,
    required this.updatedAt,
    required this.viewerHolding,
    required this.viewerBenefits,
  });

  final String id;
  final String clubId;
  final String creatorUserId;
  final String issuedByUserId;
  final String status;
  final double sharePriceCoin;
  final int maxSharesIssued;
  final int sharesSold;
  final int sharesRemaining;
  final int maxSharesPerFan;
  final int creatorControlledShares;
  final int creatorControlBps;
  final int shareholderRevenueShareBps;
  final int shareholderCount;
  final double totalPurchaseVolumeCoin;
  final double totalRevenueDistributedCoin;
  final Map<String, Object?> metadata;
  final CreatorClubGovernancePolicy governancePolicy;
  final CreatorClubOwnershipLedger ownershipLedger;
  final DateTime createdAt;
  final DateTime updatedAt;
  final CreatorClubShareHolding? viewerHolding;
  final CreatorClubShareBenefit viewerBenefits;

  factory CreatorClubShareMarket.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share market');
    return CreatorClubShareMarket(
      id: GteJson.string(json, <String>['id']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      creatorUserId:
          GteJson.string(json, <String>['creator_user_id', 'creatorUserId']),
      issuedByUserId:
          GteJson.string(json, <String>['issued_by_user_id', 'issuedByUserId']),
      status: GteJson.string(json, <String>['status']),
      sharePriceCoin:
          GteJson.number(json, <String>['share_price_coin', 'sharePriceCoin']),
      maxSharesIssued: GteJson.integer(
        json,
        <String>['max_shares_issued', 'maxSharesIssued'],
      ),
      sharesSold: GteJson.integer(json, <String>['shares_sold', 'sharesSold']),
      sharesRemaining: GteJson.integer(
        json,
        <String>['shares_remaining', 'sharesRemaining'],
      ),
      maxSharesPerFan: GteJson.integer(
        json,
        <String>['max_shares_per_fan', 'maxSharesPerFan'],
      ),
      creatorControlledShares: GteJson.integer(
        json,
        <String>['creator_controlled_shares', 'creatorControlledShares'],
      ),
      creatorControlBps: GteJson.integer(
        json,
        <String>['creator_control_bps', 'creatorControlBps'],
      ),
      shareholderRevenueShareBps: GteJson.integer(
        json,
        <String>[
          'shareholder_revenue_share_bps',
          'shareholderRevenueShareBps',
        ],
      ),
      shareholderCount: GteJson.integer(
        json,
        <String>['shareholder_count', 'shareholderCount'],
      ),
      totalPurchaseVolumeCoin: GteJson.number(
        json,
        <String>['total_purchase_volume_coin', 'totalPurchaseVolumeCoin'],
      ),
      totalRevenueDistributedCoin: GteJson.number(
        json,
        <String>[
          'total_revenue_distributed_coin',
          'totalRevenueDistributedCoin',
        ],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      governancePolicy: CreatorClubGovernancePolicy.fromJson(
        GteJson.value(json, <String>['governance_policy', 'governancePolicy']),
      ),
      ownershipLedger: CreatorClubOwnershipLedger.fromJson(
        GteJson.value(json, <String>['ownership_ledger', 'ownershipLedger']),
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
      viewerHolding:
          GteJson.value(json, <String>['viewer_holding', 'viewerHolding']) ==
                  null
              ? null
              : CreatorClubShareHolding.fromJson(
                  GteJson.value(
                    json,
                    <String>['viewer_holding', 'viewerHolding'],
                  ),
                ),
      viewerBenefits: CreatorClubShareBenefit.fromJson(
        GteJson.value(json, <String>['viewer_benefits', 'viewerBenefits']),
      ),
    );
  }
}

class CreatorClubSharePurchase {
  const CreatorClubSharePurchase({
    required this.id,
    required this.marketId,
    required this.clubId,
    required this.creatorUserId,
    required this.userId,
    required this.shareCount,
    required this.sharePriceCoin,
    required this.totalPriceCoin,
    required this.ledgerTransactionId,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String marketId;
  final String clubId;
  final String creatorUserId;
  final String userId;
  final int shareCount;
  final double sharePriceCoin;
  final double totalPriceCoin;
  final String? ledgerTransactionId;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubSharePurchase.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share purchase');
    return CreatorClubSharePurchase(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      creatorUserId:
          GteJson.string(json, <String>['creator_user_id', 'creatorUserId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      shareCount: GteJson.integer(json, <String>['share_count', 'shareCount']),
      sharePriceCoin:
          GteJson.number(json, <String>['share_price_coin', 'sharePriceCoin']),
      totalPriceCoin:
          GteJson.number(json, <String>['total_price_coin', 'totalPriceCoin']),
      ledgerTransactionId: GteJson.stringOrNull(
        json,
        <String>['ledger_transaction_id', 'ledgerTransactionId'],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class CreatorClubShareDistribution {
  const CreatorClubShareDistribution({
    required this.id,
    required this.marketId,
    required this.clubId,
    required this.creatorUserId,
    required this.distributionType,
    required this.grossRevenueCoin,
    required this.shareholderPoolCoin,
    required this.shareholderRevenueShareBps,
    required this.eligibleShareCount,
    required this.eligibleShareholderCount,
    required this.status,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String marketId;
  final String clubId;
  final String creatorUserId;
  final String distributionType;
  final double grossRevenueCoin;
  final double shareholderPoolCoin;
  final int shareholderRevenueShareBps;
  final int eligibleShareCount;
  final int eligibleShareholderCount;
  final String status;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubShareDistribution.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator share distribution');
    return CreatorClubShareDistribution(
      id: GteJson.string(json, <String>['id']),
      marketId: GteJson.string(json, <String>['market_id', 'marketId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      creatorUserId:
          GteJson.string(json, <String>['creator_user_id', 'creatorUserId']),
      distributionType: GteJson.string(
        json,
        <String>['distribution_type', 'distributionType'],
        fallback: 'revenue',
      ),
      grossRevenueCoin: GteJson.number(
          json, <String>['gross_revenue_coin', 'grossRevenueCoin']),
      shareholderPoolCoin: GteJson.number(
        json,
        <String>['shareholder_pool_coin', 'shareholderPoolCoin'],
      ),
      shareholderRevenueShareBps: GteJson.integer(
        json,
        <String>[
          'shareholder_revenue_share_bps',
          'shareholderRevenueShareBps',
        ],
      ),
      eligibleShareCount: GteJson.integer(
        json,
        <String>['eligible_share_count', 'eligibleShareCount'],
      ),
      eligibleShareholderCount: GteJson.integer(
        json,
        <String>[
          'eligible_shareholder_count',
          'eligibleShareholderCount',
        ],
      ),
      status: GteJson.string(json, <String>['status']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}
