import 'package:gte_frontend/data/gte_models.dart';

enum CompetitionLifecycleStage {
  unknown,
  draft,
  published,
  openForJoin,
  filled,
  locked,
  seeding,
  scheduled,
  inProgress,
  paused,
  completed,
  cancelled,
  refunded,
  disputed,
}

enum CompetitionBracketNodeStatus {
  unknown,
  pending,
  scheduled,
  live,
  completed,
  cancelled,
  bye,
  walkover,
  blocked,
}

class CompetitionLifecycleState {
  const CompetitionLifecycleState({
    required this.stage,
    required this.rawStage,
    this.reason,
    this.blockedReason,
    this.bracketPublished = false,
    this.degraded = false,
    this.degradedReasons = const <String>[],
    this.registrationOpensAt,
    this.registrationClosesAt,
    this.lockAt,
    this.startsAt,
    this.completedAt,
    this.updatedAt,
  });

  final CompetitionLifecycleStage stage;
  final String rawStage;
  final String? reason;
  final String? blockedReason;
  final bool bracketPublished;
  final bool degraded;
  final List<String> degradedReasons;
  final DateTime? registrationOpensAt;
  final DateTime? registrationClosesAt;
  final DateTime? lockAt;
  final DateTime? startsAt;
  final DateTime? completedAt;
  final DateTime? updatedAt;

  bool get isBlocked => blockedReason != null;

  bool get isTerminal =>
      stage == CompetitionLifecycleStage.completed ||
      stage == CompetitionLifecycleStage.cancelled ||
      stage == CompetitionLifecycleStage.refunded;

  bool get isLive => stage == CompetitionLifecycleStage.inProgress;

  factory CompetitionLifecycleState.fromJson(Object? value) {
    if (value == null) {
      return const CompetitionLifecycleState(
        stage: CompetitionLifecycleStage.unknown,
        rawStage: 'unknown',
        degraded: true,
        degradedReasons: <String>['lifecycle_payload_missing'],
      );
    }
    if (value is String) {
      return CompetitionLifecycleState(
        stage: competitionLifecycleStageFromString(value),
        rawStage: value,
      );
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition lifecycle state',
    );
    final String rawStage =
        _stringOrNullFrom(
          <Map<String, Object?>>[json],
          <String>[
            'stage',
            'status',
            'state',
            'lifecycle_status',
            'lifecycleStatus',
            'lifecycle_stage',
            'lifecycleStage',
          ],
        ) ??
        'unknown';
    final List<String> degradedReasons = _stringsFrom(
      _firstValue(
        <Map<String, Object?>>[json],
        <String>[
          'degraded_reasons',
          'degradedReasons',
          'warnings',
          'backend_warnings',
          'backendWarnings',
        ],
      ),
    );
    return CompetitionLifecycleState(
      stage: competitionLifecycleStageFromString(rawStage),
      rawStage: rawStage,
      reason: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['reason', 'status_reason', 'statusReason'],
      ),
      blockedReason: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'blocked_reason',
          'blockedReason',
          'block_reason',
          'blockReason',
        ],
      ),
      bracketPublished: _boolFrom(
        <Map<String, Object?>>[json],
        <String>[
          'bracket_published',
          'bracketPublished',
          'has_bracket',
          'hasBracket',
        ],
      ),
      degraded:
          _boolFrom(
            <Map<String, Object?>>[json],
            <String>['degraded', 'is_degraded', 'isDegraded'],
          ) ||
          degradedReasons.isNotEmpty,
      degradedReasons: degradedReasons,
      registrationOpensAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['registration_opens_at', 'registrationOpensAt'],
      ),
      registrationClosesAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['registration_closes_at', 'registrationClosesAt'],
      ),
      lockAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['lock_at', 'lockAt', 'locked_at', 'lockedAt'],
      ),
      startsAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>[
          'starts_at',
          'startsAt',
          'scheduled_start_at',
          'scheduledStartAt',
        ],
      ),
      completedAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['completed_at', 'completedAt'],
      ),
      updatedAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['updated_at', 'updatedAt'],
      ),
    );
  }
}

