import 'dart:async';

import '../../../data/gte_authed_api.dart';
import 'gtex_match_models.dart';
import 'gtex_match_repository.dart';

export 'gtex_match_repository.dart';

class ApiBackedMatchRepository implements GtexMatchRepository {
  const ApiBackedMatchRepository({
    required GteAuthedApi client,
    Stream<Map<String, Object?>> Function(String matchId)? realtimeEvents,
    Duration minimumRefreshInterval = const Duration(milliseconds: 400),
  }) : _client = client,
       _realtimeEvents = realtimeEvents,
       _minimumRefreshInterval = minimumRefreshInterval;

  final GteAuthedApi _client;
  final Stream<Map<String, Object?>> Function(String matchId)? _realtimeEvents;

  /// Floor between two state re-fetches.
  ///
  /// The realtime channel emits one frame per match event, and a busy minute
  /// can burst a dozen of them. Without coalescing, each burst turned into a
  /// dozen `/state` round trips for a single visible update.
  final Duration _minimumRefreshInterval;

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
    final Stream<Map<String, Object?>> Function(String matchId)?
    realtimeEvents = _realtimeEvents;
    if (realtimeEvents == null) {
      // No realtime channel wired: emit the current snapshot once and close.
      // The controller treats the close as a drop and polls with backoff.
      yield await fetchLiveMatch(matchId);
      return;
    }

    DateTime? lastFetchedAt;
    int consecutiveFailures = 0;

    await for (final Map<String, Object?> event in realtimeEvents(matchId)) {
      // Coalesce event bursts into at most one refetch per interval.
      final DateTime now = DateTime.now();
      final DateTime? previous = lastFetchedAt;
      if (previous != null &&
          now.difference(previous) < _minimumRefreshInterval &&
          !_isTerminalEvent(event)) {
        continue;
      }
      lastFetchedAt = now;

      try {
        final GtexLiveMatchState snapshot = await fetchLiveMatch(matchId);
        consecutiveFailures = 0;
        yield snapshot;
        if (snapshot.phase == GtexMatchPhase.fullTime) {
          return;
        }
      } catch (error) {
        // A single malformed or failed refresh must not kill the feed. Give up
        // only after the backend has failed repeatedly, at which point the
        // controller takes over with its own backoff.
        consecutiveFailures += 1;
        if (consecutiveFailures >= 3) {
          rethrow;
        }
      }
    }
  }

  /// Full-time and similar terminal frames bypass burst coalescing so the
  /// final result is never withheld behind the refresh floor.
  static bool _isTerminalEvent(Map<String, Object?> event) {
    final Object? raw = event['phase'] ?? event['status'] ?? event['type'];
    if (raw == null) {
      return false;
    }
    final String normalized = raw.toString().trim().toUpperCase();
    return normalized == 'FT' ||
        normalized == 'FULL_TIME' ||
        normalized == 'FULLTIME' ||
        normalized == 'MATCH_ENDED';
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
        if (instruction.formation != null) 'formation': instruction.formation,
        if (instruction.mentality != null) 'mentality': instruction.mentality,
        if (instruction.side != null) 'side': instruction.side,
        if (instruction.substitutions != null && instruction.substitutions!.isNotEmpty)
          'substitutions': instruction.substitutions,
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
    ball: _parsePitchBall(_asMap(payload['ball'])),
    preMatch: _parsePreMatchPackage(_asMap(payload['pre_match'] ?? payload['preMatch'])),
    postMatch: _parsePostMatchPackage(_asMap(payload['post_match'] ?? payload['postMatch'])),
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
    players: _list(json['players'] ?? json['lineup'] ?? json['starters'])
        .map((Object? value) => _parseLineupPlayer(_asMap(value)))
        .toList(growable: false),
    badgeUrl: _nullableString(json, const <String>['badge_url', 'badgeUrl']),
    primaryColorHex: _nullableString(json, const <String>[
      'primary_color_hex',
      'primaryColorHex',
    ]),
    managerName: _nullableString(json, const <String>[
      'manager_name', 'managerName', 'coach_name', 'coachName',
    ]),
    recentFormPercent: _nullableInt(json, const <String>[
      'recent_form_percent', 'recentFormPercent', 'recent_form', 'recentForm',
    ]),
    mentality: _nullableString(json, const <String>['mentality', 'manager_mentality']),
    instructionSummary: _list(
      json['instruction_summary'] ?? json['instructionSummary'] ?? json['tactical_instructions'],
    ).map((Object? value) => value?.toString().trim() ?? '')
      .where((String value) => value.isNotEmpty).toList(growable: false),
    bench: _list(json['bench'] ?? json['bench_players'] ?? json['substitutes'])
        .map((Object? value) => _parseLineupPlayer(_asMap(value)))
        .toList(growable: false),
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
    rating: _double(json, const <String>['rating', 'overall', 'overall_rating'], fallback: 0),
    imageUrl: _nullableString(json, const <String>['image_url', 'imageUrl', 'portrait_url', 'portraitUrl']),
    isRegen: _boolOrDefault(json, const <String>['is_regen', 'isRegen']),
    formLabel: _nullableString(json, const <String>['form', 'form_label', 'formLabel']),
    fitnessPct: _nullableDouble(json, const <String>['fitness_pct', 'fitnessPct', 'fitness']),
  );
}

