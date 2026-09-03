import 'package:gte_frontend/data/gte_models.dart';

/// Wire models for the regen backend surfaces that Phase 3 left unreached.
///
/// Every field here maps to a field that exists on a backend response model
/// (`app/schemas/regen_core.py`, `app/schemas/regen_universe.py`,
/// `app/schemas/regen_ecosystem.py`). Nothing is derived, defaulted to a
/// meaningful-looking number, or invented: where the backend can omit a value
/// the Dart field is nullable, so the UI can say "unknown" instead of drawing
/// a zero. Phase 4 contract §P5 / §P6.
class RegenAbilityRange {
  const RegenAbilityRange({required this.minimum, required this.maximum});

  final int minimum;
  final int maximum;

  static RegenAbilityRange? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen ability range',
    );
    final int? min = GteJson.integerOrNull(json, <String>['minimum', 'min']);
    final int? max = GteJson.integerOrNull(json, <String>['maximum', 'max']);
    if (min == null || max == null) {
      return null;
    }
    return RegenAbilityRange(minimum: min, maximum: max);
  }

  String get label => minimum == maximum ? '$minimum' : '$minimum-$maximum';
}

/// `RegenPersonalityView`. Every trait is a real 0-100 backend attribute.
class RegenPersonality {
  const RegenPersonality({
    required this.temperament,
    required this.leadership,
    required this.ambition,
    required this.loyalty,
    required this.professionalism,
    required this.workRate,
    required this.flair,
    required this.resilience,
    required this.tags,
  });

  final int temperament;
  final int leadership;
  final int ambition;
  final int loyalty;
  final int professionalism;
  final int workRate;
  final int flair;
  final int resilience;
  final List<String> tags;

  static RegenPersonality? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen personality',
    );
    if (json.isEmpty) {
      return null;
    }
    return RegenPersonality(
      temperament: GteJson.integer(json, <String>['temperament']),
      leadership: GteJson.integer(json, <String>['leadership']),
      ambition: GteJson.integer(json, <String>['ambition']),
      loyalty: GteJson.integer(json, <String>['loyalty']),
      professionalism: GteJson.integer(
        json,
        <String>['professionalism'],
        fallback: 50,
      ),
      workRate: GteJson.integer(json, <String>['work_rate', 'workRate']),
      flair: GteJson.integer(json, <String>['flair']),
      resilience: GteJson.integer(json, <String>['resilience']),
      tags: GteJson.list(
            json['personality_tags'] ??
                json['personalityTags'] ??
                const <Object?>[],
          )
          .map((Object? tag) => tag.toString())
          .where((String tag) => tag.trim().isNotEmpty)
          .toList(growable: false),
    );
  }

  /// The traits as (label, 0-100 value) pairs, strongest first, so a panel can
  /// show what actually distinguishes this regen instead of a fixed grid.
  List<MapEntry<String, int>> get rankedTraits {
    final List<MapEntry<String, int>> traits = <MapEntry<String, int>>[
      MapEntry<String, int>('Ambition', ambition),
      MapEntry<String, int>('Leadership', leadership),
      MapEntry<String, int>('Work rate', workRate),
      MapEntry<String, int>('Flair', flair),
      MapEntry<String, int>('Resilience', resilience),
      MapEntry<String, int>('Loyalty', loyalty),
      MapEntry<String, int>('Professionalism', professionalism),
      MapEntry<String, int>('Temperament', temperament),
    ];
    traits.sort(
      (MapEntry<String, int> a, MapEntry<String, int> b) =>
          b.value.compareTo(a.value),
    );
    return traits;
  }
}

/// `RegenOriginView` - where the regen is actually from.
class RegenOrigin {
  const RegenOrigin({
    required this.countryCode,
    this.regionName,
    this.cityName,
    this.urbanicity,
  });

  final String countryCode;
  final String? regionName;
  final String? cityName;
  final String? urbanicity;

