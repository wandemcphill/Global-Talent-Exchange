import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/models/player_avatar.dart';

enum LiveMatchPhase { preMatch, firstHalf, halftime, secondHalf, fullTime }

enum LiveMatchEventType { goal, card, substitution, incident }

enum LiveMatchOverlayMode { shape, pressure, shots, xg, territory, market }

class LiveMatchEvent {
  const LiveMatchEvent({
    required this.minute,
    required this.title,
    required this.detail,
    required this.team,
    required this.type,
    this.isKeyMoment = false,
  });

  final int minute;
  final String title;
  final String detail;
  final String team;
  final LiveMatchEventType type;
  final bool isKeyMoment;
}

class LiveMatchLineupPlayer {
  const LiveMatchLineupPlayer({
    required this.name,
    required this.position,
    required this.rating,
    this.captain = false,
    this.playerId,
    this.nationalityCode,
    this.avatarSeedToken,
    this.avatarDnaSeed,
    this.avatar,
  });

  final String name;
  final String position;
  final double rating;
  final bool captain;
  final String? playerId;
  final String? nationalityCode;
  final String? avatarSeedToken;
  final String? avatarDnaSeed;
  final PlayerAvatar? avatar;

  String stablePlayerReference({
    required String teamName,
    required String matchId,
  }) {
    final String? explicitId = playerId?.trim();
    if (explicitId != null && explicitId.isNotEmpty) {
      return explicitId;
    }
    final String normalizedName = name.trim().toLowerCase().replaceAll(
      RegExp(r'[^a-z0-9]+'),
      '-',
    );
    final String normalizedPosition = position.trim().toLowerCase().replaceAll(
      RegExp(r'[^a-z0-9]+'),
      '-',
    );
    final String normalizedTeam = teamName.trim().toLowerCase().replaceAll(
      RegExp(r'[^a-z0-9]+'),
      '-',
    );
    return '$matchId-$normalizedTeam-$normalizedName-$normalizedPosition';
  }
}

class LiveMatchTacticalSuggestion {
  const LiveMatchTacticalSuggestion({
    required this.title,
    required this.detail,
    required this.impactLabel,
  });

  final String title;
  final String detail;
  final String impactLabel;
}

class LiveMatchStatPair {
  const LiveMatchStatPair({
    required this.home,
    required this.away,
    this.unit = '',
  });

  final double home;
  final double away;
  final String unit;

  double get total => home + away;

  double get homeShare {
    final double denominator = total;
    if (denominator <= 0) {
      return 0.5;
    }
    return (home / denominator).clamp(0, 1).toDouble();
  }

  String homeLabel({int decimals = 0}) => _formatMetric(home, unit, decimals);

  String awayLabel({int decimals = 0}) => _formatMetric(away, unit, decimals);
}

class LiveMatchShotMarker {
  const LiveMatchShotMarker({
    required this.x,
    required this.y,
    required this.xg,
    required this.team,
  });

  final double x;
  final double y;
  final double xg;
  final String team;

  bool get isHome => team.trim().toLowerCase() != 'away';
}

class LiveMatchStatsSnapshot {
  const LiveMatchStatsSnapshot({
    this.possession,
    this.shots,
    this.shotsOnTarget,
    this.expectedGoals,
    this.territory,
    this.pressure,
    this.marketSignal,
    this.marketDetail,
    this.shotMap = const <LiveMatchShotMarker>[],
  });

  final LiveMatchStatPair? possession;
  final LiveMatchStatPair? shots;
  final LiveMatchStatPair? shotsOnTarget;
  final LiveMatchStatPair? expectedGoals;
  final LiveMatchStatPair? territory;
  final LiveMatchStatPair? pressure;
  final String? marketSignal;
  final String? marketDetail;
  final List<LiveMatchShotMarker> shotMap;

  bool get hasAny =>
      possession != null ||
      shots != null ||
      shotsOnTarget != null ||
      expectedGoals != null ||
      territory != null ||
      pressure != null ||
      hasMarketContext ||
      shotMap.isNotEmpty;

  bool get hasMarketContext =>
      marketSignal?.trim().isNotEmpty == true ||
      marketDetail?.trim().isNotEmpty == true;

  bool supportsOverlay(LiveMatchOverlayMode mode) {
    switch (mode) {
      case LiveMatchOverlayMode.shape:
        return true;
      case LiveMatchOverlayMode.pressure:
        return pressure != null;
      case LiveMatchOverlayMode.shots:
        return shotMap.isNotEmpty;
      case LiveMatchOverlayMode.xg:
        return shotMap.any((LiveMatchShotMarker marker) => marker.xg > 0) ||
            expectedGoals != null;
      case LiveMatchOverlayMode.territory:
        return territory != null;
      case LiveMatchOverlayMode.market:
        return hasMarketContext;
    }
  }

  LiveMatchStatsSnapshot mergeWith(LiveMatchStatsSnapshot incoming) {
    return LiveMatchStatsSnapshot(
      possession: incoming.possession ?? possession,
      shots: incoming.shots ?? shots,
      shotsOnTarget: incoming.shotsOnTarget ?? shotsOnTarget,
      expectedGoals: incoming.expectedGoals ?? expectedGoals,
      territory: incoming.territory ?? territory,
      pressure: incoming.pressure ?? pressure,
      marketSignal:
          incoming.marketSignal?.trim().isNotEmpty == true
              ? incoming.marketSignal
              : marketSignal,
      marketDetail:
          incoming.marketDetail?.trim().isNotEmpty == true
              ? incoming.marketDetail
              : marketDetail,
      shotMap: incoming.shotMap.isNotEmpty ? incoming.shotMap : shotMap,
    );
  }

