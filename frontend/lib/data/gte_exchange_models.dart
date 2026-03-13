import 'gte_models.dart';

class GteMarketPlayersQuery {
  const GteMarketPlayersQuery({
    this.limit = 20,
    this.offset = 0,
    this.search,
  });

  final int limit;
  final int offset;
  final String? search;

  Map<String, Object?> toQueryParameters() {
    final String? trimmedSearch = search?.trim();
    return <String, Object?>{
      'limit': limit,
      'offset': offset,
      if (trimmedSearch != null && trimmedSearch.isNotEmpty)
        'search': trimmedSearch,
    };
  }
}

class GteMarketPlayerListItem {
  const GteMarketPlayerListItem({
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.nationality,
    required this.currentClubName,
    required this.age,
    required this.currentValueCredits,
    required this.movementPct,
    required this.trendScore,
    required this.marketInterestScore,
    required this.averageRating,
  });

  final String playerId;
  final String playerName;
  final String? position;
  final String? nationality;
  final String? currentClubName;
  final int age;
  final double currentValueCredits;
  final double movementPct;
  final double trendScore;
  final int marketInterestScore;
  final double? averageRating;

  bool get isRising => movementPct > 0;

  factory GteMarketPlayerListItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market player list item');
    return GteMarketPlayerListItem(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      nationality: GteJson.stringOrNull(json, <String>['nationality']),
      currentClubName: GteJson.stringOrNull(
          json, <String>['current_club_name', 'currentClubName']),
      age: GteJson.integer(json, <String>['age']),
      currentValueCredits: GteJson.number(
          json, <String>['current_value_credits', 'currentValueCredits']),
      movementPct:
          GteJson.number(json, <String>['movement_pct', 'movementPct']),
      trendScore: GteJson.number(json, <String>['trend_score', 'trendScore']),
      marketInterestScore: GteJson.integer(
        json,
        <String>['market_interest_score', 'marketInterestScore'],
      ),
      averageRating:
          _nullableNumber(json, <String>['average_rating', 'averageRating']),
    );
  }
}

class GteMarketPlayerListView {
  const GteMarketPlayerListView({
    required this.items,
    required this.limit,
    required this.offset,
    required this.total,
  });

  final List<GteMarketPlayerListItem> items;
  final int limit;
  final int offset;
  final int total;

  factory GteMarketPlayerListView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market players');
    return GteMarketPlayerListView(
      items: GteJson.typedList(
          json, <String>['items'], GteMarketPlayerListItem.fromJson),
      limit: GteJson.integer(json, <String>['limit'], fallback: 20),
      offset: GteJson.integer(json, <String>['offset']),
      total: GteJson.integer(json, <String>['total']),
    );
  }
}

class GteMarketPlayerIdentity {
  const GteMarketPlayerIdentity({
    required this.playerName,
    required this.firstName,
    required this.lastName,
    required this.shortName,
    required this.position,
    required this.normalizedPosition,
    required this.nationality,
    required this.nationalityCode,
    required this.age,
    required this.dateOfBirth,
    required this.preferredFoot,
    required this.shirtNumber,
    required this.heightCm,
    required this.weightKg,
    required this.currentClubId,
    required this.currentClubName,
    required this.currentCompetitionId,
    required this.currentCompetitionName,
    required this.imageUrl,
  });

  final String playerName;
  final String? firstName;
  final String? lastName;
  final String? shortName;
  final String? position;
  final String? normalizedPosition;
  final String? nationality;
  final String? nationalityCode;
  final int age;
  final String? dateOfBirth;
  final String? preferredFoot;
  final int? shirtNumber;
  final int? heightCm;
  final int? weightKg;
  final String? currentClubId;
  final String? currentClubName;
  final String? currentCompetitionId;
  final String? currentCompetitionName;
  final String? imageUrl;

