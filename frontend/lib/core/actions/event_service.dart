import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../app/gte_app_config.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_http_transport.dart';
import '../../shared/auth/auth_identity_store.dart';
import '../../shared/models/auth_session.dart';

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
    this.creatorId,
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
  final String? creatorId;
  final String? formatKey;
  final String? clipEventType;
  final String? teamName;
  final List<String> tags;
}

class QueuedEvent {
  const QueuedEvent({
    required this.eventId,
    required this.clipId,
    required this.userId,
    required this.sessionId,
    required this.timestamp,
    required this.eventType,
    required this.metadata,
    this.watchTimeMs,
    this.videoLengthMs,
    this.retryCount = 0,
  });

  factory QueuedEvent.fromJson(Map<String, Object?> json) {
    return QueuedEvent(
      eventId: (json['event_id'] ?? '').toString(),
      clipId: (json['clip_id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
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
  final String userId;
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
    this.creatorId,
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
      creatorId: _stringOrNull(json['creator_id']),
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
  final String? creatorId;
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
      'creator_id': creatorId,
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
}

class SharedPreferencesEventQueueStore implements EventQueueStore {
  SharedPreferencesEventQueueStore({
    SharedPreferences? preferences,
    this.queueKey = _defaultQueueKey,
  }) : _preferences = preferences;

  static const String _defaultQueueKey = 'gtex_action_pipeline_queue';

  SharedPreferences? _preferences;
  final String queueKey;

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
}

abstract class EventTransport {
  Future<void> postEvents(
    List<QueuedEvent> events, {
    required AuthSession authSession,
    required String deviceId,
  });
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
  Future<void> postEvents(
    List<QueuedEvent> events, {
    required AuthSession authSession,
    required String deviceId,
  }) async {
    final GteAuthedApi api = GteAuthedApi(
      config: _config,
      transport: _transport,
      authSession: authSession,
      deviceId: deviceId,
      mode: GteBackendMode.live,
    );
    await api.post(
      endpointPath,
      body: <String, Object?>{
        'events': events
            .map((QueuedEvent event) => event.toApiJson())
            .toList(growable: false),
      },
    );
  }
}

class EventService {
  EventService({
    required EventTransport transport,
    required EventQueueStore store,
    required AuthSessionStore authSessionStore,
    required DeviceIdentityStore deviceIdentityStore,
    Duration? batchWindow,
    Duration? retryBaseDelay,
    Duration? retryMaxDelay,
    int maxBatchSize = 50,
    String defaultCountry = 'unknown',
    String defaultReferrer = 'viral_feed',
    String defaultContentType = 'clip',
    String? deviceId,
    DateTime Function()? now,
    String Function()? uuidGenerator,
    String Function()? deviceResolver,
  }) : _transport = transport,
       _store = store,
       _authSessionStore = authSessionStore,
       _deviceIdentityStore = deviceIdentityStore,
       batchWindow = batchWindow ?? const Duration(milliseconds: 300),
       retryBaseDelay = retryBaseDelay ?? const Duration(seconds: 1),
       retryMaxDelay = retryMaxDelay ?? const Duration(seconds: 30),
       _maxBatchSize = maxBatchSize,
       _defaultCountry = defaultCountry,
       _defaultReferrer = defaultReferrer,
       _defaultContentType = defaultContentType,
       _configuredDeviceId = deviceId?.trim(),
       _now = now ?? _defaultNow,
       _uuidGenerator = uuidGenerator ?? generateIdentityUuid,
       _deviceResolver = deviceResolver ?? _defaultDevice;

  factory EventService.standard({
    String? baseUrl,
    GteTransport? transport,
    EventQueueStore? store,
    AuthSessionStore? authSessionStore,
    DeviceIdentityStore? deviceIdentityStore,
    Duration? batchWindow,
    Duration? retryBaseDelay,
    Duration? retryMaxDelay,
    String? deviceId,
  }) {
    final String resolvedBaseUrl =
        baseUrl ?? resolveGteApiBaseUrlFromEnvironment();
    return EventService(
      transport: ClipEventsApiTransport(
        config: GteRepositoryConfig(
          baseUrl: resolvedBaseUrl,
          mode: GteBackendMode.live,
        ),
        transport: transport,
      ),
      store: store ?? SharedPreferencesEventQueueStore(),
      authSessionStore: authSessionStore ?? SecureAuthSessionStore(),
      deviceIdentityStore: deviceIdentityStore ?? SecureDeviceIdentityStore(),
      batchWindow: batchWindow,
      retryBaseDelay: retryBaseDelay,
      retryMaxDelay: retryMaxDelay,
      deviceId: deviceId,
    );
  }

  final EventTransport _transport;
  final EventQueueStore _store;
  final AuthSessionStore _authSessionStore;
  final DeviceIdentityStore _deviceIdentityStore;
  final Duration batchWindow;
  final Duration retryBaseDelay;
  final Duration retryMaxDelay;
  final int _maxBatchSize;
  final String _defaultCountry;
  final String _defaultReferrer;
  final String _defaultContentType;
  final String? _configuredDeviceId;
  final DateTime Function() _now;
  final String Function() _uuidGenerator;
  final String Function() _deviceResolver;

  final List<QueuedEvent> _queue = <QueuedEvent>[];
  bool _initialized = false;
  bool _isFlushing = false;
  Future<void>? _initializing;
  Timer? _flushTimer;
  Timer? _retryTimer;

  @visibleForTesting
  List<QueuedEvent> get queuedEvents => List<QueuedEvent>.unmodifiable(_queue);

  Future<void> trackEvent(TrackEventRequest request) async {
    await _ensureInitialized();
    final AuthSession authSession = await _requireAuthSession();
    final String deviceId = await _resolveDeviceId();
    final QueuedEvent event = QueuedEvent(
      eventId: _uuidGenerator(),
      clipId: request.clipId,
      userId: authSession.userId,
      sessionId: authSession.sessionId,
      timestamp: _now().toUtc(),
      eventType: request.eventType,
      watchTimeMs: request.watchTimeMs,
      videoLengthMs: request.videoLengthMs,
      metadata: EventMetadata(
        device: _trimmedOrFallback(request.device, _deviceResolver()),
        country: _trimmedOrFallback(request.country, _defaultCountry),
        referrer: _trimmedOrFallback(request.referrer, _defaultReferrer),
        contentType: _trimmedOrNull(request.contentType) ?? _defaultContentType,
        creatorId: _trimmedOrNull(request.creatorId),
        formatKey: _trimmedOrNull(request.formatKey),
        clipEventType: _trimmedOrNull(request.clipEventType),
        teamName: _trimmedOrNull(request.teamName),
        tags: request.tags
            .map((String value) => value.trim())
            .where((String value) => value.isNotEmpty)
            .toList(growable: false),
      ),
    );
    try {
      await _transport.postEvents(
        <QueuedEvent>[event],
        authSession: authSession,
        deviceId: deviceId,
      );
    } catch (error, stackTrace) {
      _queue.add(event.copyWith(retryCount: 1));
      await _persistQueue();
      _scheduleRetry(_retryDelayFor(1));
      debugPrint('EventService.trackEvent failed: $error\n$stackTrace');
      rethrow;
    }
  }

  Future<void> flush({bool propagateError = false}) async {
    await _ensureInitialized();
    if (_isFlushing || _queue.isEmpty) {
      return;
    }
    await _discardStaleQueue();
    if (_queue.isEmpty) {
      return;
    }

    _flushTimer?.cancel();
    _flushTimer = null;
    _retryTimer?.cancel();
    _retryTimer = null;

    _isFlushing = true;
    final AuthSession authSession = await _requireAuthSession();
    final String deviceId = await _resolveDeviceId();
    final List<QueuedEvent> batch = _queue
        .take(_maxBatchSize)
        .toList(growable: false);
    try {
      await _transport.postEvents(
        batch,
        authSession: authSession,
        deviceId: deviceId,
      );
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
    _initialized = true;
    await _resolveDeviceId();
    if (_queue.isNotEmpty) {
      _scheduleFlush(const Duration(milliseconds: 10));
    }
  }

  Future<AuthSession> _requireAuthSession() async {
    final AuthSession? authSession = await _authSessionStore.readSession();
    if (authSession == null) {
      throw const GteApiException(
        type: GteApiErrorType.unauthorized,
        message: 'Authentication required for this action.',
      );
    }
    return authSession;
  }

  Future<String> _resolveDeviceId() async {
    final String resolvedDeviceId = _configuredDeviceId?.trim() ?? '';
    if (resolvedDeviceId.isNotEmpty) {
      await _deviceIdentityStore.writeDeviceId(resolvedDeviceId);
      return resolvedDeviceId;
    }
    return ensureDeviceId(_deviceIdentityStore, uuidGenerator: _uuidGenerator);
  }

  Future<void> _discardStaleQueue() async {
    final AuthSession? authSession = await _authSessionStore.readSession();
    if (authSession == null) {
      if (_queue.isNotEmpty) {
        _queue.clear();
        await _persistQueue();
      }
      return;
    }
    final List<QueuedEvent> retained = _queue
        .where(
          (QueuedEvent event) =>
              event.userId == authSession.userId &&
              event.sessionId == authSession.sessionId,
        )
        .toList(growable: false);
    if (retained.length == _queue.length) {
      return;
    }
    _queue
      ..clear()
      ..addAll(retained);
    await _persistQueue();
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
