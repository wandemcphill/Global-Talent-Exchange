import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../data/gte_api_repository.dart';
import '../../data/gte_http_transport.dart';

class TrackEventRequest {
  const TrackEventRequest({
    required this.clipId,
    required this.eventType,
    this.userId,
    this.watchTimeMs,
    this.videoLengthMs,
    this.device,
    this.country,
    this.referrer,
    this.contentType,
    this.formatKey,
    this.clipEventType,
    this.teamName,
    this.tags = const <String>[],
  });

  final String clipId;
  final String eventType;
  final String? userId;
  final int? watchTimeMs;
  final int? videoLengthMs;
  final String? device;
  final String? country;
  final String? referrer;
  final String? contentType;
  final String? formatKey;
  final String? clipEventType;
  final String? teamName;
  final List<String> tags;
}

class QueuedEvent {
  const QueuedEvent({
    required this.eventId,
    required this.clipId,
    required this.sessionId,
    required this.timestamp,
    required this.eventType,
    required this.metadata,
    this.userId,
    this.watchTimeMs,
    this.videoLengthMs,
    this.retryCount = 0,
  });

  factory QueuedEvent.fromJson(Map<String, Object?> json) {
    return QueuedEvent(
      eventId: (json['event_id'] ?? '').toString(),
      clipId: (json['clip_id'] ?? '').toString(),
      userId: _stringOrNull(json['user_id']),
      sessionId: (json['session_id'] ?? '').toString(),
      timestamp: DateTime.parse((json['timestamp'] ?? '').toString()).toUtc(),
      eventType: (json['event_type'] ?? '').toString(),
      watchTimeMs: _intOrNull(json['watch_time_ms']),
      videoLengthMs: _intOrNull(json['video_length_ms']),
      metadata: EventMetadata.fromJson(
        Map<String, Object?>.from(
          (json['metadata'] as Map<Object?, Object?>?) ??
              const <Object?, Object?>{},
        ),
      ),
      retryCount: _intOrNull(json['retry_count']) ?? 0,
    );
  }

  final String eventId;
  final String clipId;
  final String? userId;
  final String sessionId;
  final DateTime timestamp;
  final String eventType;
  final int? watchTimeMs;
  final int? videoLengthMs;
  final EventMetadata metadata;
  final int retryCount;

  QueuedEvent copyWith({int? retryCount}) {
    return QueuedEvent(
      eventId: eventId,
      clipId: clipId,
      userId: userId,
      sessionId: sessionId,
      timestamp: timestamp,
      eventType: eventType,
      watchTimeMs: watchTimeMs,
      videoLengthMs: videoLengthMs,
      metadata: metadata,
      retryCount: retryCount ?? this.retryCount,
    );
  }

  Map<String, Object?> toStorageJson() {
    return <String, Object?>{
      'event_id': eventId,
      'clip_id': clipId,
      'user_id': userId,
      'session_id': sessionId,
      'timestamp': timestamp.toUtc().toIso8601String(),
      'event_type': eventType,
      'watch_time_ms': watchTimeMs,
      'video_length_ms': videoLengthMs,
      'metadata': metadata.toJson(),
      'retry_count': retryCount,
    };
  }

  Map<String, Object?> toApiJson() {
    return <String, Object?>{
      'event_id': eventId,
      'clip_id': clipId,
      'user_id': userId,
      'session_id': sessionId,
      'timestamp': timestamp.toUtc().toIso8601String(),
      'event_type': eventType,
      'watch_time_ms': watchTimeMs,
      'video_length_ms': videoLengthMs,
      'metadata': metadata.toJson(),
    };
  }
}

class EventMetadata {
  const EventMetadata({
    required this.device,
    required this.country,
    required this.referrer,
    this.contentType,
    this.formatKey,
    this.clipEventType,
    this.teamName,
    this.tags = const <String>[],
  });

  factory EventMetadata.fromJson(Map<String, Object?> json) {
    return EventMetadata(
      device: (json['device'] ?? '').toString(),
      country: (json['country'] ?? '').toString(),
      referrer: (json['referrer'] ?? '').toString(),
      contentType: _stringOrNull(json['content_type']),
      formatKey: _stringOrNull(json['format_key']),
      clipEventType: _stringOrNull(json['clip_event_type']),
      teamName: _stringOrNull(json['team_name']),
      tags: _stringList(json['tags']),
    );
  }