  factory GteMarketPlayerIdentity.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market player identity');
    return GteMarketPlayerIdentity(
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      firstName:
          GteJson.stringOrNull(json, <String>['first_name', 'firstName']),
      lastName: GteJson.stringOrNull(json, <String>['last_name', 'lastName']),
      shortName:
          GteJson.stringOrNull(json, <String>['short_name', 'shortName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      normalizedPosition: GteJson.stringOrNull(
        json,
        <String>['normalized_position', 'normalizedPosition'],
      ),
      nationality: GteJson.stringOrNull(json, <String>['nationality']),
      nationalityCode: GteJson.stringOrNull(
        json,
        <String>['nationality_code', 'nationalityCode'],
      ),
      age: GteJson.integer(json, <String>['age']),
      dateOfBirth:
          GteJson.stringOrNull(json, <String>['date_of_birth', 'dateOfBirth']),
      preferredFoot: GteJson.stringOrNull(
          json, <String>['preferred_foot', 'preferredFoot']),
      shirtNumber:
          _nullableInteger(json, <String>['shirt_number', 'shirtNumber']),
      heightCm: _nullableInteger(json, <String>['height_cm', 'heightCm']),
      weightKg: _nullableInteger(json, <String>['weight_kg', 'weightKg']),
      currentClubId: GteJson.stringOrNull(
          json, <String>['current_club_id', 'currentClubId']),
      currentClubName: GteJson.stringOrNull(
        json,
        <String>['current_club_name', 'currentClubName'],
      ),
      currentCompetitionId: GteJson.stringOrNull(
        json,
        <String>['current_competition_id', 'currentCompetitionId'],
      ),
      currentCompetitionName: GteJson.stringOrNull(
        json,
        <String>['current_competition_name', 'currentCompetitionName'],
      ),
      imageUrl: GteJson.stringOrNull(json, <String>['image_url', 'imageUrl']),
    );
  }
}

class GteMarketPlayerMarketProfile {
  const GteMarketPlayerMarketProfile({
    required this.isTradable,
    required this.marketValueEur,
    required this.supplyTier,
    required this.liquidityBand,
    required this.holderCount,
    required this.topHolderSharePct,
    required this.top3HolderSharePct,
    required this.snapshotMarketPriceCredits,
    required this.quotedMarketPriceCredits,
    required this.trustedTradePriceCredits,
    required this.tradeTrustScore,
  });

  final bool isTradable;
  final double? marketValueEur;
  final String? supplyTier;
  final String? liquidityBand;
  final int? holderCount;
  final double? topHolderSharePct;
  final double? top3HolderSharePct;
  final double? snapshotMarketPriceCredits;
  final double? quotedMarketPriceCredits;
  final double? trustedTradePriceCredits;
  final double? tradeTrustScore;

  factory GteMarketPlayerMarketProfile.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market profile');
    return GteMarketPlayerMarketProfile(
      isTradable: GteJson.boolean(json, <String>['is_tradable', 'isTradable']),
      marketValueEur:
          _nullableNumber(json, <String>['market_value_eur', 'marketValueEur']),
      supplyTier:
          GteJson.stringOrNull(json, <String>['supply_tier', 'supplyTier']),
      liquidityBand: GteJson.stringOrNull(
          json, <String>['liquidity_band', 'liquidityBand']),
      holderCount:
          _nullableInteger(json, <String>['holder_count', 'holderCount']),
      topHolderSharePct: _nullableNumber(
        json,
        <String>['top_holder_share_pct', 'topHolderSharePct'],
      ),
      top3HolderSharePct: _nullableNumber(
        json,
        <String>['top_3_holder_share_pct', 'top3HolderSharePct'],
      ),
      snapshotMarketPriceCredits: _nullableNumber(
        json,
        <String>['snapshot_market_price_credits', 'snapshotMarketPriceCredits'],
      ),
      quotedMarketPriceCredits: _nullableNumber(
        json,
        <String>['quoted_market_price_credits', 'quotedMarketPriceCredits'],
      ),
      trustedTradePriceCredits: _nullableNumber(
        json,
        <String>['trusted_trade_price_credits', 'trustedTradePriceCredits'],
      ),
      tradeTrustScore: _nullableNumber(
          json, <String>['trade_trust_score', 'tradeTrustScore']),
    );
  }
}

