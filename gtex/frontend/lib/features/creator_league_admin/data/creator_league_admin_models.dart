import '../../shared/data/gte_feature_support.dart';

class CreatorLeagueTierCreateRequest {
  const CreatorLeagueTierCreateRequest({
    this.name,
    this.clubCount = 20,
    this.promotionSpots = 3,
    this.relegationSpots = 0,
  });

  final String? name;
  final int clubCount;
  final int promotionSpots;
  final int relegationSpots;

  JsonMap toJson() => <String, Object?>{
        if (name != null) 'name': name,
        'club_count': clubCount,
        'promotion_spots': promotionSpots,
        'relegation_spots': relegationSpots,
      };
}

class CreatorLeagueTierUpdateRequest {
  const CreatorLeagueTierUpdateRequest({
    this.name,
    this.clubCount,
    this.promotionSpots,
    this.relegationSpots,
    this.active,
  });

  final String? name;
  final int? clubCount;
  final int? promotionSpots;
  final int? relegationSpots;
  final bool? active;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'name': name,
        'club_count': clubCount,
        'promotion_spots': promotionSpots,
        'relegation_spots': relegationSpots,
        'active': active,
      });
}

class CreatorLeagueConfigUpdateRequest {
  const CreatorLeagueConfigUpdateRequest({
    this.enabled,
    this.seasonsPaused,
    this.leagueFormat,
    this.defaultClubCount,
    this.divisionCount,
    this.matchFrequencyDays,
    this.seasonDurationDays,
    this.broadcastPurchasesEnabled,
    this.seasonPassSalesEnabled,
    this.matchGiftingEnabled,
    this.settlementReviewEnabled,
    this.settlementReviewTotalRevenueCoin,
    this.settlementReviewCreatorShareCoin,
    this.settlementReviewPlatformShareCoin,
    this.settlementReviewShareholderDistributionCoin,
  });

  final bool? enabled;
  final bool? seasonsPaused;
  final String? leagueFormat;
  final int? defaultClubCount;
  final int? divisionCount;
  final int? matchFrequencyDays;
  final int? seasonDurationDays;
  final bool? broadcastPurchasesEnabled;
  final bool? seasonPassSalesEnabled;
  final bool? matchGiftingEnabled;
  final bool? settlementReviewEnabled;
  final double? settlementReviewTotalRevenueCoin;
  final double? settlementReviewCreatorShareCoin;
  final double? settlementReviewPlatformShareCoin;
  final double? settlementReviewShareholderDistributionCoin;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'enabled': enabled,
        'seasons_paused': seasonsPaused,
        'league_format': leagueFormat,
        'default_club_count': defaultClubCount,
        'division_count': divisionCount,
        'match_frequency_days': matchFrequencyDays,
        'season_duration_days': seasonDurationDays,
        'broadcast_purchases_enabled': broadcastPurchasesEnabled,
        'season_pass_sales_enabled': seasonPassSalesEnabled,
        'match_gifting_enabled': matchGiftingEnabled,
        'settlement_review_enabled': settlementReviewEnabled,
        'settlement_review_total_revenue_coin':
            settlementReviewTotalRevenueCoin,
        'settlement_review_creator_share_coin':
            settlementReviewCreatorShareCoin,
        'settlement_review_platform_share_coin':
            settlementReviewPlatformShareCoin,
        'settlement_review_shareholder_distribution_coin':
            settlementReviewShareholderDistributionCoin,
      });
}

class CreatorLeagueSeasonTierAssignmentRequest {
  const CreatorLeagueSeasonTierAssignmentRequest({
    required this.tierId,
    required this.clubIds,
  });

  final String tierId;
  final List<String> clubIds;

  JsonMap toJson() => <String, Object?>{
        'tier_id': tierId,
        'club_ids': clubIds,
      };
}

class CreatorLeagueSeasonCreateRequest {
  const CreatorLeagueSeasonCreateRequest({
    required this.startDate,
    required this.assignments,
    this.name,
    this.activate = true,
    this.createdByUserId,
  });

  final DateTime startDate;
  final List<CreatorLeagueSeasonTierAssignmentRequest> assignments;
  final String? name;
  final bool activate;
  final String? createdByUserId;

