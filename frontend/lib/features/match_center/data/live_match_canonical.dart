import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

typedef LiveMatchJson = Map<String, Object?>;

enum GtexLiveMatchPhase {
  scheduled,
  preMatch,
  firstHalf,
  halftime,
  secondHalf,
  fullTime,
  abandoned,
  unknown,
}

enum GtexLiveOverlayMode { shape, pressure, shots, xG, territory, market }

enum GtexOverlayStatus { confirmed, degraded, blocked }

class GtexTeamSnapshot {
  const GtexTeamSnapshot({
    required this.name,
    this.id,
    this.score,
    this.shortName,
    this.formation,
  });

  final String name;
  final String? id;
  final int? score;
  final String? shortName;
  final String? formation;
}

class GtexPitchPoint {
  const GtexPitchPoint({
    required this.x,
    required this.y,
    required this.label,
    required this.team,
    this.value,
    this.detail,
  });

  final double x;
  final double y;
  final String label;
  final String team;
  final double? value;
  final String? detail;
}

class GtexShotPoint extends GtexPitchPoint {
  const GtexShotPoint({
    required super.x,
    required super.y,
    required super.label,
    required super.team,
    this.minute,
    this.xg,
    this.outcome,
  }) : super(value: xg, detail: outcome);

  final int? minute;
  final double? xg;
  final String? outcome;
}

class GtexLiveStatPair {
  const GtexLiveStatPair({
    required this.label,
    this.home,
    this.away,
    this.unit = '',
  });

  final String label;
  final double? home;
  final double? away;
  final String unit;

  bool get isComplete => home != null && away != null;

  String get homeText => _formatNumber(home, unit);

  String get awayText => _formatNumber(away, unit);
}

class GtexLiveTimelineEvent {
  const GtexLiveTimelineEvent({
    required this.id,
    required this.minute,
    required this.title,
    required this.body,
    required this.type,
    this.team,
    this.isKeyMoment = false,
  });

  final String id;
  final int? minute;
  final String title;
  final String body;
  final String type;
  final String? team;
  final bool isKeyMoment;
}

class GtexLiveIntelligence {
  const GtexLiveIntelligence({
    required this.title,
    required this.detail,
    this.severity,
    this.mode,
  });

  final String title;
  final String detail;
  final String? severity;
  final GtexLiveOverlayMode? mode;
}

class GtexOverlayReadiness {
  const GtexOverlayReadiness({
    required this.mode,
    required this.status,
    required this.message,
    this.payload = const <String, Object?>{},
  });

  final GtexLiveOverlayMode mode;
  final GtexOverlayStatus status;
  final String message;
  final LiveMatchJson payload;

  bool get isConfirmed => status == GtexOverlayStatus.confirmed;
}

class GtexLiveMatchSnapshot {
  const GtexLiveMatchSnapshot({
    required this.matchId,
    required this.home,
    required this.away,
    required this.phase,
    required this.statusLabel,
    this.minute,
    this.clockLabel,
    this.possession,
    this.pressure,
    this.expectedGoals,
    this.territory,
    this.shots,
    this.marketSignal,
    this.marketDetail,
    this.homeShape = const <GtexPitchPoint>[],
    this.awayShape = const <GtexPitchPoint>[],
    this.shotMap = const <GtexShotPoint>[],
    this.timeline = const <GtexLiveTimelineEvent>[],
    this.commentary = const <GtexLiveTimelineEvent>[],
    this.intelligence = const <GtexLiveIntelligence>[],
    this.overlayPayloads = const <GtexLiveOverlayMode, LiveMatchJson>{},
    this.raw = const <String, Object?>{},
  });

