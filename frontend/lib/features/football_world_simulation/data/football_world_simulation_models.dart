import '../../shared/data/gte_feature_support.dart';

class FootballCultureListQuery {
  const FootballCultureListQuery({
    this.countryCode,
    this.scopeType,
    this.activeOnly = true,
    this.limit = 20,
  });

  final String? countryCode;
  final String? scopeType;
  final bool activeOnly;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'country_code': countryCode,
        'scope_type': scopeType,
        'active_only': activeOnly,
        'limit': limit,
      });
}

class WorldNarrativeListQuery {
  const WorldNarrativeListQuery({
    this.clubId,
    this.competitionId,
    this.limit = 20,
  });

  final String? clubId;
  final String? competitionId;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'club_id': clubId,
        'competition_id': competitionId,
        'limit': limit,
      });
}

class FootballCultureUpsertRequest {
  const FootballCultureUpsertRequest({
    required this.displayName,
    this.scopeType = 'archetype',
    this.countryCode,
    this.regionName,
    this.cityName,
    this.playStyleSummary = '',
    this.supporterTraits = const <String>[],
    this.rivalryThemes = const <String>[],
    this.talentArchetypes = const <String>[],
    this.climateNotes = '',
    this.active = true,
    this.metadata = const <String, Object?>{},
  });

  final String displayName;
  final String scopeType;
  final String? countryCode;
  final String? regionName;
  final String? cityName;
  final String playStyleSummary;
  final List<String> supporterTraits;
  final List<String> rivalryThemes;
  final List<String> talentArchetypes;
  final String climateNotes;
  final bool active;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'display_name': displayName,
        'scope_type': scopeType,
        if (countryCode != null) 'country_code': countryCode,
        if (regionName != null) 'region_name': regionName,
        if (cityName != null) 'city_name': cityName,
        'play_style_summary': playStyleSummary,
        'supporter_traits_json': supporterTraits,
        'rivalry_themes_json': rivalryThemes,
        'talent_archetypes_json': talentArchetypes,
        'climate_notes': climateNotes,
        'active': active,
        'metadata_json': metadata,
      };
}

class ClubWorldProfileUpsertRequest {
  const ClubWorldProfileUpsertRequest({
    this.cultureKey,
    this.narrativePhase = 'establishing_identity',
    this.supporterMood = 'hopeful',
    this.derbyHeatScore = 0,
    this.globalAppealScore = 0,
    this.identityKeywords = const <String>[],
    this.transferIdentityTags = const <String>[],
    this.fanCultureTags = const <String>[],
    this.worldFlags = const <String>[],
    this.metadata = const <String, Object?>{},
  });

  final String? cultureKey;
  final String narrativePhase;
  final String supporterMood;
  final int derbyHeatScore;
  final int globalAppealScore;
  final List<String> identityKeywords;
  final List<String> transferIdentityTags;
  final List<String> fanCultureTags;
  final List<String> worldFlags;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (cultureKey != null) 'culture_key': cultureKey,
        'narrative_phase': narrativePhase,
        'supporter_mood': supporterMood,
        'derby_heat_score': derbyHeatScore,
        'global_appeal_score': globalAppealScore,
        'identity_keywords_json': identityKeywords,
        'transfer_identity_tags_json': transferIdentityTags,
        'fan_culture_tags_json': fanCultureTags,
        'world_flags_json': worldFlags,
        'metadata_json': metadata,
      };
}

class WorldNarrativeUpsertRequest {
  const WorldNarrativeUpsertRequest({
    required this.arcType,
    required this.headline,
    this.clubId,
    this.competitionId,
    this.status = 'active',
    this.visibility = 'public',
    this.summary = '',
    this.importanceScore = 50,
    this.simulationHorizon = 'seasonal',
    this.startAt,
    this.endAt,
    this.tags = const <String>[],
    this.impactVectors = const <String>[],
    this.metadata = const <String, Object?>{},
  });

  final String arcType;
  final String headline;
  final String? clubId;
  final String? competitionId;
  final String status;
  final String visibility;
  final String summary;
  final int importanceScore;
  final String simulationHorizon;
  final DateTime? startAt;
  final DateTime? endAt;
  final List<String> tags;
  final List<String> impactVectors;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (clubId != null) 'club_id': clubId,
        if (competitionId != null) 'competition_id': competitionId,
        'arc_type': arcType,
        'status': status,
        'visibility': visibility,
        'headline': headline,
        'summary': summary,
        'importance_score': importanceScore,
        'simulation_horizon': simulationHorizon,
        if (startAt != null) 'start_at': startAt!.toUtc().toIso8601String(),
        if (endAt != null) 'end_at': endAt!.toUtc().toIso8601String(),
        'tags_json': tags,
        'impact_vectors_json': impactVectors,
        'metadata_json': metadata,
      };
}

