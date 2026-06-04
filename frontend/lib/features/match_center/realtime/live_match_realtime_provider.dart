import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'live_match_realtime_models.dart';

typedef LiveMatchRealtimeSocketFactory = WebSocketChannel Function(Uri uri);

final Provider<BackendLiveMatchRealtimeProvider>
backendLiveMatchRealtimeProvider = Provider<BackendLiveMatchRealtimeProvider>((
  Ref ref,
) {
  return BackendLiveMatchRealtimeProvider();
});

final backendLiveMatchRealtimeStreamProvider =
    StreamProvider.family<LiveMatchRealtimeFrame, LiveMatchRealtimeRequest>((
      Ref ref,
      LiveMatchRealtimeRequest request,
    ) {
      final BackendLiveMatchRealtimeProvider provider = ref.watch(
        backendLiveMatchRealtimeProvider,
      );
      return provider.watch(request);
    });

class BackendLiveMatchRealtimeProvider {
  BackendLiveMatchRealtimeProvider({
    LiveMatchRealtimeSocketFactory? socketFactory,
  }) : _socketFactory = socketFactory ?? WebSocketChannel.connect;

  final LiveMatchRealtimeSocketFactory _socketFactory;

  Stream<LiveMatchRealtimeFrame> watch(LiveMatchRealtimeRequest request) {
    return Stream<LiveMatchRealtimeFrame>.multi((
      MultiStreamController<LiveMatchRealtimeFrame> controller,
    ) {
      LiveMatchSnapshot current = _pendingLiveMatchSnapshot(request.seed);
      final List<WebSocketChannel> channels = <WebSocketChannel>[];
      final List<StreamSubscription<dynamic>> subscriptions =
          <StreamSubscription<dynamic>>[];
      bool cancelled = false;
      bool hasConfirmedBackendSnapshotTruth = false;

      void emit(
        LiveMatchRealtimeStatus status,
        LiveMatchRealtimeSource source, {
        bool? hasBackendSnapshotTruth,
        LiveMatchRealtimeIssue? issue,
      }) {
        if (cancelled) {
          return;
        }
        controller.add(
          LiveMatchRealtimeFrame.fromSnapshot(
            snapshot: current,
            status: status,
            source: source,
            hasBackendSnapshotTruth:
                hasBackendSnapshotTruth ?? hasConfirmedBackendSnapshotTruth,
            issue: issue,
          ),
        );
      }

      void handleMessage(Object? message, LiveMatchRealtimeSource source) {
        final LiveMatchRealtimePayloadResult result =
            LiveMatchRealtimePayloadMapper.decode(message, source: source);
        if (result.payload == null) {
          emit(result.status, source, issue: result.issue);
          return;
        }
        final bool hasBackendSnapshotTruth = _hasBackendSnapshotTruthPayload(
          result.payload!,
        );
        current = mergeLiveMatchSnapshotPayload(current, result.payload!);
        hasConfirmedBackendSnapshotTruth =
            hasConfirmedBackendSnapshotTruth || hasBackendSnapshotTruth;
        emit(
          result.status,
          source,
          hasBackendSnapshotTruth: hasConfirmedBackendSnapshotTruth,
        );
      }

      void bind(Uri uri, LiveMatchRealtimeSource source) {
        emit(LiveMatchRealtimeStatus.connecting, source);
        try {
          final WebSocketChannel channel = _socketFactory(uri);
          channels.add(channel);
          subscriptions.add(
            channel.stream.listen(
              (dynamic message) => handleMessage(message, source),
              onError: (Object error, StackTrace stackTrace) {
                emit(
                  LiveMatchRealtimeStatus.degraded,
                  source,
                  issue: LiveMatchRealtimeIssue(
                    code: 'websocket_error',
                    message: 'Live match websocket emitted an error.',
                    source: source,
                  ),
                );
              },
              onDone: () {
                emit(
                  LiveMatchRealtimeStatus.blocked,
                  source,
                  issue: LiveMatchRealtimeIssue(
                    code: 'websocket_closed',
                    message: 'Live match websocket closed.',
                    source: source,
                  ),
                );
              },
              cancelOnError: false,
            ),
          );
          unawaited(
            channel.ready.then(
              (_) => emit(
                LiveMatchRealtimeStatus.syncing,
                source,
                issue: LiveMatchRealtimeIssue(
                  code: 'awaiting_backend_snapshot',
                  message:
                      'Live match websocket connected; waiting for backend match frame.',
                  source: source,
                ),
              ),
              onError: (_) {
                emit(
                  LiveMatchRealtimeStatus.blocked,
                  source,
                  issue: LiveMatchRealtimeIssue(
                    code: 'websocket_open_failed',
                    message: 'Live match websocket could not be opened.',
                    source: source,
                  ),
                );
              },
            ),
          );
        } catch (_) {
          emit(
            LiveMatchRealtimeStatus.blocked,
            source,
            issue: LiveMatchRealtimeIssue(
              code: 'websocket_unavailable',
              message: 'Live match websocket could not be created.',
              source: source,
            ),
          );
        }
      }

      emit(LiveMatchRealtimeStatus.idle, LiveMatchRealtimeSource.seed);

      final Uri? snapshotWebSocketUri = request.snapshotWebSocketUri;
      if (snapshotWebSocketUri == null) {
        emit(
          LiveMatchRealtimeStatus.blocked,
          LiveMatchRealtimeSource.snapshotWebSocket,
          issue: const LiveMatchRealtimeIssue(
            code: 'missing_snapshot_websocket',
            message: 'Live match snapshot websocket endpoint is missing.',
            source: LiveMatchRealtimeSource.snapshotWebSocket,
          ),
        );
      } else {
        bind(snapshotWebSocketUri, LiveMatchRealtimeSource.snapshotWebSocket);
      }

      final Uri? commentaryWebSocketUri = request.commentaryWebSocketUri;
      if (commentaryWebSocketUri != null &&
          commentaryWebSocketUri != snapshotWebSocketUri) {
        bind(
          commentaryWebSocketUri,
          LiveMatchRealtimeSource.commentaryWebSocket,
        );
      }

      controller.onCancel = () async {
        cancelled = true;
        for (final StreamSubscription<dynamic> subscription in subscriptions) {
          await subscription.cancel();
        }
        for (final WebSocketChannel channel in channels) {
          await channel.sink.close();
        }
      };
    });
  }
}

