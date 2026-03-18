import '../../shared/data/gte_feature_support.dart';

class CreatorClubShareMarketIssueRequest {
  const CreatorClubShareMarketIssueRequest({
    required this.sharePriceCoin,
    required this.maxSharesIssued,
    this.maxSharesPerFan,
    this.metadata = const <String, Object?>{},
  });

  final double sharePriceCoin;
  final int maxSharesIssued;
  final int? maxSharesPerFan;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'share_price_coin': sharePriceCoin,
      'max_shares_issued': maxSharesIssued,
      if (maxSharesPerFan != null) 'max_shares_per_fan': maxSharesPerFan,
      'metadata_json': metadata,
    };
  }
}

class CreatorClubSharePurchaseRequest {
  const CreatorClubSharePurchaseRequest({
    required this.shareCount,
  });

  final int shareCount;

  JsonMap toJson() => <String, Object?>{'share_count': shareCount};
}

class CreatorClubShareMarketControlUpdateRequest {
  const CreatorClubShareMarketControlUpdateRequest({
    required this.maxSharesPerClub,
    required this.maxSharesPerFan,
    required this.shareholderRevenueShareBps,
    required this.issuanceEnabled,
    required this.purchaseEnabled,
    required this.maxPrimaryPurchaseValueCoin,
  });

  final int maxSharesPerClub;
  final int maxSharesPerFan;
  final int shareholderRevenueShareBps;
  final bool issuanceEnabled;
  final bool purchaseEnabled;
  final double maxPrimaryPurchaseValueCoin;

