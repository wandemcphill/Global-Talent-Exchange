import '../../shared/data/gte_feature_support.dart';
import '../../../models/player_avatar.dart';

class PlayerCardMarketplaceQuery {
  const PlayerCardMarketplaceQuery({
    this.search,
    this.club,
    this.position,
    this.ratingMin,
    this.ratingMax,
    this.tierCode,
    this.rarityRankMin,
    this.rarityRankMax,
    this.assetOrigin,
    this.listingType,
    this.salePriceMin,
    this.salePriceMax,
    this.loanFeeMin,
    this.loanFeeMax,
    this.loanDurationMin,
    this.loanDurationMax,
    this.availability = 'available',
    this.negotiable,
    this.sort = 'relevance',
    this.limit = 20,
    this.offset = 0,
  });

  final String? search;
  final String? club;
  final String? position;
  final double? ratingMin;
  final double? ratingMax;
  final String? tierCode;
  final int? rarityRankMin;
  final int? rarityRankMax;
  final String? assetOrigin;
  final String? listingType;
  final double? salePriceMin;
  final double? salePriceMax;
  final double? loanFeeMin;
  final double? loanFeeMax;
  final int? loanDurationMin;
  final int? loanDurationMax;
  final String availability;
  final bool? negotiable;
  final String sort;
  final int limit;
  final int offset;

  Map<String, Object?> toQuery({String? forceListingType}) {
    return compactQuery(<String, Object?>{
      'search': search,
      'club': club,
      'position': position,
      'rating_min': ratingMin,
      'rating_max': ratingMax,
      'tier_code': tierCode,
      'rarity_rank_min': rarityRankMin,
      'rarity_rank_max': rarityRankMax,
      'asset_origin': assetOrigin,
      'listing_type': forceListingType ?? listingType,
      'sale_price_min': salePriceMin,
      'sale_price_max': salePriceMax,
      'loan_fee_min': loanFeeMin,
      'loan_fee_max': loanFeeMax,
      'loan_duration_min': loanDurationMin,
      'loan_duration_max': loanDurationMax,
      'availability': availability,
      'negotiable': negotiable,
      'sort': sort,
      'limit': limit,
      'offset': offset,
    });
  }
}

class PlayerCardPlayersQuery {
  const PlayerCardPlayersQuery({
    this.search,
    this.limit = 20,
    this.offset = 0,
  });

  final String? search;
  final int limit;
  final int offset;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'search': search,
        'limit': limit,
        'offset': offset,
      });
}

class PlayerCardListingsQuery {
  const PlayerCardListingsQuery({
    this.status = 'open',
    this.playerId,
    this.tierId,
    this.limit = 200,
  });

  final String status;
  final String? playerId;
  final String? tierId;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'status_filter': status,
        'player_id': playerId,
        'tier_id': tierId,
        'limit': limit,
      });
}

class PlayerCardLoanSupportQuery {
  const PlayerCardLoanSupportQuery({
    this.position,
    this.tierCode,
    this.maxCost,
    this.maxDurationDays,
    this.limit = 100,
  });

  final String? position;
  final String? tierCode;
  final double? maxCost;
  final int? maxDurationDays;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'position': position,
        'tier_code': tierCode,
        'max_cost': maxCost,
        'max_duration_days': maxDurationDays,
        'limit': limit,
      });
}

class PlayerCardLoanContractsQuery {
  const PlayerCardLoanContractsQuery({
    this.role,
    this.statusFilter,
  });

  final String? role;
  final String? statusFilter;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'role': role,
        'status_filter': statusFilter,
      });
}

class PlayerCardMarketplaceSaleListingCreateRequest {
  const PlayerCardMarketplaceSaleListingCreateRequest({
    required this.playerCardId,
    required this.pricePerCardCredits,
    this.quantity = 1,
    this.isNegotiable = false,
    this.expiresAt,
  });

  final String playerCardId;
  final int quantity;
  final double pricePerCardCredits;
  final bool isNegotiable;
  final DateTime? expiresAt;