class CompetitionBracketPayload {
  const CompetitionBracketPayload({
    required this.competitionId,
    required this.lifecycle,
    required this.rounds,
    this.bracketId,
    this.title,
    this.revision,
    this.generatedAt,
    this.updatedAt,
    this.backendWarnings = const <String>[],
  });

  final String competitionId;
  final String? bracketId;
  final String? title;
  final String? revision;
  final CompetitionLifecycleState lifecycle;
  final List<CompetitionBracketRound> rounds;
  final DateTime? generatedAt;
  final DateTime? updatedAt;
  final List<String> backendWarnings;

  bool get hasRounds => rounds.isNotEmpty;

  bool get hasMatches =>
      rounds.any((CompetitionBracketRound round) => round.matches.isNotEmpty);

  bool get isDegraded =>
      backendWarnings.isNotEmpty || lifecycle.degraded || !hasRounds;

  factory CompetitionBracketPayload.fromJson(Object? value) {
    final Map<String, Object?> root = GteJson.map(
      value,
      label: 'competition bracket payload',
    );
    final Map<String, Object?> bracket =
        _mapOrNull(
          _firstValue(
            <Map<String, Object?>>[root],
            <String>[
              'bracket',
              'bracket_payload',
              'bracketPayload',
              'competition_bracket',
              'competitionBracket',
            ],
          ),
        ) ??
        root;
    final Object? lifecycleValue = _firstValue(
      <Map<String, Object?>>[root, bracket],
      <String>[
        'lifecycle',
        'lifecycle_state',
        'lifecycleState',
        'lifecycle_status',
        'lifecycleStatus',
        'stage',
        'status',
      ],
    );
    final List<Object?> roundItems = _listOrEmpty(
      _firstValue(
        <Map<String, Object?>>[bracket, root],
        <String>['rounds', 'bracket_rounds', 'bracketRounds'],
      ),
      label: 'competition bracket rounds',
    );
    final CompetitionLifecycleState lifecycle =
        lifecycleValue == null
            ? const CompetitionLifecycleState(
              stage: CompetitionLifecycleStage.unknown,
              rawStage: 'unknown',
              degraded: true,
              degradedReasons: <String>['lifecycle_payload_missing'],
            )
            : CompetitionLifecycleState.fromJson(lifecycleValue);
    return CompetitionBracketPayload(
      competitionId: _stringFrom(
        <Map<String, Object?>>[root, bracket],
        <String>['competition_id', 'competitionId', 'competition', 'id'],
      ),
      bracketId: _stringOrNullFrom(
        <Map<String, Object?>>[bracket, root],
        <String>['bracket_id', 'bracketId', 'id'],
      ),
      title: _stringOrNullFrom(
        <Map<String, Object?>>[root, bracket],
        <String>['title', 'name', 'competition_name', 'competitionName'],
      ),
      revision: _stringOrNullFrom(
        <Map<String, Object?>>[bracket, root],
        <String>[
          'revision',
          'version',
          'etag',
          'backend_revision',
          'backendRevision',
        ],
      ),
      lifecycle: lifecycle,
      rounds: roundItems
          .asMap()
          .entries
          .map(
            (MapEntry<int, Object?> entry) => CompetitionBracketRound.fromJson(
              entry.value,
              fallbackOrder: entry.key,
            ),
          )
          .toList(growable: false),
      generatedAt: _dateTimeFrom(
        <Map<String, Object?>>[bracket, root],
        <String>['generated_at', 'generatedAt', 'built_at', 'builtAt'],
      ),
      updatedAt: _dateTimeFrom(
        <Map<String, Object?>>[bracket, root],
        <String>['updated_at', 'updatedAt'],
      ),
      backendWarnings: _mergeStrings(<List<String>>[
        _stringsFrom(
          _firstValue(
            <Map<String, Object?>>[root, bracket],
            <String>[
              'warnings',
              'backend_warnings',
              'backendWarnings',
              'degraded_reasons',
              'degradedReasons',
            ],
          ),
        ),
        lifecycle.degradedReasons,
      ]),
    );
  }
}