  JsonMap toJson() {
    return <String, Object?>{
      'max_shares_per_club': maxSharesPerClub,
      'max_shares_per_fan': maxSharesPerFan,
      'shareholder_revenue_share_bps': shareholderRevenueShareBps,
      'issuance_enabled': issuanceEnabled,
      'purchase_enabled': purchaseEnabled,
      'max_primary_purchase_value_coin': maxPrimaryPurchaseValueCoin,
    };
  }
}

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
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubShareMarketControl.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share market control');
    return CreatorClubShareMarketControl(
      id: stringValue(json['id']),
      controlKey: stringValue(json['control_key']),
      maxSharesPerClub: intValue(json['max_shares_per_club']),
      maxSharesPerFan: intValue(json['max_shares_per_fan']),
      shareholderRevenueShareBps:
          intValue(json['shareholder_revenue_share_bps']),
      issuanceEnabled: boolValue(json['issuance_enabled']),
      purchaseEnabled: boolValue(json['purchase_enabled']),
      maxPrimaryPurchaseValueCoin: numberValue(
        json['max_primary_purchase_value_coin'],
      ),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
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
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubShareHolding.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share holding');
    return CreatorClubShareHolding(
      id: stringValue(json['id']),
      marketId: stringValue(json['market_id']),
      clubId: stringValue(json['club_id']),
      userId: stringValue(json['user_id']),
      shareCount: intValue(json['share_count']),
      totalSpentCoin: numberValue(json['total_spent_coin']),
      revenueEarnedCoin: numberValue(json['revenue_earned_coin']),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
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
    final JsonMap json = jsonMap(value, label: 'creator share benefits');
    return CreatorClubShareBenefit(
      shareholder: boolValue(json['shareholder']),
      shareCount: intValue(json['share_count']),
      hasPriorityChatVisibility:
          boolValue(json['has_priority_chat_visibility']),
      hasEarlyTicketAccess: boolValue(json['has_early_ticket_access']),
      hasCosmeticVotingRights: boolValue(json['has_cosmetic_voting_rights']),
      tournamentQualificationMethod: stringOrNullValue(
        json['tournament_qualification_method'],
      ),
      cosmeticVotePower: intValue(json['cosmetic_vote_power']),
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
    final JsonMap json = jsonMap(value, label: 'creator governance policy');
    return CreatorClubGovernancePolicy(
      governanceMode: stringValue(json['governance_mode']),
      voteWeightModel: stringValue(json['vote_weight_model']),
      antiTakeoverEnabled: boolValue(json['anti_takeover_enabled']),
      maxHolderBps: intValue(json['max_holder_bps']),
      ownerApprovalThresholdBps: intValue(json['owner_approval_threshold_bps']),
      proposalShareThreshold: intValue(json['proposal_share_threshold']),
      quorumShareBps: intValue(json['quorum_share_bps']),
      shareholderRightsPreservedOnSale: boolValue(
        json['shareholder_rights_preserved_on_sale'],
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
  final JsonMap metadata;

  factory CreatorClubOwnershipLedgerEntry.fromJson(Object? value) {
    final JsonMap json =
        jsonMap(value, label: 'creator ownership ledger entry');
    return CreatorClubOwnershipLedgerEntry(
      entryType: stringValue(json['entry_type']),
      entryReferenceId: stringValue(json['entry_reference_id']),
      userId: stringOrNullValue(json['user_id']),
      shareDelta: intValue(json['share_delta']),
      ownershipBps: intValue(json['ownership_bps']),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      summary: stringValue(json['summary']),
      metadata: jsonMap(
        json['metadata_json'],
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
    final JsonMap json = jsonMap(value, label: 'creator ownership ledger');
    return CreatorClubOwnershipLedger(
      currentOwnerUserId: stringValue(json['current_owner_user_id']),
      totalGovernanceShares: intValue(json['total_governance_shares']),
      shareholderCount: intValue(json['shareholder_count']),
      circulatingShareCount: intValue(json['circulating_share_count']),
      lastTransferId: stringOrNullValue(json['last_transfer_id']),
      lastTransferAt: dateTimeValue(json['last_transfer_at']),
      recentEntries: parseList(
        json['recent_entries'],
        CreatorClubOwnershipLedgerEntry.fromJson,
        label: 'creator ownership ledger entries',
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
  final JsonMap metadata;
  final CreatorClubGovernancePolicy governancePolicy;
  final CreatorClubOwnershipLedger ownershipLedger;
  final DateTime createdAt;
  final DateTime updatedAt;
  final CreatorClubShareHolding? viewerHolding;
  final CreatorClubShareBenefit viewerBenefits;

  factory CreatorClubShareMarket.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share market');
    return CreatorClubShareMarket(
      id: stringValue(json['id']),
      clubId: stringValue(json['club_id']),
      creatorUserId: stringValue(json['creator_user_id']),
      issuedByUserId: stringValue(json['issued_by_user_id']),
      status: stringValue(json['status']),
      sharePriceCoin: numberValue(json['share_price_coin']),
      maxSharesIssued: intValue(json['max_shares_issued']),
      sharesSold: intValue(json['shares_sold']),
      sharesRemaining: intValue(json['shares_remaining']),
      maxSharesPerFan: intValue(json['max_shares_per_fan']),
      creatorControlledShares: intValue(json['creator_controlled_shares']),
      creatorControlBps: intValue(json['creator_control_bps']),
      shareholderRevenueShareBps: intValue(
        json['shareholder_revenue_share_bps'],
      ),
      shareholderCount: intValue(json['shareholder_count']),
      totalPurchaseVolumeCoin: numberValue(json['total_purchase_volume_coin']),
      totalRevenueDistributedCoin: numberValue(
        json['total_revenue_distributed_coin'],
      ),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      governancePolicy: CreatorClubGovernancePolicy.fromJson(
        json['governance_policy'],
      ),
      ownershipLedger: CreatorClubOwnershipLedger.fromJson(
        json['ownership_ledger'],
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      viewerHolding: jsonMapOrNull(json['viewer_holding']) == null
          ? null
          : CreatorClubShareHolding.fromJson(json['viewer_holding']),
      viewerBenefits: CreatorClubShareBenefit.fromJson(json['viewer_benefits']),
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
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubSharePurchase.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share purchase');
    return CreatorClubSharePurchase(
      id: stringValue(json['id']),
      marketId: stringValue(json['market_id']),
      clubId: stringValue(json['club_id']),
      creatorUserId: stringValue(json['creator_user_id']),
      userId: stringValue(json['user_id']),
      shareCount: intValue(json['share_count']),
      sharePriceCoin: numberValue(json['share_price_coin']),
      totalPriceCoin: numberValue(json['total_price_coin']),
      ledgerTransactionId: stringOrNullValue(json['ledger_transaction_id']),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    );
  }
}

class CreatorClubSharePayout {
  const CreatorClubSharePayout({
    required this.id,
    required this.distributionId,
    required this.holdingId,
    required this.clubId,
    required this.userId,
    required this.shareCount,
    required this.payoutCoin,
    required this.ownershipBps,
    required this.ledgerTransactionId,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String distributionId;
  final String? holdingId;
  final String clubId;
  final String userId;
  final int shareCount;
  final double payoutCoin;
  final int ownershipBps;
  final String? ledgerTransactionId;
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CreatorClubSharePayout.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share payout');
    return CreatorClubSharePayout(
      id: stringValue(json['id']),
      distributionId: stringValue(json['distribution_id']),
      holdingId: stringOrNullValue(json['holding_id']),
      clubId: stringValue(json['club_id']),
      userId: stringValue(json['user_id']),
      shareCount: intValue(json['share_count']),
      payoutCoin: numberValue(json['payout_coin']),
      ownershipBps: intValue(json['ownership_bps']),
      ledgerTransactionId: stringOrNullValue(json['ledger_transaction_id']),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    );
  }
}

class CreatorClubShareDistribution {
  const CreatorClubShareDistribution({
    required this.id,
    required this.marketId,
    required this.clubId,
    required this.creatorUserId,
    required this.sourceType,
    required this.sourceReferenceId,
    required this.seasonId,
    required this.competitionId,
    required this.matchId,
    required this.eligibleRevenueCoin,
    required this.shareholderPoolCoin,
    required this.creatorRetainedCoin,
    required this.shareholderRevenueShareBps,
    required this.distributedShareCount,
    required this.recipientCount,
    required this.status,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
    required this.payouts,
  });

  final String id;
  final String marketId;
  final String clubId;
  final String creatorUserId;
  final String sourceType;
  final String sourceReferenceId;
  final String? seasonId;
  final String? competitionId;
  final String? matchId;
  final double eligibleRevenueCoin;
  final double shareholderPoolCoin;
  final double creatorRetainedCoin;
  final int shareholderRevenueShareBps;
  final int distributedShareCount;
  final int recipientCount;
  final String status;
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<CreatorClubSharePayout> payouts;

  double get totalPayoutCoin => payouts.fold<double>(
        0,
        (double sum, CreatorClubSharePayout payout) => sum + payout.payoutCoin,
      );

  factory CreatorClubShareDistribution.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'creator share distribution');
    return CreatorClubShareDistribution(
      id: stringValue(json['id']),
      marketId: stringValue(json['market_id']),
      clubId: stringValue(json['club_id']),
      creatorUserId: stringValue(json['creator_user_id']),
      sourceType: stringValue(json['source_type']),
      sourceReferenceId: stringValue(json['source_reference_id']),
      seasonId: stringOrNullValue(json['season_id']),
      competitionId: stringOrNullValue(json['competition_id']),
      matchId: stringOrNullValue(json['match_id']),
      eligibleRevenueCoin: numberValue(json['eligible_revenue_coin']),
      shareholderPoolCoin: numberValue(json['shareholder_pool_coin']),
      creatorRetainedCoin: numberValue(json['creator_retained_coin']),
      shareholderRevenueShareBps: intValue(
        json['shareholder_revenue_share_bps'],
      ),
      distributedShareCount: intValue(json['distributed_share_count']),
      recipientCount: intValue(json['recipient_count']),
      status: stringValue(json['status']),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: dateTimeValue(json['updated_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      payouts: parseList(
        json['payouts'],
        CreatorClubSharePayout.fromJson,
        label: 'creator share payouts',
      ),
    );
  }
}
