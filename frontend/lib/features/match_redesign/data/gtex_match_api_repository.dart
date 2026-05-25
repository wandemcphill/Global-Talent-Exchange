import 'dart:async';

import '../../../data/gte_authed_api.dart';
import 'gtex_match_models.dart';
import 'gtex_match_repository.dart';

export 'gtex_match_repository.dart';

class ApiBackedMatchRepository implements GtexMatchRepository {
  const ApiBackedMatchRepository({
    required GteAuthedApi client,
    Stream<Map<String, Object?>> Function(String matchId)? realtimeEvents,
  }) : _client = client,
       _realtimeEvents = realtimeEvents;

  final GteAuthedApi _client;
  final Stream<Map<String, Object?>> Function(String matchId)? _realtimeEvents;

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) async {
    final Map<String, dynamic> payload = await _client.getMap(
      '/api/matches/$matchId/state',
    );
    if (payload['fixture'] == true ||
        payload['demo'] == true ||
        payload['mock'] == true ||
        payload['synthetic'] == true) {
      throw StateError('Match $matchId returned fixture data in live runtime.');
    }
    return _parseLiveMatchState(payload, expectedMatchId: matchId);
  }

  @override
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId) async* {
    yield await fetchLiveMatch(matchId);
    final Stream<Map<String, Object?>> Function(String matchId)?
    realtimeEvents = _realtimeEvents;
    if (realtimeEvents == null) {
      return;
    }
    await for (final Map<String, Object?> _ in realtimeEvents(matchId)) {
      yield await fetchLiveMatch(matchId);
    }
  }

  @override
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  ) async {
    await _client.post(
      '/api/matches/$matchId/tactics',
      body: <String, Object?>{
        'press_intensity': instruction.pressIntensity,
        'defensive_line': instruction.defensiveLine,
        'tempo': instruction.tempo,
        'risk_level': instruction.riskLevel,
      },
    );
  }
}

GtexLiveMatchState _parseLiveMatchState(
  Map<String, Object?> payload, {
  required String expectedMatchId,
}) {
  final Map<String, Object?> home = _asMap(payload['home']);
  final Map<String, Object?> away = _asMap(payload['away']);
  final String matchId = _string(payload, const <String>[
    'match_id',
    'matchId',
  ], fallback: expectedMatchId);
  return GtexLiveMatchState(
    matchId: matchId,
    home: _parseTeam(home, fallbackId: 'home'),
    away: _parseTeam(away, fallbackId: 'away'),
    minute: _int(payload, const <String>['minute', 'clock'], fallback: 0),
    phase: _phase(
      _string(payload, const <String>[
        'phase',
        'status',
      ], fallback: 'scheduled'),
    ),
    pitchPlayers: _list(payload['pitch_players'] ?? payload['pitchPlayers'])
        .map((Object? value) => _parsePitchPlayer(_asMap(value)))
        .toList(growable: false),
    timeline: _list(payload['timeline'] ?? payload['events'])
        .map((Object? value) => _parseTimelineEvent(_asMap(value)))
        .toList(growable: false),
    stats: _parseStats(_asMap(payload['stats'])),
    highlights: _list(payload['highlights'])
        .map((Object? value) => _parseHighlight(_asMap(value)))
        .toList(growable: false),
    homeMomentumPercent: _nullableInt(payload, const <String>[
      'home_momentum_percent',
      'homeMomentumPercent',
    ]),
    economyImpacts: _list(
          payload['economy_impacts'] ?? payload['economyImpacts'],
        )
        .map((Object? value) => _parseEconomyImpact(_asMap(value)))
        .toList(growable: false),
    isWatchedByOwner: _bool(payload, const <String>[
      'is_watched_by_owner',
      'isWatchedByOwner',
    ]),
  );
}

GtexMatchTeam _parseTeam(
  Map<String, Object?> json, {
  required String fallbackId,
}) {
  final String name = _requiredString(json, const <String>[
    'name',
  ], 'match team name');
  return GtexMatchTeam(
    id: _string(
      json,
      const <String>['id', 'team_id', 'teamId'],
      fallback:
          fallbackId == 'home' || fallbackId == 'away' ? name : fallbackId,
    ),
    name: name,
    shortName: _string(json, const <String>[
      'short_name',
      'shortName',
    ], fallback: _shortName(name)),
    score: _int(json, const <String>['score'], fallback: 0),
    formation: _string(json, const <String>[
      'formation',
    ], fallback: 'unavailable'),
    players: _list(json['players'] ?? json['lineup'])
        .map((Object? value) => _parseLineupPlayer(_asMap(value)))
        .toList(growable: false),
    badgeUrl: _nullableString(json, const <String>['badge_url', 'badgeUrl']),
    primaryColorHex: _nullableString(json, const <String>[
      'primary_color_hex',
      'primaryColorHex',
    ]),
  );
}