  final String matchId;
  final GtexTeamSnapshot home;
  final GtexTeamSnapshot away;
  final GtexLiveMatchPhase phase;
  final String statusLabel;
  final int? minute;
  final String? clockLabel;
  final GtexLiveStatPair? possession;
  final GtexLiveStatPair? pressure;
  final GtexLiveStatPair? expectedGoals;
  final GtexLiveStatPair? territory;
  final GtexLiveStatPair? shots;
  final String? marketSignal;
  final String? marketDetail;
  final List<GtexPitchPoint> homeShape;
  final List<GtexPitchPoint> awayShape;
  final List<GtexShotPoint> shotMap;
  final List<GtexLiveTimelineEvent> timeline;
  final List<GtexLiveTimelineEvent> commentary;
  final List<GtexLiveIntelligence> intelligence;
  final Map<GtexLiveOverlayMode, LiveMatchJson> overlayPayloads;
  final LiveMatchJson raw;

  bool get hasScore => home.score != null && away.score != null;

  bool get hasClock =>
      minute != null || (clockLabel?.trim().isNotEmpty ?? false);

  String get scoreLabel =>
      '${home.score?.toString() ?? '--'} - ${away.score?.toString() ?? '--'}';

  String get matchClockLabel {
    final String? explicit = clockLabel?.trim();
    if (explicit != null && explicit.isNotEmpty) {
      return explicit;
    }
    final int? resolvedMinute = minute;
    if (resolvedMinute != null) {
      return "$resolvedMinute'";
    }
    return statusLabel;
  }

  List<GtexPitchPoint> get shape => <GtexPitchPoint>[
    ...homeShape,
    ...awayShape,
  ];

  List<GtexLiveStatPair> get statPairs => <GtexLiveStatPair>[
    if (possession != null) possession!,
    if (pressure != null) pressure!,
    if (expectedGoals != null) expectedGoals!,
    if (territory != null) territory!,
    if (shots != null) shots!,
  ];

  GtexOverlayReadiness overlay(GtexLiveOverlayMode mode) {
    final LiveMatchJson payload =
        overlayPayloads[mode] ?? const <String, Object?>{};
    final String? backendStatus = _stringValue(payload, const <String>[
      'status',
      'state',
      'readiness',
    ]);
    if (_isBlockedStatus(backendStatus)) {
      return GtexOverlayReadiness(
        mode: mode,
        status: GtexOverlayStatus.blocked,
        message:
            _stringValue(payload, const <String>['reason', 'message']) ??
            _blockedMessage(mode),
        payload: payload,
      );
    }
    if (_isDegradedStatus(backendStatus)) {
      return GtexOverlayReadiness(
        mode: mode,
        status: GtexOverlayStatus.degraded,
        message:
            _stringValue(payload, const <String>['reason', 'message']) ??
            _degradedMessage(mode),
        payload: payload,
      );
    }
    final bool confirmed = switch (mode) {
      GtexLiveOverlayMode.shape => shape.isNotEmpty || payload.isNotEmpty,
      GtexLiveOverlayMode.pressure =>
        pressure?.isComplete == true || payload.isNotEmpty,
      GtexLiveOverlayMode.shots => shotMap.isNotEmpty || payload.isNotEmpty,
      GtexLiveOverlayMode.xG =>
        expectedGoals?.isComplete == true ||
            shotMap.any((GtexShotPoint shot) => shot.xg != null) ||
            _hasAuthoritativeXgPayload(payload),
      GtexLiveOverlayMode.territory =>
        territory?.isComplete == true || payload.isNotEmpty,
      GtexLiveOverlayMode.market =>
        (marketSignal?.trim().isNotEmpty ?? false) ||
            (marketDetail?.trim().isNotEmpty ?? false) ||
            payload.isNotEmpty,
    };
    return GtexOverlayReadiness(
      mode: mode,
      status:
          confirmed ? GtexOverlayStatus.confirmed : GtexOverlayStatus.blocked,
      message:
          confirmed
              ? _confirmedMessage(mode)
              : _stringValue(payload, const <String>['reason', 'message']) ??
                  _blockedMessage(mode),
      payload: payload,
    );
  }