  static LiveMatchStatsSnapshot? fromPayload(Map<String, Object?> payload) {
    final Map<String, Object?> source = _statsSource(payload);
    final Map<String, Object?> marketSource = _optionalMap(
      GteJson.value(source, <String>[
            'market_context',
            'marketContext',
            'market',
          ]) ??
          GteJson.value(payload, <String>[
            'market_context',
            'marketContext',
            'market',
          ]),
    );
    final LiveMatchStatsSnapshot snapshot = LiveMatchStatsSnapshot(
      possession: _metricPair(
        source,
        nestedKeys: const <String>[
          'possession',
          'possession_pct',
          'possessionPct',
        ],
        homeKeys: const <String>[
          'home_possession',
          'homePossession',
          'home_possession_pct',
          'homePossessionPct',
        ],
        awayKeys: const <String>[
          'away_possession',
          'awayPossession',
          'away_possession_pct',
          'awayPossessionPct',
        ],
        unit: '%',
      ),
      shots: _metricPair(
        source,
        nestedKeys: const <String>['shots', 'total_shots', 'totalShots'],
        homeKeys: const <String>['home_shots', 'homeShots'],
        awayKeys: const <String>['away_shots', 'awayShots'],
      ),
      shotsOnTarget: _metricPair(
        source,
        nestedKeys: const <String>['shots_on_target', 'shotsOnTarget', 'sot'],
        homeKeys: const <String>[
          'home_shots_on_target',
          'homeShotsOnTarget',
          'home_sot',
        ],
        awayKeys: const <String>[
          'away_shots_on_target',
          'awayShotsOnTarget',
          'away_sot',
        ],
      ),
      expectedGoals: _metricPair(
        source,
        nestedKeys: const <String>['xg', 'expected_goals', 'expectedGoals'],
        homeKeys: const <String>['home_xg', 'homeXg', 'home_expected_goals'],
        awayKeys: const <String>['away_xg', 'awayXg', 'away_expected_goals'],
      ),
      territory: _metricPair(
        source,
        nestedKeys: const <String>[
          'territory',
          'territory_pct',
          'territoryPct',
        ],
        homeKeys: const <String>[
          'home_territory',
          'homeTerritory',
          'home_territory_pct',
        ],
        awayKeys: const <String>[
          'away_territory',
          'awayTerritory',
          'away_territory_pct',
        ],
        unit: '%',
      ),
      pressure: _metricPair(
        source,
        nestedKeys: const <String>[
          'pressure',
          'pressure_index',
          'pressureIndex',
        ],
        homeKeys: const <String>[
          'home_pressure',
          'homePressure',
          'home_pressure_index',
        ],
        awayKeys: const <String>[
          'away_pressure',
          'awayPressure',
          'away_pressure_index',
        ],
      ),
      marketSignal: GteJson.stringOrNull(marketSource, const <String>[
        'signal',
        'headline',
        'market_signal',
        'marketSignal',
      ]),
      marketDetail: GteJson.stringOrNull(marketSource, const <String>[
        'detail',
        'summary',
        'market_detail',
        'marketDetail',
      ]),
      shotMap: _shotMapFromPayload(
        GteJson.value(source, const <String>[
              'shot_map',
              'shotMap',
              'shots_map',
              'shotsMap',
              'shots',
            ]) ??
            GteJson.value(payload, const <String>[
              'shot_map',
              'shotMap',
              'shots_map',
              'shotsMap',
              'shots',
            ]),
      ),
    );
    return snapshot.hasAny ? snapshot : null;
  }
}

class LiveMatchIntelligenceSignal {
  const LiveMatchIntelligenceSignal({
    required this.title,
    required this.detail,
    this.severity,
    this.source,
  });

  final String title;
  final String detail;
  final String? severity;
  final String? source;
}

class LiveMatchLiveIntelligence {
  const LiveMatchLiveIntelligence({
    required this.status,
    this.summary,
    this.updatedAt,
    this.signals = const <LiveMatchIntelligenceSignal>[],
  });

  final String status;
  final String? summary;
  final DateTime? updatedAt;
  final List<LiveMatchIntelligenceSignal> signals;

  bool get hasSignals => signals.isNotEmpty || summary?.isNotEmpty == true;

  LiveMatchLiveIntelligence mergeWith(LiveMatchLiveIntelligence incoming) {
    return LiveMatchLiveIntelligence(
      status: incoming.status.trim().isNotEmpty ? incoming.status : status,
      summary:
          incoming.summary?.trim().isNotEmpty == true
              ? incoming.summary
              : summary,
      updatedAt: incoming.updatedAt ?? updatedAt,
      signals: incoming.signals.isNotEmpty ? incoming.signals : signals,
    );
  }

  static LiveMatchLiveIntelligence? fromPayload(Map<String, Object?> payload) {
    final Map<String, Object?> source = _optionalMap(
      GteJson.value(payload, const <String>[
        'live_intelligence',
        'liveIntelligence',
        'inspector',
        'inspector_payload',
        'inspectorPayload',
        'intelligence',
        'ai_insights',
        'aiInsights',
      ]),
    );
    if (source.isEmpty) {
      return null;
    }
    final String status =
        GteJson.stringOrNull(source, const <String>['status', 'state']) ??
        'provided';
    final List<LiveMatchIntelligenceSignal> signals =
        _intelligenceSignalsFromPayload(
          GteJson.value(source, const <String>['signals', 'items', 'insights']),
        );
    final LiveMatchLiveIntelligence intelligence = LiveMatchLiveIntelligence(
      status: status,
      summary: GteJson.stringOrNull(source, const <String>[
        'summary',
        'headline',
        'detail',
      ]),
      updatedAt: GteJson.dateTimeOrNull(source, const <String>[
        'updated_at',
        'updatedAt',
        'generated_at',
        'generatedAt',
      ]),
      signals: signals,
    );
    return intelligence.hasSignals || status.trim().isNotEmpty
        ? intelligence
        : null;
  }
}

class LiveMatchHighlightClip {
  const LiveMatchHighlightClip({
    required this.id,
    required this.title,
    required this.minute,
    required this.durationLabel,
    required this.isPremium,
    required this.isArchived,
    required this.expiresAt,
    required this.downloadEligible,
    this.streamUrl,
    this.subtitle,
    this.cameraSequence = const <String>[],
  });

  final String id;
  final String title;
  final int minute;
  final String durationLabel;
  final bool isPremium;
  final bool isArchived;
  final DateTime expiresAt;
  final bool downloadEligible;
  final String? streamUrl;
  final String? subtitle;
  final List<String> cameraSequence;

  bool get hasPlayableStream => streamUrl?.trim().isNotEmpty == true;
}

class LiveMatchSnapshot {
  const LiveMatchSnapshot({
    this.matchId,
    this.halftimeAnalyticsAvailable = false,
    this.highlightsAvailable = false,
    this.keyMomentsAvailable = false,
    required this.homeTeam,
    required this.awayTeam,
    required this.homeScore,
    required this.awayScore,
    required this.minute,
    required this.phase,
    required this.momentum,
    required this.commentary,
    required this.homeLineup,
    required this.awayLineup,
    required this.substitutions,
    required this.cards,
    required this.tacticalSuggestions,
    required this.keyMoments,
    required this.highlights,
    required this.standardHighlightExpiresAt,
    required this.premiumHighlightExpiresAt,
    this.stats,
    this.liveIntelligence,
  });

  final String? matchId;
  final bool halftimeAnalyticsAvailable;
  final bool highlightsAvailable;
  final bool keyMomentsAvailable;
  final String homeTeam;
  final String awayTeam;
  final int homeScore;
  final int awayScore;
  final int minute;
  final LiveMatchPhase phase;
  final List<int> momentum;
  final List<LiveMatchEvent> commentary;
  final List<LiveMatchLineupPlayer> homeLineup;
  final List<LiveMatchLineupPlayer> awayLineup;
  final List<LiveMatchEvent> substitutions;
  final List<LiveMatchEvent> cards;
  final List<LiveMatchTacticalSuggestion> tacticalSuggestions;
  final List<LiveMatchHighlightClip> keyMoments;
  final List<LiveMatchHighlightClip> highlights;
  final DateTime standardHighlightExpiresAt;
  final DateTime premiumHighlightExpiresAt;
  final LiveMatchStatsSnapshot? stats;
  final LiveMatchLiveIntelligence? liveIntelligence;