LiveMatchSnapshot _pendingLiveMatchSnapshot(LiveMatchSnapshot seed) {
  return LiveMatchSnapshot(
    matchId: seed.matchId,
    homeTeam: seed.homeTeam,
    awayTeam: seed.awayTeam,
    homeScore: 0,
    awayScore: 0,
    minute: 0,
    phase: LiveMatchPhase.preMatch,
    momentum: const <int>[],
    commentary: const <LiveMatchEvent>[],
    homeLineup: const <LiveMatchLineupPlayer>[],
    awayLineup: const <LiveMatchLineupPlayer>[],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    highlightsAvailable: false,
    keyMomentsAvailable: false,
    halftimeAnalyticsAvailable: false,
    standardHighlightExpiresAt: seed.standardHighlightExpiresAt,
    premiumHighlightExpiresAt: seed.premiumHighlightExpiresAt,
  );
}

class LiveMatchRealtimePayloadResult {
  const LiveMatchRealtimePayloadResult._({
    required this.status,
    this.payload,
    this.issue,
  });

  factory LiveMatchRealtimePayloadResult.payload(
    Map<String, Object?> payload, {
    LiveMatchRealtimeStatus status = LiveMatchRealtimeStatus.live,
  }) {
    return LiveMatchRealtimePayloadResult._(status: status, payload: payload);
  }

  factory LiveMatchRealtimePayloadResult.status({
    required LiveMatchRealtimeStatus status,
    required LiveMatchRealtimeSource source,
    String? message,
  }) {
    return LiveMatchRealtimePayloadResult._(
      status: status,
      issue:
          message == null
              ? null
              : LiveMatchRealtimeIssue(
                code: 'websocket_${_normalized(status.name)}',
                message: message,
                source: source,
              ),
    );
  }

