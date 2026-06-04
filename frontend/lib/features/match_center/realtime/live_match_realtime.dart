import 'dart:async';

import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';

enum LiveMatchRealtimeConnection { connecting, live, degraded, closed }

class LiveMatchRealtimeState {
  const LiveMatchRealtimeState({
    required this.snapshot,
    required this.connection,
    required this.hasBackendSnapshotTruth,
    this.message,
  });

  final LiveMatchSnapshot snapshot;
  final LiveMatchRealtimeConnection connection;
  final bool hasBackendSnapshotTruth;
  final String? message;

  bool get isUsable =>
      hasBackendSnapshotTruth && connection == LiveMatchRealtimeConnection.live;
}

class LiveMatchRealtimeReducer {
  const LiveMatchRealtimeReducer();

  Stream<LiveMatchRealtimeState> bind({
    required LiveMatchSnapshot seed,
    required Stream<Map<String, Object?>> backendPayloads,
    CompetitionSummary? competition,
  }) async* {
    LiveMatchSnapshot current = _pendingLiveMatchSnapshot(seed);
    bool hasConfirmedBackendSnapshotTruth = false;
    yield LiveMatchRealtimeState(
      snapshot: current,
      connection: LiveMatchRealtimeConnection.connecting,
      hasBackendSnapshotTruth: false,
    );
    try {
      await for (final Map<String, Object?> payload in backendPayloads) {
        hasConfirmedBackendSnapshotTruth =
            hasConfirmedBackendSnapshotTruth ||
            _hasBackendSnapshotTruthPayload(payload);
        current = mergeLiveMatchSnapshotPayload(
          current,
          payload,
          competition: competition,
        );
        yield LiveMatchRealtimeState(
          snapshot: current,
          connection: LiveMatchRealtimeConnection.live,
          hasBackendSnapshotTruth: hasConfirmedBackendSnapshotTruth,
        );
      }
      yield LiveMatchRealtimeState(
        snapshot: current,
        connection: LiveMatchRealtimeConnection.closed,
        hasBackendSnapshotTruth: false,
      );
    } catch (error) {
      yield LiveMatchRealtimeState(
        snapshot: current,
        connection: LiveMatchRealtimeConnection.degraded,
        hasBackendSnapshotTruth: false,
        message: error.toString(),
      );
    }
  }
}

bool _hasBackendSnapshotTruthPayload(Map<String, Object?> payload) {
  final Object? score = payload['score'] ?? payload['scoreboard'];
  final Map<dynamic, dynamic>? scoreMap = score is Map ? score : null;
  final bool hasHomeScore =
      payload['home_score'] != null ||
      payload['homeScore'] != null ||
      _scoreValue(scoreMap, 'home') != null;
  final bool hasAwayScore =
      payload['away_score'] != null ||
      payload['awayScore'] != null ||
      _scoreValue(scoreMap, 'away') != null;
  final bool hasClock =
      payload['minute'] != null ||
      payload['current_minute'] != null ||
      payload['currentMinute'] != null ||
      payload['clock_minute'] != null ||
      payload['clockMinute'] != null;
  return hasClock && hasHomeScore && hasAwayScore;
}

Object? _scoreValue(Map<dynamic, dynamic>? scoreMap, String side) {
  final Object? value = scoreMap?[side];
  if (value is Map) {
    return value['score'] ?? value['goals'] ?? value['value'];
  }
  return value;
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
    standardHighlightExpiresAt: seed.standardHighlightExpiresAt,
    premiumHighlightExpiresAt: seed.premiumHighlightExpiresAt,
  );
}

class LiveCommentaryRealtimeReducer {
  const LiveCommentaryRealtimeReducer();

  Stream<List<LiveMatchEvent>> bind({
    required List<LiveMatchEvent> seed,
    required Stream<List<LiveMatchEvent>> backendEvents,
  }) async* {
    List<LiveMatchEvent> current = seed;
    yield current;
    await for (final List<LiveMatchEvent> events in backendEvents) {
      current = _merge(current, events);
      yield current;
    }
  }

  List<LiveMatchEvent> _merge(
    List<LiveMatchEvent> current,
    List<LiveMatchEvent> incoming,
  ) {
    final Map<String, LiveMatchEvent> merged = <String, LiveMatchEvent>{
      for (final LiveMatchEvent event in current) _key(event): event,
    };
    for (final LiveMatchEvent event in incoming) {
      merged[_key(event)] = event;
    }
    final List<LiveMatchEvent> events = merged.values.toList(growable: false);
    events.sort((LiveMatchEvent a, LiveMatchEvent b) {
      final int minuteCompare = a.minute.compareTo(b.minute);
      return minuteCompare == 0 ? a.title.compareTo(b.title) : minuteCompare;
    });
    return events;
  }

  String _key(LiveMatchEvent event) {
    return '${event.minute}|${event.type.name}|${event.team}|${event.title}|${event.detail}';
  }
}