class CompetitionBracketRound {
  const CompetitionBracketRound({
    required this.id,
    required this.order,
    required this.status,
    required this.matches,
    this.name,
    this.startsAt,
    this.completedAt,
  });

  final String id;
  final int order;
  final String? name;
  final CompetitionBracketNodeStatus status;
  final List<CompetitionBracketMatch> matches;
  final DateTime? startsAt;
  final DateTime? completedAt;

  String get displayName {
    final String? trimmed = _nonEmpty(name);
    if (trimmed != null) {
      return trimmed;
    }
    if (order > 0) {
      return 'Round $order';
    }
    return 'Round';
  }

  bool get hasMatches => matches.isNotEmpty;

  factory CompetitionBracketRound.fromJson(
    Object? value, {
    int fallbackOrder = 0,
  }) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition bracket round',
    );
    final int order =
        _intOrNullFrom(
          <Map<String, Object?>>[json],
          <String>[
            'order',
            'sequence',
            'round_order',
            'roundOrder',
            'round_index',
            'roundIndex',
            'index',
          ],
        ) ??
        fallbackOrder;
    final List<Object?> matchItems = _listOrEmpty(
      _firstValue(
        <Map<String, Object?>>[json],
        <String>['matches', 'fixtures', 'ties'],
      ),
      label: 'competition bracket matches',
    );
    return CompetitionBracketRound(
      id: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['id', 'round_id', 'roundId'],
        fallback: 'round-$fallbackOrder',
      ),
      order: order,
      name: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['name', 'title', 'label', 'round_name', 'roundName'],
      ),
      status: competitionBracketNodeStatusFromString(
        _stringOrNullFrom(
          <Map<String, Object?>>[json],
          <String>['status', 'state'],
        ),
      ),
      matches: matchItems
          .asMap()
          .entries
          .map(
            (MapEntry<int, Object?> entry) => CompetitionBracketMatch.fromJson(
              entry.value,
              fallbackOrder: entry.key,
            ),
          )
          .toList(growable: false),
      startsAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['starts_at', 'startsAt'],
      ),
      completedAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['completed_at', 'completedAt'],
      ),
    );
  }
}

class CompetitionBracketMatch {
  const CompetitionBracketMatch({
    required this.id,
    required this.order,
    required this.status,
    required this.home,
    required this.away,
    this.roundId,
    this.label,
    this.homeScore,
    this.awayScore,
    this.winnerParticipantId,
    this.liveMatchId,
    this.scheduledAt,
    this.startedAt,
    this.completedAt,
  });

  final String id;
  final String? roundId;
  final int order;
  final String? label;
  final CompetitionBracketNodeStatus status;
  final CompetitionBracketSide home;
  final CompetitionBracketSide away;
  final int? homeScore;
  final int? awayScore;
  final String? winnerParticipantId;
  final String? liveMatchId;
  final DateTime? scheduledAt;
  final DateTime? startedAt;
  final DateTime? completedAt;

  bool get hasScore => homeScore != null || awayScore != null;

  bool get hasParticipants => home.hasPayload || away.hasPayload;

  String get displayLabel =>
      _nonEmpty(label) ?? _nonEmpty(id) ?? 'Backend match';