  factory GtexLiveMatchSnapshot.fromJson(
    Object? value, {
    String? fallbackMatchId,
  }) {
    final LiveMatchJson source = _canonicalPayload(value);
    final LiveMatchJson scoreboard = _mapValue(source, const <String>[
      'scoreboard',
      'score_board',
      'scoreBoard',
      'score',
    ]);
    final LiveMatchJson clock = _mapValue(source, const <String>[
      'clock',
      'match_clock',
      'matchClock',
      'time',
    ]);
    final LiveMatchJson teams = _mapValue(source, const <String>['teams']);
    final LiveMatchJson homeMap = _firstMap(source, <List<String>>[
      const <String>['home'],
      const <String>['home_team'],
      const <String>['homeTeam'],
    ]);
    final LiveMatchJson awayMap = _firstMap(source, <List<String>>[
      const <String>['away'],
      const <String>['away_team'],
      const <String>['awayTeam'],
    ]);
    final LiveMatchJson nestedHome = _mapValue(teams, const <String>['home']);
    final LiveMatchJson nestedAway = _mapValue(teams, const <String>['away']);
    final LiveMatchJson scoreboardHome = _mapValue(scoreboard, const <String>[
      'home',
    ]);
    final LiveMatchJson scoreboardAway = _mapValue(scoreboard, const <String>[
      'away',
    ]);
    final LiveMatchJson stats = _statsSource(source);
    final LiveMatchJson market = _marketSource(source);
    final LiveMatchJson overlays = _mapValue(source, const <String>[
      'overlays',
      'tactical_overlays',
      'tacticalOverlays',
    ]);

    final GtexTeamSnapshot home = _teamSnapshot(
      <LiveMatchJson>[homeMap, nestedHome, scoreboardHome, scoreboard, source],
      nameKeys: const <String>[
        'home_team_name',
        'homeTeamName',
        'home_name',
        'homeName',
        'home_team',
        'homeTeam',
      ],
      scoreKeys: const <String>['home_score', 'homeScore', 'home_goals'],
    );
    final GtexTeamSnapshot away = _teamSnapshot(
      <LiveMatchJson>[awayMap, nestedAway, scoreboardAway, scoreboard, source],
      nameKeys: const <String>[
        'away_team_name',
        'awayTeamName',
        'away_name',
        'awayName',
        'away_team',
        'awayTeam',
      ],
      scoreKeys: const <String>['away_score', 'awayScore', 'away_goals'],
    );
    final String status =
        _firstString(
          <LiveMatchJson>[clock, source],
          const <String>[
            'status',
            'state',
            'phase',
            'period',
            'match_status',
            'matchStatus',
          ],
        ) ??
        'unknown';
    final List<GtexLiveTimelineEvent> events = _timelineEvents(source);

    return GtexLiveMatchSnapshot(
      matchId:
          _stringValue(source, const <String>['match_id', 'matchId', 'id']) ??
          fallbackMatchId ??
          'unresolved-match',
      home: home,
      away: away,
      phase: _phaseFrom(status),
      statusLabel: status,
      minute: _intValue(
        _firstValue(
          <LiveMatchJson>[clock, source],
          const <String>[
            'minute',
            'match_minute',
            'matchMinute',
            'current_minute',
            'currentMinute',
            'clock_minute',
            'clockMinute',
            'elapsed_minute',
            'elapsedMinute',
          ],
        ),
      ),
      clockLabel: _firstString(
        <LiveMatchJson>[clock, source],
        const <String>['clock', 'clock_label', 'clockLabel', 'label'],
      ),
      possession: _pair(
        stats,
        'Possession',
        const <String>['possession', 'possession_pct', 'possessionPct'],
        const <String>['home_possession', 'homePossession'],
        const <String>['away_possession', 'awayPossession'],
        unit: '%',
      ),
      pressure: _pair(
        stats,
        'Pressure',
        const <String>['pressure', 'pressure_index', 'pressureIndex'],
        const <String>['home_pressure', 'homePressure'],
        const <String>['away_pressure', 'awayPressure'],
      ),
      expectedGoals: _pair(
        stats,
        'xG',
        const <String>['xg', 'expected_goals', 'expectedGoals'],
        const <String>['home_xg', 'homeXg', 'home_expected_goals'],
        const <String>['away_xg', 'awayXg', 'away_expected_goals'],
      ),
      territory: _pair(
        stats,
        'Territory',
        const <String>['territory', 'territory_pct', 'territoryPct'],
        const <String>['home_territory', 'homeTerritory'],
        const <String>['away_territory', 'awayTerritory'],
        unit: '%',
      ),
      shots: _pair(
        stats,
        'Shots',
        const <String>['shots', 'total_shots', 'totalShots'],
        const <String>['home_shots', 'homeShots'],
        const <String>['away_shots', 'awayShots'],
      ),
      marketSignal: _stringValue(market, const <String>[
        'signal',
        'headline',
        'market_signal',
        'marketSignal',
      ]),
      marketDetail: _stringValue(market, const <String>[
        'detail',
        'summary',
        'market_detail',
        'marketDetail',
      ]),
      homeShape: _shapePoints(source, side: 'home'),
      awayShape: _shapePoints(source, side: 'away'),
      shotMap: _shotMap(source),
      timeline: events,
      commentary: events
          .where(
            (GtexLiveTimelineEvent event) =>
                event.body.trim().isNotEmpty ||
                event.type.toLowerCase().contains('comment'),
          )
          .toList(growable: false),
      intelligence: _intelligence(source),
      overlayPayloads: _overlayPayloads(overlays),
      raw: source,
    );
  }
}