class FootballCulture {
  const FootballCulture._(this.raw);

  final JsonMap raw;

  factory FootballCulture.fromJson(Object? value) {
    return FootballCulture._(jsonMap(value, label: 'football culture'));
  }

  String get id => stringValue(raw['id']);
  String get cultureKey => stringValue(raw['culture_key']);
  String get displayName => stringValue(raw['display_name']);
  String get scopeType => stringValue(raw['scope_type']);
  String? get countryCode => stringOrNullValue(raw['country_code']);
  String? get regionName => stringOrNullValue(raw['region_name']);
  String? get cityName => stringOrNullValue(raw['city_name']);
  String get playStyleSummary => stringValue(raw['play_style_summary']);
  List<String> get supporterTraits =>
      stringListValue(raw['supporter_traits_json']);
  List<String> get rivalryThemes => stringListValue(raw['rivalry_themes_json']);
  List<String> get talentArchetypes =>
      stringListValue(raw['talent_archetypes_json']);
  String get climateNotes => stringValue(raw['climate_notes']);
  bool get active => boolValue(raw['active']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class ClubWorldContext {
  const ClubWorldContext._(this.raw);

  final JsonMap raw;

  factory ClubWorldContext.fromJson(Object? value) {
    return ClubWorldContext._(jsonMap(value, label: 'club world context'));
  }

  String get clubId => stringValue(raw['club_id']);
  String get clubName => stringValue(raw['club_name']);
  String? get shortName => stringOrNullValue(raw['short_name']);
  String? get countryCode => stringOrNullValue(raw['country_code']);
  String? get regionName => stringOrNullValue(raw['region_name']);
  String? get cityName => stringOrNullValue(raw['city_name']);
  int get reputationScore => intValue(raw['reputation_score']);
  String? get prestigeTier => stringOrNullValue(raw['prestige_tier']);
  JsonMap? get culture => jsonMapOrNull(raw['culture']);
  JsonMap get worldProfile =>
      jsonMap(raw['world_profile'], fallback: const <String, Object?>{});
  List<JsonMap> get activeNarratives =>
      jsonMapList(raw['active_narratives'], label: 'club world narratives');
  List<JsonMap> get simulationHooks =>
      jsonMapList(raw['simulation_hooks'], label: 'club world hooks');
}

class CompetitionWorldContext {
  const CompetitionWorldContext._(this.raw);

  final JsonMap raw;

  factory CompetitionWorldContext.fromJson(Object? value) {
    return CompetitionWorldContext._(
      jsonMap(value, label: 'competition world context'),
    );
  }

  String get competitionId => stringValue(raw['competition_id']);
  String get name => stringValue(raw['name']);
  String get status => stringValue(raw['status']);
  String get format => stringValue(raw['format']);
  String get stage => stringValue(raw['stage']);
  int get participantCount => intValue(raw['participant_count']);
  List<JsonMap> get activeNarratives => jsonMapList(
        raw['active_narratives'],
        label: 'competition world narratives',
      );
  List<JsonMap> get simulationHooks =>
      jsonMapList(raw['simulation_hooks'], label: 'competition world hooks');
}

class WorldNarrative {
  const WorldNarrative._(this.raw);

  final JsonMap raw;

  factory WorldNarrative.fromJson(Object? value) {
    return WorldNarrative._(jsonMap(value, label: 'world narrative'));
  }

  String get id => stringValue(raw['id']);
  String get slug => stringValue(raw['slug']);
  String get scopeType => stringValue(raw['scope_type']);
  String? get clubId => stringOrNullValue(raw['club_id']);
  String? get competitionId => stringOrNullValue(raw['competition_id']);
  String get arcType => stringValue(raw['arc_type']);
  String get status => stringValue(raw['status']);
  String get visibility => stringValue(raw['visibility']);
  String get headline => stringValue(raw['headline']);
  String get summary => stringValue(raw['summary']);
  int get importanceScore => intValue(raw['importance_score']);
  String get simulationHorizon => stringValue(raw['simulation_horizon']);
  DateTime? get startAt => dateTimeValue(raw['start_at']);
  DateTime? get endAt => dateTimeValue(raw['end_at']);
  List<String> get tags => stringListValue(raw['tags_json']);
  List<String> get impactVectors => stringListValue(raw['impact_vectors_json']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}