class GteMarketPlayerValue {
  const GteMarketPlayerValue({
    required this.lastSnapshotId,
    required this.lastSnapshotAt,
    required this.currentValueCredits,
    required this.previousValueCredits,
    required this.movementPct,
    required this.footballTruthValueCredits,
    required this.marketSignalValueCredits,
    required this.publishedCardValueCredits,
    required this.scoutingSignalValueCredits,
    required this.egameSignalValueCredits,
    required this.confidenceScore,
    required this.confidenceTier,
    required this.trend7dPct,
    required this.trend30dPct,
    required this.trendDirection,
    required this.trendConfidence,
    required this.movementTags,
  });

  final String? lastSnapshotId;
  final DateTime? lastSnapshotAt;
  final double currentValueCredits;
  final double? previousValueCredits;
  final double movementPct;
  final double? footballTruthValueCredits;
  final double? marketSignalValueCredits;
  final double? publishedCardValueCredits;
  final double? scoutingSignalValueCredits;
  final double? egameSignalValueCredits;
  final double? confidenceScore;
  final String? confidenceTier;
  final double? trend7dPct;
  final double? trend30dPct;
  final String? trendDirection;
  final double? trendConfidence;
  final List<String> movementTags;

  factory GteMarketPlayerValue.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market player value');
    return GteMarketPlayerValue(
      lastSnapshotId: GteJson.stringOrNull(
          json, <String>['last_snapshot_id', 'lastSnapshotId']),
      lastSnapshotAt: GteJson.dateTimeOrNull(
          json, <String>['last_snapshot_at', 'lastSnapshotAt']),
      currentValueCredits: GteJson.number(
        json,
        <String>['current_value_credits', 'currentValueCredits'],
      ),
      previousValueCredits: _nullableNumber(
        json,
        <String>['previous_value_credits', 'previousValueCredits'],
      ),
      movementPct:
          GteJson.number(json, <String>['movement_pct', 'movementPct']),
      footballTruthValueCredits: _nullableNumber(
        json,
        <String>['football_truth_value_credits', 'footballTruthValueCredits'],
      ),
      marketSignalValueCredits: _nullableNumber(
        json,
        <String>['market_signal_value_credits', 'marketSignalValueCredits'],
      ),
      publishedCardValueCredits: _nullableNumber(
        json,
        <String>['published_card_value_credits', 'publishedCardValueCredits'],
      ),
      scoutingSignalValueCredits: _nullableNumber(
        json,
        <String>['scouting_signal_value_credits', 'scoutingSignalValueCredits'],
      ),
      egameSignalValueCredits: _nullableNumber(
        json,
        <String>['egame_signal_value_credits', 'egameSignalValueCredits'],
      ),
      confidenceScore:
          _nullableNumber(json, <String>['confidence_score', 'confidenceScore']),
      confidenceTier: GteJson.stringOrNull(
        json,
        <String>['confidence_tier', 'confidenceTier'],
      ),
      trend7dPct: _nullableNumber(json, <String>['trend_7d_pct', 'trend7dPct']),
      trend30dPct:
          _nullableNumber(json, <String>['trend_30d_pct', 'trend30dPct']),
      trendDirection: GteJson.stringOrNull(
        json,
        <String>['trend_direction', 'trendDirection'],
      ),
      trendConfidence: _nullableNumber(
        json,
        <String>['trend_confidence', 'trendConfidence'],
      ),
      movementTags: GteJson.typedList(
        json,
        <String>['movement_tags', 'movementTags'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
    );
  }
}

class GteMarketPlayerTrend {
  const GteMarketPlayerTrend({
    required this.trendScore,
    required this.marketInterestScore,
    required this.averageRating,
    required this.globalScoutingIndex,
    required this.previousGlobalScoutingIndex,
    required this.globalScoutingIndexMovementPct,
    required this.drivers,
    required this.trend7dPct,
    required this.trend30dPct,
    required this.trendDirection,
    required this.trendConfidence,
    required this.confidenceTier,
    required this.movementTags,
  });

  final double trendScore;
  final int marketInterestScore;
  final double? averageRating;
  final double globalScoutingIndex;
  final double? previousGlobalScoutingIndex;
  final double? globalScoutingIndexMovementPct;
  final List<String> drivers;
  final double? trend7dPct;
  final double? trend30dPct;
  final String? trendDirection;
  final double? trendConfidence;
  final String? confidenceTier;
  final List<String> movementTags;