class CanonicalLiveMatchRepository {
  CanonicalLiveMatchRepository({required this.client});

  final GteAuthedApi client;

  factory CanonicalLiveMatchRepository.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
    String? accessToken,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return CanonicalLiveMatchRepository(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  Future<GtexLiveMatchSnapshot> fetchSnapshot(String matchId) async {
    if (client.mode == GteBackendMode.fixture) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message: 'Canonical match center requires backend live mode.',
      );
    }
    final LiveMatchJson payload = await client.getMap(
      '/api/match-engine/live-feed/$matchId',
      auth: false,
    );
    return GtexLiveMatchSnapshot.fromJson(payload, fallbackMatchId: matchId);
  }
}

LiveMatchJson _canonicalPayload(Object? value) {
  LiveMatchJson map = _asMap(value);
  for (final String key in const <String>[
    'payload',
    'data',
    'match',
    'snapshot',
    'live_feed',
    'liveFeed',
  ]) {
    final LiveMatchJson nested = _mapValue(map, <String>[key]);
    if (nested.isNotEmpty) {
      map = nested;
    }
  }
  return map;
}

LiveMatchJson _asMap(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (dynamic key, dynamic item) =>
          MapEntry<String, Object?>(key.toString(), item),
    );
  }
  return const <String, Object?>{};
}

List<Object?> _asList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is Iterable) {
    return value.cast<Object?>().toList(growable: false);
  }
  return const <Object?>[];
}

Object? _pick(LiveMatchJson source, List<String> keys) {
  for (final String key in keys) {
    if (source.containsKey(key)) {
      return source[key];
    }
  }
  return null;
}

Object? _firstValue(List<LiveMatchJson> sources, List<String> keys) {
  for (final LiveMatchJson source in sources) {
    final Object? value = _pick(source, keys);
    if (value != null) {
      return value;
    }
  }
  return null;
}

String? _firstString(List<LiveMatchJson> sources, List<String> keys) {
  for (final LiveMatchJson source in sources) {
    final String? value = _stringValue(source, keys);
    if (value != null) {
      return value;
    }
  }
  return null;
}

LiveMatchJson _mapValue(LiveMatchJson source, List<String> keys) =>
    _asMap(_pick(source, keys));