  bool get isLive =>
      phase == LiveMatchPhase.firstHalf || phase == LiveMatchPhase.secondHalf;

  bool get isHalftime => phase == LiveMatchPhase.halftime;

  bool get isFinal => phase == LiveMatchPhase.fullTime;

  LiveMatchSnapshot copyWith({
    String? matchId,
    bool? halftimeAnalyticsAvailable,
    bool? highlightsAvailable,
    bool? keyMomentsAvailable,
    String? homeTeam,
    String? awayTeam,
    int? homeScore,
    int? awayScore,
    int? minute,
    LiveMatchPhase? phase,
    List<int>? momentum,
    List<LiveMatchEvent>? commentary,
    List<LiveMatchLineupPlayer>? homeLineup,
    List<LiveMatchLineupPlayer>? awayLineup,
    List<LiveMatchEvent>? substitutions,
    List<LiveMatchEvent>? cards,
    List<LiveMatchTacticalSuggestion>? tacticalSuggestions,
    List<LiveMatchHighlightClip>? keyMoments,
    List<LiveMatchHighlightClip>? highlights,
    DateTime? standardHighlightExpiresAt,
    DateTime? premiumHighlightExpiresAt,
    LiveMatchStatsSnapshot? stats,
    LiveMatchLiveIntelligence? liveIntelligence,
  }) {
    return LiveMatchSnapshot(
      matchId: matchId ?? this.matchId,
      halftimeAnalyticsAvailable:
          halftimeAnalyticsAvailable ?? this.halftimeAnalyticsAvailable,
      highlightsAvailable: highlightsAvailable ?? this.highlightsAvailable,
      keyMomentsAvailable: keyMomentsAvailable ?? this.keyMomentsAvailable,
      homeTeam: homeTeam ?? this.homeTeam,
      awayTeam: awayTeam ?? this.awayTeam,
      homeScore: homeScore ?? this.homeScore,
      awayScore: awayScore ?? this.awayScore,
      minute: minute ?? this.minute,
      phase: phase ?? this.phase,
      momentum: momentum ?? this.momentum,
      commentary: commentary ?? this.commentary,
      homeLineup: homeLineup ?? this.homeLineup,
      awayLineup: awayLineup ?? this.awayLineup,
      substitutions: substitutions ?? this.substitutions,
      cards: cards ?? this.cards,
      tacticalSuggestions: tacticalSuggestions ?? this.tacticalSuggestions,
      keyMoments: keyMoments ?? this.keyMoments,
      highlights: highlights ?? this.highlights,
      standardHighlightExpiresAt:
          standardHighlightExpiresAt ?? this.standardHighlightExpiresAt,
      premiumHighlightExpiresAt:
          premiumHighlightExpiresAt ?? this.premiumHighlightExpiresAt,
      stats: stats ?? this.stats,
      liveIntelligence: liveIntelligence ?? this.liveIntelligence,
    );
  }
}

Future<LiveMatchSnapshot> loadLiveMatchSnapshot(
  CompetitionSummary competition, {
  String? matchId,
  GteAppConfig? config,
  GteExchangeApiClient? api,
}) async {
  final GteAppConfig resolvedConfig = config ?? _matchApiConfig;
  if (resolvedConfig.activeShellBackendMode == GteBackendMode.fixture) {
    throw const GteApiException(
      type: GteApiErrorType.unavailable,
      message:
          'Canonical match center requires a backend-authored websocket or live snapshot.',
    );
  }

  final GteExchangeApiClient client =
      api ?? _resolveMatchApiClient(resolvedConfig);
  final String resolvedMatchId =
      matchId?.trim().isNotEmpty == true ? matchId!.trim() : competition.id;

  final Map<String, Object?> livePayload = await client.fetchMatchLiveFeed(
    resolvedMatchId,
  );
  LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
    livePayload,
    competition: competition,
  );
  try {
    final Map<String, Object?> highlightPayload = await client
        .fetchMatchHighlights(resolvedMatchId);
    snapshot = _mergeHighlightsSnapshot(snapshot, highlightPayload);
  } catch (_) {
    return snapshot;
  }
  return snapshot;
}

final GteAppConfig _matchApiConfig = GteAppConfig.fromRuntimeEnvironment();
final GteExchangeApiClient _matchApiClient = GteExchangeApiClient.standard(
  baseUrl: _matchApiConfig.apiBaseUrl,
  mode: _matchApiConfig.activeShellBackendMode,
);

GteExchangeApiClient _resolveMatchApiClient(GteAppConfig config) {
  if (identical(config, _matchApiConfig)) {
    return _matchApiClient;
  }
  return GteExchangeApiClient.standard(
    baseUrl: config.apiBaseUrl,
    mode: config.activeShellBackendMode,
  );
}