GtexPostMatchPackage? _parsePostMatchPackage(Map<String, Object?> json) {
  if (json.isEmpty || json['analytics_available'] == false) return null;
  final motmMap = _asMap(json['motm']);
  final ratingRaw = motmMap['rating'];
  final assistsRaw = motmMap['assists'];
  final keyPassesRaw = motmMap['key_passes'] ?? motmMap['keyPasses'];
  final passAccRaw = motmMap['pass_acc'] ?? motmMap['passAcc'];
  final motm = GtexPlayerOfTheMatch(
    playerName: _string(motmMap, const <String>['player_name', 'playerName'], fallback: ''),
    teamName: _string(motmMap, const <String>['team_name', 'teamName'], fallback: ''),
    shirtNumber: _int(motmMap, const <String>['shirt_number', 'shirtNumber'], fallback: 0),
    rating: _double(motmMap, const <String>['rating'], fallback: 0),
    goals: _int(motmMap, const <String>['goals'], fallback: 0),
    assists: _int(motmMap, const <String>['assists'], fallback: 0),
    keyPasses: _int(motmMap, const <String>['key_passes', 'keyPasses'], fallback: 0),
    passAcc: _int(motmMap, const <String>['pass_acc', 'passAcc'], fallback: 0),
    summary: _string(motmMap, const <String>['summary'], fallback: 'Verified player-performance data is unavailable.'),
    available: _boolOrDefault(motmMap, const <String>['available'], fallback: false),
    ratingAvailable: ratingRaw is num,
    assistsAvailable: assistsRaw is num,
    keyPassesAvailable: keyPassesRaw is num,
    passAccAvailable: passAccRaw is num,
  );

  final shotMap = _list(json['shot_map'] ?? json['shotMap'])
      .map(_asMap)
      .where((Map<String, Object?> m) =>
          m['coordinates_measured'] == true && m['x'] is num && m['y'] is num && m['xg'] is num)
      .map((Map<String, Object?> m) => GtexShotMapEntry(
            minute: _int(m, const <String>['minute'], fallback: 0),
            isHome: _bool(m, const <String>['is_home', 'isHome']),
            x: _double(m, const <String>['x'], fallback: 0),
            y: _double(m, const <String>['y'], fallback: 0),
            xg: _double(m, const <String>['xg'], fallback: 0),
            outcome: _string(m, const <String>['outcome'], fallback: 'unknown'),
            playerName: _string(m, const <String>['player_name', 'playerName'], fallback: 'Unknown player'),
          ))
      .toList(growable: false);

  final momentum = _list(json['momentum']).map((item) {
    final m = _asMap(item);
    return GtexMomentumPoint(
      minute: _int(m, const <String>['minute'], fallback: 0),
      value: _int(m, const <String>['value'], fallback: 0),
    );
  }).toList(growable: false);

  final ratings = _list(json['ratings'])
      .map(_asMap)
      .where((Map<String, Object?> m) => m['rating'] is num)
      .map((Map<String, Object?> m) => GtexPlayerRatingItem(
            playerId: _string(m, const <String>['player_id', 'playerId', 'id'], fallback: ''),
            name: _string(m, const <String>['name', 'label'], fallback: 'Unknown player'),
            shirtNumber: _int(m, const <String>['shirt_number', 'shirtNumber'], fallback: 0),
            position: _string(m, const <String>['position', 'role'], fallback: 'N/A'),
            rating: _double(m, const <String>['rating'], fallback: 0),
            isHome: _bool(m, const <String>['is_home', 'isHome']),
            badges: _list(m['badges']).map((e) => e.toString()).toList(),
          ))
      .toList(growable: false);

  return GtexPostMatchPackage(
    motm: motm,
    shotMap: shotMap,
    momentum: momentum,
    ratings: ratings,
    shareSummary: _string(json, const <String>['share_summary', 'shareSummary'], fallback: 'Verified match analytics are unavailable.'),
  );
}

