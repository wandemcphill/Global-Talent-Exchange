import '../../shared/data/gte_feature_support.dart';

class FanWarsPeriodQuery {
  const FanWarsPeriodQuery({
    this.periodType = 'weekly',
    this.limit = 20,
    this.referenceDate,
  });

  final String periodType;
  final int limit;
  final DateTime? referenceDate;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'period_type': periodType,
        'limit': limit,
        'reference_date': dateQueryValue(referenceDate),
      });
}

class FanWarsDashboardQuery {
  const FanWarsDashboardQuery({
    this.periodType = 'weekly',
    this.referenceDate,
  });

  final String periodType;
  final DateTime? referenceDate;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'period_type': periodType,
        'reference_date': dateQueryValue(referenceDate),
      });
}

class FanWarProfileUpsertRequest {
  const FanWarProfileUpsertRequest({
    required this.profileType,
    this.displayName,
    this.clubId,
    this.creatorProfileId,
    this.countryCode,
    this.countryName,
    this.tagline,
    this.scoringConfig = const <String, Object?>{},
    this.metadata = const <String, Object?>{},
  });

  final String profileType;
  final String? displayName;
  final String? clubId;
  final String? creatorProfileId;
  final String? countryCode;
  final String? countryName;
  final String? tagline;
  final JsonMap scoringConfig;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'profile_type': profileType,
        if (displayName != null) 'display_name': displayName,
        if (clubId != null) 'club_id': clubId,
        if (creatorProfileId != null) 'creator_profile_id': creatorProfileId,
        if (countryCode != null) 'country_code': countryCode,
        if (countryName != null) 'country_name': countryName,
        if (tagline != null) 'tagline': tagline,
        'scoring_config_json': scoringConfig,
        'metadata_json': metadata,
      };
}

class FanWarPointRecordRequest {
  const FanWarPointRecordRequest({
    required this.sourceType,
    this.actorUserId,
    this.sourceRef,
    this.competitionId,
    this.matchId,
    this.clubId,
    this.creatorProfileId,
    this.countryCode,
    this.countryName,
    this.profileIds = const <String>[],
    this.targetCategories = const <String>[],
    this.spendAmountMinor = 0,
    this.engagementUnits = 1,
    this.qualityMultiplierBps = 10000,
    this.dedupeKey,
    this.nationsCupEntryId,
    this.awardedAt,
    this.metadata = const <String, Object?>{},
  });

  final String sourceType;
  final String? actorUserId;
  final String? sourceRef;
  final String? competitionId;
  final String? matchId;
  final String? clubId;
  final String? creatorProfileId;
  final String? countryCode;
  final String? countryName;
  final List<String> profileIds;
  final List<String> targetCategories;
  final int spendAmountMinor;
  final int engagementUnits;
  final int qualityMultiplierBps;
  final String? dedupeKey;
  final String? nationsCupEntryId;
  final DateTime? awardedAt;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (actorUserId != null) 'actor_user_id': actorUserId,
        'source_type': sourceType,
        if (sourceRef != null) 'source_ref': sourceRef,
        if (competitionId != null) 'competition_id': competitionId,
        if (matchId != null) 'match_id': matchId,
        if (clubId != null) 'club_id': clubId,
        if (creatorProfileId != null) 'creator_profile_id': creatorProfileId,
        if (countryCode != null) 'country_code': countryCode,
        if (countryName != null) 'country_name': countryName,
        'profile_ids': profileIds,
        'target_categories': targetCategories,
        'spend_amount_minor': spendAmountMinor,
        'engagement_units': engagementUnits,
        'quality_multiplier_bps': qualityMultiplierBps,
        if (dedupeKey != null) 'dedupe_key': dedupeKey,
        if (nationsCupEntryId != null)
          'nations_cup_entry_id': nationsCupEntryId,
        if (awardedAt != null)
          'awarded_at': awardedAt!.toUtc().toIso8601String(),
        'metadata_json': metadata,
      };
}

class CreatorCountryAssignmentRequest {
  const CreatorCountryAssignmentRequest({
    required this.creatorProfileId,
    required this.representedCountryCode,
    this.representedCountryName,
    this.eligibleCountryCodes = const <String>[],
    this.assignmentRule = 'admin_approved',
    this.allowAdminOverride = false,
    this.effectiveFrom,
    this.metadata = const <String, Object?>{},
  });

  final String creatorProfileId;
  final String representedCountryCode;
  final String? representedCountryName;
  final List<String> eligibleCountryCodes;
  final String assignmentRule;
  final bool allowAdminOverride;
  final DateTime? effectiveFrom;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'creator_profile_id': creatorProfileId,
        'represented_country_code': representedCountryCode,
        if (representedCountryName != null)
          'represented_country_name': representedCountryName,
        'eligible_country_codes': eligibleCountryCodes,
        'assignment_rule': assignmentRule,
        'allow_admin_override': allowAdminOverride,
        if (effectiveFrom != null)
          'effective_from': dateQueryValue(effectiveFrom),
        'metadata_json': metadata,
      };
}

class NationsCupCreateRequest {
  const NationsCupCreateRequest({
    required this.startDate,
    this.title,
    this.seasonLabel,
    this.groupCount = 8,
    this.groupSize = 4,
    this.groupAdvanceCount = 2,
    this.metadata = const <String, Object?>{},
  });