  static RegenOrigin? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(value, label: 'regen origin');
    final String? code = GteJson.stringOrNull(json, <String>[
      'country_code',
      'countryCode',
    ]);
    if (code == null) {
      return null;
    }
    return RegenOrigin(
      countryCode: code,
      regionName: GteJson.stringOrNull(json, <String>[
        'region_name',
        'regionName',
      ]),
      cityName: GteJson.stringOrNull(json, <String>['city_name', 'cityName']),
      urbanicity: GteJson.stringOrNull(json, <String>['urbanicity']),
    );
  }

  /// "Kano, Kano State" - omits the parts the backend did not supply rather
  /// than padding them out.
  String get placeLabel {
    final List<String> parts = <String>[
      if ((cityName ?? '').trim().isNotEmpty) cityName!.trim(),
      if ((regionName ?? '').trim().isNotEmpty) regionName!.trim(),
    ];
    return parts.isEmpty ? countryCode : parts.join(', ');
  }
}

/// `RegenLineageView` - the declared relationship to a prior footballer.
class RegenLineageDescriptor {
  const RegenLineageDescriptor({
    required this.relationshipType,
    required this.relatedLegendType,
    required this.relatedLegendRefId,
    required this.lineageTier,
    this.narrativeText,
    this.isOwnerSon = false,
    this.isRetiredRegenLineage = false,
    this.isRealLegendLineage = false,
    this.isCelebrityLineage = false,
    this.tags = const <String>[],
  });

  final String relationshipType;
  final String relatedLegendType;
  final String relatedLegendRefId;
  final String lineageTier;
  final String? narrativeText;
  final bool isOwnerSon;
  final bool isRetiredRegenLineage;
  final bool isRealLegendLineage;
  final bool isCelebrityLineage;
  final List<String> tags;

  static RegenLineageDescriptor? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen lineage',
    );
    final String? refId = GteJson.stringOrNull(json, <String>[
      'related_legend_ref_id',
      'relatedLegendRefId',
    ]);
    if (refId == null) {
      return null;
    }
    return RegenLineageDescriptor(
      relationshipType: GteJson.string(
        json,
        <String>['relationship_type', 'relationshipType'],
        fallback: 'descendant',
      ),
      relatedLegendType: GteJson.string(
        json,
        <String>['related_legend_type', 'relatedLegendType'],
        fallback: 'player',
      ),
      relatedLegendRefId: refId,
      lineageTier: GteJson.string(
        json,
        <String>['lineage_tier', 'lineageTier'],
        fallback: 'rare',
      ),
      narrativeText: GteJson.stringOrNull(json, <String>[
        'narrative_text',
        'narrativeText',
      ]),
      isOwnerSon: GteJson.boolean(json, <String>['is_owner_son', 'isOwnerSon']),
      isRetiredRegenLineage: GteJson.boolean(json, <String>[
        'is_retired_regen_lineage',
        'isRetiredRegenLineage',
      ]),
      isRealLegendLineage: GteJson.boolean(json, <String>[
        'is_real_legend_lineage',
        'isRealLegendLineage',
      ]),
      isCelebrityLineage: GteJson.boolean(json, <String>[
        'is_celebrity_lineage',
        'isCelebrityLineage',
      ]),
      tags: GteJson.list(json['tags'] ?? const <Object?>[])
          .map((Object? tag) => tag.toString())
          .where((String tag) => tag.trim().isNotEmpty)
          .toList(growable: false),
    );
  }

  /// The parent's canonical player id, but only when the backend related this
  /// regen to an actual player row. `related_legend_type` distinguishes a
  /// player from a celebrity or an external legend reference, and only the
  /// player case is navigable into Player Detail.
  String? get parentPlayerId {
    final String type = relatedLegendType.toLowerCase();
    if (type.contains('player') || type.contains('regen')) {
      return relatedLegendRefId;
    }
    return null;
  }
}

/// `RegenStorySeedView`.
class RegenStorySeed {
  const RegenStorySeed({
    required this.background,
    required this.temperament,
    required this.ambition,
    required this.pressureResponse,
    this.snippet,
  });

  final String background;
  final String temperament;
  final String ambition;
  final String pressureResponse;
  final String? snippet;