  JsonMap toJson() => <String, Object?>{
        'start_date': dateQueryValue(startDate),
        if (name != null) 'name': name,
        'activate': activate,
        if (createdByUserId != null) 'created_by_user_id': createdByUserId,
        'assignments': assignments
            .map((CreatorLeagueSeasonTierAssignmentRequest item) =>
                item.toJson())
            .toList(growable: false),
      };
}

class CreatorLeagueSettlementReviewRequest {
  const CreatorLeagueSettlementReviewRequest({
    this.reviewNote,
  });

  final String? reviewNote;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'review_note': reviewNote,
      });
}

class CreatorLeagueLivePriorityQuery {
  const CreatorLeagueLivePriorityQuery({
    this.limit = 10,
  });

  final int limit;

  Map<String, Object?> toQuery() => <String, Object?>{'limit': limit};
}

class CreatorLeagueFinancialReportQuery {
  const CreatorLeagueFinancialReportQuery({
    this.seasonId,
    this.settlementLimit = 10,
    this.auditLimit = 20,
  });

  final String? seasonId;
  final int settlementLimit;
  final int auditLimit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'season_id': seasonId,
        'settlement_limit': settlementLimit,
        'audit_limit': auditLimit,
      });
}

class CreatorLeagueFinancialSettlementsQuery {
  const CreatorLeagueFinancialSettlementsQuery({
    this.seasonId,
    this.reviewStatus,
    this.limit = 50,
  });

  final String? seasonId;
  final String? reviewStatus;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'season_id': seasonId,
        'review_status': reviewStatus,
        'limit': limit,
      });
}

class CreatorLeagueConfig {
  const CreatorLeagueConfig._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueConfig.fromJson(Object? value) {
    return CreatorLeagueConfig._(
      jsonMap(value, label: 'creator league config'),
    );
  }

  String get id => stringValue(raw['id']);
  String get leagueKey => stringValue(raw['league_key']);
  bool get enabled => boolValue(raw['enabled']);
  bool get seasonsPaused => boolValue(raw['seasons_paused']);
  String get leagueFormat => stringValue(raw['league_format']);
  int get defaultClubCount => intValue(raw['default_club_count']);
  int get divisionCount => intValue(raw['division_count']);
  int get matchFrequencyDays => intValue(raw['match_frequency_days']);
  int get seasonDurationDays => intValue(raw['season_duration_days']);
  bool get broadcastPurchasesEnabled =>
      boolValue(raw['broadcast_purchases_enabled']);
  bool get seasonPassSalesEnabled =>
      boolValue(raw['season_pass_sales_enabled']);
  bool get matchGiftingEnabled => boolValue(raw['match_gifting_enabled']);
  bool get settlementReviewEnabled =>
      boolValue(raw['settlement_review_enabled']);
  double get settlementReviewTotalRevenueCoin =>
      numberValue(raw['settlement_review_total_revenue_coin']);
  double get settlementReviewCreatorShareCoin =>
      numberValue(raw['settlement_review_creator_share_coin']);
  double get settlementReviewPlatformShareCoin =>
      numberValue(raw['settlement_review_platform_share_coin']);
  double get settlementReviewShareholderDistributionCoin =>
      numberValue(raw['settlement_review_shareholder_distribution_coin']);
  List<JsonMap> get tiers =>
      jsonMapList(raw['tiers'], label: 'creator league tiers');
  List<JsonMap> get movementRules => jsonMapList(raw['movement_rules'],
      label: 'creator league movement rules');
  JsonMap? get currentSeason => jsonMapOrNull(raw['current_season']);
}

class CreatorLeagueSeason {
  const CreatorLeagueSeason._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueSeason.fromJson(Object? value) {
    return CreatorLeagueSeason._(
      jsonMap(value, label: 'creator league season'),
    );
  }

  String get id => stringValue(raw['id']);
  int get seasonNumber => intValue(raw['season_number']);
  String get name => stringValue(raw['name']);
  String get status => stringValue(raw['status']);
  String get startDate => stringValue(raw['start_date']);
  String get endDate => stringValue(raw['end_date']);
  int get matchFrequencyDays => intValue(raw['match_frequency_days']);
  int get seasonDurationDays => intValue(raw['season_duration_days']);
  DateTime? get launchedAt => dateTimeValue(raw['launched_at']);
  DateTime? get pausedAt => dateTimeValue(raw['paused_at']);
  DateTime? get completedAt => dateTimeValue(raw['completed_at']);
  List<JsonMap> get tiers =>
      jsonMapList(raw['tiers'], label: 'creator league season tiers');
}