  factory GteMarketPlayerTrend.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market player trend');
    return GteMarketPlayerTrend(
      trendScore: GteJson.number(json, <String>['trend_score', 'trendScore']),
      marketInterestScore: GteJson.integer(
        json,
        <String>['market_interest_score', 'marketInterestScore'],
      ),
      averageRating:
          _nullableNumber(json, <String>['average_rating', 'averageRating']),
      globalScoutingIndex: GteJson.number(
        json,
        <String>['global_scouting_index', 'globalScoutingIndex'],
      ),
      previousGlobalScoutingIndex: _nullableNumber(
        json,
        <String>[
          'previous_global_scouting_index',
          'previousGlobalScoutingIndex'
        ],
      ),
      globalScoutingIndexMovementPct: _nullableNumber(
        json,
        <String>[
          'global_scouting_index_movement_pct',
          'globalScoutingIndexMovementPct'
        ],
      ),
      drivers: GteJson.typedList(
        json,
        <String>['drivers'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
      trend7dPct: _nullableNumber(json, <String>['trend_7d_pct', 'trend7dPct']),
      trend30dPct:
          _nullableNumber(json, <String>['trend_30d_pct', 'trend30dPct']),
      trendDirection: GteJson.stringOrNull(
        json,
        <String>['trend_direction', 'trendDirection'],
      ),
      trendConfidence: _nullableNumber(
        json,
        <String>['trend_confidence', 'trendConfidence'],
      ),
      confidenceTier: GteJson.stringOrNull(
        json,
        <String>['confidence_tier', 'confidenceTier'],
      ),
      movementTags: GteJson.typedList(
        json,
        <String>['movement_tags', 'movementTags'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
    );
  }
}

class GteMarketPlayerDetailView {
  const GteMarketPlayerDetailView({
    required this.playerId,
    required this.identity,
    required this.marketProfile,
    required this.value,
    required this.trend,
  });

  final String playerId;
  final GteMarketPlayerIdentity identity;
  final GteMarketPlayerMarketProfile marketProfile;
  final GteMarketPlayerValue value;
  final GteMarketPlayerTrend trend;

  factory GteMarketPlayerDetailView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'market player detail');
    return GteMarketPlayerDetailView(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      identity: GteMarketPlayerIdentity.fromJson(
        GteJson.value(json, <String>['identity']) ?? const <String, Object?>{},
      ),
      marketProfile: GteMarketPlayerMarketProfile.fromJson(
        GteJson.value(json, <String>['market_profile', 'marketProfile']) ??
            const <String, Object?>{},
      ),
      value: GteMarketPlayerValue.fromJson(
        GteJson.value(json, <String>['value']) ?? const <String, Object?>{},
      ),
      trend: GteMarketPlayerTrend.fromJson(
        GteJson.value(json, <String>['trend']) ?? const <String, Object?>{},
      ),
    );
  }
}



class GteLifecycleBadgeView {
  const GteLifecycleBadgeView({
    required this.status,
    required this.label,
    required this.available,
    this.reason,
    this.until,
  });

  final String status;
  final String label;
  final bool available;
  final String? reason;
  final DateTime? until;

  factory GteLifecycleBadgeView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'lifecycle badge');
    return GteLifecycleBadgeView(
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      label: GteJson.string(json, <String>['label'], fallback: 'Unknown'),
      available: GteJson.boolean(json, <String>['available'], fallback: false),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      until: GteJson.dateTimeOrNull(json, <String>['until']),
    );
  }
}

class GteContractBadgeView {
  const GteContractBadgeView({
    required this.status,
    required this.label,
    this.clubName,
    this.endsOn,
  });

  final String status;
  final String label;
  final String? clubName;
  final DateTime? endsOn;

  factory GteContractBadgeView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'contract badge');
    return GteContractBadgeView(
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      label: GteJson.string(json, <String>['label'], fallback: 'Unknown'),
      clubName: GteJson.stringOrNull(json, <String>['club_name', 'clubName']),
      endsOn: GteJson.dateTimeOrNull(json, <String>['ends_on', 'endsOn']),
    );
  }
}