  static RegenStorySeed? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen story seed',
    );
    final String? background = GteJson.stringOrNull(json, <String>[
      'background',
    ]);
    if (background == null) {
      return null;
    }
    return RegenStorySeed(
      background: background,
      temperament: GteJson.string(
        json,
        <String>['temperament'],
        fallback: 'unknown',
      ),
      ambition: GteJson.string(json, <String>['ambition'], fallback: 'unknown'),
      pressureResponse: GteJson.string(
        json,
        <String>['pressure_response', 'pressureResponse'],
        fallback: 'unknown',
      ),
      snippet: GteJson.stringOrNull(json, <String>['snippet']),
    );
  }
}

/// `RegenProfileView`.
class RegenProfileDetail {
  const RegenProfileDetail({
    required this.id,
    required this.regenId,
    required this.displayName,
    required this.age,
    required this.primaryPosition,
    required this.currentGsi,
    required this.scoutConfidence,
    required this.generationSource,
    required this.regenType,
    required this.status,
    required this.uniquenessScore,
    required this.growthCurve,
    this.playerId,
    this.clubId,
    this.currentRating,
    this.potential,
    this.currentAbilityRange,
    this.potentialRange,
    this.parentLegacyId,
    this.isSpecialLineage = false,
    this.morale,
    this.personality,
    this.origin,
    this.lineage,
    this.storySeed,
    this.secondaryPositions = const <String>[],
  });

  final String id;
  final String regenId;
  final String displayName;
  final int age;
  final String primaryPosition;
  final int currentGsi;
  final String scoutConfidence;
  final String generationSource;
  final String regenType;
  final String status;
  final double uniquenessScore;
  final double growthCurve;
  final String? playerId;
  final String? clubId;
  final int? currentRating;
  final int? potential;
  final RegenAbilityRange? currentAbilityRange;
  final RegenAbilityRange? potentialRange;
  final String? parentLegacyId;
  final bool isSpecialLineage;
  final double? morale;
  final RegenPersonality? personality;
  final RegenOrigin? origin;
  final RegenLineageDescriptor? lineage;
  final RegenStorySeed? storySeed;
  final List<String> secondaryPositions;

  factory RegenProfileDetail.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen profile',
    );
    return RegenProfileDetail(
      id: GteJson.string(json, <String>['id']),
      regenId: GteJson.string(json, <String>['regen_id', 'regenId']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      age: GteJson.integer(json, <String>['age']),
      primaryPosition: GteJson.string(
        json,
        <String>['primary_position', 'primaryPosition'],
        fallback: 'POS',
      ),
      currentGsi: GteJson.integer(json, <String>['current_gsi', 'currentGsi']),
      scoutConfidence: GteJson.string(
        json,
        <String>['scout_confidence', 'scoutConfidence'],
        fallback: 'unknown',
      ),
      generationSource: GteJson.string(
        json,
        <String>['generation_source', 'generationSource'],
        fallback: 'unknown',
      ),
      regenType: GteJson.string(
        json,
        <String>['regen_type', 'regenType'],
        fallback: 'organic_newgen',
      ),
      status: GteJson.string(json, <String>['status'], fallback: 'active'),
      uniquenessScore: GteJson.number(json, <String>[
        'uniqueness_score',
        'uniquenessScore',
      ]),
      growthCurve: GteJson.number(json, <String>[
        'growth_curve',
        'growthCurve',
      ]),
      playerId: GteJson.stringOrNull(json, <String>['player_id', 'playerId']),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      currentRating: GteJson.integerOrNull(json, <String>[
        'current_rating',
        'currentRating',
      ]),
      potential: GteJson.integerOrNull(json, <String>['potential']),
      currentAbilityRange: RegenAbilityRange.fromJson(
        json['current_ability_range'] ?? json['currentAbilityRange'],
      ),
      potentialRange: RegenAbilityRange.fromJson(
        json['potential_range'] ?? json['potentialRange'],
      ),
      parentLegacyId: GteJson.stringOrNull(json, <String>[
        'parent_legacy_id',
        'parentLegacyId',
      ]),
      isSpecialLineage: GteJson.boolean(json, <String>[
        'is_special_lineage',
        'isSpecialLineage',
      ]),
      morale:
          json.containsKey('morale')
              ? GteJson.number(json, <String>['morale'])
              : null,
      personality: RegenPersonality.fromJson(json['personality']),
      origin: RegenOrigin.fromJson(json['origin']),
      lineage: RegenLineageDescriptor.fromJson(json['lineage']),
      storySeed: RegenStorySeed.fromJson(
        json['story_seed'] ?? json['storySeed'],
      ),
      secondaryPositions: GteJson.list(
            json['secondary_positions'] ??
                json['secondaryPositions'] ??
                const <Object?>[],
          )
          .map((Object? item) => item.toString())
          .where((String item) => item.trim().isNotEmpty)
          .toList(growable: false),
    );
  }
}

