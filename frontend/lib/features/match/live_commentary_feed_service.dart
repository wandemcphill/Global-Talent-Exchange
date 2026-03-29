import 'dart:async';
import 'dart:convert';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/services/reliability/reliable_event_queue.dart';
import 'package:gte_frontend/services/reliability/reliable_websocket_manager.dart';

import 'live_match_session_service.dart';

abstract interface class LiveCommentaryFeedService {
  Stream<List<LiveMatchEvent>> watch({
    required String matchId,
    required List<LiveMatchEvent> seedEvents,
  });
}

class HybridLiveCommentaryFeedService implements LiveCommentaryFeedService {
  HybridLiveCommentaryFeedService({
    GteAppConfig? config,
    LiveCommentaryFeedService? fallback,
    LiveMatchSessionService? sessionService,
  }) : _config = config ?? GteAppConfig.fromEnvironment(),
       _sessionService = sessionService ?? LiveMatchSessionService(config: config),
        _fallback = fallback ?? const StaticLiveCommentaryFeedService();

  final GteAppConfig _config;
  final LiveMatchSessionService _sessionService;
  final LiveCommentaryFeedService _fallback;

  @override
  Stream<List<LiveMatchEvent>> watch({
    required String matchId,
    required List<LiveMatchEvent> seedEvents,
  }) {
    if (_config.backendMode == GteBackendMode.fixture) {
      return _fallback.watch(matchId: matchId, seedEvents: seedEvents);
    }
    return Stream<List<LiveMatchEvent>>.multi((
      MultiStreamController<List<LiveMatchEvent>> controller,
    ) {
      controller.add(List<LiveMatchEvent>.unmodifiable(_sortEvents(seedEvents)));

      StreamSubscription<List<LiveMatchEvent>>? relaySubscription;

      () async {
        final session = await _sessionService.resolveSession(matchId);
        final Uri? socketUri = _sessionService.resolveWebSocketUri(
          session?.commentaryWebsocketPath,
        );
        if (socketUri == null) {
          relaySubscription = _fallback
              .watch(matchId: matchId, seedEvents: seedEvents)
              .listen(
                (List<LiveMatchEvent> events) => controller.add(events),
                onError: (_) {},
              );
          return;
        }
        relaySubscription = WebSocketLiveCommentaryFeedService(
          socketUri: socketUri,
        ).watch(matchId: matchId, seedEvents: seedEvents).listen(
              (List<LiveMatchEvent> events) => controller.add(events),
              onError: (_) {},
            );
      }();

      controller.onCancel = () async {
        await relaySubscription?.cancel();
      };
    });
  }
}

class StaticLiveCommentaryFeedService implements LiveCommentaryFeedService {
  const StaticLiveCommentaryFeedService();

  @override
  Stream<List<LiveMatchEvent>> watch({
    required String matchId,
    required List<LiveMatchEvent> seedEvents,
  }) {
    return Stream<List<LiveMatchEvent>>.value(
      List<LiveMatchEvent>.unmodifiable(_sortEvents(seedEvents)),
    );
  }
}

class WebSocketLiveCommentaryFeedService implements LiveCommentaryFeedService {
  WebSocketLiveCommentaryFeedService({
    required this.socketUri,
    this.managerFactory,
  });

  final Uri socketUri;
  final ReliableWebSocketManager Function(Uri socketUri)? managerFactory;

  @override
  Stream<List<LiveMatchEvent>> watch({
    required String matchId,
    required List<LiveMatchEvent> seedEvents,
  }) {
    return Stream<List<LiveMatchEvent>>.multi((
      MultiStreamController<List<LiveMatchEvent>> controller,
    ) {
      List<LiveMatchEvent> merged = _sortEvents(seedEvents);
      controller.add(List<LiveMatchEvent>.unmodifiable(merged));

      StreamSubscription<dynamic>? subscription;
      final ReliableWebSocketManager manager =
          managerFactory?.call(socketUri) ??
          ReliableWebSocketManager(
            socketUri: socketUri,
            onConnectionRestored: gteReliableEventQueue.markConnectionRestored,
          );

      subscription = manager.messages.listen((dynamic message) {
        final int fallbackMinute =
            merged.isEmpty ? 0 : merged.last.minute.clamp(0, 120);
        final List<LiveMatchEvent> incoming = _parseMessage(
          message,
          fallbackMinute: fallbackMinute,
        );
        if (incoming.isEmpty) {
          return;
        }
        merged = _mergeEvents(merged, incoming);
        controller.add(List<LiveMatchEvent>.unmodifiable(merged));
      }, onError: (_) {});
      manager.connect();

      controller.onCancel = () async {
        await subscription?.cancel();
        await manager.dispose();
      };
    });
  }