  factory CompetitionBracketMatch.fromJson(
    Object? value, {
    int fallbackOrder = 0,
  }) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition bracket match',
    );
    final Map<String, Object?>? score = _mapOrNull(
      _firstValue(
        <Map<String, Object?>>[json],
        <String>['score', 'scores', 'result'],
      ),
    );
    final CompetitionBracketSide home = _sideFrom(
      json,
      preferredKeys: const <String>[
        'home',
        'home_participant',
        'homeParticipant',
        'team_a',
        'teamA',
        'participant_a',
        'participantA',
      ],
      listIndex: 0,
    );
    final CompetitionBracketSide away = _sideFrom(
      json,
      preferredKeys: const <String>[
        'away',
        'away_participant',
        'awayParticipant',
        'team_b',
        'teamB',
        'participant_b',
        'participantB',
      ],
      listIndex: 1,
    );
    final int? homeScore =
        _intOrNullFrom(
          <Map<String, Object?>>[if (score != null) score, json],
          <String>[
            'home_score',
            'homeScore',
            'home_goals',
            'homeGoals',
            'team_a_score',
            'teamAScore',
            'home',
          ],
        ) ??
        home.score;
    final int? awayScore =
        _intOrNullFrom(
          <Map<String, Object?>>[if (score != null) score, json],
          <String>[
            'away_score',
            'awayScore',
            'away_goals',
            'awayGoals',
            'team_b_score',
            'teamBScore',
            'away',
          ],
        ) ??
        away.score;
    return CompetitionBracketMatch(
      id: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['id', 'match_id', 'matchId', 'fixture_id', 'fixtureId'],
        fallback: 'match-$fallbackOrder',
      ),
      roundId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['round_id', 'roundId'],
      ),
      order:
          _intOrNullFrom(
            <Map<String, Object?>>[json],
            <String>['order', 'sequence', 'match_order', 'matchOrder', 'index'],
          ) ??
          fallbackOrder,
      label: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['label', 'name', 'title'],
      ),
      status: competitionBracketNodeStatusFromString(
        _stringOrNullFrom(
          <Map<String, Object?>>[json],
          <String>['status', 'state', 'match_status', 'matchStatus'],
        ),
      ),
      home: home,
      away: away,
      homeScore: homeScore,
      awayScore: awayScore,
      winnerParticipantId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'winner_participant_id',
          'winnerParticipantId',
          'winner_id',
          'winnerId',
        ],
      ),
      liveMatchId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'live_match_id',
          'liveMatchId',
          'match_viewer_id',
          'matchViewerId',
        ],
      ),
      scheduledAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['scheduled_at', 'scheduledAt', 'starts_at', 'startsAt'],
      ),
      startedAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['started_at', 'startedAt'],
      ),
      completedAt: _dateTimeFrom(
        <Map<String, Object?>>[json],
        <String>['completed_at', 'completedAt'],
      ),
    );
  }
}

class CompetitionBracketSide {
  const CompetitionBracketSide({
    this.participantId,
    this.clubId,
    this.name,
    this.seed,
    this.score,
    this.sourceMatchId,
    this.sourceLabel,
  });

  final String? participantId;
  final String? clubId;
  final String? name;
  final int? seed;
  final int? score;
  final String? sourceMatchId;
  final String? sourceLabel;

  bool get hasPayload =>
      participantId != null ||
      clubId != null ||
      name != null ||
      sourceMatchId != null ||
      sourceLabel != null;

  String get displayName {
    final String? directName = _nonEmpty(name);
    if (directName != null) {
      return directName;
    }
    final String? source = _nonEmpty(sourceLabel) ?? _nonEmpty(sourceMatchId);
    if (source != null) {
      return source;
    }
    return 'Awaiting backend seed';
  }

  factory CompetitionBracketSide.fromJson(Object? value) {
    if (value == null) {
      return const CompetitionBracketSide();
    }
    if (value is String || value is num) {
      return CompetitionBracketSide(name: value.toString().trim());
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition bracket side',
    );
    return CompetitionBracketSide(
      participantId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'participant_id',
          'participantId',
          'entry_id',
          'entryId',
          'team_id',
          'teamId',
          'id',
        ],
      ),
      clubId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['club_id', 'clubId'],
      ),
      name: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'name',
          'display_name',
          'displayName',
          'participant_name',
          'participantName',
          'team_name',
          'teamName',
          'club_name',
          'clubName',
          'label',
        ],
      ),
      seed: _intOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['seed', 'seed_number', 'seedNumber', 'rank'],
      ),
      score: _intOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['score', 'goals', 'points'],
      ),
      sourceMatchId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'source_match_id',
          'sourceMatchId',
          'from_match_id',
          'fromMatchId',
        ],
      ),
      sourceLabel: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>[
          'source_label',
          'sourceLabel',
          'placeholder',
          'placeholder_label',
          'placeholderLabel',
        ],
      ),
    );
  }
}