  factory LiveMatchRealtimePayloadResult.degraded({
    required String code,
    required String message,
    required LiveMatchRealtimeSource source,
  }) {
    return LiveMatchRealtimePayloadResult._(
      status: LiveMatchRealtimeStatus.degraded,
      issue: LiveMatchRealtimeIssue(
        code: code,
        message: message,
        source: source,
      ),
    );
  }

  factory LiveMatchRealtimePayloadResult.blocked({
    required String code,
    required String message,
    required LiveMatchRealtimeSource source,
  }) {
    return LiveMatchRealtimePayloadResult._(
      status: LiveMatchRealtimeStatus.blocked,
      issue: LiveMatchRealtimeIssue(
        code: code,
        message: message,
        source: source,
      ),
    );
  }

  final LiveMatchRealtimeStatus status;
  final Map<String, Object?>? payload;
  final LiveMatchRealtimeIssue? issue;
}

class LiveMatchRealtimePayloadMapper {
  const LiveMatchRealtimePayloadMapper._();

  static LiveMatchRealtimePayloadResult decode(
    Object? message, {
    required LiveMatchRealtimeSource source,
  }) {
    final Object? decoded = _decodeMessage(message);
    if (decoded == null) {
      return LiveMatchRealtimePayloadResult.degraded(
        code: 'invalid_websocket_message',
        message: 'Live match websocket message was empty or invalid.',
        source: source,
      );
    }

    final LiveMatchRealtimePayloadResult? fromValue = _payloadFromValue(
      decoded,
      source: source,
      fallbackMinute: null,
    );
    if (fromValue != null) {
      return fromValue;
    }

    return LiveMatchRealtimePayloadResult.degraded(
      code: 'missing_websocket_payload',
      message: 'Live match websocket message did not include backend payload.',
      source: source,
    );
  }
}

LiveMatchRealtimePayloadResult? _payloadFromValue(
  Object? value, {
  required LiveMatchRealtimeSource source,
  required int? fallbackMinute,
}) {
  if (value is List) {
    final List<Object?> events = _eventList(value, fallbackMinute);
    if (events.isEmpty) {
      return LiveMatchRealtimePayloadResult.degraded(
        code: 'missing_websocket_payload',
        message: 'Live match websocket event list did not include payloads.',
        source: source,
      );
    }
    return LiveMatchRealtimePayloadResult.payload(<String, Object?>{
      'events': events,
    });
  }

  final Map<String, Object?>? map = _stringMap(value);
  if (map == null) {
    return null;
  }

  final LiveMatchRealtimePayloadResult? blocked = _blockedStatus(map, source);
  if (blocked != null) {
    return blocked;
  }

  final int? rootMinute = _minuteFromMap(map) ?? fallbackMinute;
  final Object? nested = _firstValue(map, const <String>[
    'payload',
    'data',
    'snapshot',
    'live_match_snapshot',
    'liveMatchSnapshot',
    'match',
  ]);
  if (nested != null) {
    final LiveMatchRealtimePayloadResult? nestedResult = _payloadFromValue(
      nested,
      source: source,
      fallbackMinute: rootMinute,
    );
    if (nestedResult != null) {
      return nestedResult;
    }
  }

  final Object? event = _firstValue(map, const <String>[
    'event',
    'commentary_event',
    'commentaryEvent',
  ]);
  if (event != null) {
    final List<Object?> events = _eventList(<Object?>[event], rootMinute);
    if (events.isNotEmpty) {
      return LiveMatchRealtimePayloadResult.payload(<String, Object?>{
        'events': events,
      });
    }
  }

  if (_looksLikeEvent(map) && !_hasSnapshotPayloadSignal(map)) {
    final Map<String, Object?>? eventPayload = _eventMap(map, rootMinute);
    if (eventPayload == null) {
      return LiveMatchRealtimePayloadResult.degraded(
        code: 'missing_event_minute',
        message: 'Live match commentary payload did not include a clock.',
        source: source,
      );
    }
    return LiveMatchRealtimePayloadResult.payload(<String, Object?>{
      'events': <Object?>[eventPayload],
    });
  }

  final LiveMatchRealtimePayloadResult? statusOnly = _statusOnlyResult(
    map,
    source,
  );
  if (statusOnly != null) {
    return statusOnly;
  }

  if (_looksLikeLivePayload(map)) {
    final Map<String, Object?> sanitized = _sanitizeLivePayload(map);
    if (_hasMergeableTruth(sanitized)) {
      return LiveMatchRealtimePayloadResult.payload(
        sanitized,
        status:
            _realtimeStatusFromMap(map) ??
            _realtimeStatusFromMap(sanitized) ??
            LiveMatchRealtimeStatus.live,
      );
    }
  }

  return null;
}