class GteTransferStatusView {
  const GteTransferStatusView({
    required this.windowOpen,
    required this.eligible,
    this.reason,
    this.windowLabel,
    this.lastBidStatus,
  });

  final bool windowOpen;
  final bool eligible;
  final String? reason;
  final String? windowLabel;
  final String? lastBidStatus;

  factory GteTransferStatusView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'transfer status');
    return GteTransferStatusView(
      windowOpen: GteJson.boolean(json, <String>['window_open', 'windowOpen']),
      eligible: GteJson.boolean(json, <String>['eligible']),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      windowLabel: GteJson.stringOrNull(json, <String>['window_label', 'windowLabel']),
      lastBidStatus: GteJson.stringOrNull(json, <String>['last_bid_status', 'lastBidStatus']),
    );
  }
}

class GteLifecycleEventItem {
  const GteLifecycleEventItem({
    required this.eventType,
    required this.summary,
    this.occurredOn,
  });

  final String eventType;
  final String summary;
  final DateTime? occurredOn;

  factory GteLifecycleEventItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'lifecycle event');
    return GteLifecycleEventItem(
      eventType: GteJson.string(json, <String>['event_type', 'eventType']),
      summary: GteJson.string(json, <String>['summary'], fallback: 'Lifecycle event'),
      occurredOn: GteJson.dateTimeOrNull(json, <String>['occurred_on', 'occurredOn']),
    );
  }
}

class GtePlayerLifecycleSnapshot {
  const GtePlayerLifecycleSnapshot({
    required this.playerId,
    required this.playerName,
    required this.availabilityBadge,
    required this.transferStatus,
    required this.recentEvents,
    this.contractBadge,
  });

  final String playerId;
  final String playerName;
  final GteLifecycleBadgeView availabilityBadge;
  final GteTransferStatusView transferStatus;
  final List<GteLifecycleEventItem> recentEvents;
  final GteContractBadgeView? contractBadge;

  factory GtePlayerLifecycleSnapshot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'player lifecycle snapshot');
    return GtePlayerLifecycleSnapshot(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      availabilityBadge: GteLifecycleBadgeView.fromJson(
        GteJson.value(json, <String>['availability_badge', 'availabilityBadge']) ?? const <String, Object?>{},
      ),
      transferStatus: GteTransferStatusView.fromJson(
        GteJson.value(json, <String>['transfer_status', 'transferStatus']) ?? const <String, Object?>{},
      ),
      contractBadge: GteJson.value(json, <String>['contract_badge', 'contractBadge']) == null
          ? null
          : GteContractBadgeView.fromJson(
              GteJson.value(json, <String>['contract_badge', 'contractBadge']),
            ),
      recentEvents: GteJson.typedList(
        json,
        <String>['recent_events', 'recentEvents'],
        GteLifecycleEventItem.fromJson,
      ),
    );
  }
}

class GtePlayerMarketSnapshot {
  const GtePlayerMarketSnapshot({
    required this.detail,
    required this.ticker,
    required this.candles,
    required this.orderBook,
    this.lifecycle,
  });

  final GteMarketPlayerDetailView detail;
  final GteMarketTicker ticker;
  final GteMarketCandles candles;
  final GteOrderBook orderBook;
  final GtePlayerLifecycleSnapshot? lifecycle;

  GtePlayerMarketSnapshot copyWith({
    GteMarketPlayerDetailView? detail,
    GteMarketTicker? ticker,
    GteMarketCandles? candles,
    GteOrderBook? orderBook,
    GtePlayerLifecycleSnapshot? lifecycle,
  }) {
    return GtePlayerMarketSnapshot(
      detail: detail ?? this.detail,
      ticker: ticker ?? this.ticker,
      candles: candles ?? this.candles,
      orderBook: orderBook ?? this.orderBook,
      lifecycle: lifecycle ?? this.lifecycle,
    );
  }
}

double? _nullableNumber(Map<String, Object?> json, List<String> keys) {
  if (GteJson.value(json, keys) == null) {
    return null;
  }
  return GteJson.number(json, keys);
}

int? _nullableInteger(Map<String, Object?> json, List<String> keys) {
  if (GteJson.value(json, keys) == null) {
    return null;
  }
  return GteJson.integer(json, keys);
}