GtexLineupPlayer _parseLineupPlayer(Map<String, Object?> json) {
  final String name = _requiredString(json, const <String>[
    'name',
    'label',
  ], 'lineup player name');
  return GtexLineupPlayer(
    id: _string(json, const <String>[
      'id',
      'player_id',
      'playerId',
    ], fallback: name),
    name: name,
    position: _string(json, const <String>[
      'position',
      'role',
    ], fallback: 'N/A'),
    shirtNumber: _int(json, const <String>[
      'shirt_number',
      'shirtNumber',
    ], fallback: 0),
    rating: _double(json, const <String>['rating'], fallback: 0),
    imageUrl: _nullableString(json, const <String>['image_url', 'imageUrl']),
    isRegen: _bool(json, const <String>['is_regen', 'isRegen']),
  );
}

GtexPitchPlayer _parsePitchPlayer(Map<String, Object?> json) {
  final String name = _requiredString(json, const <String>[
    'name',
    'label',
  ], 'pitch player name');
  return GtexPitchPlayer(
    playerId: _string(json, const <String>[
      'player_id',
      'playerId',
      'id',
    ], fallback: name),
    teamId: _string(json, const <String>['team_id', 'teamId'], fallback: ''),
    name: name,
    shirtNumber: _int(json, const <String>[
      'shirt_number',
      'shirtNumber',
    ], fallback: 0),
    x: _double(json, const <String>['x'], fallback: 0.5).clamp(0, 1).toDouble(),
    y: _double(json, const <String>['y'], fallback: 0.5).clamp(0, 1).toDouble(),
    isHome: _bool(json, const <String>['is_home', 'isHome']),
    hasBall: _bool(json, const <String>['has_ball', 'hasBall']),
  );
}

GtexMatchTimelineEvent _parseTimelineEvent(Map<String, Object?> json) {
  final String rawType = _string(json, const <String>[
    'type',
  ], fallback: 'pass');
  final String? description = _nullableString(json, const <String>[
    'description',
    'summary',
  ]);
  return GtexMatchTimelineEvent(
    minute: _int(json, const <String>['minute', 'clock'], fallback: 0),
    type: _eventType(rawType),
    title:
        _nullableString(json, const <String>['title']) ??
        description ??
        rawType.replaceAll('_', ' '),
    description: description ?? '',
    teamId: _nullableString(json, const <String>['team_id', 'teamId']),
    playerName: _nullableString(json, const <String>[
      'player_name',
      'playerName',
    ]),
  );
}

GtexMatchStats _parseStats(Map<String, Object?> json) {
  return GtexMatchStats(
    homePossession: _int(json, const <String>[
      'home_possession',
      'homePossession',
    ], fallback: 0),
    awayPossession: _int(json, const <String>[
      'away_possession',
      'awayPossession',
    ], fallback: 0),
    homeShots: _int(json, const <String>[
      'home_shots',
      'homeShots',
    ], fallback: 0),
    awayShots: _int(json, const <String>[
      'away_shots',
      'awayShots',
    ], fallback: 0),
    homeShotsOnTarget: _int(json, const <String>[
      'home_shots_on_target',
      'homeShotsOnTarget',
    ], fallback: 0),
    awayShotsOnTarget: _int(json, const <String>[
      'away_shots_on_target',
      'awayShotsOnTarget',
    ], fallback: 0),
    homePassAccuracy: _int(json, const <String>[
      'home_pass_accuracy',
      'homePassAccuracy',
    ], fallback: 0),
    awayPassAccuracy: _int(json, const <String>[
      'away_pass_accuracy',
      'awayPassAccuracy',
    ], fallback: 0),
    homeExpectedGoals: _double(json, const <String>[
      'home_expected_goals',
      'homeExpectedGoals',
    ], fallback: 0),
    awayExpectedGoals: _double(json, const <String>[
      'away_expected_goals',
      'awayExpectedGoals',
    ], fallback: 0),
  );
}

GtexMatchHighlight _parseHighlight(Map<String, Object?> json) {
  final String? title = _nullableString(json, const <String>['title']);
  final String summary = _string(json, const <String>[
    'summary',
    'description',
  ], fallback: '');
  if (title == null && summary.isEmpty) {
    throw StateError('Live match highlight is missing title and summary.');
  }
  return GtexMatchHighlight(
    minute: _int(json, const <String>['minute'], fallback: 0),
    title: title ?? summary,
    summary: summary,
    importance: _int(json, const <String>['importance'], fallback: 1),
  );
}

