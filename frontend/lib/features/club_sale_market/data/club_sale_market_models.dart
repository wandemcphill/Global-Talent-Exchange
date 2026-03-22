import '../../shared/data/gte_feature_support.dart';

class ClubSaleListingsQuery {
  const ClubSaleListingsQuery({
    this.limit = 50,
    this.offset = 0,
  });

  final int limit;
  final int offset;

  JsonMap toQuery() => <String, Object?>{'limit': limit, 'offset': offset};
}

class ClubSaleHistoryQuery {
  const ClubSaleHistoryQuery({this.limit = 50});

  final int limit;

  JsonMap toQuery() => <String, Object?>{'limit': limit};
}

class ClubSaleListingUpsertRequest {
  const ClubSaleListingUpsertRequest({
    required this.askingPrice,
    this.visibility = 'public',
    this.note,
    this.metadata = const <String, Object?>{},
  });

  final double askingPrice;
  final String visibility;
  final String? note;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'asking_price': askingPrice,
      'visibility': visibility,
      if (note != null && note!.trim().isNotEmpty) 'note': note!.trim(),
      'metadata_json': metadata,
    };
  }
}

class ClubSaleListingCancelRequest {
  const ClubSaleListingCancelRequest({this.reason});

  final String? reason;

  JsonMap toJson() {
    return <String, Object?>{
      if (reason != null && reason!.trim().isNotEmpty) 'reason': reason!.trim(),
    };
  }
}

class ClubSaleInquiryCreateRequest {
  const ClubSaleInquiryCreateRequest({
    required this.message,
    this.metadata = const <String, Object?>{},
  });

  final String message;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'message': message.trim(),
      'metadata_json': metadata,
    };
  }
}

class ClubSaleInquiryRespondRequest {
  const ClubSaleInquiryRespondRequest({
    required this.responseMessage,
    this.closeThread = true,
    this.metadata = const <String, Object?>{},
  });

  final String responseMessage;
  final bool closeThread;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'response_message': responseMessage.trim(),
      'close_thread': closeThread,
      'metadata_json': metadata,
    };
  }
}

class ClubSaleOfferCreateRequest {
  const ClubSaleOfferCreateRequest({
    required this.offerPrice,
    this.inquiryId,
    this.message,
    this.expiresAt,
    this.metadata = const <String, Object?>{},
  });

  final double offerPrice;
  final String? inquiryId;
  final String? message;
  final DateTime? expiresAt;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'offer_price': offerPrice,
      if (inquiryId != null && inquiryId!.trim().isNotEmpty)
        'inquiry_id': inquiryId!.trim(),
      if (message != null && message!.trim().isNotEmpty)
        'message': message!.trim(),
      if (expiresAt != null) 'expires_at': expiresAt!.toUtc().toIso8601String(),
      'metadata_json': metadata,
    };
  }
}

class ClubSaleOfferCounterRequest {
  const ClubSaleOfferCounterRequest({
    required this.offerPrice,
    this.message,
    this.expiresAt,
    this.metadata = const <String, Object?>{},
  });

  final double offerPrice;
  final String? message;
  final DateTime? expiresAt;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'offer_price': offerPrice,
      if (message != null && message!.trim().isNotEmpty)
        'message': message!.trim(),
      if (expiresAt != null) 'expires_at': expiresAt!.toUtc().toIso8601String(),
      'metadata_json': metadata,
    };
  }
}

class ClubSaleOfferRespondRequest {
  const ClubSaleOfferRespondRequest({
    this.message,
    this.metadata = const <String, Object?>{},
  });

  final String? message;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      if (message != null && message!.trim().isNotEmpty)
        'message': message!.trim(),
      'metadata_json': metadata,
    };
  }
}

class ClubSaleTransferExecuteRequest {
  const ClubSaleTransferExecuteRequest({
    required this.offerId,
    required this.executedSalePrice,
    this.metadata = const <String, Object?>{},
  });

  final String offerId;
  final double executedSalePrice;
  final JsonMap metadata;