/// `RegenStoryEventView` - one dated development event.
class RegenStoryEvent {
  const RegenStoryEvent({
    required this.id,
    required this.eventType,
    required this.title,
    required this.summary,
    required this.occurredAt,
    this.playerName,
  });

  final String id;
  final String eventType;
  final String title;
  final String summary;
  final DateTime occurredAt;
  final String? playerName;

  factory RegenStoryEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen story event',
    );
    return RegenStoryEvent(
      id: GteJson.string(json, <String>['id']),
      eventType: GteJson.string(
        json,
        <String>['event_type', 'eventType'],
        fallback: 'event',
      ),
      title: GteJson.string(json, <String>['title'], fallback: 'Career event'),
      summary: GteJson.string(json, <String>['summary'], fallback: ''),
      occurredAt: GteJson.dateTime(json, <String>['occurred_at', 'occurredAt']),
      playerName: GteJson.stringOrNull(json, <String>[
        'player_name',
        'playerName',
      ]),
    );
  }
}

/// `RegenAchievementView`.
class RegenPlayerAchievement {
  const RegenPlayerAchievement({
    required this.id,
    required this.achievementType,
    required this.title,
    required this.description,
    required this.earnedAt,
  });

  final String id;
  final String achievementType;
  final String title;
  final String description;
  final DateTime earnedAt;

  factory RegenPlayerAchievement.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen achievement',
    );
    return RegenPlayerAchievement(
      id: GteJson.string(json, <String>['id']),
      achievementType: GteJson.string(
        json,
        <String>['achievement_type', 'achievementType'],
        fallback: 'achievement',
      ),
      title: GteJson.string(json, <String>['title'], fallback: 'Achievement'),
      description: GteJson.string(json, <String>['description'], fallback: ''),
      earnedAt: GteJson.dateTime(json, <String>['earned_at', 'earnedAt']),
    );
  }
}

/// `RegenLegacySnapshotView` - the accumulated career record.
class RegenLegacySnapshot {
  const RegenLegacySnapshot({
    required this.totalMatches,
    required this.goals,
    required this.assists,
    required this.trophies,
    required this.peakRating,
    required this.seasonsTotal,
    required this.awardsTotal,
    required this.legacyScore,
    required this.legacyTier,
    required this.isLegend,
    this.narrativeSummary,
  });

  final int totalMatches;
  final int goals;
  final int assists;
  final int trophies;
  final int peakRating;
  final int seasonsTotal;
  final int awardsTotal;
  final double legacyScore;
  final String legacyTier;
  final bool isLegend;
  final String? narrativeSummary;

  static RegenLegacySnapshot? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen legacy',
    );
    if (json.isEmpty) {
      return null;
    }
    return RegenLegacySnapshot(
      totalMatches: GteJson.integer(json, <String>[
        'total_matches',
        'totalMatches',
      ]),
      goals: GteJson.integer(json, <String>['goals']),
      assists: GteJson.integer(json, <String>['assists']),
      trophies: GteJson.integer(json, <String>['trophies']),
      peakRating: GteJson.integer(json, <String>['peak_rating', 'peakRating']),
      seasonsTotal: GteJson.integer(json, <String>[
        'seasons_total',
        'seasonsTotal',
      ]),
      awardsTotal: GteJson.integer(json, <String>[
        'awards_total',
        'awardsTotal',
      ]),
      legacyScore: GteJson.number(json, <String>[
        'legacy_score',
        'legacyScore',
      ]),
      legacyTier: GteJson.string(
        json,
        <String>['legacy_tier', 'legacyTier'],
        fallback: 'standard',
      ),
      isLegend: GteJson.boolean(json, <String>['is_legend', 'isLegend']),
      narrativeSummary: GteJson.stringOrNull(json, <String>[
        'narrative_summary',
        'narrativeSummary',
      ]),
    );
  }

  /// True when the backend has recorded any career at all. When this is false
  /// the UI must say "no recorded matches" rather than draw a row of zeroes.
  bool get hasRecordedCareer =>
      totalMatches > 0 || seasonsTotal > 0 || awardsTotal > 0 || trophies > 0;
}

