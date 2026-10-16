import 'package:gte_frontend/data/gte_models.dart';

class ClubSaleValuationBreakdown {
  const ClubSaleValuationBreakdown({
    required this.firstTeamValue,
    required this.reserveSquadValue,
    required this.u19SquadValue,
    required this.academyValue,
    required this.stadiumValue,
    required this.paidEnhancementsValue,
    required this.metadata,
  });

  final double firstTeamValue;
  final double reserveSquadValue;
  final double u19SquadValue;
  final double academyValue;
  final double stadiumValue;
  final double paidEnhancementsValue;
  final Map<String, Object?> metadata;

  factory ClubSaleValuationBreakdown.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale valuation breakdown');
    return ClubSaleValuationBreakdown(
      firstTeamValue:
          GteJson.number(json, <String>['first_team_value', 'firstTeamValue']),
      reserveSquadValue: GteJson.number(
        json,
        <String>['reserve_squad_value', 'reserveSquadValue'],
      ),
      u19SquadValue:
          GteJson.number(json, <String>['u19_squad_value', 'u19SquadValue']),
      academyValue:
          GteJson.number(json, <String>['academy_value', 'academyValue']),
      stadiumValue:
          GteJson.number(json, <String>['stadium_value', 'stadiumValue']),
      paidEnhancementsValue: GteJson.number(
        json,
        <String>['paid_enhancements_value', 'paidEnhancementsValue'],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class ClubSaleValuation {
  const ClubSaleValuation({
    required this.clubId,
    required this.clubName,
    required this.currency,
    required this.systemValuation,
    required this.systemValuationMinor,
    required this.breakdown,
    required this.lastRefreshedAt,
  });

  final String clubId;
  final String clubName;
  final String currency;
  final double systemValuation;
  final int systemValuationMinor;
  final ClubSaleValuationBreakdown breakdown;
  final DateTime? lastRefreshedAt;

  factory ClubSaleValuation.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale valuation');
    return ClubSaleValuation(
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, <String>['club_name', 'clubName']),
      currency: GteJson.string(json, <String>['currency'], fallback: 'credits'),
      systemValuation: GteJson.number(
        json,
        <String>['system_valuation', 'systemValuation'],
      ),
      systemValuationMinor: GteJson.integer(
        json,
        <String>['system_valuation_minor', 'systemValuationMinor'],
      ),
      breakdown: ClubSaleValuationBreakdown.fromJson(
        GteJson.value(json, <String>['breakdown']),
      ),
      lastRefreshedAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_refreshed_at', 'lastRefreshedAt'],
      ),
    );
  }
}