LiveMatchJson _firstMap(LiveMatchJson source, List<List<String>> keySets) {
  for (final List<String> keys in keySets) {
    final LiveMatchJson map = _mapValue(source, keys);
    if (map.isNotEmpty) {
      return map;
    }
  }
  return const <String, Object?>{};
}

String? _stringValue(LiveMatchJson source, List<String> keys) {
  final Object? value = _pick(source, keys);
  if (value is Map || value is List) {
    return null;
  }
  final String? text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}

int? _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString().trim() ?? '');
}

double? _doubleValue(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  final String normalized = value?.toString().replaceAll('%', '').trim() ?? '';
  return double.tryParse(normalized);
}

String _formatNumber(double? value, String unit) {
  if (value == null) {
    return '--';
  }
  final String text =
      value == value.roundToDouble()
          ? value.round().toString()
          : value.toStringAsFixed(2);
  return '$text$unit';
}

GtexTeamSnapshot _teamSnapshot(
  List<LiveMatchJson> candidates, {
  required List<String> nameKeys,
  required List<String> scoreKeys,
}) {
  String? name;
  String? id;
  String? shortName;
  String? formation;
  int? score;
  for (final LiveMatchJson candidate in candidates) {
    name ??= _stringValue(candidate, <String>[
      'name',
      'team_name',
      'teamName',
      ...nameKeys,
    ]);
    id ??= _stringValue(candidate, const <String>['id', 'team_id', 'teamId']);
    shortName ??= _stringValue(candidate, const <String>[
      'short_name',
      'shortName',
    ]);
    formation ??= _stringValue(candidate, const <String>['formation']);
    score ??= _intValue(_pick(candidate, <String>['score', ...scoreKeys]));
  }
  return GtexTeamSnapshot(
    name: name ?? 'Team pending',
    id: id,
    score: score,
    shortName: shortName,
    formation: formation,
  );
}

GtexLiveMatchPhase _phaseFrom(String value) {
  final String normalized = value.toLowerCase().replaceAll(
    RegExp(r'[^a-z0-9]'),
    '',
  );
  return switch (normalized) {
    'scheduled' => GtexLiveMatchPhase.scheduled,
    'prematch' || 'pre' || 'notstarted' => GtexLiveMatchPhase.preMatch,
    'firsthalf' || '1h' || 'livefirsthalf' => GtexLiveMatchPhase.firstHalf,
    'halftime' || 'half' => GtexLiveMatchPhase.halftime,
    'secondhalf' || '2h' || 'livesecondhalf' => GtexLiveMatchPhase.secondHalf,
    'fulltime' || 'ft' || 'completed' || 'final' => GtexLiveMatchPhase.fullTime,
    'abandoned' || 'cancelled' || 'canceled' => GtexLiveMatchPhase.abandoned,
    _ => GtexLiveMatchPhase.unknown,
  };
}

LiveMatchJson _statsSource(LiveMatchJson source) {
  final LiveMatchJson nested = _mapValue(source, const <String>[
    'stats',
    'match_stats',
    'matchStats',
    'analytics',
  ]);
  final LiveMatchJson overlays = _mapValue(source, const <String>[
    'overlays',
    'overlay_payloads',
    'overlayPayloads',
  ]);
  if (nested.isEmpty && overlays.isEmpty) {
    return source;
  }
  return <String, Object?>{...source, ...nested, ...overlays};
}

LiveMatchJson _marketSource(LiveMatchJson source) {
  final LiveMatchJson stats = _statsSource(source);
  final LiveMatchJson nested = _mapValue(stats, const <String>[
    'market',
    'market_context',
    'marketContext',
  ]);
  return nested.isEmpty ? stats : nested;
}