GtexPreMatchPackage? _parsePreMatchPackage(Map<String, Object?> json) {
  if (json.isEmpty) return null;
  final keyDuelMap = _asMap(json['key_duel'] ?? json['keyDuel']);
  final homeRatingRaw = keyDuelMap['home_player_rating'] ?? keyDuelMap['homePlayerRating'];
  final awayRatingRaw = keyDuelMap['away_player_rating'] ?? keyDuelMap['awayPlayerRating'];
  final GtexKeyDuel? keyDuel = keyDuelMap.isNotEmpty && keyDuelMap['available'] != false
      ? GtexKeyDuel(
          homePlayerName: _string(keyDuelMap, const <String>['home_player_name', 'homePlayerName'], fallback: ''),
          homePlayerRole: _string(keyDuelMap, const <String>['home_player_role', 'homePlayerRole'], fallback: 'N/A'),
          homePlayerRating: _double(keyDuelMap, const <String>['home_player_rating', 'homePlayerRating'], fallback: 0),
          awayPlayerName: _string(keyDuelMap, const <String>['away_player_name', 'awayPlayerName'], fallback: ''),
          awayPlayerRole: _string(keyDuelMap, const <String>['away_player_role', 'awayPlayerRole'], fallback: 'N/A'),
          awayPlayerRating: _double(keyDuelMap, const <String>['away_player_rating', 'awayPlayerRating'], fallback: 0),
          description: _string(keyDuelMap, const <String>['description'], fallback: 'Recorded lineups are unavailable.'),
          available: _boolOrDefault(keyDuelMap, const <String>['available'], fallback: true),
          homePlayerRatingAvailable: homeRatingRaw is num,
          awayPlayerRatingAvailable: awayRatingRaw is num,
        )
      : null;
  final homeForm = _list(json['home_form'] ?? json['homeForm']).map((e) => e.toString()).toList(growable: false);
  final awayForm = _list(json['away_form'] ?? json['awayForm']).map((e) => e.toString()).toList(growable: false);
  final votes = _int(json, const <String>['total_votes', 'totalVotes'], fallback: 0);

  return GtexPreMatchPackage(
    homeForm: homeForm,
    awayForm: awayForm,
    homeWinRate: _int(json, const <String>['home_win_rate', 'homeWinRate'], fallback: 0),
    awayWinRate: _int(json, const <String>['away_win_rate', 'awayWinRate'], fallback: 0),
    h2hTotal: _int(json, const <String>['h2h_total', 'h2hTotal'], fallback: 0),
    h2hHomeWins: _int(json, const <String>['h2h_home_wins', 'h2hHomeWins'], fallback: 0),
    h2hDraws: _int(json, const <String>['h2h_draws', 'h2hDraws'], fallback: 0),
    h2hAwayWins: _int(json, const <String>['h2h_away_wins', 'h2hAwayWins'], fallback: 0),
    h2hLastMeeting: _string(json, const <String>['h2h_last_meeting', 'h2hLastMeeting'], fallback: 'No recorded previous meeting'),
    homeWinPct: _int(json, const <String>['home_win_pct', 'homeWinPct'], fallback: 0),
    drawPct: _int(json, const <String>['draw_pct', 'drawPct'], fallback: 0),
    awayWinPct: _int(json, const <String>['away_win_pct', 'awayWinPct'], fallback: 0),
    totalVotes: votes,
    keyDuel: keyDuel,
    storyline: _nullableString(json, const <String>['storyline']),
    homeFormAvailable: _boolOrDefault(json, const <String>['home_form_available', 'homeFormAvailable'], fallback: homeForm.isNotEmpty),
    awayFormAvailable: _boolOrDefault(json, const <String>['away_form_available', 'awayFormAvailable'], fallback: awayForm.isNotEmpty),
    h2hAvailable: _boolOrDefault(json, const <String>['h2h_available', 'h2hAvailable'], fallback: _int(json, const <String>['h2h_total', 'h2hTotal'], fallback: 0) > 0),
    probabilityAvailable: _boolOrDefault(json, const <String>['win_probability_available', 'probabilityAvailable'], fallback: json['home_win_pct'] is num && json['draw_pct'] is num && json['away_win_pct'] is num),
    votesAvailable: votes > 0,
    homeWinRateAvailable: json['home_win_rate'] is num || json['homeWinRate'] is num,
    awayWinRateAvailable: json['away_win_rate'] is num || json['awayWinRate'] is num,
  );
}