LiveMatchSnapshot liveMatchSnapshotFromPayload(
  Map<String, Object?> payload, {
  required CompetitionSummary competition,
}) {
  final Map<String, Object?> scoreboard = _scoreboardSource(payload);
  final Map<String, Object?> clock = _clockSource(payload);
  final String matchId =
      _stringFromSources(
        <Map<String, Object?>>[payload, scoreboard],
        const <String>['match_id', 'matchId', 'id'],
      ) ??
      competition.id;
  final String homeTeam = _requiredStringFromSources(
    <Map<String, Object?>>[
      payload,
      scoreboard,
      _optionalMap(GteJson.value(scoreboard, const <String>['home'])),
      _optionalMap(GteJson.value(payload, const <String>['home', 'home_team'])),
    ],
    const <String>[
      'home_team_name',
      'homeTeamName',
      'home_team',
      'homeTeam',
      'home_name',
      'homeName',
      'home',
      'team_name',
      'teamName',
      'name',
    ],
    'home team name',
  );
  final String awayTeam = _requiredStringFromSources(
    <Map<String, Object?>>[
      payload,
      scoreboard,
      _optionalMap(GteJson.value(scoreboard, const <String>['away'])),
      _optionalMap(GteJson.value(payload, const <String>['away', 'away_team'])),
    ],
    const <String>[
      'away_team_name',
      'awayTeamName',
      'away_team',
      'awayTeam',
      'away_name',
      'awayName',
      'away',
      'team_name',
      'teamName',
      'name',
    ],
    'away team name',
  );
  final int homeScore = _requiredIntFromSources(
    <Map<String, Object?>>[
      payload,
      scoreboard,
      _optionalMap(GteJson.value(scoreboard, const <String>['home'])),
      _optionalMap(GteJson.value(payload, const <String>['home', 'home_team'])),
    ],
    const <String>['home_score', 'homeScore', 'home_goals', 'score', 'goals'],
    'home score',
  );
  final int awayScore = _requiredIntFromSources(
    <Map<String, Object?>>[
      payload,
      scoreboard,
      _optionalMap(GteJson.value(scoreboard, const <String>['away'])),
      _optionalMap(GteJson.value(payload, const <String>['away', 'away_team'])),
    ],
    const <String>['away_score', 'awayScore', 'away_goals', 'score', 'goals'],
    'away score',
  );
  final String status = _requiredStringFromSources(
    <Map<String, Object?>>[payload, clock],
    const <String>['status', 'match_status', 'matchStatus', 'state'],
    'match status',
  );
  final String phaseLabel =
      _stringFromSources(
        <Map<String, Object?>>[payload, clock],
        const <String>['phase', 'period', 'match_phase', 'matchPhase'],
      ) ??
      '';
  final int minute = _requiredIntFromSources(
    <Map<String, Object?>>[payload, clock],
    const <String>[
      'minute',
      'current_minute',
      'currentMinute',
      'clock_minute',
      'clockMinute',
      'elapsed_minute',
      'elapsedMinute',
    ],
    'match clock minute',
  );
  final List<LiveMatchEvent> commentary = _mapLiveFeedEvents(
    payload,
    fallback: const <LiveMatchEvent>[],
  );
  final List<LiveMatchEvent> substitutions = commentary
      .where(
        (LiveMatchEvent event) => event.type == LiveMatchEventType.substitution,
      )
      .toList(growable: false);
  final List<LiveMatchEvent> cards = commentary
      .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
      .toList(growable: false);

  final Map<String, Object?> availability = GteJson.map(
    GteJson.value(payload, <String>['availability']) ??
        const <String, Object?>{},
    label: 'match availability',
  );
  final bool halftimeAvailable = GteJson.boolean(availability, <String>[
    'halftime_analytics_available',
    'halftimeAnalyticsAvailable',
  ], fallback: false);
  final bool highlightsAvailable = GteJson.boolean(availability, <String>[
    'highlights_available',
    'highlightsAvailable',
  ], fallback: false);
  final bool keyMomentsAvailable = GteJson.boolean(availability, <String>[
    'key_moments_available',
    'keyMomentsAvailable',
  ], fallback: false);

  final List<LiveMatchLineupPlayer>? homeLineup = _lineupFromPayload(
    GteJson.value(payload, <String>['home_lineup', 'homeLineup']),
  );
  final List<LiveMatchLineupPlayer>? awayLineup = _lineupFromPayload(
    GteJson.value(payload, <String>['away_lineup', 'awayLineup']),
  );
  final LiveMatchStatsSnapshot? stats = LiveMatchStatsSnapshot.fromPayload(
    payload,
  );
  final List<int> momentum = _momentumFromPayload(payload);
  final List<LiveMatchTacticalSuggestion> tacticalSuggestions =
      _tacticalSuggestionsFromPayload(payload);
  final List<LiveMatchHighlightClip> keyMoments = _highlightClipsFromPayload(
    GteJson.value(payload, const <String>['key_moments', 'keyMoments']),
    defaultPremium: true,
    fallbackMatchId: matchId,
  );
  final List<LiveMatchHighlightClip> highlights = _highlightClipsFromPayload(
    GteJson.value(payload, const <String>['highlights', 'highlight_clips']),
    fallbackMatchId: matchId,
  );
  final DateTime standardExpiry =
      _expiryFromPayload(payload, isPremium: false) ??
      _unknownHighlightExpiry();
  final DateTime premiumExpiry =
      _expiryFromPayload(payload, isPremium: true) ?? _unknownHighlightExpiry();

  return LiveMatchSnapshot(
    matchId: matchId,
    halftimeAnalyticsAvailable: halftimeAvailable,
    highlightsAvailable: highlightsAvailable || highlights.isNotEmpty,
    keyMomentsAvailable: keyMomentsAvailable || keyMoments.isNotEmpty,
    homeTeam: homeTeam,
    awayTeam: awayTeam,
    homeScore: homeScore,
    awayScore: awayScore,
    minute: minute,
    phase: _phaseFromLiveFeed(phaseLabel, status, minute),
    momentum: momentum,
    commentary: commentary,
    homeLineup: homeLineup ?? const <LiveMatchLineupPlayer>[],
    awayLineup: awayLineup ?? const <LiveMatchLineupPlayer>[],
    substitutions: substitutions,
    cards: cards,
    tacticalSuggestions: tacticalSuggestions,
    keyMoments: keyMoments,
    highlights: highlights,
    standardHighlightExpiresAt: standardExpiry,
    premiumHighlightExpiresAt: premiumExpiry,
    stats: stats,
    liveIntelligence: LiveMatchLiveIntelligence.fromPayload(payload),
  );
}