GtexLiveStatPair? _pair(
  LiveMatchJson source,
  String label,
  List<String> nestedKeys,
  List<String> homeKeys,
  List<String> awayKeys, {
  String unit = '',
}) {
  final LiveMatchJson nested = _mapValue(source, nestedKeys);
  final double? home =
      _doubleValue(
        _pick(nested, const <String>['home', 'home_value', 'homeValue']),
      ) ??
      _doubleValue(_pick(source, homeKeys));
  final double? away =
      _doubleValue(
        _pick(nested, const <String>['away', 'away_value', 'awayValue']),
      ) ??
      _doubleValue(_pick(source, awayKeys));
  if (home == null && away == null) {
    return null;
  }
  return GtexLiveStatPair(label: label, home: home, away: away, unit: unit);
}

List<GtexPitchPoint> _shapePoints(
  LiveMatchJson source, {
  required String side,
}) {
  final LiveMatchJson lineups = _mapValue(source, const <String>[
    'lineups',
    'lineup',
    'players',
  ]);
  final Object? raw =
      _pick(source, <String>[
        '${side}_shape',
        '${side}Shape',
        '${side}_lineup',
        '${side}Lineup',
      ]) ??
      _pick(lineups, <String>[side, '${side}_team', '${side}Team']);
  return _asList(raw)
      .map((Object? item) {
        final LiveMatchJson json = _asMap(item);
        final double? x = _coordinate(
          _pick(json, const <String>['x', 'pitch_x', 'pitchX']),
        );
        final double? y = _coordinate(
          _pick(json, const <String>['y', 'pitch_y', 'pitchY']),
        );
        if (x == null || y == null) {
          return null;
        }
        return GtexPitchPoint(
          x: x,
          y: y,
          label:
              _stringValue(json, const <String>[
                'label',
                'name',
                'player_name',
              ]) ??
              side,
          team: side,
          value: _doubleValue(_pick(json, const <String>['value', 'rating'])),
          detail: _stringValue(json, const <String>['position', 'role']),
        );
      })
      .whereType<GtexPitchPoint>()
      .toList(growable: false);
}

List<GtexShotPoint> _shotMap(LiveMatchJson source) {
  final LiveMatchJson stats = _statsSource(source);
  final Object? rawValue = _pick(stats, const <String>[
    'shot_map',
    'shotMap',
    'shots_map',
    'shotsMap',
    'shots_detail',
    'shotsDetail',
  ]);
  final Object? raw =
      rawValue is Map
          ? _firstValue(
            <LiveMatchJson>[_asMap(rawValue)],
            const <String>['shots', 'markers', 'items'],
          )
          : rawValue;
  return _asList(raw)
      .map((Object? item) {
        final LiveMatchJson json = _asMap(item);
        final double? x = _coordinate(
          _pick(json, const <String>['x', 'pitch_x', 'pitchX']),
        );
        final double? y = _coordinate(
          _pick(json, const <String>['y', 'pitch_y', 'pitchY']),
        );
        if (x == null || y == null) {
          return null;
        }
        return GtexShotPoint(
          x: x,
          y: y,
          label:
              _stringValue(json, const <String>[
                'player',
                'player_name',
                'label',
              ]) ??
              'Shot',
          team: _stringValue(json, const <String>['team', 'side']) ?? 'home',
          minute: _intValue(_pick(json, const <String>['minute'])),
          xg: _doubleValue(_pick(json, const <String>['xg', 'expected_goals'])),
          outcome: _stringValue(json, const <String>['outcome', 'result']),
        );
      })
      .whereType<GtexShotPoint>()
      .toList(growable: false);
}