class ClubSaleListingSummary {
  const ClubSaleListingSummary({
    required this.listingId,
    required this.clubId,
    required this.clubName,
    required this.sellerUserId,
    required this.status,
    required this.visibility,
    required this.currency,
    required this.askingPrice,
    required this.systemValuation,
    required this.systemValuationMinor,
    required this.valuationLastRefreshedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  final String listingId;
  final String clubId;
  final String clubName;
  final String sellerUserId;
  final String status;
  final String visibility;
  final String currency;
  final double askingPrice;
  final double systemValuation;
  final int systemValuationMinor;
  final DateTime? valuationLastRefreshedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ClubSaleListingSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale listing summary');
    return ClubSaleListingSummary(
      listingId: GteJson.string(json, <String>['listing_id', 'listingId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, <String>['club_name', 'clubName']),
      sellerUserId:
          GteJson.string(json, <String>['seller_user_id', 'sellerUserId']),
      status: GteJson.string(json, <String>['status']),
      visibility:
          GteJson.string(json, <String>['visibility'], fallback: 'public'),
      currency: GteJson.string(json, <String>['currency'], fallback: 'credits'),
      askingPrice:
          GteJson.number(json, <String>['asking_price', 'askingPrice']),
      systemValuation: GteJson.number(
        json,
        <String>['system_valuation', 'systemValuation'],
      ),
      systemValuationMinor: GteJson.integer(
        json,
        <String>['system_valuation_minor', 'systemValuationMinor'],
      ),
      valuationLastRefreshedAt: GteJson.dateTimeOrNull(
        json,
        <String>['valuation_last_refreshed_at', 'valuationLastRefreshedAt'],
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class ClubSaleListingDetail extends ClubSaleListingSummary {
  const ClubSaleListingDetail({
    required super.listingId,
    required super.clubId,
    required super.clubName,
    required super.sellerUserId,
    required super.status,
    required super.visibility,
    required super.currency,
    required super.askingPrice,
    required super.systemValuation,
    required super.systemValuationMinor,
    required super.valuationLastRefreshedAt,
    required super.createdAt,
    required super.updatedAt,
    required this.valuationBreakdown,
    required this.note,
    required this.metadata,
  });

  final ClubSaleValuationBreakdown valuationBreakdown;
  final String? note;
  final Map<String, Object?> metadata;

  factory ClubSaleListingDetail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale listing detail');
    final ClubSaleListingSummary summary =
        ClubSaleListingSummary.fromJson(json);
    return ClubSaleListingDetail(
      listingId: summary.listingId,
      clubId: summary.clubId,
      clubName: summary.clubName,
      sellerUserId: summary.sellerUserId,
      status: summary.status,
      visibility: summary.visibility,
      currency: summary.currency,
      askingPrice: summary.askingPrice,
      systemValuation: summary.systemValuation,
      systemValuationMinor: summary.systemValuationMinor,
      valuationLastRefreshedAt: summary.valuationLastRefreshedAt,
      createdAt: summary.createdAt,
      updatedAt: summary.updatedAt,
      valuationBreakdown: ClubSaleValuationBreakdown.fromJson(
        GteJson.value(
          json,
          <String>['valuation_breakdown', 'valuationBreakdown'],
        ),
      ),
      note: GteJson.stringOrNull(json, <String>['note']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class ClubSaleListingCollection {
  const ClubSaleListingCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleListingSummary> items;

  factory ClubSaleListingCollection.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale listing collection');
    return ClubSaleListingCollection(
      total: GteJson.integer(json, <String>['total']),
      items: GteJson.typedList(
        json,
        <String>['items'],
        ClubSaleListingSummary.fromJson,
      ),
    );
  }
}

class ClubSaleInquiry {
  const ClubSaleInquiry({
    required this.inquiryId,
    required this.clubId,
    required this.listingId,
    required this.sellerUserId,
    required this.buyerUserId,
    required this.status,
    required this.message,
    required this.responseMessage,
    required this.respondedByUserId,
    required this.respondedAt,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String inquiryId;
  final String clubId;
  final String? listingId;
  final String sellerUserId;
  final String buyerUserId;
  final String status;
  final String message;
  final String? responseMessage;
  final String? respondedByUserId;
  final DateTime? respondedAt;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ClubSaleInquiry.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale inquiry');
    return ClubSaleInquiry(
      inquiryId: GteJson.string(json, <String>['inquiry_id', 'inquiryId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      listingId:
          GteJson.stringOrNull(json, <String>['listing_id', 'listingId']),
      sellerUserId:
          GteJson.string(json, <String>['seller_user_id', 'sellerUserId']),
      buyerUserId:
          GteJson.string(json, <String>['buyer_user_id', 'buyerUserId']),
      status: GteJson.string(json, <String>['status']),
      message: GteJson.string(json, <String>['message']),
      responseMessage: GteJson.stringOrNull(
        json,
        <String>['response_message', 'responseMessage'],
      ),
      respondedByUserId: GteJson.stringOrNull(
        json,
        <String>['responded_by_user_id', 'respondedByUserId'],
      ),
      respondedAt:
          GteJson.dateTimeOrNull(json, <String>['responded_at', 'respondedAt']),
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

class ClubSaleInquiryCollection {
  const ClubSaleInquiryCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleInquiry> items;

  factory ClubSaleInquiryCollection.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale inquiry collection');
    return ClubSaleInquiryCollection(
      total: GteJson.integer(json, <String>['total']),
      items: GteJson.typedList(
        json,
        <String>['items'],
        ClubSaleInquiry.fromJson,
      ),
    );
  }
}

class ClubSaleOffer {
  const ClubSaleOffer({
    required this.offerId,
    required this.clubId,
    required this.listingId,
    required this.inquiryId,
    required this.parentOfferId,
    required this.sellerUserId,
    required this.buyerUserId,
    required this.proposerUserId,
    required this.counterpartyUserId,
    required this.offerType,
    required this.status,
    required this.currency,
    required this.offerPrice,
    required this.message,
    required this.respondedMessage,
    required this.respondedByUserId,
    required this.respondedAt,
    required this.acceptedAt,
    required this.rejectedAt,
    required this.expiresAt,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String offerId;
  final String clubId;
  final String? listingId;
  final String? inquiryId;
  final String? parentOfferId;
  final String sellerUserId;
  final String buyerUserId;
  final String proposerUserId;
  final String counterpartyUserId;
  final String offerType;
  final String status;
  final String currency;
  final double offerPrice;
  final String? message;
  final String? respondedMessage;
  final String? respondedByUserId;
  final DateTime? respondedAt;
  final DateTime? acceptedAt;
  final DateTime? rejectedAt;
  final DateTime? expiresAt;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ClubSaleOffer.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale offer');
    return ClubSaleOffer(
      offerId: GteJson.string(json, <String>['offer_id', 'offerId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      listingId:
          GteJson.stringOrNull(json, <String>['listing_id', 'listingId']),
      inquiryId:
          GteJson.stringOrNull(json, <String>['inquiry_id', 'inquiryId']),
      parentOfferId: GteJson.stringOrNull(
        json,
        <String>['parent_offer_id', 'parentOfferId'],
      ),
      sellerUserId:
          GteJson.string(json, <String>['seller_user_id', 'sellerUserId']),
      buyerUserId:
          GteJson.string(json, <String>['buyer_user_id', 'buyerUserId']),
      proposerUserId:
          GteJson.string(json, <String>['proposer_user_id', 'proposerUserId']),
      counterpartyUserId: GteJson.string(
        json,
        <String>['counterparty_user_id', 'counterpartyUserId'],
      ),
      offerType: GteJson.string(json, <String>['offer_type', 'offerType']),
      status: GteJson.string(json, <String>['status']),
      currency: GteJson.string(json, <String>['currency'], fallback: 'credits'),
      offerPrice: GteJson.number(json, <String>['offer_price', 'offerPrice']),
      message: GteJson.stringOrNull(json, <String>['message']),
      respondedMessage: GteJson.stringOrNull(
        json,
        <String>['responded_message', 'respondedMessage'],
      ),
      respondedByUserId: GteJson.stringOrNull(
        json,
        <String>['responded_by_user_id', 'respondedByUserId'],
      ),
      respondedAt:
          GteJson.dateTimeOrNull(json, <String>['responded_at', 'respondedAt']),
      acceptedAt:
          GteJson.dateTimeOrNull(json, <String>['accepted_at', 'acceptedAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      expiresAt:
          GteJson.dateTimeOrNull(json, <String>['expires_at', 'expiresAt']),
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

class ClubSaleOfferCollection {
  const ClubSaleOfferCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleOffer> items;

  factory ClubSaleOfferCollection.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale offer collection');
    return ClubSaleOfferCollection(
      total: GteJson.integer(json, <String>['total']),
      items: GteJson.typedList(
        json,
        <String>['items'],
        ClubSaleOffer.fromJson,
      ),
    );
  }
}

class ClubSaleOwnershipTransition {
  const ClubSaleOwnershipTransition({
    required this.previousOwnerUserId,
    required this.newOwnerUserId,
    required this.ownershipLineageIndex,
    required this.shareholderCountPreserved,
    required this.shareholderRightsPreserved,
  });

  final String? previousOwnerUserId;
  final String? newOwnerUserId;
  final int ownershipLineageIndex;
  final int shareholderCountPreserved;
  final bool shareholderRightsPreserved;

  factory ClubSaleOwnershipTransition.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale ownership transition');
    return ClubSaleOwnershipTransition(
      previousOwnerUserId: GteJson.stringOrNull(
        json,
        <String>['previous_owner_user_id', 'previousOwnerUserId'],
      ),
      newOwnerUserId: GteJson.stringOrNull(
        json,
        <String>['new_owner_user_id', 'newOwnerUserId'],
      ),
      ownershipLineageIndex: GteJson.integer(
        json,
        <String>['ownership_lineage_index', 'ownershipLineageIndex'],
      ),
      shareholderCountPreserved: GteJson.integer(
        json,
        <String>['shareholder_count_preserved', 'shareholderCountPreserved'],
      ),
      shareholderRightsPreserved: GteJson.boolean(
        json,
        <String>[
          'shareholder_rights_preserved',
          'shareholderRightsPreserved',
        ],
      ),
    );
  }
}

class ClubSaleTransferExecution {
  const ClubSaleTransferExecution({
    required this.transferId,
    required this.clubId,
    required this.listingId,
    required this.offerId,
    required this.sellerUserId,
    required this.buyerUserId,
    required this.currency,
    required this.executedSalePrice,
    required this.platformFeeAmount,
    required this.sellerNetAmount,
    required this.platformFeeBps,
    required this.status,
    required this.settlementReference,
    required this.ledgerTransactionId,
    required this.storyFeedItemId,
    required this.calendarEventId,
    required this.metadata,
    required this.ownershipTransition,
    required this.createdAt,
  });

  final String transferId;
  final String clubId;
  final String? listingId;
  final String offerId;
  final String sellerUserId;
  final String buyerUserId;
  final String currency;
  final double executedSalePrice;
  final double platformFeeAmount;
  final double sellerNetAmount;
  final int platformFeeBps;
  final String status;
  final String settlementReference;
  final String? ledgerTransactionId;
  final String? storyFeedItemId;
  final String? calendarEventId;
  final Map<String, Object?> metadata;
  final ClubSaleOwnershipTransition? ownershipTransition;
  final DateTime createdAt;

  factory ClubSaleTransferExecution.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale transfer execution');
    return ClubSaleTransferExecution(
      transferId: GteJson.string(json, <String>['transfer_id', 'transferId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      listingId:
          GteJson.stringOrNull(json, <String>['listing_id', 'listingId']),
      offerId: GteJson.string(json, <String>['offer_id', 'offerId']),
      sellerUserId:
          GteJson.string(json, <String>['seller_user_id', 'sellerUserId']),
      buyerUserId:
          GteJson.string(json, <String>['buyer_user_id', 'buyerUserId']),
      currency: GteJson.string(json, <String>['currency'], fallback: 'credits'),
      executedSalePrice: GteJson.number(
        json,
        <String>['executed_sale_price', 'executedSalePrice'],
      ),
      platformFeeAmount: GteJson.number(
        json,
        <String>['platform_fee_amount', 'platformFeeAmount'],
      ),
      sellerNetAmount: GteJson.number(
        json,
        <String>['seller_net_amount', 'sellerNetAmount'],
      ),
      platformFeeBps: GteJson.integer(
        json,
        <String>['platform_fee_bps', 'platformFeeBps'],
      ),
      status: GteJson.string(json, <String>['status']),
      settlementReference: GteJson.string(
        json,
        <String>['settlement_reference', 'settlementReference'],
      ),
      ledgerTransactionId: GteJson.stringOrNull(
        json,
        <String>['ledger_transaction_id', 'ledgerTransactionId'],
      ),
      storyFeedItemId: GteJson.stringOrNull(
        json,
        <String>['story_feed_item_id', 'storyFeedItemId'],
      ),
      calendarEventId: GteJson.stringOrNull(
        json,
        <String>['calendar_event_id', 'calendarEventId'],
      ),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      ownershipTransition:
          GteJson.value(json, <String>['ownership_transition']) == null
              ? null
              : ClubSaleOwnershipTransition.fromJson(
                  GteJson.value(json, <String>['ownership_transition']),
                ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
    );
  }
}

class ClubSaleAuditEvent {
  const ClubSaleAuditEvent({
    required this.id,
    required this.clubId,
    required this.listingId,
    required this.inquiryId,
    required this.offerId,
    required this.transferId,
    required this.actorUserId,
    required this.action,
    required this.statusFrom,
    required this.statusTo,
    required this.payload,
    required this.createdAt,
  });

  final String id;
  final String clubId;
  final String? listingId;
  final String? inquiryId;
  final String? offerId;
  final String? transferId;
  final String? actorUserId;
  final String action;
  final String? statusFrom;
  final String? statusTo;
  final Map<String, Object?> payload;
  final DateTime createdAt;

  factory ClubSaleAuditEvent.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale audit event');
    return ClubSaleAuditEvent(
      id: GteJson.string(json, <String>['id']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      listingId:
          GteJson.stringOrNull(json, <String>['listing_id', 'listingId']),
      inquiryId:
          GteJson.stringOrNull(json, <String>['inquiry_id', 'inquiryId']),
      offerId: GteJson.stringOrNull(json, <String>['offer_id', 'offerId']),
      transferId:
          GteJson.stringOrNull(json, <String>['transfer_id', 'transferId']),
      actorUserId:
          GteJson.stringOrNull(json, <String>['actor_user_id', 'actorUserId']),
      action: GteJson.string(json, <String>['action']),
      statusFrom:
          GteJson.stringOrNull(json, <String>['status_from', 'statusFrom']),
      statusTo: GteJson.stringOrNull(json, <String>['status_to', 'statusTo']),
      payload: GteJson.map(
        json,
        keys: <String>['payload_json', 'payloadJson', 'payload'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
    );
  }
}

class ClubSaleOwnershipHistoryEvent {
  const ClubSaleOwnershipHistoryEvent({
    required this.transferId,
    required this.sellerUserId,
    required this.buyerUserId,
    required this.executedSalePrice,
    required this.createdAt,
    required this.metadata,
  });

  final String transferId;
  final String sellerUserId;
  final String buyerUserId;
  final double executedSalePrice;
  final DateTime createdAt;
  final Map<String, Object?> metadata;

  factory ClubSaleOwnershipHistoryEvent.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale ownership history event');
    return ClubSaleOwnershipHistoryEvent(
      transferId: GteJson.string(json, <String>['transfer_id', 'transferId']),
      sellerUserId:
          GteJson.string(json, <String>['seller_user_id', 'sellerUserId']),
      buyerUserId:
          GteJson.string(json, <String>['buyer_user_id', 'buyerUserId']),
      executedSalePrice: GteJson.number(
        json,
        <String>['executed_sale_price', 'executedSalePrice'],
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class ClubSaleOwnershipHistory {
  const ClubSaleOwnershipHistory({
    required this.currentOwnerUserId,
    required this.transferCount,
    required this.ownershipEras,
    required this.shareholderCount,
    required this.activeGovernanceProposalCount,
    required this.lastTransferId,
    required this.lastTransferAt,
    required this.previousOwnerUserIds,
    required this.recentTransfers,
  });

  final String currentOwnerUserId;
  final int transferCount;
  final int ownershipEras;
  final int shareholderCount;
  final int activeGovernanceProposalCount;
  final String? lastTransferId;
  final DateTime? lastTransferAt;
  final List<String> previousOwnerUserIds;
  final List<ClubSaleOwnershipHistoryEvent> recentTransfers;

  factory ClubSaleOwnershipHistory.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale ownership history');
    return ClubSaleOwnershipHistory(
      currentOwnerUserId: GteJson.string(
        json,
        <String>['current_owner_user_id', 'currentOwnerUserId'],
      ),
      transferCount:
          GteJson.integer(json, <String>['transfer_count', 'transferCount']),
      ownershipEras:
          GteJson.integer(json, <String>['ownership_eras', 'ownershipEras']),
      shareholderCount: GteJson.integer(
          json, <String>['shareholder_count', 'shareholderCount']),
      activeGovernanceProposalCount: GteJson.integer(
        json,
        <String>[
          'active_governance_proposal_count',
          'activeGovernanceProposalCount',
        ],
      ),
      lastTransferId: GteJson.stringOrNull(
        json,
        <String>['last_transfer_id', 'lastTransferId'],
      ),
      lastTransferAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_transfer_at', 'lastTransferAt'],
      ),
      previousOwnerUserIds: GteJson.list(
        GteJson.value(
          json,
          <String>['previous_owner_user_ids', 'previousOwnerUserIds'],
        ),
        label: 'previous owner user ids',
      ).map((Object? item) => item.toString()).toList(growable: false),
      recentTransfers: GteJson.typedList(
        json,
        <String>['recent_transfers', 'recentTransfers'],
        ClubSaleOwnershipHistoryEvent.fromJson,
      ),
    );
  }
}

class ClubSaleDynastySnapshot {
  const ClubSaleDynastySnapshot({
    required this.dynastyScore,
    required this.dynastyLevel,
    required this.dynastyTitle,
    required this.seasonsCompleted,
    required this.lastSeasonLabel,
    required this.ownershipEras,
    required this.shareholderContinuityTransfers,
    required this.showcaseSummary,
  });

  final int dynastyScore;
  final int dynastyLevel;
  final String dynastyTitle;
  final int seasonsCompleted;
  final String? lastSeasonLabel;
  final int ownershipEras;
  final int shareholderContinuityTransfers;
  final Map<String, Object?> showcaseSummary;

  factory ClubSaleDynastySnapshot.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale dynasty snapshot');
    return ClubSaleDynastySnapshot(
      dynastyScore:
          GteJson.integer(json, <String>['dynasty_score', 'dynastyScore']),
      dynastyLevel:
          GteJson.integer(json, <String>['dynasty_level', 'dynastyLevel']),
      dynastyTitle:
          GteJson.string(json, <String>['dynasty_title', 'dynastyTitle']),
      seasonsCompleted: GteJson.integer(
        json,
        <String>['seasons_completed', 'seasonsCompleted'],
      ),
      lastSeasonLabel: GteJson.stringOrNull(
        json,
        <String>['last_season_label', 'lastSeasonLabel'],
      ),
      ownershipEras:
          GteJson.integer(json, <String>['ownership_eras', 'ownershipEras']),
      shareholderContinuityTransfers: GteJson.integer(
        json,
        <String>[
          'shareholder_continuity_transfers',
          'shareholderContinuityTransfers',
        ],
      ),
      showcaseSummary: GteJson.map(
        json,
        keys: <String>['showcase_summary_json', 'showcaseSummaryJson'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class ClubSaleHistory {
  const ClubSaleHistory({
    required this.clubId,
    required this.listings,
    required this.offers,
    required this.transfers,
    required this.auditEvents,
    required this.ownershipHistory,
    required this.dynastySnapshot,
  });

  final String clubId;
  final List<ClubSaleListingSummary> listings;
  final List<ClubSaleOffer> offers;
  final List<ClubSaleTransferExecution> transfers;
  final List<ClubSaleAuditEvent> auditEvents;
  final ClubSaleOwnershipHistory ownershipHistory;
  final ClubSaleDynastySnapshot dynastySnapshot;

  factory ClubSaleHistory.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'club sale history');
    return ClubSaleHistory(
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      listings: GteJson.typedList(
        json,
        <String>['listings'],
        ClubSaleListingSummary.fromJson,
      ),
      offers:
          GteJson.typedList(json, <String>['offers'], ClubSaleOffer.fromJson),
      transfers: GteJson.typedList(
        json,
        <String>['transfers'],
        ClubSaleTransferExecution.fromJson,
      ),
      auditEvents: GteJson.typedList(
        json,
        <String>['audit_events', 'auditEvents'],
        ClubSaleAuditEvent.fromJson,
      ),
      ownershipHistory: ClubSaleOwnershipHistory.fromJson(
        GteJson.value(json, <String>['ownership_history', 'ownershipHistory']),
      ),
      dynastySnapshot: ClubSaleDynastySnapshot.fromJson(
        GteJson.value(json, <String>['dynasty_snapshot', 'dynastySnapshot']),
      ),
    );
  }
}