  JsonMap toJson() {
    return <String, Object?>{
      'offer_id': offerId,
      'executed_sale_price': executedSalePrice,
      'metadata_json': metadata,
    };
  }
}

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
  final JsonMap metadata;

  factory ClubSaleValuationBreakdown.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale valuation breakdown');
    return ClubSaleValuationBreakdown(
      firstTeamValue: numberValue(json['first_team_value']),
      reserveSquadValue: numberValue(json['reserve_squad_value']),
      u19SquadValue: numberValue(json['u19_squad_value']),
      academyValue: numberValue(json['academy_value']),
      stadiumValue: numberValue(json['stadium_value']),
      paidEnhancementsValue: numberValue(json['paid_enhancements_value']),
      metadata: jsonMap(
        json['metadata_json'],
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
    final JsonMap json = jsonMap(value, label: 'club sale valuation');
    return ClubSaleValuation(
      clubId: stringValue(json['club_id']),
      clubName: stringValue(json['club_name']),
      currency: stringValue(json['currency']),
      systemValuation: numberValue(json['system_valuation']),
      systemValuationMinor: intValue(json['system_valuation_minor']),
      breakdown: ClubSaleValuationBreakdown.fromJson(json['breakdown']),
      lastRefreshedAt: dateTimeValue(json['last_refreshed_at']),
    );
  }
}