LiveMatchRealtimePayloadResult? _statusOnlyResult(
  Map<String, Object?> map,
  LiveMatchRealtimeSource source,
) {
  final LiveMatchRealtimeStatus? status = _realtimeStatusFromMap(map);
  if (status == null || _hasMatchTruthBeyondConnectionStatus(map)) {
    return null;
  }
  return LiveMatchRealtimePayloadResult.status(
    status: status,
    source: source,
    message: _firstString(map, const <String>[
      'message',
      'detail',
      'reason',
      'error',
    ]),
  );
}

LiveMatchRealtimeStatus? _realtimeStatusFromMap(Map<String, Object?> map) {
  final String normalized = _normalized(
    _firstString(map, const <String>[
          'status',
          'state',
          'connection_status',
          'connectionStatus',
        ]) ??
        '',
  );
  switch (normalized) {
    case 'idle':
    case 'seed':
      return LiveMatchRealtimeStatus.idle;
    case 'connecting':
    case 'opening':
      return LiveMatchRealtimeStatus.connecting;
    case 'syncing':
    case 'sync_start':
    case 'sync_started':
      return LiveMatchRealtimeStatus.syncing;
    case 'live':
    case 'connected':
      return LiveMatchRealtimeStatus.live;
    case 'confirmed':
    case 'confirmation_wait':
    case 'sync_complete':
    case 'sync_completed':
      return LiveMatchRealtimeStatus.confirmed;
    case 'reconnecting':
    case 'retrying':
      return LiveMatchRealtimeStatus.reconnecting;
    case 'degraded':
    case 'delayed':
      return LiveMatchRealtimeStatus.degraded;
    case 'blocked':
    case 'forbidden':
    case 'unauthorized':
    case 'unauthenticated':
    case 'token_expired':
    case 'not_authorized':
    case 'permission_denied':
      return LiveMatchRealtimeStatus.blocked;
    case 'closed':
    case 'disconnected':
      return LiveMatchRealtimeStatus.closed;
    case 'error':
    case 'failed':
      return LiveMatchRealtimeStatus.error;
    default:
      return null;
  }
}

Object? _decodeMessage(Object? message) {
  if (message is List<int>) {
    return _decodeMessage(utf8.decode(message));
  }
  if (message is String) {
    final String trimmed = message.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    try {
      return jsonDecode(trimmed);
    } catch (_) {
      return null;
    }
  }
  return message;
}

Map<String, Object?>? _stringMap(Object? value) {
  if (value is! Map) {
    return null;
  }
  return <String, Object?>{
    for (final MapEntry<dynamic, dynamic> entry in value.entries)
      entry.key.toString(): entry.value,
  };
}

LiveMatchRealtimePayloadResult? _blockedStatus(
  Map<String, Object?> map,
  LiveMatchRealtimeSource source,
) {
  final String status = _normalized(
    _firstString(map, const <String>[
          'status',
          'state',
          'connection_status',
          'connectionStatus',
        ]) ??
        '',
  );
  final String type = _normalized(
    _firstString(map, const <String>['type', 'kind', 'event_type']) ?? '',
  );
  final Set<String> blockers = <String>{
    'blocked',
    'forbidden',
    'unauthorized',
    'unauthenticated',
    'token_expired',
    'not_authorized',
    'permission_denied',
  };
  if (!blockers.contains(status) && !blockers.contains(type)) {
    return null;
  }
  return LiveMatchRealtimePayloadResult.blocked(
    code: 'websocket_blocked',
    message:
        _firstString(map, const <String>[
          'reason',
          'message',
          'detail',
          'error',
        ]) ??
        'Live match websocket is blocked by backend state.',
    source: source,
  );
}