LiveMatchSnapshot mergeLiveMatchSnapshotPayload(
  LiveMatchSnapshot current,
  Map<String, Object?> payload, {
  CompetitionSummary? competition,
}) {
  final Map<String, Object?> scoreboard = _scoreboardSource(payload);
  final Map<String, Object?> clock = _clockSource(payload);
  final List<LiveMatchEvent> commentary = _mergeLiveEvents(
    current.commentary,
    _mapLiveFeedEvents(payload, fallback: current.commentary),
  );
  final List<LiveMatchEvent> substitutions = commentary
      .where(
        (LiveMatchEvent event) => event.type == LiveMatchEventType.substitution,
      )
      .toList(growable: false);
  final List<LiveMatchEvent> cards = commentary
      .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
      .toList(growable: false);
  final int minute =
      _intFromSources(
        <Map<String, Object?>>[payload, clock],
        const <String>[
          'minute',
          'current_minute',
          'currentMinute',
          'clock_minute',
          'clockMinute',
          'elapsed_minute',
          'elapsedMinute',
        ],
      ) ??
      current.minute;
  final String status =
      _stringFromSources(
        <Map<String, Object?>>[payload, clock],
        const <String>['status', 'match_status', 'matchStatus', 'state'],
      ) ??
      '';
  final String phaseLabel =
      _stringFromSources(
        <Map<String, Object?>>[payload, clock],
        const <String>['phase', 'period', 'match_phase', 'matchPhase'],
      ) ??
      '';
  final LiveMatchStatsSnapshot? stats = LiveMatchStatsSnapshot.fromPayload(
    payload,
  );
  final List<LiveMatchHighlightClip> keyMoments = _mergeHighlightClips(
    current.keyMoments,
    _highlightClipsFromPayload(
      GteJson.value(payload, const <String>['key_moments', 'keyMoments']),
      defaultPremium: true,
      fallbackMatchId: current.matchId ?? competition?.id,
    ),
  );
  final List<LiveMatchHighlightClip> highlights = _mergeHighlightClips(
    current.highlights,
    _highlightClipsFromPayload(
      GteJson.value(payload, const <String>['highlights', 'highlight_clips']),
      fallbackMatchId: current.matchId ?? competition?.id,
    ),
  );

  return current.copyWith(
    matchId:
        _stringFromSources(
          <Map<String, Object?>>[payload, scoreboard],
          const <String>['match_id', 'matchId', 'id'],
        ) ??
        current.matchId ??
        competition?.id,
    homeTeam:
        _stringFromSources(
          <Map<String, Object?>>[
            payload,
            scoreboard,
            _optionalMap(GteJson.value(scoreboard, const <String>['home'])),
            _optionalMap(
              GteJson.value(payload, const <String>['home', 'home_team']),
            ),
          ],
          const <String>[
            'home_team_name',
            'homeTeamName',
            'home_team',
            'homeTeam',
            'home_name',
            'homeName',
            'home',
            'team_name',
            'teamName',
            'name',
          ],
        ) ??
        current.homeTeam,
    awayTeam:
        _stringFromSources(
          <Map<String, Object?>>[
            payload,
            scoreboard,
            _optionalMap(GteJson.value(scoreboard, const <String>['away'])),
            _optionalMap(
              GteJson.value(payload, const <String>['away', 'away_team']),
            ),
          ],
          const <String>[
            'away_team_name',
            'awayTeamName',
            'away_team',
            'awayTeam',
            'away_name',
            'awayName',
            'away',
            'team_name',
            'teamName',
            'name',
          ],
        ) ??
        current.awayTeam,
    homeScore:
        _intFromSources(
          <Map<String, Object?>>[
            payload,
            scoreboard,
            _optionalMap(GteJson.value(scoreboard, const <String>['home'])),
            _optionalMap(
              GteJson.value(payload, const <String>['home', 'home_team']),
            ),
          ],
          const <String>[
            'home_score',
            'homeScore',
            'home_goals',
            'score',
            'goals',
          ],
        ) ??
        current.homeScore,
    awayScore:
        _intFromSources(
          <Map<String, Object?>>[
            payload,
            scoreboard,
            _optionalMap(GteJson.value(scoreboard, const <String>['away'])),
            _optionalMap(
              GteJson.value(payload, const <String>['away', 'away_team']),
            ),
          ],
          const <String>[
            'away_score',
            'awayScore',
            'away_goals',
            'score',
            'goals',
          ],
        ) ??
        current.awayScore,
    minute: minute,
    phase:
        status.isEmpty && phaseLabel.isEmpty
            ? current.phase
            : _phaseFromLiveFeed(phaseLabel, status, minute),
    momentum:
        _momentumFromPayload(payload).isEmpty
            ? current.momentum
            : _momentumFromPayload(payload),
    commentary: commentary,
    homeLineup:
        _lineupFromPayload(
          GteJson.value(payload, <String>['home_lineup', 'homeLineup']),
        ) ??
        current.homeLineup,
    awayLineup:
        _lineupFromPayload(
          GteJson.value(payload, <String>['away_lineup', 'awayLineup']),
        ) ??
        current.awayLineup,
    substitutions: substitutions,
    cards: cards,
    tacticalSuggestions:
        _tacticalSuggestionsFromPayload(payload).isEmpty
            ? current.tacticalSuggestions
            : _tacticalSuggestionsFromPayload(payload),
    keyMoments: keyMoments,
    highlights: highlights,
    highlightsAvailable: current.highlightsAvailable || highlights.isNotEmpty,
    keyMomentsAvailable: current.keyMomentsAvailable || keyMoments.isNotEmpty,
    stats:
        stats == null
            ? current.stats
            : current.stats?.mergeWith(stats) ?? stats,
    liveIntelligence: _mergeLiveIntelligence(
      current.liveIntelligence,
      LiveMatchLiveIntelligence.fromPayload(payload),
    ),
  );
}

LiveMatchLiveIntelligence? _mergeLiveIntelligence(
  LiveMatchLiveIntelligence? current,
  LiveMatchLiveIntelligence? incoming,
) {
  if (incoming == null) {
    return current;
  }
  return current?.mergeWith(incoming) ?? incoming;
}

LiveMatchSnapshot _mergeHighlightsSnapshot(
  LiveMatchSnapshot base,
  Map<String, Object?> payload,
) {
  final List<LiveMatchHighlightClip> highlights = <LiveMatchHighlightClip>[];
  final List<LiveMatchHighlightClip> keyMoments = <LiveMatchHighlightClip>[];

  final List<Object?> rawHighlights = _optionalList(
    GteJson.value(payload, const <String>['highlights', 'clips']),
  );
  for (int index = 0; index < rawHighlights.length; index += 1) {
    final Map<String, Object?> item = _optionalMap(rawHighlights[index]);
    final LiveMatchHighlightClip? clip = _highlightClipFromPayload(
      item,
      fallbackId: '${base.matchId ?? 'live-match'}-clip-$index',
    );
    if (clip == null) {
      continue;
    }
    if (_isKeyMoment(
      GteJson.stringOrNull(item, const <String>['event_type', 'eventType']) ??
          '',
    )) {
      keyMoments.add(clip);
    } else {
      highlights.add(clip);
    }
  }

  keyMoments.addAll(
    _highlightClipsFromPayload(
      GteJson.value(payload, const <String>['key_moments', 'keyMoments']),
      defaultPremium: true,
      fallbackMatchId: base.matchId,
    ),
  );

  final DateTime standardExpiry =
      _expiryFromPayload(payload, isPremium: false) ??
      base.standardHighlightExpiresAt;
  final DateTime premiumExpiry =
      _expiryFromPayload(payload, isPremium: true) ??
      base.premiumHighlightExpiresAt;

  return base.copyWith(
    highlightsAvailable: base.highlightsAvailable || highlights.isNotEmpty,
    keyMomentsAvailable: base.keyMomentsAvailable || keyMoments.isNotEmpty,
    keyMoments: _mergeHighlightClips(base.keyMoments, keyMoments),
    highlights: _mergeHighlightClips(base.highlights, highlights),
    standardHighlightExpiresAt: standardExpiry,
    premiumHighlightExpiresAt: premiumExpiry,
  );
}

Map<String, Object?> _scoreboardSource(Map<String, Object?> payload) {
  final Map<String, Object?> scoreboard = _optionalMap(
    GteJson.value(payload, const <String>[
      'scoreboard',
      'score_board',
      'scoreBoard',
      'score',
    ]),
  );
  return scoreboard.isEmpty
      ? payload
      : <String, Object?>{...payload, ...scoreboard};
}