  static List<LiveMatchEvent> _parseMessage(
    dynamic message, {
    required int fallbackMinute,
  }) {
    final Object? decoded = _decodeMessage(message);
    if (decoded == null) {
      return const <LiveMatchEvent>[];
    }
    if (decoded is List) {
      return decoded
          .map(
            (Object? value) =>
                _parseEventValue(value, fallbackMinute: fallbackMinute),
          )
          .whereType<LiveMatchEvent>()
          .toList(growable: false);
    }
    if (decoded is Map) {
      final List<Object?>? embeddedEvents =
          _listValue(decoded, 'events') ?? _listValue(decoded, 'commentary');
      if (embeddedEvents != null) {
        return embeddedEvents
            .map(
              (Object? value) =>
                  _parseEventValue(value, fallbackMinute: fallbackMinute),
            )
            .whereType<LiveMatchEvent>()
            .toList(growable: false);
      }
    }
    final LiveMatchEvent? event = _parseEventValue(
      decoded,
      fallbackMinute: fallbackMinute,
    );
    return event == null ? const <LiveMatchEvent>[] : <LiveMatchEvent>[event];
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
        return trimmed;
      }
    }
    return message;
  }

  static LiveMatchEvent? _parseEventValue(
    Object? value, {
    required int fallbackMinute,
  }) {
    if (value is String) {
      final String detail = value.trim();
      if (detail.isEmpty) {
        return null;
      }
      return LiveMatchEvent(
        minute: fallbackMinute,
        title: 'Live commentary',
        detail: detail,
        team: '',
        type: LiveMatchEventType.incident,
      );
    }
    if (value is! Map) {
      return null;
    }

    final Map<Object?, Object?> raw = value;
    final Object? nested =
        raw['data'] is Map
            ? raw['data']
            : raw['event'] is Map
            ? raw['event']
            : null;
    final Map<Object?, Object?> payload =
        nested is Map<Object?, Object?> ? nested : raw;
    final List<Object?>? events =
        _listValue(payload, 'events') ?? _listValue(payload, 'commentary');
    if (events != null) {
      return null;
    }

    final String detail =
        _stringValue(payload, 'detail') ??
        _stringValue(payload, 'description') ??
        _stringValue(payload, 'commentary') ??
        '';
    final String eventTypeRaw =
        _stringValue(payload, 'event_type') ??
        _stringValue(payload, 'eventType') ??
        _stringValue(payload, 'type') ??
        '';
    final LiveMatchEventType type = _eventTypeFromRaw(eventTypeRaw);
    final String team =
        _stringValue(payload, 'team_name') ??
        _stringValue(payload, 'teamName') ??
        _stringValue(payload, 'team') ??
        '';
    final int minute =
        _intValue(payload, 'minute') ??
        _intValue(payload, 'clock_minute') ??
        _intValue(payload, 'clockMinute') ??
        fallbackMinute;
    final bool isKeyMoment =
        _boolValue(payload, 'is_key_moment') ??
        _boolValue(payload, 'isKeyMoment') ??
        type == LiveMatchEventType.goal;
    final String title =
        _stringValue(payload, 'title') ??
        _stringValue(payload, 'headline') ??
        _defaultTitleFor(type: type, team: team);

    if (title.trim().isEmpty && detail.trim().isEmpty) {
      return null;
    }
    return LiveMatchEvent(
      minute: minute,
      title: title.trim().isEmpty ? 'Live commentary' : title.trim(),
      detail: detail.trim().isEmpty ? title.trim() : detail.trim(),
      team: team.trim(),
      type: type,
      isKeyMoment: isKeyMoment,
    );
  }

  static List<LiveMatchEvent> _mergeEvents(
    List<LiveMatchEvent> existing,
    List<LiveMatchEvent> incoming,
  ) {
    final Map<String, LiveMatchEvent> byKey = <String, LiveMatchEvent>{
      for (final LiveMatchEvent event in existing) _eventKey(event): event,
    };
    for (final LiveMatchEvent event in incoming) {
      byKey[_eventKey(event)] = event;
    }
    return _sortEvents(byKey.values);
  }

  static List<Object?>? _listValue(Map<Object?, Object?> payload, String key) {
    final Object? value = payload[key];
    if (value is! List) {
      return null;
    }
    return value.cast<Object?>();
  }

  static String? _stringValue(Map<Object?, Object?> payload, String key) {
    final Object? value = payload[key];
    if (value == null) {
      return null;
    }
    final String text = value.toString().trim();
    return text.isEmpty ? null : text;
  }

  static int? _intValue(Map<Object?, Object?> payload, String key) {
    final Object? value = payload[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    if (value is String) {
      return int.tryParse(value.trim());
    }
    return null;
  }

  static bool? _boolValue(Map<Object?, Object?> payload, String key) {
    final Object? value = payload[key];
    if (value is bool) {
      return value;
    }
    if (value is String) {
      final String normalized = value.trim().toLowerCase();
      if (normalized == 'true') {
        return true;
      }
      if (normalized == 'false') {
        return false;
      }
    }
    return null;
  }

  static LiveMatchEventType _eventTypeFromRaw(String raw) {
    switch (raw.trim().toLowerCase()) {
      case 'goal':
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

  static String _defaultTitleFor({
    required LiveMatchEventType type,
    required String team,
  }) {
    final String prefix = team.trim().isEmpty ? '' : '$team ';
    switch (type) {
      case LiveMatchEventType.goal:
        return '${prefix}goal'.trim();
      case LiveMatchEventType.card:
        return '${prefix}card'.trim();
      case LiveMatchEventType.substitution:
        return '${prefix}substitution'.trim();
      case LiveMatchEventType.incident:
        return prefix.isEmpty ? 'Live commentary' : '${prefix}moment'.trim();
    }
  }
}

String _eventKey(LiveMatchEvent event) {
  return <Object>[
    event.minute,
    event.type.name,
    event.team.trim().toLowerCase(),
    event.title.trim().toLowerCase(),
    event.detail.trim().toLowerCase(),
    event.isKeyMoment,
  ].join('|');
}

List<LiveMatchEvent> _sortEvents(Iterable<LiveMatchEvent> events) {
  final List<LiveMatchEvent> sorted = events.toList(growable: false);
  sorted.sort((LiveMatchEvent left, LiveMatchEvent right) {
    final int minuteCompare = left.minute.compareTo(right.minute);
    if (minuteCompare != 0) {
      return minuteCompare;
    }
    final int titleCompare = left.title.compareTo(right.title);
    if (titleCompare != 0) {
      return titleCompare;
    }
    return left.detail.compareTo(right.detail);
  });
  return sorted;
}