bool _hasAuthoritativeXgPayload(LiveMatchJson payload) {
  if (payload.isEmpty) {
    return false;
  }
  final GtexLiveStatPair? totals = _pair(
    payload,
    'xG',
    const <String>['xg', 'expected_goals', 'expectedGoals'],
    const <String>['home_xg', 'homeXg', 'home_expected_goals'],
    const <String>['away_xg', 'awayXg', 'away_expected_goals'],
  );
  if (totals?.isComplete == true) {
    return true;
  }

  final Object? rawValue = _pick(payload, const <String>[
    'shot_map',
    'shotMap',
    'shots_map',
    'shotsMap',
    'shots_detail',
    'shotsDetail',
    'shots',
    'markers',
    'items',
  ]);
  final Object? raw =
      rawValue is Map
          ? _firstValue(
            <LiveMatchJson>[_asMap(rawValue)],
            const <String>['shots', 'markers', 'items'],
          )
          : rawValue;
  return _asList(raw).any((Object? item) {
    final LiveMatchJson shot = _asMap(item);
    return _pick(shot, const <String>[
          'xg',
          'expected_goals',
          'expectedGoals',
        ]) !=
        null;
  });
}

double? _coordinate(Object? value) {
  final double? raw = _doubleValue(value);
  if (raw == null) {
    return null;
  }
  return (raw > 1 ? raw / 100 : raw).clamp(0, 1).toDouble();
}

List<GtexLiveTimelineEvent> _timelineEvents(LiveMatchJson source) {
  final Object? raw = _pick(source, const <String>[
    'events',
    'timeline',
    'commentary',
    'feed',
  ]);
  return _asList(raw)
      .asMap()
      .entries
      .map((MapEntry<int, Object?> entry) {
        final LiveMatchJson json = _asMap(entry.value);
        final String type =
            _stringValue(json, const <String>[
              'type',
              'event_type',
              'eventType',
            ]) ??
            'event';
        final String title =
            _stringValue(json, const <String>['title', 'headline', 'label']) ??
            _titleFromType(type);
        return GtexLiveTimelineEvent(
          id:
              _stringValue(json, const <String>['id', 'event_id', 'eventId']) ??
              'event-${entry.key}',
          minute: _intValue(
            _pick(json, const <String>['minute', 'match_minute']),
          ),
          title: title,
          body:
              _stringValue(json, const <String>[
                'body',
                'detail',
                'description',
                'text',
              ]) ??
              '',
          type: type,
          team: _stringValue(json, const <String>[
            'team',
            'team_name',
            'teamName',
          ]),
          isKeyMoment: _boolValue(
            _pick(json, const <String>[
              'is_key_moment',
              'isKeyMoment',
              'key_moment',
            ]),
          ),
        );
      })
      .toList(growable: false);
}

List<GtexLiveIntelligence> _intelligence(LiveMatchJson source) {
  final Object? raw = _pick(source, const <String>[
    'intelligence',
    'live_intelligence',
    'liveIntelligence',
    'inspector',
    'tactical_suggestions',
    'tacticalSuggestions',
  ]);
  final LiveMatchJson rawMap = _asMap(raw);
  final Object? resolvedRaw =
      rawMap.isNotEmpty
          ? _firstValue(
                <LiveMatchJson>[rawMap],
                const <String>['signals', 'items', 'insights'],
              ) ??
              <Object?>[rawMap]
          : raw;
  return _asList(resolvedRaw)
      .map((Object? item) {
        final LiveMatchJson json = _asMap(item);
        final String? title = _stringValue(json, const <String>[
          'title',
          'headline',
          'label',
        ]);
        final String? detail = _stringValue(json, const <String>[
          'detail',
          'body',
          'summary',
        ]);
        if (title == null && detail == null) {
          return null;
        }
        return GtexLiveIntelligence(
          title: title ?? 'Live intelligence',
          detail: detail ?? '',
          severity: _stringValue(json, const <String>['severity', 'tone']),
          mode: _modeFromString(
            _stringValue(json, const <String>['mode', 'overlay']),
          ),
        );
      })
      .whereType<GtexLiveIntelligence>()
      .toList(growable: false);
}

Map<GtexLiveOverlayMode, LiveMatchJson> _overlayPayloads(LiveMatchJson source) {
  return <GtexLiveOverlayMode, LiveMatchJson>{
    for (final GtexLiveOverlayMode mode in GtexLiveOverlayMode.values)
      mode: _mapValue(source, <String>[_overlayKey(mode), mode.name]),
  }..removeWhere((_, LiveMatchJson value) => value.isEmpty);
}