Map<String, Object?> _clockSource(Map<String, Object?> payload) {
  final Map<String, Object?> clock = _optionalMap(
    GteJson.value(payload, const <String>[
      'clock',
      'match_clock',
      'matchClock',
      'time',
    ]),
  );
  return clock.isEmpty ? payload : <String, Object?>{...payload, ...clock};
}

String _requiredStringFromSources(
  List<Map<String, Object?>> sources,
  List<String> keys,
  String label,
) {
  final String? value = _stringFromSources(sources, keys);
  if (value == null) {
    throw GteParsingException('Missing required live match $label.', sources);
  }
  return value;
}

String? _stringFromSources(
  List<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final Map<String, Object?> source in sources) {
    final Object? raw = GteJson.value(source, keys);
    if (raw == null || raw is Map || raw is List) {
      continue;
    }
    final String value = raw.toString().trim();
    if (value.isNotEmpty) {
      return value;
    }
  }
  return null;
}

int _requiredIntFromSources(
  List<Map<String, Object?>> sources,
  List<String> keys,
  String label,
) {
  final int? value = _intFromSources(sources, keys);
  if (value == null) {
    throw GteParsingException('Missing required live match $label.', sources);
  }
  return value;
}

int? _intFromSources(List<Map<String, Object?>> sources, List<String> keys) {
  for (final Map<String, Object?> source in sources) {
    final Object? raw = GteJson.value(source, keys);
    final int? value = _intOrNull(raw);
    if (value != null) {
      return value;
    }
  }
  return null;
}

int? _intOrNull(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  final String text = value?.toString().trim() ?? '';
  return text.isEmpty ? null : int.tryParse(text);
}

List<Object?> _optionalList(Object? value) {
  if (value == null) {
    return const <Object?>[];
  }
  try {
    return GteJson.list(value);
  } catch (_) {
    return const <Object?>[];
  }
}

List<LiveMatchHighlightClip> _highlightClipsFromPayload(
  Object? value, {
  bool defaultPremium = false,
  String? fallbackMatchId,
}) {
  final List<Object?> rawClips = _optionalList(value);
  return rawClips
      .asMap()
      .entries
      .map((MapEntry<int, Object?> entry) {
        return _highlightClipFromPayload(
          _optionalMap(entry.value),
          fallbackId:
              '${fallbackMatchId ?? 'live-match'}-highlight-${entry.key}',
          defaultPremium: defaultPremium,
        );
      })
      .whereType<LiveMatchHighlightClip>()
      .toList(growable: false);
}

LiveMatchHighlightClip? _highlightClipFromPayload(
  Map<String, Object?> item, {
  required String fallbackId,
  bool defaultPremium = false,
}) {
  if (item.isEmpty) {
    return null;
  }
  final String? title = GteJson.stringOrNull(item, const <String>[
    'title',
    'headline',
    'label',
  ]);
  if (title == null) {
    return null;
  }
  final String eventType =
      GteJson.stringOrNull(item, const <String>['event_type', 'eventType']) ??
      '';
  final String accessState =
      GteJson.stringOrNull(item, const <String>[
        'access_state',
        'accessState',
      ]) ??
      'available';
  final bool isPremium =
      GteJson.boolean(item, const <String>[
        'is_premium',
        'isPremium',
      ], fallback: defaultPremium || _isKeyMoment(eventType)) ||
      accessState != 'available';
  return LiveMatchHighlightClip(
    id:
        GteJson.stringOrNull(item, const <String>[
          'highlight_id',
          'highlightId',
          'id',
        ]) ??
        fallbackId,
    title: title,
    minute:
        _intFromSources(
          <Map<String, Object?>>[item],
          const <String>['minute', 'clock_minute', 'clockMinute'],
        ) ??
        0,
    durationLabel: _highlightDurationLabel(item),
    isPremium: isPremium,
    isArchived: GteJson.boolean(item, const <String>[
      'archive_available',
      'archiveAvailable',
      'is_archived',
      'isArchived',
    ]),
    expiresAt:
        _expiryFromPayload(item, isPremium: isPremium) ??
        _unknownHighlightExpiry(),
    downloadEligible: GteJson.boolean(item, const <String>[
      'download_available',
      'downloadAvailable',
      'download_eligible',
      'downloadEligible',
    ]),
    streamUrl: GteJson.stringOrNull(item, const <String>[
      'stream_url',
      'streamUrl',
      'video_url',
      'videoUrl',
      'url',
    ]),
    subtitle: GteJson.stringOrNull(item, const <String>[
      'subtitle',
      'description',
      'detail',
    ]),
    cameraSequence: _optionalList(
      GteJson.value(item, const <String>['camera_sequence', 'cameraSequence']),
    ).map((Object? value) => value.toString()).toList(growable: false),
  );
}

String _highlightDurationLabel(Map<String, Object?> item) {
  final String? label = GteJson.stringOrNull(item, const <String>[
    'duration_label',
    'durationLabel',
  ]);
  if (label != null) {
    return label;
  }
  final int? seconds = _intFromSources(
    <Map<String, Object?>>[item],
    const <String>['duration_seconds', 'durationSeconds', 'seconds'],
  );
  if (seconds == null) {
    return 'Duration unavailable';
  }
  return '$seconds sec';
}

DateTime? _expiryFromPayload(
  Map<String, Object?> payload, {
  required bool isPremium,
}) {
  final DateTime? explicit = GteJson.dateTimeOrNull(payload, const <String>[
    'expires_at',
    'expiresAt',
  ]);
  if (explicit != null) {
    return explicit;
  }
  return GteJson.dateTimeOrNull(
    payload,
    isPremium
        ? const <String>[
          'premium_highlight_expires_at',
          'premiumHighlightExpiresAt',
        ]
        : const <String>[
          'standard_highlight_expires_at',
          'standardHighlightExpiresAt',
        ],
  );
}

DateTime _unknownHighlightExpiry() {
  return DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
}

List<LiveMatchHighlightClip> _mergeHighlightClips(
  List<LiveMatchHighlightClip> current,
  List<LiveMatchHighlightClip> incoming,
) {
  if (incoming.isEmpty) {
    return current;
  }
  final Map<String, LiveMatchHighlightClip> merged =
      <String, LiveMatchHighlightClip>{
        for (final LiveMatchHighlightClip clip in current) clip.id: clip,
      };
  for (final LiveMatchHighlightClip clip in incoming) {
    merged[clip.id] = clip;
  }
  return merged.values.toList(growable: false);
}