class CreatorLeagueStanding {
  const CreatorLeagueStanding._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueStanding.fromJson(Object? value) {
    return CreatorLeagueStanding._(
      jsonMap(value, label: 'creator league standing'),
    );
  }

  int get rank => intValue(raw['rank']);
  String get clubId => stringValue(raw['club_id']);
  String? get clubName => stringOrNullValue(raw['club_name']);
  int get played => intValue(raw['played']);
  int get wins => intValue(raw['wins']);
  int get draws => intValue(raw['draws']);
  int get losses => intValue(raw['losses']);
  int get goalsFor => intValue(raw['goals_for']);
  int get goalsAgainst => intValue(raw['goals_against']);
  int get goalDiff => intValue(raw['goal_diff']);
  int get points => intValue(raw['points']);
  String get movementZone => stringValue(raw['movement_zone']);
}

class CreatorLeagueLivePriority {
  const CreatorLeagueLivePriority._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueLivePriority.fromJson(Object? value) {
    return CreatorLeagueLivePriority._(
      jsonMap(value, label: 'creator league live priority'),
    );
  }

  String? get bannerTitle => stringOrNullValue(raw['banner_title']);
  String? get bannerSubtitle => stringOrNullValue(raw['banner_subtitle']);
  List<JsonMap> get matches =>
      jsonMapList(raw['matches'], label: 'creator league live matches');
}

class CreatorLeagueSettlement {
  const CreatorLeagueSettlement._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueSettlement.fromJson(Object? value) {
    return CreatorLeagueSettlement._(
      jsonMap(value, label: 'creator league settlement'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  String get homeClubId => stringValue(raw['home_club_id']);
  String get awayClubId => stringValue(raw['away_club_id']);
  double get totalRevenueCoin => numberValue(raw['total_revenue_coin']);
  double get totalCreatorShareCoin =>
      numberValue(raw['total_creator_share_coin']);
  double get totalPlatformShareCoin =>
      numberValue(raw['total_platform_share_coin']);
  double get shareholderTotalDistributionCoin =>
      numberValue(raw['shareholder_total_distribution_coin']);
  String get reviewStatus => stringValue(raw['review_status']);
  List<String> get reviewReasonCodes =>
      stringListValue(raw['review_reason_codes_json']);
  JsonMap get policySnapshot =>
      jsonMap(raw['policy_snapshot_json'], fallback: const <String, Object?>{});
  String? get reviewedByUserId => stringOrNullValue(raw['reviewed_by_user_id']);
  DateTime? get reviewedAt => dateTimeValue(raw['reviewed_at']);
  String? get reviewNote => stringOrNullValue(raw['review_note']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorLeagueFinancialReport {
  const CreatorLeagueFinancialReport._(this.raw);

  final JsonMap raw;

  factory CreatorLeagueFinancialReport.fromJson(Object? value) {
    return CreatorLeagueFinancialReport._(
      jsonMap(value, label: 'creator league financial report'),
    );
  }

  CreatorLeagueConfig get config => CreatorLeagueConfig.fromJson(raw['config']);
  JsonMap get shareMarketControl =>
      jsonMap(raw['share_market_control'], fallback: const <String, Object?>{});
  JsonMap get stadiumControl =>
      jsonMap(raw['stadium_control'], fallback: const <String, Object?>{});
  JsonMap get creatorMatchGiftControls => jsonMap(
        raw['creator_match_gift_controls'],
        fallback: const <String, Object?>{},
      );
  JsonMap? get currentSeasonSummary =>
      jsonMapOrNull(raw['current_season_summary']);
  List<CreatorLeagueSettlement> get settlementsRequiringReview => parseList(
        raw['settlements_requiring_review'],
        CreatorLeagueSettlement.fromJson,
        label: 'creator league settlements requiring review',
      );
  List<JsonMap> get recentAuditEvents => jsonMapList(raw['recent_audit_events'],
      label: 'creator league audit events');
}