CompetitionLifecycleStage competitionLifecycleStageFromString(Object? value) {
  switch (_normalized(value)) {
    case 'draft':
      return CompetitionLifecycleStage.draft;
    case 'published':
      return CompetitionLifecycleStage.published;
    case 'open':
    case 'openforjoin':
    case 'registrationopen':
    case 'joinopen':
      return CompetitionLifecycleStage.openForJoin;
    case 'filled':
      return CompetitionLifecycleStage.filled;
    case 'locked':
    case 'registrationlocked':
      return CompetitionLifecycleStage.locked;
    case 'seeding':
    case 'seeded':
      return CompetitionLifecycleStage.seeding;
    case 'scheduled':
    case 'ready':
      return CompetitionLifecycleStage.scheduled;
    case 'live':
    case 'inprogress':
    case 'running':
      return CompetitionLifecycleStage.inProgress;
    case 'paused':
    case 'suspended':
      return CompetitionLifecycleStage.paused;
    case 'completed':
    case 'complete':
    case 'final':
    case 'settlementready':
    case 'settlement_ready':
    case 'awaitingsettlement':
    case 'awaiting_settlement':
      return CompetitionLifecycleStage.completed;
    case 'cancelled':
    case 'canceled':
      return CompetitionLifecycleStage.cancelled;
    case 'refunded':
      return CompetitionLifecycleStage.refunded;
    case 'disputed':
    case 'underreview':
      return CompetitionLifecycleStage.disputed;
    default:
      return CompetitionLifecycleStage.unknown;
  }
}

CompetitionBracketNodeStatus competitionBracketNodeStatusFromString(
  Object? value,
) {
  switch (_normalized(value)) {
    case 'pending':
    case 'unplayed':
    case 'notstarted':
      return CompetitionBracketNodeStatus.pending;
    case 'scheduled':
    case 'ready':
      return CompetitionBracketNodeStatus.scheduled;
    case 'live':
    case 'inprogress':
    case 'running':
      return CompetitionBracketNodeStatus.live;
    case 'completed':
    case 'complete':
    case 'final':
    case 'finished':
      return CompetitionBracketNodeStatus.completed;
    case 'cancelled':
    case 'canceled':
      return CompetitionBracketNodeStatus.cancelled;
    case 'bye':
      return CompetitionBracketNodeStatus.bye;
    case 'walkover':
    case 'forfeit':
      return CompetitionBracketNodeStatus.walkover;
    case 'blocked':
    case 'degraded':
      return CompetitionBracketNodeStatus.blocked;
    default:
      return CompetitionBracketNodeStatus.unknown;
  }
}

String competitionLifecycleStageLabel(CompetitionLifecycleStage stage) {
  return switch (stage) {
    CompetitionLifecycleStage.draft => 'Draft',
    CompetitionLifecycleStage.published => 'Published',
    CompetitionLifecycleStage.openForJoin => 'Open for join',
    CompetitionLifecycleStage.filled => 'Filled',
    CompetitionLifecycleStage.locked => 'Locked',
    CompetitionLifecycleStage.seeding => 'Seeding',
    CompetitionLifecycleStage.scheduled => 'Scheduled',
    CompetitionLifecycleStage.inProgress => 'In progress',
    CompetitionLifecycleStage.paused => 'Paused',
    CompetitionLifecycleStage.completed => 'Completed',
    CompetitionLifecycleStage.cancelled => 'Cancelled',
    CompetitionLifecycleStage.refunded => 'Refunded',
    CompetitionLifecycleStage.disputed => 'Disputed',
    CompetitionLifecycleStage.unknown => 'Lifecycle pending',
  };
}

String competitionBracketNodeStatusLabel(CompetitionBracketNodeStatus status) {
  return switch (status) {
    CompetitionBracketNodeStatus.pending => 'Pending',
    CompetitionBracketNodeStatus.scheduled => 'Scheduled',
    CompetitionBracketNodeStatus.live => 'Live',
    CompetitionBracketNodeStatus.completed => 'Completed',
    CompetitionBracketNodeStatus.cancelled => 'Cancelled',
    CompetitionBracketNodeStatus.bye => 'Bye',
    CompetitionBracketNodeStatus.walkover => 'Walkover',
    CompetitionBracketNodeStatus.blocked => 'Blocked',
    CompetitionBracketNodeStatus.unknown => 'Status pending',
  };
}