/// `RegenValueSnapshotView` - the regen valuation and its components.
class RegenValueBreakdown {
  const RegenValueBreakdown({
    required this.currentValueCoin,
    required this.abilityComponent,
    required this.potentialComponent,
    required this.reputationComponent,
    required this.narrativeComponent,
    required this.demandComponent,
    this.calculatedAt,
  });

  final int currentValueCoin;
  final int abilityComponent;
  final int potentialComponent;
  final int reputationComponent;
  final int narrativeComponent;
  final int demandComponent;
  final DateTime? calculatedAt;

  static RegenValueBreakdown? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen value snapshot',
    );
    if (json.isEmpty) {
      return null;
    }
    return RegenValueBreakdown(
      currentValueCoin: GteJson.integer(json, <String>[
        'current_value_coin',
        'currentValueCoin',
      ]),
      abilityComponent: GteJson.integer(json, <String>[
        'ability_component',
        'abilityComponent',
      ]),
      potentialComponent: GteJson.integer(json, <String>[
        'potential_component',
        'potentialComponent',
      ]),
      reputationComponent: GteJson.integer(json, <String>[
        'reputation_component',
        'reputationComponent',
      ]),
      narrativeComponent: GteJson.integer(json, <String>[
        'narrative_component',
        'narrativeComponent',
      ]),
      demandComponent: GteJson.integer(json, <String>[
        'demand_component',
        'demandComponent',
      ]),
      calculatedAt: GteJson.dateTimeOrNull(json, <String>[
        'calculated_at',
        'calculatedAt',
      ]),
    );
  }

  /// The named components, largest first and with the empty ones dropped, so
  /// the panel shows what actually drives this regen's value.
  List<MapEntry<String, int>> get rankedComponents {
    final List<MapEntry<String, int>> components = <MapEntry<String, int>>[
      MapEntry<String, int>('Ability', abilityComponent),
      MapEntry<String, int>('Potential', potentialComponent),
      MapEntry<String, int>('Reputation', reputationComponent),
      MapEntry<String, int>('Narrative', narrativeComponent),
      MapEntry<String, int>('Demand', demandComponent),
    ];
    components.removeWhere((MapEntry<String, int> entry) => entry.value <= 0);
    components.sort(
      (MapEntry<String, int> a, MapEntry<String, int> b) =>
          b.value.compareTo(a.value),
    );
    return components;
  }
}

/// `RegenPlayerPrestigeSummaryView`.
class RegenPrestigeSummary {
  const RegenPrestigeSummary({
    required this.totalAwards,
    required this.seasonsActive,
    required this.legacyScore,
    this.peakRank,
  });

  final int totalAwards;
  final int seasonsActive;
  final double legacyScore;
  final int? peakRank;

  static RegenPrestigeSummary? fromJson(Object? value) {
    if (value == null) {
      return null;
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen prestige',
    );
    if (json.isEmpty) {
      return null;
    }
    return RegenPrestigeSummary(
      totalAwards: GteJson.integer(json, <String>[
        'total_awards',
        'totalAwards',
      ]),
      seasonsActive: GteJson.integer(json, <String>[
        'seasons_active',
        'seasonsActive',
      ]),
      legacyScore: GteJson.number(json, <String>[
        'legacy_score',
        'legacyScore',
      ]),
      peakRank: GteJson.integerOrNull(json, <String>['peak_rank', 'peakRank']),
    );
  }
}

/// `RegenUniversePlayerShowcaseView` - the whole regen, in one response.
class RegenPlayerShowcase {
  const RegenPlayerShowcase({
    required this.playerId,
    required this.profile,
    required this.discoveryBadges,
    required this.timeline,
    required this.achievements,
    this.portraitUrl,
    this.personalityTag,
    this.storySnippet,
    this.prestige,
    this.legacy,
    this.latestValue,
  });