  JsonMap toJson() => <String, Object?>{
        'player_card_id': playerCardId,
        'quantity': quantity,
        'price_per_card_credits': pricePerCardCredits,
        'is_negotiable': isNegotiable,
        if (expiresAt != null)
          'expires_at': expiresAt!.toUtc().toIso8601String(),
      };
}

class PlayerCardMarketplaceSalePurchaseRequest {
  const PlayerCardMarketplaceSalePurchaseRequest({
    this.quantity = 1,
  });

  final int quantity;

  JsonMap toJson() => <String, Object?>{'quantity': quantity};
}

class PlayerCardMarketplaceLoanListingCreateRequest {
  const PlayerCardMarketplaceLoanListingCreateRequest({
    required this.playerCardId,
    required this.totalSlots,
    required this.durationDays,
    required this.loanFeeCredits,
    this.usageRestrictions = const <String, Object?>{},
    this.terms = const <String, Object?>{},
    this.expiresAt,
  });

  final String playerCardId;
  final int totalSlots;
  final int durationDays;
  final double loanFeeCredits;
  final JsonMap usageRestrictions;
  final JsonMap terms;
  final DateTime? expiresAt;

  JsonMap toJson() => <String, Object?>{
        'player_card_id': playerCardId,
        'total_slots': totalSlots,
        'duration_days': durationDays,
        'loan_fee_credits': loanFeeCredits,
        'usage_restrictions_json': usageRestrictions,
        'terms_json': terms,
        if (expiresAt != null)
          'expires_at': expiresAt!.toUtc().toIso8601String(),
      };
}

class PlayerCardMarketplaceLoanNegotiationCreateRequest {
  const PlayerCardMarketplaceLoanNegotiationCreateRequest({
    required this.proposedFeeCredits,
    required this.proposedDurationDays,
    this.note,
    this.requestedTerms = const <String, Object?>{},
  });

  final double proposedFeeCredits;
  final int proposedDurationDays;
  final String? note;
  final JsonMap requestedTerms;

  JsonMap toJson() => <String, Object?>{
        'proposed_loan_fee_credits': proposedFeeCredits,
        'proposed_duration_days': proposedDurationDays,
        if (note != null) 'note': note,
        'requested_terms_json': requestedTerms,
      };
}

class PlayerCardMarketplaceSwapListingCreateRequest {
  const PlayerCardMarketplaceSwapListingCreateRequest({
    required this.playerCardId,
    this.requestedPlayerCardId,
    this.requestedFilters = const <String, Object?>{},
    this.isNegotiable = false,
    this.expiresAt,
  });

  final String playerCardId;
  final String? requestedPlayerCardId;
  final JsonMap requestedFilters;
  final bool isNegotiable;
  final DateTime? expiresAt;

  JsonMap toJson() => <String, Object?>{
        'player_card_id': playerCardId,
        if (requestedPlayerCardId != null)
          'requested_player_card_id': requestedPlayerCardId,
        'requested_filters_json': requestedFilters,
        'is_negotiable': isNegotiable,
        if (expiresAt != null)
          'expires_at': expiresAt!.toUtc().toIso8601String(),
      };
}

class PlayerCardMarketplaceSwapExecuteRequest {
  const PlayerCardMarketplaceSwapExecuteRequest({
    required this.counterpartyPlayerCardId,
  });

  final String counterpartyPlayerCardId;

  JsonMap toJson() => <String, Object?>{
        'counterparty_player_card_id': counterpartyPlayerCardId,
      };
}

class PlayerCardWatchlistCreateRequest {
  const PlayerCardWatchlistCreateRequest({
    required this.playerId,
    this.playerCardId,
    this.notes,
  });

  final String playerId;
  final String? playerCardId;
  final String? notes;

  JsonMap toJson() => <String, Object?>{
        'player_id': playerId,
        if (playerCardId != null) 'player_card_id': playerCardId,
        if (notes != null && notes!.trim().isNotEmpty) 'notes': notes,
      };
}

class PlayerCardMarketplaceListing {
  const PlayerCardMarketplaceListing._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceListing.fromJson(Object? value) {
    return PlayerCardMarketplaceListing._(
      jsonMap(value, label: 'player card marketplace listing'),
    );
  }