CompetitionBracketSide _sideFrom(
  Map<String, Object?> json, {
  required List<String> preferredKeys,
  required int listIndex,
}) {
  Object? value = _firstValue(<Map<String, Object?>>[json], preferredKeys);
  if (value == null) {
    final Object? listValue = _firstValue(
      <Map<String, Object?>>[json],
      <String>['participants', 'sides', 'entrants', 'teams'],
    );
    final List<Object?> list = _listOrEmpty(
      listValue,
      label: 'competition bracket match sides',
    );
    if (list.length > listIndex) {
      value = list[listIndex];
    }
  }
  return CompetitionBracketSide.fromJson(value);
}

Object? _firstValue(List<Map<String, Object?>> maps, List<String> keys) {
  for (final Map<String, Object?> map in maps) {
    for (final String key in keys) {
      if (map.containsKey(key)) {
        return map[key];
      }
    }
  }
  return null;
}

Map<String, Object?>? _mapOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  try {
    return GteJson.map(value);
  } on GteParsingException {
    return null;
  }
}

List<Object?> _listOrEmpty(Object? value, {required String label}) {
  if (value == null) {
    return const <Object?>[];
  }
  try {
    return GteJson.list(value, label: label);
  } on GteParsingException {
    return const <Object?>[];
  }
}

String _stringFrom(
  List<Map<String, Object?>> maps,
  List<String> keys, {
  String fallback = '',
}) {
  return _stringOrNullFrom(maps, keys) ?? fallback;
}

String? _stringOrNullFrom(List<Map<String, Object?>> maps, List<String> keys) {
  final Object? raw = _firstValue(maps, keys);
  return _nonEmpty(raw);
}

int? _intOrNullFrom(List<Map<String, Object?>> maps, List<String> keys) {
  for (final Map<String, Object?> map in maps) {
    for (final String key in keys) {
      if (!map.containsKey(key)) {
        continue;
      }
      final Object? raw = map[key];
      if (raw is int) {
        return raw;
      }
      if (raw is num) {
        return raw.toInt();
      }
      final int? parsed = int.tryParse(raw?.toString() ?? '');
      if (parsed != null) {
        return parsed;
      }
    }
  }
  return null;
}

bool _boolFrom(
  List<Map<String, Object?>> maps,
  List<String> keys, {
  bool fallback = false,
}) {
  final Object? raw = _firstValue(maps, keys);
  if (raw == null) {
    return fallback;
  }
  if (raw is bool) {
    return raw;
  }
  final String normalized = raw.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return fallback;
}

DateTime? _dateTimeFrom(List<Map<String, Object?>> maps, List<String> keys) {
  final Object? raw = _firstValue(maps, keys);
  if (raw == null) {
    return null;
  }
  if (raw is DateTime) {
    return raw.toUtc();
  }
  return DateTime.tryParse(raw.toString())?.toUtc();
}

List<String> _stringsFrom(Object? value) {
  if (value == null) {
    return const <String>[];
  }
  if (value is List || value is List<Object?>) {
    return _listOrEmpty(
      value,
      label: 'string list',
    ).map(_nonEmpty).whereType<String>().toList(growable: false);
  }
  final String? single = _nonEmpty(value);
  return single == null ? const <String>[] : <String>[single];
}

List<String> _mergeStrings(List<List<String>> groups) {
  final Set<String> seen = <String>{};
  final List<String> values = <String>[];
  for (final List<String> group in groups) {
    for (final String item in group) {
      if (seen.add(item)) {
        values.add(item);
      }
    }
  }
  return values;
}

String? _nonEmpty(Object? value) {
  if (value == null) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}

String _normalized(Object? value) {
  return value.toString().trim().toLowerCase().replaceAll(
    RegExp(r'[\s_\-]+'),
    '',
  );
}