GtexPitchBall? _parsePitchBall(Map<String, Object?> json) {
  if (json.isEmpty) {
    return null;
  }
  return GtexPitchBall(
    x: _double(json, const <String>['x'], fallback: 0.5).clamp(0, 1).toDouble(),
    y: _double(json, const <String>['y'], fallback: 0.5).clamp(0, 1).toDouble(),
    z: _double(json, const <String>['z'], fallback: 0.0),
    ownerPlayerId: _nullableString(json, const <String>['owner_player_id', 'ownerPlayerId']),
    state: _string(json, const <String>['state'], fallback: 'rolling'),
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
    isHome: _boolOrDefault(json, const <String>['is_home', 'isHome']),
    hasBall: _boolOrDefault(json, const <String>['has_ball', 'hasBall']),
    role: _nullableString(json, const <String>['role', 'position']),
    state: _string(json, const <String>['state'], fallback: 'idle'),
    animationState: _string(json, const <String>['animation_state', 'animationState'], fallback: 'idle'),
    staminaPct: _double(json, const <String>['stamina_pct', 'staminaPct', 'stamina'], fallback: 100.0),
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
  final Map<String, Object?> projections = _asMap(json['projections']);
  final Map<String, Object?> shots = _asMap(projections['shots']);
  final Map<String, Object?> possession = _asMap(projections['possession']);
  final Map<String, Object?> passing = _asMap(projections['passing']);
  final Map<String, Object?> xg = _asMap(projections['expected_goals']);
  return GtexMatchStats(
    homePossession: _int(json, const <String>['home_possession', 'homePossession'], fallback: 0),
    awayPossession: _int(json, const <String>['away_possession', 'awayPossession'], fallback: 0),
    homeShots: _int(json, const <String>['home_shots', 'homeShots'], fallback: 0),
    awayShots: _int(json, const <String>['away_shots', 'awayShots'], fallback: 0),
    homeShotsOnTarget: _int(json, const <String>['home_shots_on_target', 'homeShotsOnTarget'], fallback: 0),
    awayShotsOnTarget: _int(json, const <String>['away_shots_on_target', 'awayShotsOnTarget'], fallback: 0),
    homePassAccuracy: _int(json, const <String>['home_pass_accuracy', 'homePassAccuracy'], fallback: 0),
    awayPassAccuracy: _int(json, const <String>['away_pass_accuracy', 'awayPassAccuracy'], fallback: 0),
    homeExpectedGoals: _double(json, const <String>['home_expected_goals', 'homeExpectedGoals'], fallback: 0),
    awayExpectedGoals: _double(json, const <String>['away_expected_goals', 'awayExpectedGoals'], fallback: 0),
    shotsAvailable: _boolOrDefault(shots, const <String>['available'], fallback: json['home_shots'] != null && json['away_shots'] != null),
    possessionAvailable: _boolOrDefault(possession, const <String>['available'], fallback: json['home_possession'] != null && json['away_possession'] != null),
    passingAvailable: _boolOrDefault(passing, const <String>['available'], fallback: json['home_pass_accuracy'] != null && json['away_pass_accuracy'] != null),
    expectedGoalsAvailable: _boolOrDefault(xg, const <String>['available'], fallback: json['home_expected_goals'] != null && json['away_expected_goals'] != null),
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

bool _boolOrDefault(
  Map<String, Object?> json,
  List<String> keys, {
  required bool fallback,
}) {
  final bool hasValue = keys.any(json.containsKey);
  return hasValue ? _bool(json, keys) : fallback;
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