GtexMatchEconomyImpact _parseEconomyImpact(Map<String, Object?> json) {
  final String playerName = _requiredString(json, const <String>[
    'player_name',
    'playerName',
    'name',
  ], 'economy impact player name');
  return GtexMatchEconomyImpact(
    playerName: playerName,
    teamId: _nullableString(json, const <String>['team_id', 'teamId']),
    currentValueLabel: _nullableString(json, const <String>[
      'current_value_label',
      'currentValueLabel',
      'current_value',
      'currentValue',
    ]),
    deltaLabel: _nullableString(json, const <String>[
      'delta_label',
      'deltaLabel',
      'value_delta',
      'valueDelta',
    ]),
    deltaPercent: _nullableDouble(json, const <String>[
      'delta_percent',
      'deltaPercent',
    ]),
  );
}

GtexMatchPhase _phase(String raw) {
  switch (raw.toUpperCase()) {
    case 'PRE':
    case 'SCHEDULED':
      return GtexMatchPhase.scheduled;
    case 'LIVE':
    case '1H':
    case 'FIRST_HALF':
      return GtexMatchPhase.firstHalf;
    case 'HT':
    case 'HALF_TIME':
      return GtexMatchPhase.halfTime;
    case '2H':
    case 'SECOND_HALF':
      return GtexMatchPhase.secondHalf;
    case 'ET':
    case 'EXTRA_TIME':
      return GtexMatchPhase.extraTime;
    case 'PEN':
    case 'PENALTIES':
      return GtexMatchPhase.penalties;
    case 'FT':
    case 'FULL_TIME':
      return GtexMatchPhase.fullTime;
    default:
      return GtexMatchPhase.scheduled;
  }
}

GtexPitchEventType _eventType(String raw) {
  switch (raw.toLowerCase()) {
    case 'kickoff':
      return GtexPitchEventType.kickoff;
    case 'shot':
      return GtexPitchEventType.shot;
    case 'goal':
      return GtexPitchEventType.goal;
    case 'tackle':
      return GtexPitchEventType.tackle;
    case 'save':
      return GtexPitchEventType.save;
    case 'foul':
      return GtexPitchEventType.foul;
    case 'yellow_card':
    case 'yellowcard':
      return GtexPitchEventType.yellowCard;
    case 'red_card':
    case 'redcard':
      return GtexPitchEventType.redCard;
    case 'substitution':
      return GtexPitchEventType.substitution;
    case 'tactical_change':
    case 'tacticalchange':
      return GtexPitchEventType.tacticalChange;
    default:
      return GtexPitchEventType.pass;
  }
}

Map<String, Object?> _asMap(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return Map<String, Object?>.from(value);
  }
  return const <String, Object?>{};
}

List<Object?> _list(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

String _string(
  Map<String, Object?> json,
  List<String> keys, {
  required String fallback,
}) {
  return _nullableString(json, keys) ?? fallback;
}

String _requiredString(
  Map<String, Object?> json,
  List<String> keys,
  String fieldName,
) {
  final String? value = _nullableString(json, keys);
  if (value == null) {
    throw StateError('Live match payload missing $fieldName.');
  }
  return value;
}

String? _nullableString(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value != null) {
      final String parsed = value.toString().trim();
      if (parsed.isNotEmpty) {
        return parsed;
      }
    }
  }
  return null;
}

int _int(
  Map<String, Object?> json,
  List<String> keys, {
  required int fallback,
}) {
  final String? raw = _nullableString(json, keys);
  if (raw == null) {
    return fallback;
  }
  return int.tryParse(raw) ?? double.tryParse(raw)?.round() ?? fallback;
}

int? _nullableInt(Map<String, Object?> json, List<String> keys) {
  final String? raw = _nullableString(json, keys);
  if (raw == null) {
    return null;
  }
  return int.tryParse(raw) ?? double.tryParse(raw)?.round();
}

double _double(
  Map<String, Object?> json,
  List<String> keys, {
  required double fallback,
}) {
  final String? raw = _nullableString(json, keys);
  if (raw == null) {
    return fallback;
  }
  return double.tryParse(raw) ?? fallback;
}

double? _nullableDouble(Map<String, Object?> json, List<String> keys) {
  final String? raw = _nullableString(json, keys);
  if (raw == null) {
    return null;
  }
  return double.tryParse(raw);
}

bool _bool(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is bool) {
      return value;
    }
    if (value is num) {
      return value != 0;
    }
    if (value is String) {
      final String normalized = value.trim().toLowerCase();
      if (normalized == 'true' || normalized == 'yes' || normalized == '1') {
        return true;
      }
      if (normalized == 'false' || normalized == 'no' || normalized == '0') {
        return false;
      }
    }
  }
  return false;
}

String _shortName(String name) {
  final List<String> parts = name
      .split(RegExp(r'\s+'))
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.length >= 2) {
    return parts.take(3).map((String part) => part[0]).join().toUpperCase();
  }
  return name.length <= 3
      ? name.toUpperCase()
      : name.substring(0, 3).toUpperCase();
}