class ClubSaleListing {
  const ClubSaleListing({
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
    required this.valuationBreakdown,
    required this.note,
    required this.metadata,
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
  final ClubSaleValuationBreakdown? valuationBreakdown;
  final String? note;
  final JsonMap metadata;

  bool get isActive => status.toLowerCase() == 'active';

  factory ClubSaleListing.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale listing');
    final JsonMap? club = jsonMapOrNull(json['club']);
    final JsonMap? seller = jsonMapOrNull(json['seller']);
    final String clubId = _clubSaleString(
      <Object?>[
        json['club_id'],
        json['clubId'],
        club?['id'],
        club?['club_id'],
        club?['clubId'],
        club?['slug'],
        club?['club_slug'],
      ],
    );
    final double askingPrice = _clubSaleNumber(
      <Object?>[json['asking_price'], json['askingPrice']],
    );
    final double systemValuation = _clubSaleNumber(
      <Object?>[json['system_valuation'], json['systemValuation']],
      fallback: askingPrice,
    );
    return ClubSaleListing(
      listingId: _clubSaleString(
        <Object?>[json['listing_id'], json['listingId'], json['id'], clubId],
      ),
      clubId: clubId,
      clubName: _clubSaleString(
        <Object?>[
          json['club_name'],
          json['clubName'],
          club?['name'],
          club?['club_name'],
          club?['clubName'],
          club?['display_name'],
          club?['displayName'],
          club?['slug'],
          club?['club_slug'],
          if (clubId.isNotEmpty) _prettifyClubSaleClubId(clubId),
        ],
      ),
      sellerUserId: _clubSaleString(
        <Object?>[
          json['seller_user_id'],
          json['sellerUserId'],
          json['seller_id'],
          json['sellerId'],
          seller?['id'],
          seller?['user_id'],
          seller?['userId'],
        ],
      ),
      status: _clubSaleString(<Object?>[json['status']], fallback: 'active'),
      visibility: _clubSaleString(
        <Object?>[json['visibility']],
        fallback: 'public',
      ),
      currency: _clubSaleString(
        <Object?>[json['currency']],
        fallback: 'credits',
      ),
      askingPrice: askingPrice,
      systemValuation: systemValuation,
      systemValuationMinor: _clubSaleInt(
        <Object?>[json['system_valuation_minor'], json['systemValuationMinor']],
        fallback: systemValuation.round(),
      ),
      valuationLastRefreshedAt: _clubSaleDateTime(
        <Object?>[
          json['valuation_last_refreshed_at'],
          json['valuationLastRefreshedAt'],
        ],
      ),
      createdAt: _clubSaleDateTime(
            <Object?>[json['created_at'], json['createdAt']],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: _clubSaleDateTime(
            <Object?>[json['updated_at'], json['updatedAt']],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      valuationBreakdown: jsonMapOrNull(
                json['valuation_breakdown'] ?? json['valuationBreakdown'],
              ) ==
              null
          ? null
          : ClubSaleValuationBreakdown.fromJson(
              json['valuation_breakdown'] ?? json['valuationBreakdown'],
            ),
      note: stringOrNullValue(
        json['note'] ?? json['listing_note'] ?? json['listingNote'],
      ),
      metadata: jsonMapOrNull(
            json['metadata_json'] ?? json['metadataJson'],
          ) ??
          const <String, Object?>{},
    );
  }
}

class ClubSaleListingCollection {
  const ClubSaleListingCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleListing> items;

  const ClubSaleListingCollection.empty()
      : total = 0,
        items = const <ClubSaleListing>[];

  factory ClubSaleListingCollection.fromJson(Object? value) {
    if (value is List) {
      final List<ClubSaleListing> items = parseList(
          value, ClubSaleListing.fromJson,
          label: 'club sale listings');
      return ClubSaleListingCollection(total: items.length, items: items);
    }
    final JsonMap json = jsonMap(value, label: 'club sale listing collection');
    final Object? rawItems = _firstNonNullObject(
      <Object?>[json['items'], json['listings'], json['results']],
    );
    final List<ClubSaleListing> items = rawItems == null
        ? const <ClubSaleListing>[]
        : parseList(
            rawItems,
            ClubSaleListing.fromJson,
            label: 'club sale listings',
          );
    return ClubSaleListingCollection(
      total: intValue(
        _firstNonNullObject(<Object?>[json['total'], json['count']]),
        fallback: items.length,
      ),
      items: items,
    );
  }
}

Object? _firstNonNullObject(List<Object?> values) {
  for (final Object? value in values) {
    if (value != null) {
      return value;
    }
  }
  return null;
}

String _clubSaleString(
  List<Object?> values, {
  String fallback = '',
}) {
  for (final Object? value in values) {
    final String? parsed = stringOrNullValue(value);
    if (parsed != null && parsed.isNotEmpty) {
      return parsed;
    }
  }
  return fallback;
}

double _clubSaleNumber(
  List<Object?> values, {
  double fallback = 0,
}) {
  for (final Object? value in values) {
    if (value == null) {
      continue;
    }
    final double parsed = numberValue(value, fallback: fallback);
    if (parsed != fallback || value.toString().trim().isNotEmpty) {
      return parsed;
    }
  }
  return fallback;
}

int _clubSaleInt(
  List<Object?> values, {
  int fallback = 0,
}) {
  for (final Object? value in values) {
    if (value == null) {
      continue;
    }
    final int parsed = intValue(value, fallback: fallback);
    if (parsed != fallback || value.toString().trim().isNotEmpty) {
      return parsed;
    }
  }
  return fallback;
}

DateTime? _clubSaleDateTime(List<Object?> values) {
  for (final Object? value in values) {
    final DateTime? parsed = dateTimeValue(value);
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

String _prettifyClubSaleClubId(String clubId) {
  return clubId.replaceAll(RegExp(r'[-_]+'), ' ').replaceAllMapped(
        RegExp(r'\b[a-z]'),
        (Match match) => match.group(0)!.toUpperCase(),
      );
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
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ClubSaleInquiry.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale inquiry');
    return ClubSaleInquiry(
      inquiryId: stringValue(json['inquiry_id']),
      clubId: stringValue(json['club_id']),
      listingId: stringOrNullValue(json['listing_id']),
      sellerUserId: stringValue(json['seller_user_id']),
      buyerUserId: stringValue(json['buyer_user_id']),
      status: stringValue(json['status']),
      message: stringValue(json['message']),
      responseMessage: stringOrNullValue(json['response_message']),
      respondedByUserId: stringOrNullValue(json['responded_by_user_id']),
      respondedAt: dateTimeValue(json['responded_at']),
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

class ClubSaleInquiryCollection {
  const ClubSaleInquiryCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleInquiry> items;

  const ClubSaleInquiryCollection.empty()
      : total = 0,
        items = const <ClubSaleInquiry>[];

  factory ClubSaleInquiryCollection.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale inquiry collection');
    return ClubSaleInquiryCollection(
      total: intValue(json['total']),
      items: parseList(
        json['items'],
        ClubSaleInquiry.fromJson,
        label: 'club sale inquiries',
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
  final JsonMap metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isOpen => status.toLowerCase() == 'open';

  factory ClubSaleOffer.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale offer');
    return ClubSaleOffer(
      offerId: stringValue(json['offer_id']),
      clubId: stringValue(json['club_id']),
      listingId: stringOrNullValue(json['listing_id']),
      inquiryId: stringOrNullValue(json['inquiry_id']),
      parentOfferId: stringOrNullValue(json['parent_offer_id']),
      sellerUserId: stringValue(json['seller_user_id']),
      buyerUserId: stringValue(json['buyer_user_id']),
      proposerUserId: stringValue(json['proposer_user_id']),
      counterpartyUserId: stringValue(json['counterparty_user_id']),
      offerType: stringValue(json['offer_type']),
      status: stringValue(json['status']),
      currency: stringValue(json['currency']),
      offerPrice: numberValue(json['offer_price']),
      message: stringOrNullValue(json['message']),
      respondedMessage: stringOrNullValue(json['responded_message']),
      respondedByUserId: stringOrNullValue(json['responded_by_user_id']),
      respondedAt: dateTimeValue(json['responded_at']),
      acceptedAt: dateTimeValue(json['accepted_at']),
      rejectedAt: dateTimeValue(json['rejected_at']),
      expiresAt: dateTimeValue(json['expires_at']),
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

class ClubSaleOfferCollection {
  const ClubSaleOfferCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<ClubSaleOffer> items;

  const ClubSaleOfferCollection.empty()
      : total = 0,
        items = const <ClubSaleOffer>[];

  factory ClubSaleOfferCollection.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale offer collection');
    return ClubSaleOfferCollection(
      total: intValue(json['total']),
      items: parseList(
        json['items'],
        ClubSaleOffer.fromJson,
        label: 'club sale offers',
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
    final JsonMap json =
        jsonMap(value, label: 'club sale ownership transition');
    return ClubSaleOwnershipTransition(
      previousOwnerUserId: stringOrNullValue(json['previous_owner_user_id']),
      newOwnerUserId: stringOrNullValue(json['new_owner_user_id']),
      ownershipLineageIndex: intValue(json['ownership_lineage_index']),
      shareholderCountPreserved: intValue(json['shareholder_count_preserved']),
      shareholderRightsPreserved: boolValue(
        json['shareholder_rights_preserved'],
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
  final JsonMap metadata;
  final ClubSaleOwnershipTransition? ownershipTransition;
  final DateTime createdAt;

  factory ClubSaleTransferExecution.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale transfer execution');
    return ClubSaleTransferExecution(
      transferId: stringValue(json['transfer_id']),
      clubId: stringValue(json['club_id']),
      listingId: stringOrNullValue(json['listing_id']),
      offerId: stringValue(json['offer_id']),
      sellerUserId: stringValue(json['seller_user_id']),
      buyerUserId: stringValue(json['buyer_user_id']),
      currency: stringValue(json['currency']),
      executedSalePrice: numberValue(json['executed_sale_price']),
      platformFeeAmount: numberValue(json['platform_fee_amount']),
      sellerNetAmount: numberValue(json['seller_net_amount']),
      platformFeeBps: intValue(json['platform_fee_bps']),
      status: stringValue(json['status']),
      settlementReference: stringValue(json['settlement_reference']),
      ledgerTransactionId: stringOrNullValue(json['ledger_transaction_id']),
      storyFeedItemId: stringOrNullValue(json['story_feed_item_id']),
      calendarEventId: stringOrNullValue(json['calendar_event_id']),
      metadata: jsonMap(
        json['metadata_json'],
        fallback: const <String, Object?>{},
      ),
      ownershipTransition: jsonMapOrNull(json['ownership_transition']) == null
          ? null
          : ClubSaleOwnershipTransition.fromJson(json['ownership_transition']),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
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
  final JsonMap payload;
  final DateTime createdAt;

  factory ClubSaleAuditEvent.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale audit event');
    return ClubSaleAuditEvent(
      id: stringValue(json['id']),
      clubId: stringValue(json['club_id']),
      listingId: stringOrNullValue(json['listing_id']),
      inquiryId: stringOrNullValue(json['inquiry_id']),
      offerId: stringOrNullValue(json['offer_id']),
      transferId: stringOrNullValue(json['transfer_id']),
      actorUserId: stringOrNullValue(json['actor_user_id']),
      action: stringValue(json['action']),
      statusFrom: stringOrNullValue(json['status_from']),
      statusTo: stringOrNullValue(json['status_to']),
      payload: jsonMap(
        json['payload_json'],
        fallback: const <String, Object?>{},
      ),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
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
  final JsonMap metadata;

  factory ClubSaleOwnershipHistoryEvent.fromJson(Object? value) {
    final JsonMap json =
        jsonMap(value, label: 'club sale ownership history event');
    return ClubSaleOwnershipHistoryEvent(
      transferId: stringValue(json['transfer_id']),
      sellerUserId: stringValue(json['seller_user_id']),
      buyerUserId: stringValue(json['buyer_user_id']),
      executedSalePrice: numberValue(json['executed_sale_price']),
      createdAt: dateTimeValue(json['created_at']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      metadata: jsonMap(
        json['metadata_json'],
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
    final JsonMap json = jsonMap(value, label: 'club sale ownership history');
    return ClubSaleOwnershipHistory(
      currentOwnerUserId: stringValue(json['current_owner_user_id']),
      transferCount: intValue(json['transfer_count']),
      ownershipEras: intValue(json['ownership_eras']),
      shareholderCount: intValue(json['shareholder_count']),
      activeGovernanceProposalCount: intValue(
        json['active_governance_proposal_count'],
      ),
      lastTransferId: stringOrNullValue(json['last_transfer_id']),
      lastTransferAt: dateTimeValue(json['last_transfer_at']),
      previousOwnerUserIds: parseList<String>(
        json['previous_owner_user_ids'],
        (Object? item) => stringValue(item),
        label: 'club sale previous owners',
      ),
      recentTransfers: parseList(
        json['recent_transfers'],
        ClubSaleOwnershipHistoryEvent.fromJson,
        label: 'club sale recent transfers',
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
  final JsonMap showcaseSummary;

  factory ClubSaleDynastySnapshot.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale dynasty snapshot');
    return ClubSaleDynastySnapshot(
      dynastyScore: intValue(json['dynasty_score']),
      dynastyLevel: intValue(json['dynasty_level']),
      dynastyTitle: stringValue(json['dynasty_title']),
      seasonsCompleted: intValue(json['seasons_completed']),
      lastSeasonLabel: stringOrNullValue(json['last_season_label']),
      ownershipEras: intValue(json['ownership_eras']),
      shareholderContinuityTransfers: intValue(
        json['shareholder_continuity_transfers'],
      ),
      showcaseSummary: jsonMap(
        json['showcase_summary_json'],
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
  final List<ClubSaleListing> listings;
  final List<ClubSaleOffer> offers;
  final List<ClubSaleTransferExecution> transfers;
  final List<ClubSaleAuditEvent> auditEvents;
  final ClubSaleOwnershipHistory ownershipHistory;
  final ClubSaleDynastySnapshot dynastySnapshot;

  factory ClubSaleHistory.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'club sale history');
    return ClubSaleHistory(
      clubId: stringValue(json['club_id']),
      listings: parseList(
        json['listings'],
        ClubSaleListing.fromJson,
        label: 'club sale history listings',
      ),
      offers: parseList(
        json['offers'],
        ClubSaleOffer.fromJson,
        label: 'club sale history offers',
      ),
      transfers: parseList(
        json['transfers'],
        ClubSaleTransferExecution.fromJson,
        label: 'club sale history transfers',
      ),
      auditEvents: parseList(
        json['audit_events'],
        ClubSaleAuditEvent.fromJson,
        label: 'club sale history audit events',
      ),
      ownershipHistory: ClubSaleOwnershipHistory.fromJson(
        json['ownership_history'],
      ),
      dynastySnapshot: ClubSaleDynastySnapshot.fromJson(
        json['dynasty_snapshot'],
      ),
    );
  }
}