  final String device;
  final String country;
  final String referrer;
  final String? contentType;
  final String? formatKey;
  final String? clipEventType;
  final String? teamName;
  final List<String> tags;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'device': device,
      'country': country,
      'referrer': referrer,
      'content_type': contentType,
      'format_key': formatKey,
      'clip_event_type': clipEventType,
      'team_name': teamName,
      'tags': tags,
    };
  }
}

abstract class EventQueueStore {
  Future<List<QueuedEvent>> readQueue();

  Future<void> writeQueue(List<QueuedEvent> events);

  Future<String?> readSessionId();

  Future<void> writeSessionId(String sessionId);
}

class SharedPreferencesEventQueueStore implements EventQueueStore {
  SharedPreferencesEventQueueStore({
    SharedPreferences? preferences,
    this.queueKey = _defaultQueueKey,
    this.sessionIdKey = _defaultSessionIdKey,
  }) : _preferences = preferences;

  static const String _defaultQueueKey = 'gtex_action_pipeline_queue';
  static const String _defaultSessionIdKey = 'gtex_action_pipeline_session_id';

  SharedPreferences? _preferences;
  final String queueKey;
  final String sessionIdKey;

  Future<SharedPreferences> _prefs() async {
    _preferences ??= await SharedPreferences.getInstance();
    return _preferences!;
  }

  @override
  Future<List<QueuedEvent>> readQueue() async {
    final SharedPreferences prefs = await _prefs();
    final String raw = prefs.getString(queueKey) ?? '';
    if (raw.trim().isEmpty) {
      return const <QueuedEvent>[];
    }
    final Object? decoded = jsonDecode(raw);
    if (decoded is! List) {
      return const <QueuedEvent>[];
    }
    return decoded
        .whereType<Map>()
        .map(
          (Map<Object?, Object?> entry) =>
              QueuedEvent.fromJson(Map<String, Object?>.from(entry)),
        )
        .toList(growable: false);
  }

  @override
  Future<void> writeQueue(List<QueuedEvent> events) async {
    final SharedPreferences prefs = await _prefs();
    final String payload = jsonEncode(
      events.map((QueuedEvent event) => event.toStorageJson()).toList(),
    );
    await prefs.setString(queueKey, payload);
  }

  @override
  Future<String?> readSessionId() async {
    final SharedPreferences prefs = await _prefs();
    final String value = (prefs.getString(sessionIdKey) ?? '').trim();
    return value.isEmpty ? null : value;
  }

  @override
  Future<void> writeSessionId(String sessionId) async {
    final SharedPreferences prefs = await _prefs();
    await prefs.setString(sessionIdKey, sessionId);
  }
}

abstract class EventTransport {
  Future<void> postEvents(List<QueuedEvent> events);
}

class ClipEventsApiTransport implements EventTransport {
  ClipEventsApiTransport({
    required GteRepositoryConfig config,
    GteTransport? transport,
  }) : _config = config,
       _transport = transport ?? GteHttpTransport();

  static const String endpointPath = '/events/clip';

  final GteRepositoryConfig _config;
  final GteTransport _transport;

  @override
  Future<void> postEvents(List<QueuedEvent> events) async {
    final GteTransportResponse response = await _transport.send(
      GteTransportRequest(
        method: 'POST',
        uri: _config.uriFor(endpointPath),
        headers: const <String, String>{'Content-Type': 'application/json'},
        body: <String, Object?>{
          'events': events
              .map((QueuedEvent event) => event.toApiJson())
              .toList(growable: false),
        },
      ),
    );
    if (response.statusCode >= 400) {
      throw GteApiException(
        type: _errorType(response.statusCode),
        message: _errorMessage(response.body),
        statusCode: response.statusCode,
      );
    }
  }

  GteApiErrorType _errorType(int statusCode) {
    if (statusCode == 401 || statusCode == 403) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode == 422) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  String _errorMessage(Object? body) {
    if (body is Map<String, dynamic>) {
      final Object? detail = body['detail'] ?? body['message'];
      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }
    }
    if (body is String && body.trim().isNotEmpty) {
      return body;
    }
    return 'Clip event request failed.';
  }
}