bool _boolValue(Object? value) {
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  return normalized == 'true' || normalized == '1' || normalized == 'yes';
}

String _titleFromType(String type) {
  final String normalized = type.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) {
    return 'Match event';
  }
  return normalized[0].toUpperCase() + normalized.substring(1);
}

GtexLiveOverlayMode? _modeFromString(String? value) {
  final String normalized =
      value?.toLowerCase().replaceAll(RegExp(r'[^a-z]'), '') ?? '';
  for (final GtexLiveOverlayMode mode in GtexLiveOverlayMode.values) {
    if (_overlayKey(mode).toLowerCase() == normalized ||
        mode.name.toLowerCase() == normalized) {
      return mode;
    }
  }
  return null;
}

String _overlayKey(GtexLiveOverlayMode mode) => switch (mode) {
  GtexLiveOverlayMode.shape => 'shape',
  GtexLiveOverlayMode.pressure => 'pressure',
  GtexLiveOverlayMode.shots => 'shots',
  GtexLiveOverlayMode.xG => 'xg',
  GtexLiveOverlayMode.territory => 'territory',
  GtexLiveOverlayMode.market => 'market',
};

bool _isBlockedStatus(String? value) {
  final String normalized = value?.toLowerCase().trim() ?? '';
  return normalized == 'blocked' ||
      normalized == 'missing' ||
      normalized == 'unavailable';
}

bool _isDegradedStatus(String? value) {
  final String normalized = value?.toLowerCase().trim() ?? '';
  return normalized == 'degraded' ||
      normalized == 'partial' ||
      normalized == 'pending' ||
      normalized == 'syncing' ||
      normalized == 'stale' ||
      normalized == 'delayed';
}

String _confirmedMessage(GtexLiveOverlayMode mode) => switch (mode) {
  GtexLiveOverlayMode.shape => 'Shape overlay confirmed from live positions.',
  GtexLiveOverlayMode.pressure =>
    'Pressure overlay confirmed from backend pressure values.',
  GtexLiveOverlayMode.shots => 'Shots overlay confirmed from backend shot map.',
  GtexLiveOverlayMode.xG =>
    'xG overlay confirmed from expected-goals payloads.',
  GtexLiveOverlayMode.territory =>
    'Territory overlay confirmed from field-control payloads.',
  GtexLiveOverlayMode.market =>
    'Market overlay confirmed from match-market context.',
};

String _blockedMessage(GtexLiveOverlayMode mode) => switch (mode) {
  GtexLiveOverlayMode.shape =>
    'Shape overlay is blocked until the backend sends player positions.',
  GtexLiveOverlayMode.pressure =>
    'Pressure overlay is blocked until the backend sends pressure values.',
  GtexLiveOverlayMode.shots =>
    'Shots overlay is blocked until the backend sends a shot map.',
  GtexLiveOverlayMode.xG =>
    'xG overlay is blocked until the backend sends xG totals or weighted shots.',
  GtexLiveOverlayMode.territory =>
    'Territory overlay is blocked until the backend sends territory values.',
  GtexLiveOverlayMode.market =>
    'Market overlay is blocked until the backend sends match-market context.',
};

String _degradedMessage(GtexLiveOverlayMode mode) =>
    '${_overlayLabel(mode)} overlay is degraded by the backend payload.';

String _overlayLabel(GtexLiveOverlayMode mode) => switch (mode) {
  GtexLiveOverlayMode.shape => 'Shape',
  GtexLiveOverlayMode.pressure => 'Pressure',
  GtexLiveOverlayMode.shots => 'Shots',
  GtexLiveOverlayMode.xG => 'xG',
  GtexLiveOverlayMode.territory => 'Territory',
  GtexLiveOverlayMode.market => 'Market',
};