Map<String, Object?> _sanitizeLivePayload(Map<String, Object?> payload) {
  final Map<String, Object?> sanitized = Map<String, Object?>.from(payload);
  _normalizeScore(sanitized);
  final int? rootMinute = _minuteFromMap(sanitized);
  for (final String key in const <String>[
    'timeline_events',
    'timelineEvents',
    'timeline',
    'commentary',
    'events',
  ]) {
    final Object? raw = sanitized[key];
    if (raw == null) {
      continue;
    }
    final List<Object?> events = _eventList(raw, rootMinute);
    if (events.isEmpty) {
      sanitized.remove(key);
    } else {
      sanitized[key] = events;
    }
  }
  return sanitized;
}

void _normalizeScore(Map<String, Object?> payload) {
  final Map<String, Object?>? score = _stringMap(
    _firstValue(payload, const <String>['score', 'scoreboard', 'score_board']),
  );
  if (score == null) {
    return;
  }
  payload['home_score'] ??= _scoreSide(score, 'home');
  payload['away_score'] ??= _scoreSide(score, 'away');
}

Object? _scoreSide(Map<String, Object?> score, String side) {
  final Object? direct = score[side];
  if (direct is num || direct is String) {
    return direct;
  }
  final Map<String, Object?>? nested = _stringMap(direct);
  if (nested == null) {
    return null;
  }
  return _firstValue(nested, const <String>['score', 'goals', 'value']);
}

List<Object?> _eventList(Object? value, int? fallbackMinute) {
  if (value is! List) {
    return const <Object?>[];
  }
  final List<Object?> events = <Object?>[];
  for (final Object? item in value) {
    final Map<String, Object?>? event = _eventMap(item, fallbackMinute);
    if (event != null) {
      events.add(event);
    }
  }
  return List<Object?>.unmodifiable(events);
}

Map<String, Object?>? _eventMap(Object? value, int? fallbackMinute) {
  final Map<String, Object?>? event = _stringMap(value);
  if (event == null || !_looksLikeEvent(event)) {
    return null;
  }
  final String type = _normalized(
    _firstString(event, const <String>[
          'event_type',
          'eventType',
          'type',
          'kind',
        ]) ??
        '',
  );
  if (const <String>{
    'ping',
    'pong',
    'subscription_ack',
    'ack',
    'match_update',
    'snapshot',
    'events',
  }.contains(type)) {
    return null;
  }

  final int? minute = _minuteFromMap(event) ?? fallbackMinute;
  if (minute == null) {
    return null;
  }
  final String? text = _firstString(event, const <String>[
    'commentary',
    'description',
    'detail',
    'text',
    'title',
    'headline',
  ]);
  if (text == null) {
    return null;
  }
  return <String, Object?>{...event, 'minute': minute};
}

bool _looksLikeLivePayload(Map<String, Object?> map) {
  return const <String>{
    'match_id',
    'matchId',
    'id',
    'scoreboard',
    'score_board',
    'scoreBoard',
    'score',
    'home_score',
    'homeScore',
    'away_score',
    'awayScore',
    'home_team_name',
    'homeTeamName',
    'away_team_name',
    'awayTeamName',
    'minute',
    'current_minute',
    'currentMinute',
    'clock_minute',
    'clockMinute',
    'clock',
    'match_clock',
    'matchClock',
    'status',
    'phase',
    'period',
    'timeline_events',
    'timelineEvents',
    'timeline',
    'commentary',
    'events',
    'availability',
    'home_lineup',
    'homeLineup',
    'away_lineup',
    'awayLineup',
    'momentum',
    'stats',
    'live_intelligence',
    'liveIntelligence',
    'key_moments',
    'keyMoments',
    'highlights',
  }.any(map.containsKey);
}