class EventService {
  EventService({
    required EventTransport transport,
    required EventQueueStore store,
    Duration? batchWindow,
    Duration? retryBaseDelay,
    Duration? retryMaxDelay,
    int maxBatchSize = 50,
    String defaultCountry = 'unknown',
    String defaultReferrer = 'viral_feed',
    String defaultContentType = 'clip',
    DateTime Function()? now,
    String Function()? uuidGenerator,
    String Function()? deviceResolver,
  }) : _transport = transport,
       _store = store,
       batchWindow = batchWindow ?? const Duration(milliseconds: 300),
       retryBaseDelay = retryBaseDelay ?? const Duration(seconds: 1),
       retryMaxDelay = retryMaxDelay ?? const Duration(seconds: 30),
       _maxBatchSize = maxBatchSize,
       _defaultCountry = defaultCountry,
       _defaultReferrer = defaultReferrer,
       _defaultContentType = defaultContentType,
       _now = now ?? _defaultNow,
       _uuidGenerator = uuidGenerator ?? _generateUuid,
       _deviceResolver = deviceResolver ?? _defaultDevice;

  factory EventService.standard({
    String baseUrl = _defaultActionApiBaseUrl,
    GteTransport? transport,
    EventQueueStore? store,
    Duration? batchWindow,
    Duration? retryBaseDelay,
    Duration? retryMaxDelay,
  }) {
    return EventService(
      transport: ClipEventsApiTransport(
        config: GteRepositoryConfig(
          baseUrl: baseUrl,
          mode: GteBackendMode.live,
        ),
        transport: transport,
      ),
      store: store ?? SharedPreferencesEventQueueStore(),
      batchWindow: batchWindow,
      retryBaseDelay: retryBaseDelay,
      retryMaxDelay: retryMaxDelay,
    );
  }

  final EventTransport _transport;
  final EventQueueStore _store;
  final Duration batchWindow;
  final Duration retryBaseDelay;
  final Duration retryMaxDelay;
  final int _maxBatchSize;
  final String _defaultCountry;
  final String _defaultReferrer;
  final String _defaultContentType;
  final DateTime Function() _now;
  final String Function() _uuidGenerator;
  final String Function() _deviceResolver;

  final List<QueuedEvent> _queue = <QueuedEvent>[];
  bool _initialized = false;
  bool _isFlushing = false;
  Future<void>? _initializing;
  String? _sessionId;
  Timer? _flushTimer;
  Timer? _retryTimer;

  @visibleForTesting
  List<QueuedEvent> get queuedEvents => List<QueuedEvent>.unmodifiable(_queue);

  Future<void> trackEvent(TrackEventRequest request) async {
    await _ensureInitialized();
    final QueuedEvent event = QueuedEvent(
      eventId: _uuidGenerator(),
      clipId: request.clipId,
      userId: _trimmedOrNull(request.userId),
      sessionId: _sessionId!,
      timestamp: _now().toUtc(),
      eventType: request.eventType,
      watchTimeMs: request.watchTimeMs,
      videoLengthMs: request.videoLengthMs,
      metadata: EventMetadata(
        device: _trimmedOrFallback(request.device, _deviceResolver()),
        country: _trimmedOrFallback(request.country, _defaultCountry),
        referrer: _trimmedOrFallback(request.referrer, _defaultReferrer),
        contentType: _trimmedOrNull(request.contentType) ?? _defaultContentType,
        formatKey: _trimmedOrNull(request.formatKey),
        clipEventType: _trimmedOrNull(request.clipEventType),
        teamName: _trimmedOrNull(request.teamName),
        tags: request.tags
            .map((String value) => value.trim())
            .where((String value) => value.isNotEmpty)
            .toList(growable: false),
      ),
    );
    _queue.add(event);
    await _persistQueue();
    if (_queue.length >= _maxBatchSize) {
      _scheduleFlush(Duration.zero);
      return;
    }
    _scheduleFlush(batchWindow);
  }