  final DateTime startDate;
  final String? title;
  final String? seasonLabel;
  final int groupCount;
  final int groupSize;
  final int groupAdvanceCount;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (title != null) 'title': title,
        if (seasonLabel != null) 'season_label': seasonLabel,
        'start_date': dateQueryValue(startDate),
        'group_count': groupCount,
        'group_size': groupSize,
        'group_advance_count': groupAdvanceCount,
        'metadata_json': metadata,
      };
}

class FanWarLeaderboard {
  const FanWarLeaderboard._(this.raw);

  final JsonMap raw;

  factory FanWarLeaderboard.fromJson(Object? value) {
    return FanWarLeaderboard._(jsonMap(value, label: 'fan war leaderboard'));
  }

  String get boardType => stringValue(raw['board_type']);
  String get periodType => stringValue(raw['period_type']);
  String get windowStart => stringValue(raw['window_start']);
  String get windowEnd => stringValue(raw['window_end']);
  JsonMap? get banner => jsonMapOrNull(raw['banner']);
  List<JsonMap> get entries =>
      jsonMapList(raw['entries'], label: 'fan war leaderboard entries');
}

class RivalryLeaderboard {
  const RivalryLeaderboard._(this.raw);

  final JsonMap raw;

  factory RivalryLeaderboard.fromJson(Object? value) {
    return RivalryLeaderboard._(
      jsonMap(value, label: 'fan war rivalry leaderboard'),
    );
  }

  String get boardType => stringValue(raw['board_type']);
  String get periodType => stringValue(raw['period_type']);
  JsonMap? get banner => jsonMapOrNull(raw['banner']);
  List<JsonMap> get entries =>
      jsonMapList(raw['entries'], label: 'fan war rivalry entries');
}

class FanWarDashboard {
  const FanWarDashboard._(this.raw);

  final JsonMap raw;

  factory FanWarDashboard.fromJson(Object? value) {
    return FanWarDashboard._(jsonMap(value, label: 'fan war dashboard'));
  }

  JsonMap get profile =>
      jsonMap(raw['profile'], fallback: const <String, Object?>{});
  String get periodType => stringValue(raw['period_type']);
  String get windowStart => stringValue(raw['window_start']);
  String get windowEnd => stringValue(raw['window_end']);
  int? get globalRank =>
      raw['global_rank'] == null ? null : intValue(raw['global_rank']);
  int? get categoryRank =>
      raw['category_rank'] == null ? null : intValue(raw['category_rank']);
  JsonMap? get banner => jsonMapOrNull(raw['banner']);
  JsonMap get summary =>
      jsonMap(raw['summary'], fallback: const <String, Object?>{});
  List<JsonMap> get rivalryEntries =>
      jsonMapList(raw['rivalry_entries'], label: 'fan war dashboard rivalries');
}

class NationsCupOverview {
  const NationsCupOverview._(this.raw);

  final JsonMap raw;

  factory NationsCupOverview.fromJson(Object? value) {
    return NationsCupOverview._(jsonMap(value, label: 'nations cup overview'));
  }

  String get competitionId => stringValue(raw['competition_id']);
  String get title => stringValue(raw['title']);
  String get status => stringValue(raw['status']);
  String? get seasonLabel => stringOrNullValue(raw['season_label']);
  String get startDate => stringValue(raw['start_date']);
  String? get completedAt => stringOrNullValue(raw['completed_at']);
  List<JsonMap> get groups =>
      jsonMapList(raw['groups'], label: 'nations cup groups');
  List<JsonMap> get records =>
      jsonMapList(raw['records'], label: 'nations cup records');
  List<JsonMap> get entries =>
      jsonMapList(raw['entries'], label: 'nations cup entries');
}

class FanWarProfile {
  const FanWarProfile._(this.raw);

  final JsonMap raw;

  factory FanWarProfile.fromJson(Object? value) {
    return FanWarProfile._(jsonMap(value, label: 'fan war profile'));
  }

  String get id => stringValue(raw['id']);
  String get profileType => stringValue(raw['profile_type']);
  String get displayName => stringValue(raw['display_name']);
  String get slug => stringValue(raw['slug']);
  String? get clubId => stringOrNullValue(raw['club_id']);
  String? get creatorProfileId => stringOrNullValue(raw['creator_profile_id']);
  String? get countryCode => stringOrNullValue(raw['country_code']);
  String? get countryName => stringOrNullValue(raw['country_name']);
  String? get tagline => stringOrNullValue(raw['tagline']);
  int get prestigePoints => intValue(raw['prestige_points']);
  List<String> get rivalProfileIds => stringListValue(raw['rival_profile_ids']);
  JsonMap get scoringConfig =>
      jsonMap(raw['scoring_config_json'], fallback: const <String, Object?>{});
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorCountryAssignment {
  const CreatorCountryAssignment._(this.raw);

  final JsonMap raw;

  factory CreatorCountryAssignment.fromJson(Object? value) {
    return CreatorCountryAssignment._(
      jsonMap(value, label: 'creator country assignment'),
    );
  }

  String get id => stringValue(raw['id']);
  String get creatorProfileId => stringValue(raw['creator_profile_id']);
  String get creatorUserId => stringValue(raw['creator_user_id']);
  String get representedCountryCode =>
      stringValue(raw['represented_country_code']);
  String get representedCountryName =>
      stringValue(raw['represented_country_name']);
  List<String> get eligibleCountryCodes =>
      stringListValue(raw['eligible_country_codes']);
  String get assignmentRule => stringValue(raw['assignment_rule']);
  bool get allowAdminOverride => boolValue(raw['allow_admin_override']);
  String get effectiveFrom => stringValue(raw['effective_from']);
  String? get effectiveTo => stringOrNullValue(raw['effective_to']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}