bool _hasMatchTruthBeyondConnectionStatus(Map<String, Object?> map) {
  const Set<String> connectionOnlyKeys = <String>{
    'status',
    'state',
    'connection_status',
    'connectionStatus',
    'type',
    'kind',
    'event_type',
    'eventType',
    'message',
    'detail',
    'reason',
    'error',
  };
  return map.keys.any((String key) => !connectionOnlyKeys.contains(key));
}

bool _hasSnapshotPayloadSignal(Map<String, Object?> map) {
  return const <String>{
    'match_id',
    'matchId',
    'id',
    'scoreboard',
    'score_board',
    'scoreBoard',
    'score',
    'home_score',
    'homeScore',
    'away_score',
    'awayScore',
    'home_team_name',
    'homeTeamName',
    'away_team_name',
    'awayTeamName',
    'clock',
    'match_clock',
    'matchClock',
    'status',
    'phase',
    'period',
    'timeline_events',
    'timelineEvents',
    'timeline',
    'events',
    'availability',
    'home_lineup',
    'homeLineup',
    'away_lineup',
    'awayLineup',
    'momentum',
    'stats',
    'live_intelligence',
    'liveIntelligence',
    'key_moments',
    'keyMoments',
    'highlights',
  }.any(map.containsKey);
}

bool _looksLikeEvent(Map<String, Object?> map) {
  return const <String>{
    'event_type',
    'eventType',
    'commentary',
    'description',
    'detail',
    'text',
    'title',
    'headline',
    'player_name',
    'playerName',
    'team_name',
    'teamName',
  }.any(map.containsKey);
}

bool _hasMergeableTruth(Map<String, Object?> map) {
  return const <String>{
    'match_id',
    'matchId',
    'home_score',
    'homeScore',
    'away_score',
    'awayScore',
    'home_team_name',
    'homeTeamName',
    'away_team_name',
    'awayTeamName',
    'minute',
    'current_minute',
    'currentMinute',
    'clock_minute',
    'clockMinute',
    'clock',
    'match_clock',
    'matchClock',
    'status',
    'phase',
    'period',
    'timeline_events',
    'timelineEvents',
    'timeline',
    'commentary',
    'events',
    'availability',
    'home_lineup',
    'homeLineup',
    'away_lineup',
    'awayLineup',
    'momentum',
    'stats',
    'live_intelligence',
    'liveIntelligence',
    'key_moments',
    'keyMoments',
    'highlights',
  }.any(map.containsKey);
}

bool _hasBackendSnapshotTruthPayload(Map<String, Object?> payload) {
  final Map<String, Object?> normalized = Map<String, Object?>.from(payload);
  _normalizeScore(normalized);
  final bool hasClock = _minuteFromMap(normalized) != null;
  final bool hasHomeScore =
      _firstValue(normalized, const <String>['home_score', 'homeScore']) !=
      null;
  final bool hasAwayScore =
      _firstValue(normalized, const <String>['away_score', 'awayScore']) !=
      null;
  return hasClock && hasHomeScore && hasAwayScore;
}

Object? _firstValue(Map<String, Object?> map, List<String> keys) {
  for (final String key in keys) {
    if (map.containsKey(key)) {
      return map[key];
    }
  }
  return null;
}

String? _firstString(Map<String, Object?> map, List<String> keys) {
  for (final String key in keys) {
    final Object? value = map[key];
    final String text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return null;
}

int? _minuteFromMap(Map<String, Object?> map) {
  final Object? value = _firstValue(map, const <String>[
    'minute',
    'current_minute',
    'currentMinute',
    'clock_minute',
    'clockMinute',
    'elapsed_minute',
    'elapsedMinute',
  ]);
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  final String text = value?.toString().trim() ?? '';
  return text.isEmpty ? null : int.tryParse(text);
}

String _normalized(String value) {
  return value.trim().toLowerCase().replaceAll('-', '_');
}