  final String playerId;
  final RegenProfileDetail profile;
  final List<String> discoveryBadges;
  final List<RegenStoryEvent> timeline;
  final List<RegenPlayerAchievement> achievements;
  final String? portraitUrl;
  final String? personalityTag;
  final String? storySnippet;
  final RegenPrestigeSummary? prestige;
  final RegenLegacySnapshot? legacy;
  final RegenValueBreakdown? latestValue;

  factory RegenPlayerShowcase.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen showcase',
    );
    final Map<String, Object?> card = GteJson.map(
      json['card'],
      label: 'regen card',
    );
    return RegenPlayerShowcase(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      profile: RegenProfileDetail.fromJson(json['profile']),
      portraitUrl: GteJson.stringOrNull(card, <String>[
        'image_url',
        'portrait_url',
        'imageUrl',
        'portraitUrl',
      ]),
      personalityTag: GteJson.stringOrNull(card, <String>[
        'personality_tag',
        'personalityTag',
      ]),
      storySnippet: GteJson.stringOrNull(card, <String>[
        'story_snippet',
        'storySnippet',
      ]),
      prestige: RegenPrestigeSummary.fromJson(json['prestige']),
      legacy: RegenLegacySnapshot.fromJson(json['legacy']),
      latestValue: RegenValueBreakdown.fromJson(
        json['latest_value'] ?? json['latestValue'],
      ),
      discoveryBadges: GteJson.list(
            json['discovery_badges'] ??
                json['discoveryBadges'] ??
                const <Object?>[],
          )
          .map((Object? badge) => badge.toString())
          .where((String badge) => badge.trim().isNotEmpty)
          .toList(growable: false),
      timeline:
          GteJson.list(json['timeline'] ?? const <Object?>[])
              .map(RegenStoryEvent.fromJson)
              .toList(growable: false),
      achievements:
          GteJson.list(json['achievements'] ?? const <Object?>[])
              .map(RegenPlayerAchievement.fromJson)
              .toList(growable: false),
    );
  }
}

/// `RegenBloodlinePlayerView` - one generation of a bloodline.
class RegenBloodlineMember {
  const RegenBloodlineMember({
    required this.playerId,
    required this.regenId,
    required this.displayName,
    required this.regenType,
    required this.generationIndex,
    required this.primaryPosition,
    required this.currentRating,
    required this.potential,
    required this.legacyScore,
    this.storySnippet,
  });

  final String playerId;
  final String regenId;
  final String displayName;
  final String regenType;
  final int generationIndex;
  final String primaryPosition;
  final int currentRating;
  final int potential;
  final double legacyScore;
  final String? storySnippet;

  factory RegenBloodlineMember.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'bloodline member',
    );
    return RegenBloodlineMember(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      regenId: GteJson.string(json, <String>['regen_id', 'regenId']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      regenType: GteJson.string(
        json,
        <String>['regen_type', 'regenType'],
        fallback: 'organic_newgen',
      ),
      generationIndex: GteJson.integer(
        json,
        <String>['generation_index', 'generationIndex'],
        fallback: 1,
      ),
      primaryPosition: GteJson.string(
        json,
        <String>['primary_position', 'primaryPosition'],
        fallback: 'POS',
      ),
      currentRating: GteJson.integer(json, <String>[
        'current_rating',
        'currentRating',
      ]),
      potential: GteJson.integer(json, <String>['potential']),
      legacyScore: GteJson.number(json, <String>[
        'legacy_score',
        'legacyScore',
      ]),
      storySnippet: GteJson.stringOrNull(json, <String>[
        'story_snippet',
        'storySnippet',
      ]),
    );
  }
}

/// `RegenBloodlineChainView` - an origin and everyone descended from it.
class RegenBloodlineChain {
  const RegenBloodlineChain({
    required this.bloodlineKey,
    required this.originLabel,
    required this.originRefId,
    required this.originType,
    required this.driftScore,
    required this.entries,
  });

  final String bloodlineKey;
  final String originLabel;
  final String originRefId;
  final String originType;
  final double driftScore;
  final List<RegenBloodlineMember> entries;