  String get listingId => stringValue(raw['listing_id']);
  String get listingType => stringValue(raw['listing_type']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get clubName => stringOrNullValue(raw['club_name']);
  String? get position => stringOrNullValue(raw['position']);
  double? get averageRating =>
      raw['average_rating'] == null ? null : numberValue(raw['average_rating']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  int get rarityRank => intValue(raw['rarity_rank']);
  String get editionCode => stringValue(raw['edition_code']);
  String get listingOwnerUserId => stringValue(raw['listing_owner_user_id']);
  String get status => stringValue(raw['status']);
  String get availability => stringValue(raw['availability']);
  bool get isNegotiable => boolValue(raw['is_negotiable']);
  String get assetOrigin => stringValue(raw['asset_origin']);
  bool get isRegenNewgen => boolValue(raw['is_regen_newgen']);
  bool get isCreatorLinked => boolValue(raw['is_creator_linked']);
  int? get quantity =>
      raw['quantity'] == null ? null : intValue(raw['quantity']);
  int? get availableQuantity => raw['available_quantity'] == null
      ? null
      : intValue(raw['available_quantity']);
  double? get salePriceCredits => raw['sale_price_credits'] == null
      ? null
      : numberValue(raw['sale_price_credits']);
  double? get loanFeeCredits => raw['loan_fee_credits'] == null
      ? null
      : numberValue(raw['loan_fee_credits']);
  int? get loanDurationDays => raw['loan_duration_days'] == null
      ? null
      : intValue(raw['loan_duration_days']);
  String? get requestedPlayerCardId =>
      stringOrNullValue(raw['requested_player_card_id']);
  String? get requestedPlayerId =>
      stringOrNullValue(raw['requested_player_id']);
  JsonMap get requestedFilters => jsonMap(raw['requested_filters_json'],
      fallback: const <String, Object?>{});
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get expiresAt => dateTimeValue(raw['expires_at']);
}

class PlayerCardMarketplaceSearchResult {
  const PlayerCardMarketplaceSearchResult({
    required this.total,
    required this.limit,
    required this.offset,
    required this.items,
  });

  const PlayerCardMarketplaceSearchResult.empty()
      : total = 0,
        limit = 20,
        offset = 0,
        items = const <PlayerCardMarketplaceListing>[];

  final int total;
  final int limit;
  final int offset;
  final List<PlayerCardMarketplaceListing> items;

  factory PlayerCardMarketplaceSearchResult.fromJson(Object? value) {
    final JsonMap json =
        jsonMap(value, label: 'player card marketplace result');
    return PlayerCardMarketplaceSearchResult(
      total: intValue(json['total']),
      limit: intValue(json['limit'], fallback: 20),
      offset: intValue(json['offset']),
      items: parseList(
        json['items'],
        PlayerCardMarketplaceListing.fromJson,
        label: 'player card marketplace items',
      ),
    );
  }
}

class PlayerCardMarketplaceSaleExecution {
  const PlayerCardMarketplaceSaleExecution._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceSaleExecution.fromJson(Object? value) {
    return PlayerCardMarketplaceSaleExecution._(
      jsonMap(value, label: 'player card marketplace sale execution'),
    );
  }

  String get saleId => stringValue(raw['sale_id']);
  String? get listingId => stringOrNullValue(raw['listing_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get sellerUserId => stringValue(raw['seller_user_id']);
  String get buyerUserId => stringValue(raw['buyer_user_id']);
  int get quantity => intValue(raw['quantity']);
  double get pricePerCardCredits => numberValue(raw['price_per_card_credits']);
  double get grossCredits => numberValue(raw['gross_credits']);
  double get feeCredits => numberValue(raw['fee_credits']);
  double get sellerNetCredits => numberValue(raw['seller_net_credits']);
  String get status => stringValue(raw['status']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class PlayerCardMarketplaceLoanListing {
  const PlayerCardMarketplaceLoanListing._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceLoanListing.fromJson(Object? value) {
    return PlayerCardMarketplaceLoanListing._(
      jsonMap(value, label: 'player card marketplace loan listing'),
    );
  }

  String get loanListingId => stringValue(raw['loan_listing_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get position => stringOrNullValue(raw['position']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  int get totalSlots => intValue(raw['total_slots']);
  int get availableSlots => intValue(raw['available_slots']);
  int get durationDays => intValue(raw['duration_days']);
  double get loanFeeCredits => numberValue(raw['loan_fee_credits']);
  String get currency => stringValue(raw['currency']);
  String get status => stringValue(raw['status']);
  JsonMap get usageRestrictions => jsonMap(raw['usage_restrictions_json'],
      fallback: const <String, Object?>{});
  JsonMap get terms =>
      jsonMap(raw['terms_json'], fallback: const <String, Object?>{});
  DateTime? get expiresAt => dateTimeValue(raw['expires_at']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class PlayerCardMarketplaceLoanNegotiation {
  const PlayerCardMarketplaceLoanNegotiation._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceLoanNegotiation.fromJson(Object? value) {
    return PlayerCardMarketplaceLoanNegotiation._(
      jsonMap(value, label: 'player card marketplace loan negotiation'),
    );
  }

  String get id => stringValue(raw['negotiation_id']);
  String get listingId => stringValue(raw['listing_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  String get borrowerUserId => stringValue(raw['borrower_user_id']);
  String get proposerUserId => stringValue(raw['proposer_user_id']);
  String get counterpartyUserId => stringValue(raw['counterparty_user_id']);
  double get proposedFeeCredits =>
      numberValue(raw['proposed_loan_fee_credits']);
  int get proposedDurationDays => intValue(raw['proposed_duration_days']);
  String get status => stringValue(raw['status']);
  String? get note => stringOrNullValue(raw['note']);
  JsonMap get requestedTerms =>
      jsonMap(raw['requested_terms_json'], fallback: const <String, Object?>{});
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
  DateTime? get respondedAt => dateTimeValue(raw['responded_at']);
  DateTime? get expiresAt => dateTimeValue(raw['expires_at']);
}

class PlayerCardMarketplaceLoanContract {
  const PlayerCardMarketplaceLoanContract._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceLoanContract.fromJson(Object? value) {
    return PlayerCardMarketplaceLoanContract._(
      jsonMap(value, label: 'player card marketplace loan contract'),
    );
  }

  String get loanContractId => stringValue(raw['loan_contract_id']);
  String get loanListingId => stringValue(raw['listing_id']);
  String? get acceptedNegotiationId =>
      stringOrNullValue(raw['accepted_negotiation_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get clubName => stringOrNullValue(raw['club_name']);
  String? get position => stringOrNullValue(raw['position']);
  double? get averageRating =>
      raw['average_rating'] == null ? null : numberValue(raw['average_rating']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  String get borrowerUserId => stringValue(raw['borrower_user_id']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  int get durationDays => intValue(raw['loan_duration_days']);
  double get requestedLoanFeeCredits =>
      numberValue(raw['requested_loan_fee_credits']);
  double get effectiveLoanFeeCredits =>
      numberValue(raw['effective_loan_fee_credits']);
  double get platformFeeCredits => numberValue(raw['platform_fee_credits']);
  double get lenderNetCredits => numberValue(raw['lender_net_credits']);
  int get platformFeeBps => intValue(raw['platform_fee_bps']);
  bool get feeFloorApplied => boolValue(raw['fee_floor_applied']);
  String get contractStatus => stringValue(raw['status']);
  JsonMap get usageSnapshot => jsonMap(
        raw['usage_snapshot_json'],
        fallback: const <String, Object?>{},
      );
  DateTime? get borrowedAt => dateTimeValue(raw['borrowed_at']);
  DateTime? get dueAt => dateTimeValue(raw['due_at']);
  DateTime? get returnedAt => dateTimeValue(raw['returned_at']);
  DateTime? get acceptedAt => dateTimeValue(raw['accepted_at']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
}

class PlayerCardMarketplaceLoanContractList {
  const PlayerCardMarketplaceLoanContractList({
    required this.items,
  });

  const PlayerCardMarketplaceLoanContractList.empty()
      : items = const <PlayerCardMarketplaceLoanContract>[];

  final List<PlayerCardMarketplaceLoanContract> items;

  factory PlayerCardMarketplaceLoanContractList.fromJson(Object? value) {
    final JsonMap json = jsonMap(
      value,
      label: 'player card marketplace loan contract list',
    );
    return PlayerCardMarketplaceLoanContractList(
      items: parseList(
        json['items'],
        PlayerCardMarketplaceLoanContract.fromJson,
        label: 'player card marketplace loan contracts',
      ),
    );
  }
}

class PlayerCardMarketplaceSwapListing {
  const PlayerCardMarketplaceSwapListing._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceSwapListing.fromJson(Object? value) {
    return PlayerCardMarketplaceSwapListing._(
      jsonMap(value, label: 'player card marketplace swap listing'),
    );
  }

  String get swapListingId => stringValue(raw['listing_id']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get clubName => stringOrNullValue(raw['club_name']);
  String? get position => stringOrNullValue(raw['position']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  String get status => stringValue(raw['status']);
  bool get isNegotiable => boolValue(raw['is_negotiable']);
  String? get requestedPlayerCardId =>
      stringOrNullValue(raw['requested_player_card_id']);
  String? get requestedPlayerId =>
      stringOrNullValue(raw['requested_player_id']);
  JsonMap get requestedFilters => jsonMap(raw['requested_filters_json'],
      fallback: const <String, Object?>{});
  DateTime? get expiresAt => dateTimeValue(raw['expires_at']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class PlayerCardMarketplaceSwapExecution {
  const PlayerCardMarketplaceSwapExecution._(this.raw);

  final JsonMap raw;

  factory PlayerCardMarketplaceSwapExecution.fromJson(Object? value) {
    return PlayerCardMarketplaceSwapExecution._(
      jsonMap(value, label: 'player card marketplace swap execution'),
    );
  }

  String get swapId => stringValue(raw['swap_execution_id']);
  String get listingId => stringValue(raw['listing_id']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  String get counterpartyUserId => stringValue(raw['counterparty_user_id']);
  String get ownerPlayerCardId => stringValue(raw['owner_player_card_id']);
  String get counterpartyPlayerCardId =>
      stringValue(raw['counterparty_player_card_id']);
  String get status => stringValue(raw['status']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
}

class PlayerCardPlayerSummary {
  const PlayerCardPlayerSummary._(this.raw);

  final JsonMap raw;

  factory PlayerCardPlayerSummary.fromJson(Object? value) {
    return PlayerCardPlayerSummary._(
      jsonMap(value, label: 'player card player summary'),
    );
  }

  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get position => stringOrNullValue(raw['position']);
  String? get nationalityCode => stringOrNullValue(raw['nationality_code']);
  String? get currentClubName => stringOrNullValue(raw['current_club_name']);
  int get cardSupplyTotal => intValue(raw['card_supply_total']);
  double? get latestValueCredits => raw['latest_value_credits'] == null
      ? null
      : numberValue(raw['latest_value_credits']);
}

class PlayerCardPlayerDetail {
  const PlayerCardPlayerDetail._(this.raw);

  final JsonMap raw;

  factory PlayerCardPlayerDetail.fromJson(Object? value) {
    return PlayerCardPlayerDetail._(
      jsonMap(value, label: 'player card player detail'),
    );
  }

  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get position => stringOrNullValue(raw['position']);
  String? get nationalityCode => stringOrNullValue(raw['nationality_code']);
  String? get currentClubName => stringOrNullValue(raw['current_club_name']);
  List<String> get aliases => stringListValue(raw['aliases']);
  List<String> get monikers => stringListValue(raw['monikers']);
  List<JsonMap> get cards => jsonMapList(raw['cards'], label: 'player cards');
  List<JsonMap> get effects =>
      jsonMapList(raw['effects'], label: 'player card effects');
  List<JsonMap> get formBuffs =>
      jsonMapList(raw['form_buffs'], label: 'player card form buffs');
  JsonMap? get momentum => jsonMapOrNull(raw['momentum']);
  JsonMap? get latestStatsSnapshot =>
      jsonMapOrNull(raw['latest_stats_snapshot']);
  JsonMap? get latestMarketSnapshot =>
      jsonMapOrNull(raw['latest_market_snapshot']);
  List<JsonMap> get realWorldFlags =>
      jsonMapList(raw['real_world_flags'], label: 'player real world flags');
  List<JsonMap> get realWorldFormModifiers =>
      jsonMapList(raw['real_world_form_modifiers'],
          label: 'player form modifiers');
  List<JsonMap> get demandSignals =>
      jsonMapList(raw['demand_signals'], label: 'player demand signals');
  double get recommendationPriorityDelta =>
      numberValue(raw['recommendation_priority_delta']);
  double get marketBuzzScore => numberValue(raw['market_buzz_score']);
}

class PlayerCardHolding {
  const PlayerCardHolding._(this.raw);

  final JsonMap raw;

  factory PlayerCardHolding.fromJson(Object? value) {
    return PlayerCardHolding._(
      jsonMap(value, label: 'player card holding'),
    );
  }

  String get holdingId => stringValue(raw['holding_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  int get quantityTotal => intValue(raw['quantity_total']);
  int get quantityReserved => intValue(raw['quantity_reserved']);
  int get quantityAvailable => intValue(raw['quantity_available']);
  DateTime? get lastAcquiredAt => dateTimeValue(raw['last_acquired_at']);
}

class PlayerCardListing {
  const PlayerCardListing._(this.raw);

  final JsonMap raw;

  factory PlayerCardListing.fromJson(Object? value) {
    return PlayerCardListing._(
      jsonMap(value, label: 'player card listing'),
    );
  }

  String get listingId => stringValue(raw['listing_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  String get sellerUserId => stringValue(raw['seller_user_id']);
  int get quantity => intValue(raw['quantity']);
  double get pricePerCardCredits => numberValue(raw['price_per_card_credits']);
  String get status => stringValue(raw['status']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class PlayerCardLoanSupportListing {
  const PlayerCardLoanSupportListing._(this.raw);

  final JsonMap raw;

  factory PlayerCardLoanSupportListing.fromJson(Object? value) {
    return PlayerCardLoanSupportListing._(
      jsonMap(value, label: 'player card loan support listing'),
    );
  }

  String get loanListingId => stringValue(raw['loan_listing_id']);
  String get playerCardId => stringValue(raw['player_card_id']);
  String get playerId => stringValue(raw['player_id']);
  String get playerName => stringValue(raw['player_name']);
  PlayerAvatar? get avatar => PlayerAvatar.fromJsonOrNull(raw['avatar']);
  String? get position => stringOrNullValue(raw['position']);
  String get tierCode => stringValue(raw['tier_code']);
  String get tierName => stringValue(raw['tier_name']);
  String get editionCode => stringValue(raw['edition_code']);
  String get ownerUserId => stringValue(raw['owner_user_id']);
  int get totalSlots => intValue(raw['total_slots']);
  int get availableSlots => intValue(raw['available_slots']);
  int get durationDays => intValue(raw['duration_days']);
  double get loanFeeCredits => numberValue(raw['loan_fee_credits']);
  String get status => stringValue(raw['status']);
  DateTime? get expiresAt => dateTimeValue(raw['expires_at']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
}

class PlayerCardWatchlistItem {
  const PlayerCardWatchlistItem._(this.raw);

  final JsonMap raw;

  factory PlayerCardWatchlistItem.fromJson(Object? value) {
    return PlayerCardWatchlistItem._(
      jsonMap(value, label: 'player card watchlist item'),
    );
  }

  String get id => stringValue(raw['id']);
  String get playerId => stringValue(raw['player_id']);
  String? get playerCardId => stringOrNullValue(raw['player_card_id']);
  String? get notes => stringOrNullValue(raw['notes']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}