  Future<void> flush({bool propagateError = false}) async {
    await _ensureInitialized();
    if (_isFlushing || _queue.isEmpty) {
      return;
    }
    _flushTimer?.cancel();
    _flushTimer = null;
    _retryTimer?.cancel();
    _retryTimer = null;

    _isFlushing = true;
    final List<QueuedEvent> batch = _queue
        .take(_maxBatchSize)
        .toList(growable: false);
    try {
      await _transport.postEvents(batch);
      _queue.removeRange(0, batch.length);
      await _persistQueue();
      if (_queue.isNotEmpty) {
        _scheduleFlush(Duration.zero);
      }
    } catch (error, stackTrace) {
      for (int index = 0; index < batch.length; index += 1) {
        _queue[index] = _queue[index].copyWith(
          retryCount: _queue[index].retryCount + 1,
        );
      }
      await _persistQueue();
      _scheduleRetry(_retryDelayFor(_queue.first.retryCount));
      if (propagateError) {
        _isFlushing = false;
        rethrow;
      }
      debugPrint('EventService.flush failed: $error\n$stackTrace');
    } finally {
      _isFlushing = false;
    }
  }

  void dispose() {
    _flushTimer?.cancel();
    _retryTimer?.cancel();
    _flushTimer = null;
    _retryTimer = null;
  }

  Future<void> _ensureInitialized() async {
    if (_initialized) {
      return;
    }
    _initializing ??= _initialize();
    await _initializing;
  }

  Future<void> _initialize() async {
    final List<QueuedEvent> storedQueue = await _store.readQueue();
    _queue
      ..clear()
      ..addAll(storedQueue);
    _sessionId = await _store.readSessionId();
    _sessionId ??= _uuidGenerator();
    await _store.writeSessionId(_sessionId!);
    _initialized = true;
    if (_queue.isNotEmpty) {
      _scheduleFlush(const Duration(milliseconds: 10));
    }
  }

  Future<void> _persistQueue() {
    return _store.writeQueue(_queue);
  }

  void _scheduleFlush(Duration delay) {
    if (delay <= Duration.zero) {
      _flushTimer?.cancel();
      _flushTimer = null;
      unawaited(flush());
      return;
    }
    if (_flushTimer != null || _isFlushing) {
      return;
    }
    _flushTimer = Timer(delay, () {
      _flushTimer = null;
      unawaited(flush());
    });
  }

  void _scheduleRetry(Duration delay) {
    _retryTimer?.cancel();
    _retryTimer = Timer(delay, () {
      _retryTimer = null;
      unawaited(flush());
    });
  }

  Duration _retryDelayFor(int retryCount) {
    final int cappedShift = math.min(math.max(retryCount - 1, 0), 5);
    final int multiplier = 1 << cappedShift;
    final int delayMs = retryBaseDelay.inMilliseconds * multiplier;
    return Duration(
      milliseconds: math.min(delayMs, retryMaxDelay.inMilliseconds),
    );
  }
}

const String _defaultActionApiBaseUrl = String.fromEnvironment(
  'GTE_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

DateTime _defaultNow() => DateTime.now().toUtc();

String _defaultDevice() {
  return defaultTargetPlatform.name.toLowerCase();
}

String? _stringOrNull(Object? value) {
  final String resolved = value?.toString().trim() ?? '';
  return resolved.isEmpty ? null : resolved;
}

int? _intOrNull(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '');
}

List<String> _stringList(Object? value) {
  if (value is! List) {
    return const <String>[];
  }
  return value
      .map((Object? item) => item?.toString().trim() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

String? _trimmedOrNull(String? value) {
  final String resolved = value?.trim() ?? '';
  return resolved.isEmpty ? null : resolved;
}

String _trimmedOrFallback(String? value, String fallback) {
  return _trimmedOrNull(value) ?? fallback;
}

final math.Random _uuidRandom = _createUuidRandom();

math.Random _createUuidRandom() {
  try {
    return math.Random.secure();
  } catch (_) {
    return math.Random();
  }
}

String _generateUuid() {
  final List<int> bytes = List<int>.generate(
    16,
    (_) => _uuidRandom.nextInt(256),
  );
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final String hex =
      bytes.map((int value) => value.toRadixString(16).padLeft(2, '0')).join();
  return <String>[
    hex.substring(0, 8),
    hex.substring(8, 12),
    hex.substring(12, 16),
    hex.substring(16, 20),
    hex.substring(20, 32),
  ].join('-');
}