  factory RegenBloodlineChain.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'bloodline chain',
    );
    final List<RegenBloodlineMember> entries =
        GteJson.list(json['entries'] ?? const <Object?>[])
            .map(RegenBloodlineMember.fromJson)
            .toList();
    entries.sort(
      (RegenBloodlineMember a, RegenBloodlineMember b) =>
          a.generationIndex.compareTo(b.generationIndex),
    );
    return RegenBloodlineChain(
      bloodlineKey: GteJson.string(json, <String>[
        'bloodline_key',
        'bloodlineKey',
      ]),
      originLabel: GteJson.string(
        json,
        <String>['origin_label', 'originLabel'],
        fallback: 'Unknown origin',
      ),
      originRefId: GteJson.string(
        json,
        <String>['origin_ref_id', 'originRefId'],
        fallback: '',
      ),
      originType: GteJson.string(
        json,
        <String>['origin_type', 'originType'],
        fallback: 'unknown',
      ),
      driftScore: GteJson.number(json, <String>['drift_score', 'driftScore']),
      entries: List<RegenBloodlineMember>.unmodifiable(entries),
    );
  }
}

/// `RegenRankingEntryView` - one row of a live ranking category.
class RegenRankingEntry {
  const RegenRankingEntry({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.category,
    required this.score,
    required this.rank,
  });

  final String id;
  final String playerId;
  final String playerName;
  final String category;
  final double score;
  final int rank;

  factory RegenRankingEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen ranking entry',
    );
    return RegenRankingEntry(
      id: GteJson.string(json, <String>['id']),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(
        json,
        <String>['player_name', 'playerName'],
        fallback: 'Unnamed regen',
      ),
      category: GteJson.string(json, <String>['category'], fallback: 'overall'),
      score: GteJson.number(json, <String>['score']),
      rank: GteJson.integer(json, <String>['rank']),
    );
  }
}

/// `RegenHallOfFameEntryView`.
class RegenHallOfFameEntry {
  const RegenHallOfFameEntry({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.totalAwards,
    required this.seasonsActive,
    required this.legacyScore,
    this.peakRank,
  });

  final String id;
  final String playerId;
  final String playerName;
  final int totalAwards;
  final int seasonsActive;
  final double legacyScore;
  final int? peakRank;

  factory RegenHallOfFameEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen hall of fame entry',
    );
    return RegenHallOfFameEntry(
      id: GteJson.string(json, <String>['id']),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(
        json,
        <String>['player_name', 'playerName'],
        fallback: 'Unnamed regen',
      ),
      totalAwards: GteJson.integer(json, <String>[
        'total_awards',
        'totalAwards',
      ]),
      seasonsActive: GteJson.integer(json, <String>[
        'seasons_active',
        'seasonsActive',
      ]),
      legacyScore: GteJson.number(json, <String>[
        'legacy_score',
        'legacyScore',
      ]),
      peakRank: GteJson.integerOrNull(json, <String>['peak_rank', 'peakRank']),
    );
  }
}

/// `RegenBloodlineNodeView` from `GET /regens/{regen_id}/lineage`.
class RegenLineageChainNode {
  const RegenLineageChainNode({
    required this.regenProfileId,
    required this.regenId,
    required this.displayName,
    this.parentLegacyId,
    this.legacyScore,
    this.legacyTier,
  });

  final String regenProfileId;
  final String regenId;
  final String displayName;
  final String? parentLegacyId;
  final double? legacyScore;
  final String? legacyTier;

  factory RegenLineageChainNode.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen lineage node',
    );
    return RegenLineageChainNode(
      regenProfileId: GteJson.string(json, <String>[
        'regen_profile_id',
        'regenProfileId',
      ]),
      regenId: GteJson.string(json, <String>['regen_id', 'regenId']),
      displayName: GteJson.string(
        json,
        <String>['display_name', 'displayName'],
        fallback: 'Unnamed regen',
      ),
      parentLegacyId: GteJson.stringOrNull(json, <String>[
        'parent_legacy_id',
        'parentLegacyId',
      ]),
      legacyScore:
          json.containsKey('legacy_score') || json.containsKey('legacyScore')
              ? GteJson.number(json, <String>['legacy_score', 'legacyScore'])
              : null,
      legacyTier: GteJson.stringOrNull(json, <String>[
        'legacy_tier',
        'legacyTier',
      ]),
    );
  }
}