List<LiveMatchEvent> _mergeLiveEvents(
  List<LiveMatchEvent> current,
  List<LiveMatchEvent> incoming,
) {
  if (incoming.isEmpty) {
    return current;
  }
  final Map<String, LiveMatchEvent> merged = <String, LiveMatchEvent>{
    for (final LiveMatchEvent event in current) _eventKey(event): event,
  };
  for (final LiveMatchEvent event in incoming) {
    merged[_eventKey(event)] = event;
  }
  final List<LiveMatchEvent> events = merged.values.toList(growable: false);
  events.sort((LiveMatchEvent a, LiveMatchEvent b) {
    final int minuteCompare = a.minute.compareTo(b.minute);
    if (minuteCompare != 0) {
      return minuteCompare;
    }
    return a.title.compareTo(b.title);
  });
  return events;
}

String _eventKey(LiveMatchEvent event) {
  return '${event.minute}|${event.type.name}|${event.team}|${event.title}|${event.detail}';
}

Map<String, Object?> _statsSource(Map<String, Object?> payload) {
  final Object? nested = GteJson.value(payload, const <String>[
    'stats',
    'match_stats',
    'matchStats',
    'analytics',
    'overlays',
    'overlay_payload',
    'overlayPayload',
    'overlay_payloads',
    'overlayPayloads',
  ]);
  final Map<String, Object?> nestedMap = _optionalMap(nested);
  final Map<String, Object?> overlays = _optionalMap(
    GteJson.value(payload, const <String>[
      'overlays',
      'overlay_payload',
      'overlayPayload',
      'overlay_payloads',
      'overlayPayloads',
    ]),
  );
  if (nestedMap.isNotEmpty || overlays.isNotEmpty) {
    return <String, Object?>{...payload, ...nestedMap, ...overlays};
  }
  return payload;
}

Map<String, Object?> _optionalMap(Object? value) {
  if (value == null) {
    return const <String, Object?>{};
  }
  try {
    return GteJson.map(value, fallback: const <String, Object?>{});
  } catch (_) {
    return const <String, Object?>{};
  }
}

LiveMatchStatPair? _metricPair(
  Map<String, Object?> source, {
  required List<String> nestedKeys,
  required List<String> homeKeys,
  required List<String> awayKeys,
  String unit = '',
}) {
  final Map<String, Object?> nested = _optionalMap(
    GteJson.value(source, nestedKeys),
  );
  final double? nestedHome = _numberOrNull(
    GteJson.value(nested, const <String>[
      'home',
      'home_value',
      'homeValue',
      'home_pct',
      'homePct',
    ]),
  );
  final double? nestedAway = _numberOrNull(
    GteJson.value(nested, const <String>[
      'away',
      'away_value',
      'awayValue',
      'away_pct',
      'awayPct',
    ]),
  );
  final double? home =
      nestedHome ?? _numberOrNull(GteJson.value(source, homeKeys));
  final double? away =
      nestedAway ?? _numberOrNull(GteJson.value(source, awayKeys));
  if (home == null || away == null) {
    return null;
  }
  return LiveMatchStatPair(home: home, away: away, unit: unit);
}

double? _numberOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  final String normalized = value.toString().trim().replaceAll('%', '');
  if (normalized.isEmpty) {
    return null;
  }
  return double.tryParse(normalized);
}

List<LiveMatchShotMarker> _shotMapFromPayload(Object? value) {
  if (value == null) {
    return const <LiveMatchShotMarker>[];
  }
  final Object? resolvedValue =
      value is Map
          ? GteJson.value(_optionalMap(value), const <String>[
            'shots',
            'markers',
            'shot_map',
            'shotMap',
          ])
          : value;
  final List<Object?> rawShots;
  try {
    rawShots = GteJson.list(resolvedValue, label: 'shot map');
  } catch (_) {
    return const <LiveMatchShotMarker>[];
  }
  return rawShots
      .map((Object? item) {
        final Map<String, Object?> json = _optionalMap(item);
        final double? rawX = _numberOrNull(
          GteJson.value(json, const <String>['x', 'pitch_x', 'pitchX']),
        );
        final double? rawY = _numberOrNull(
          GteJson.value(json, const <String>['y', 'pitch_y', 'pitchY']),
        );
        if (rawX == null || rawY == null) {
          return null;
        }
        return LiveMatchShotMarker(
          x: _normalizeCoordinate(rawX),
          y: _normalizeCoordinate(rawY),
          xg:
              _numberOrNull(
                GteJson.value(json, const <String>[
                  'xg',
                  'expected_goals',
                  'expectedGoals',
                ]),
              ) ??
              0,
          team:
              GteJson.stringOrNull(json, const <String>[
                'team',
                'side',
                'team_side',
                'teamSide',
              ]) ??
              'home',
        );
      })
      .whereType<LiveMatchShotMarker>()
      .toList(growable: false);
}

double _normalizeCoordinate(double value) {
  final double normalized = value > 1 ? value / 100 : value;
  return normalized.clamp(0, 1).toDouble();
}

List<int> _momentumFromPayload(Map<String, Object?> payload) {
  final Object? raw = GteJson.value(payload, const <String>[
    'momentum',
    'momentum_timeline',
    'momentumTimeline',
  ]);
  if (raw == null) {
    return const <int>[];
  }
  try {
    return GteJson.list(raw, label: 'momentum timeline')
        .map(_numberOrNull)
        .whereType<double>()
        .map((double value) => value.round())
        .toList(growable: false);
  } catch (_) {
    return const <int>[];
  }
}

List<LiveMatchTacticalSuggestion> _tacticalSuggestionsFromPayload(
  Map<String, Object?> payload,
) {
  final Object? raw = GteJson.value(payload, const <String>[
    'tactical_suggestions',
    'tacticalSuggestions',
    'tactical_overlays',
    'tacticalOverlays',
  ]);
  if (raw == null) {
    return const <LiveMatchTacticalSuggestion>[];
  }
  try {
    return GteJson.list(raw, label: 'tactical suggestions')
        .map((Object? item) {
          final Map<String, Object?> json = _optionalMap(item);
          final String? title = GteJson.stringOrNull(json, const <String>[
            'title',
            'label',
          ]);
          final String? detail = GteJson.stringOrNull(json, const <String>[
            'detail',
            'description',
            'note',
          ]);
          if (title == null || detail == null) {
            return null;
          }
          return LiveMatchTacticalSuggestion(
            title: title,
            detail: detail,
            impactLabel:
                GteJson.stringOrNull(json, const <String>[
                  'impact_label',
                  'impactLabel',
                  'state',
                ]) ??
                'Feed note',
          );
        })
        .whereType<LiveMatchTacticalSuggestion>()
        .toList(growable: false);
  } catch (_) {
    return const <LiveMatchTacticalSuggestion>[];
  }
}

