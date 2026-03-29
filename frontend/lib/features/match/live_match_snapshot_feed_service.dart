import 'dart:async';
import 'dart:convert';

import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/services/reliability/reliable_event_queue.dart';
import 'package:gte_frontend/services/reliability/reliable_websocket_manager.dart';

import 'live_match_session_service.dart';

abstract interface class LiveMatchSnapshotFeedService {
  Stream<LiveMatchSnapshot> watch({required LiveMatchSnapshot seed});
}

class HybridLiveMatchSnapshotFeedService
    implements LiveMatchSnapshotFeedService {
  HybridLiveMatchSnapshotFeedService({
    LiveMatchSessionService? sessionService,
  }) : _sessionService = sessionService ?? LiveMatchSessionService();

  final LiveMatchSessionService _sessionService;

  @override
  Stream<LiveMatchSnapshot> watch({required LiveMatchSnapshot seed}) {
    final String matchId = seed.matchId?.trim() ?? '';
    if (matchId.isEmpty) {
      return Stream<LiveMatchSnapshot>.value(seed);
    }
    return Stream<LiveMatchSnapshot>.multi((
      MultiStreamController<LiveMatchSnapshot> controller,
    ) {
      LiveMatchSnapshot current = seed;
      controller.add(current);

      StreamSubscription<dynamic>? subscription;
      ReliableWebSocketManager? manager;
      bool cancelled = false;

      () async {
        final session = await _sessionService.resolveSession(matchId);
        final Uri? socketUri =
            _sessionService.resolveWebSocketUri(session?.websocketPath);
        if (cancelled || session == null || socketUri == null) {
          await controller.close();
          return;
        }
        manager = ReliableWebSocketManager(
          socketUri: socketUri,
          onConnectionRestored: gteReliableEventQueue.markConnectionRestored,
        );
        subscription = manager!.messages.listen((dynamic message) {
          final LiveMatchSnapshot? next = _applyMessage(current, message);
          if (next == null) {
            return;
          }
          current = next;
          controller.add(current);
        }, onError: (_) {});
        manager!.connect();
      }();

      controller.onCancel = () async {
        cancelled = true;
        await subscription?.cancel();
        await manager?.dispose();
      };
    });
  }

  static LiveMatchSnapshot? _applyMessage(
    LiveMatchSnapshot current,
    dynamic message,
  ) {
    final Object? decoded = _decodeMessage(message);
    if (decoded is! Map) {
      return null;
    }
    final String kind = (decoded['kind'] ?? '').toString().trim().toLowerCase();
    if (kind == 'snapshot') {
      final Object? rawPayload = decoded['payload'];
      if (rawPayload is! Map) {
        return null;
      }
      final Map<Object?, Object?> payload = rawPayload;
      final Object? rawScore = payload['score'];
      final Map<Object?, Object?> score =
          rawScore is Map<Object?, Object?> ? rawScore : const <Object?, Object?>{};
      final int minute = _asInt(payload['current_minute']) ?? current.minute;
      final String status = (payload['status'] ?? '').toString().trim();
      return current.copyWith(
        homeScore: _asInt(score['home']) ?? current.homeScore,
        awayScore: _asInt(score['away']) ?? current.awayScore,
        minute: minute,
        phase: _phaseFor(status: status, minute: minute, fallback: current.phase),
        highlightsAvailable:
            current.highlightsAvailable || status.toLowerCase() == 'completed',
        keyMomentsAvailable: current.keyMomentsAvailable,
      );
    }
    if (kind == 'events') {
      final Object? rawPayload = decoded['payload'];
      if (rawPayload is! List) {
        return null;
      }
      final List<LiveMatchEvent> incoming = rawPayload
          .map((Object? value) => _eventFromPayload(value))
          .whereType<LiveMatchEvent>()
          .toList(growable: false);
      if (incoming.isEmpty) {
        return null;
      }
      final List<LiveMatchEvent> merged = _mergeEvents(
        current.commentary,
        incoming,
      );
      final LiveMatchEvent latest = incoming.last;
      final Map<Object?, Object?>? latestPayload = rawPayload.isNotEmpty &&
              rawPayload.last is Map<Object?, Object?>
          ? rawPayload.last as Map<Object?, Object?>
          : null;
      final bool hasHighlight = rawPayload.any((Object? value) {
        if (value is! Map) {
          return false;
        }
        return value['highlight_eligible'] == true ||
            value['highlightEligible'] == true;
      });
      return current.copyWith(
        homeScore: _asInt(latestPayload?['home_score']) ?? current.homeScore,
        awayScore: _asInt(latestPayload?['away_score']) ?? current.awayScore,
        minute: latest.minute > current.minute ? latest.minute : current.minute,
        commentary: merged,
        substitutions: merged
            .where((LiveMatchEvent item) => item.type == LiveMatchEventType.substitution)
            .toList(growable: false),
        cards: merged
            .where((LiveMatchEvent item) => item.type == LiveMatchEventType.card)
            .toList(growable: false),
        keyMomentsAvailable: current.keyMomentsAvailable || hasHighlight,
        highlightsAvailable: current.highlightsAvailable || hasHighlight,
      );
    }
    return null;
  }

  static LiveMatchEvent? _eventFromPayload(Object? value) {
    if (value is! Map) {
      return null;
    }
    final Map<Object?, Object?> payload = value;
    final int minute = _asInt(payload['minute']) ?? 0;
    final String eventTypeRaw =
        (payload['event_type'] ?? payload['eventType'] ?? payload['type'] ?? '')
            .toString();
    final LiveMatchEventType type = _eventTypeFromRaw(eventTypeRaw);
    final String team =
        (payload['team'] ?? payload['team_name'] ?? payload['teamName'] ?? '')
            .toString();
    final String detail =
        (payload['commentary'] ??
                payload['description'] ??
                _nestedValue(payload['metadata'], 'description') ??
                '')
            .toString()
            .trim();
    final String title = _titleFor(type: type, team: team);
    if (title.trim().isEmpty && detail.isEmpty) {
      return null;
    }
    return LiveMatchEvent(
      minute: minute,
      title: title,
      detail: detail.isEmpty ? title : detail,
      team: team,
      type: type,
      isKeyMoment: payload['highlight_eligible'] == true ||
          payload['highlightEligible'] == true ||
          type == LiveMatchEventType.goal,
    );
  }

  static Object? _decodeMessage(dynamic message) {
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

  static Object? _nestedValue(Object? value, String key) {
    if (value is Map) {
      return value[key];
    }
    return null;
  }

  static int? _asInt(Object? value) {
    if (value is int) {
      return value;
    }
    if (value is double) {
      return value.round();
    }
    return int.tryParse(value?.toString() ?? '');
  }

  static LiveMatchPhase _phaseFor({
    required String status,
    required int minute,
    required LiveMatchPhase fallback,
  }) {
    final String normalized = status.trim().toLowerCase();
    if (normalized == 'completed' || normalized == 'full_time') {
      return LiveMatchPhase.fullTime;
    }
    if (normalized == 'halftime') {
      return LiveMatchPhase.halftime;
    }
    if (minute <= 0) {
      return fallback;
    }
    return minute < 46 ? LiveMatchPhase.firstHalf : LiveMatchPhase.secondHalf;
  }

  static LiveMatchEventType _eventTypeFromRaw(String raw) {
    switch (raw.trim().toLowerCase()) {
      case 'goal':
      case 'penalty_goal':
      case 'penalty_scored':
        return LiveMatchEventType.goal;
      case 'card':
      case 'yellow_card':
      case 'red_card':
        return LiveMatchEventType.card;
      case 'substitution':
        return LiveMatchEventType.substitution;
      default:
        return LiveMatchEventType.incident;
    }
  }

  static String _titleFor({
    required LiveMatchEventType type,
    required String team,
  }) {
    final String resolvedTeam = team.trim();
    switch (type) {
      case LiveMatchEventType.goal:
        return resolvedTeam.isEmpty ? 'Goal' : 'Goal for $resolvedTeam';
      case LiveMatchEventType.card:
        return resolvedTeam.isEmpty ? 'Card shown' : 'Card for $resolvedTeam';
      case LiveMatchEventType.substitution:
        return resolvedTeam.isEmpty
            ? 'Substitution'
            : 'Substitution for $resolvedTeam';
      case LiveMatchEventType.incident:
        return resolvedTeam.isEmpty ? 'Live incident' : '$resolvedTeam chance';
    }
  }

  static List<LiveMatchEvent> _mergeEvents(
    List<LiveMatchEvent> current,
    List<LiveMatchEvent> incoming,
  ) {
    final Map<String, LiveMatchEvent> merged = <String, LiveMatchEvent>{
      for (final LiveMatchEvent event in current) _eventKey(event): event,
    };
    for (final LiveMatchEvent event in incoming) {
      merged[_eventKey(event)] = event;
    }
    final List<LiveMatchEvent> values = merged.values.toList(growable: false);
    values.sort((LiveMatchEvent a, LiveMatchEvent b) {
      final int byMinute = a.minute.compareTo(b.minute);
      if (byMinute != 0) {
        return byMinute;
      }
      return a.title.compareTo(b.title);
    });
    return values;
  }

  static String _eventKey(LiveMatchEvent event) {
    return '${event.minute}|${event.type.name}|${event.team}|${event.title}|${event.detail}';
  }
}