List<LiveMatchIntelligenceSignal> _intelligenceSignalsFromPayload(
  Object? value,
) {
  return _optionalList(value)
      .map((Object? item) {
        if (item is String) {
          final String detail = item.trim();
          if (detail.isEmpty) {
            return null;
          }
          return LiveMatchIntelligenceSignal(
            title: 'Live intelligence',
            detail: detail,
          );
        }
        final Map<String, Object?> json = _optionalMap(item);
        final String? title = GteJson.stringOrNull(json, const <String>[
          'title',
          'headline',
          'label',
        ]);
        final String? detail = GteJson.stringOrNull(json, const <String>[
          'detail',
          'description',
          'body',
          'summary',
        ]);
        if (title == null && detail == null) {
          return null;
        }
        return LiveMatchIntelligenceSignal(
          title: title ?? 'Live intelligence',
          detail: detail ?? title ?? '',
          severity: GteJson.stringOrNull(json, const <String>[
            'severity',
            'priority',
            'state',
          ]),
          source: GteJson.stringOrNull(json, const <String>[
            'source',
            'provider',
            'model',
          ]),
        );
      })
      .whereType<LiveMatchIntelligenceSignal>()
      .toList(growable: false);
}

String _formatMetric(double value, String unit, int decimals) {
  final String formatted =
      decimals == 0
          ? value.round().toString()
          : value.toStringAsFixed(decimals);
  return '$formatted$unit';
}

List<LiveMatchLineupPlayer>? _lineupFromPayload(Object? value) {
  if (value is! List || value.isEmpty) {
    return null;
  }
  return value
      .map((Object? item) {
        final Map<String, Object?> json = GteJson.map(
          item,
          label: 'live match lineup player',
        );
        final String? name = GteJson.stringOrNull(json, <String>[
          'player_name',
          'playerName',
          'name',
        ]);
        if (name == null) {
          return null;
        }
        return LiveMatchLineupPlayer(
          playerId: GteJson.stringOrNull(json, <String>[
            'player_id',
            'playerId',
          ]),
          name: name,
          position: GteJson.string(json, <String>['position'], fallback: 'UNK'),
          rating: GteJson.number(json, <String>['rating'], fallback: 0),
          captain: GteJson.boolean(json, <String>['captain'], fallback: false),
          nationalityCode: GteJson.stringOrNull(json, <String>[
            'nationality_code',
            'nationalityCode',
          ]),
          avatarSeedToken: GteJson.stringOrNull(json, <String>[
            'avatar_seed_token',
            'avatarSeedToken',
          ]),
          avatarDnaSeed: GteJson.stringOrNull(json, <String>[
            'avatar_dna_seed',
            'avatarDnaSeed',
          ]),
          avatar: PlayerAvatar.fromJsonOrNull(
            GteJson.value(json, <String>['avatar']),
          ),
        );
      })
      .whereType<LiveMatchLineupPlayer>()
      .toList(growable: false);
}

LiveMatchPhase _phaseFromLiveFeed(String phase, String status, int minute) {
  final String normalizedPhase = phase.trim().toLowerCase();
  final String normalizedStatus = status.trim().toLowerCase();
  if (normalizedPhase == 'scheduled' ||
      normalizedPhase == 'pre_match' ||
      normalizedPhase == 'prematch' ||
      normalizedStatus == 'scheduled' ||
      normalizedStatus == 'pre_match' ||
      normalizedStatus == 'prematch') {
    return LiveMatchPhase.preMatch;
  }
  if (normalizedPhase == 'paused' ||
      normalizedPhase == 'halftime' ||
      normalizedPhase == 'half_time' ||
      normalizedStatus == 'halftime' ||
      normalizedStatus == 'half_time') {
    return LiveMatchPhase.halftime;
  }
  if (normalizedPhase == 'fulltime' ||
      normalizedPhase == 'full_time' ||
      normalizedStatus == 'completed' ||
      normalizedStatus == 'fulltime' ||
      normalizedStatus == 'full_time') {
    return LiveMatchPhase.fullTime;
  }
  if (minute >= 45) {
    return LiveMatchPhase.secondHalf;
  }
  return LiveMatchPhase.firstHalf;
}

List<LiveMatchEvent> _mapLiveFeedEvents(
  Map<String, Object?> payload, {
  required List<LiveMatchEvent> fallback,
}) {
  final List<Object?> rawEvents = _optionalList(
    GteJson.value(payload, <String>[
      'timeline_events',
      'timelineEvents',
      'timeline',
      'commentary',
      'events',
    ]),
  );
  if (rawEvents.isEmpty) {
    return fallback;
  }
  return rawEvents
      .map((Object? rawEvent) {
        if (rawEvent is String) {
          return null;
        }
        if (rawEvent is! Map) {
          return null;
        }
        final Map<String, Object?> json = GteJson.map(
          rawEvent,
          label: 'timeline event',
        );
        final String eventType = GteJson.string(json, <String>[
          'event_type',
          'eventType',
        ], fallback: '');
        final int? minute = GteJson.integerOrNull(json, <String>[
          'minute',
          'clock_minute',
          'clockMinute',
        ]);
        if (minute == null) {
          return null;
        }
        final String? teamName = GteJson.stringOrNull(json, <String>[
          'team_name',
          'teamName',
          'club_name',
          'clubName',
        ]);
        final String? description = GteJson.stringOrNull(json, <String>[
          'description',
          'commentary',
          'detail',
          'text',
        ]);
        final String? title = GteJson.stringOrNull(json, <String>[
          'title',
          'headline',
        ]);
        final String? backendText = title ?? description;
        if (backendText == null) {
          return null;
        }
        final bool isKeyMoment =
            _isKeyMoment(eventType) ||
            GteJson.boolean(json, const <String>[
              'is_key_moment',
              'isKeyMoment',
              'highlight_eligible',
              'highlightEligible',
            ]);
        final LiveMatchEventType mappedType = _mapEventType(eventType);
        return LiveMatchEvent(
          minute: minute,
          title: title ?? backendText,
          detail: description ?? backendText,
          team: teamName ?? '',
          type: mappedType,
          isKeyMoment: isKeyMoment,
        );
      })
      .whereType<LiveMatchEvent>()
      .toList(growable: false);
}

LiveMatchEventType _mapEventType(String eventType) {
  switch (eventType.trim().toLowerCase()) {
    case 'goal':
    case 'goals':
    case 'penalty':
    case 'penalties':
    case 'penalty_goal':
      return LiveMatchEventType.goal;
    case 'card':
    case 'yellow_card':
    case 'red_card':
    case 'yellow_cards':
    case 'red_cards':
      return LiveMatchEventType.card;
    case 'substitution':
    case 'substitutions':
      return LiveMatchEventType.substitution;
    default:
      return LiveMatchEventType.incident;
  }
}

bool _isKeyMoment(String eventType) {
  final String normalized = eventType.trim().toLowerCase();
  return normalized == 'goal' ||
      normalized == 'goals' ||
      normalized == 'penalty' ||
      normalized == 'penalties' ||
      normalized == 'penalty_goal' ||
      normalized == 'red_card' ||
      normalized == 'red_cards';
}
