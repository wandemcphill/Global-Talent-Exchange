import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:shared_preferences/shared_preferences.dart';

enum FeedRefreshTrigger { followAction, sessionChange, majorInteraction }

typedef ReliableEventSender = Future<void> Function(ReliableQueuedEvent event);
typedef ReliableEventCanSend = bool Function();
typedef SharedPreferencesLoader = Future<SharedPreferences> Function();

class ReliableQueuedEvent {
  const ReliableQueuedEvent({
    required this.id,
    required this.topic,
    required this.name,
    required this.payload,
    required this.createdAt,
    required this.requiresDelivery,
    this.dedupeKey,
    this.attemptCount = 0,
    this.lastAttemptAt,
    this.nextAttemptAt,
    this.feedRefreshTrigger,
  });

  final String id;
  final String topic;
  final String name;
  final Map<String, Object?> payload;
  final String? dedupeKey;
  final DateTime createdAt;
  final int attemptCount;
  final DateTime? lastAttemptAt;
  final DateTime? nextAttemptAt;
  final FeedRefreshTrigger? feedRefreshTrigger;
  final bool requiresDelivery;

  ReliableQueuedEvent copyWith({
    String? id,
    String? topic,
    String? name,
    Map<String, Object?>? payload,
    String? dedupeKey,
    bool clearDedupeKey = false,
    DateTime? createdAt,
    int? attemptCount,
    DateTime? lastAttemptAt,
    bool clearLastAttemptAt = false,
    DateTime? nextAttemptAt,
    bool clearNextAttemptAt = false,
    FeedRefreshTrigger? feedRefreshTrigger,
    bool clearFeedRefreshTrigger = false,
    bool? requiresDelivery,
  }) {
    return ReliableQueuedEvent(
      id: id ?? this.id,
      topic: topic ?? this.topic,
      name: name ?? this.name,
      payload: payload ?? this.payload,
      dedupeKey: clearDedupeKey ? null : dedupeKey ?? this.dedupeKey,
      createdAt: createdAt ?? this.createdAt,
      attemptCount: attemptCount ?? this.attemptCount,
      lastAttemptAt:
          clearLastAttemptAt ? null : lastAttemptAt ?? this.lastAttemptAt,
      nextAttemptAt:
          clearNextAttemptAt ? null : nextAttemptAt ?? this.nextAttemptAt,
      feedRefreshTrigger:
          clearFeedRefreshTrigger
              ? null
              : feedRefreshTrigger ?? this.feedRefreshTrigger,
      requiresDelivery: requiresDelivery ?? this.requiresDelivery,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'topic': topic,
      'name': name,
      'payload': _normalizeMap(payload),
      if (dedupeKey != null) 'dedupe_key': dedupeKey,
      'created_at': createdAt.toUtc().toIso8601String(),
      'attempt_count': attemptCount,
      if (lastAttemptAt != null)
        'last_attempt_at': lastAttemptAt!.toUtc().toIso8601String(),
      if (nextAttemptAt != null)
        'next_attempt_at': nextAttemptAt!.toUtc().toIso8601String(),
      if (feedRefreshTrigger != null)
        'feed_refresh_trigger': feedRefreshTrigger!.name,
      'requires_delivery': requiresDelivery,
    };
  }

  static ReliableQueuedEvent fromJson(Map<String, Object?> json) {
    return ReliableQueuedEvent(
      id: _stringValue(json['id'], fallback: _generateUuidV4()),
      topic: _stringValue(json['topic'], fallback: 'client'),
      name: _stringValue(json['name']),
      payload: _mapValue(json['payload']),
      dedupeKey: _nullableStringValue(json['dedupe_key']),
      createdAt:
          DateTime.tryParse(_stringValue(json['created_at']))?.toUtc() ??
          DateTime.now().toUtc(),
      attemptCount: _intValue(json['attempt_count'], fallback: 0),
      lastAttemptAt: _parseDateTime(json['last_attempt_at']),
      nextAttemptAt: _parseDateTime(json['next_attempt_at']),
      feedRefreshTrigger: _parseFeedRefreshTrigger(
        json['feed_refresh_trigger'],
      ),
      requiresDelivery: _boolValue(json['requires_delivery'], fallback: true),
    );
  }
}

class ReliableEventQueue {
  ReliableEventQueue({
    SharedPreferencesLoader? sharedPreferencesLoader,
    ReliableEventSender? sender,
    ReliableEventCanSend? canSend,
    DateTime Function()? now,
    Duration retryBaseDelay = const Duration(seconds: 2),
    Duration maxRetryDelay = const Duration(minutes: 1),
    Duration dedupeWindow = const Duration(minutes: 5),
    this.storageKey = 'gte.reliable_event_queue.v1',
    this.dedupeStorageKey = 'gte.reliable_event_queue_dedupe.v1',
  }) : _sharedPreferencesLoader =
           sharedPreferencesLoader ?? SharedPreferences.getInstance,
       _sender = sender,
       _canSend = canSend,
       _now = now ?? (() => DateTime.now().toUtc()),
       _retryBaseDelay = retryBaseDelay,
       _maxRetryDelay = maxRetryDelay,
       _dedupeWindow = dedupeWindow;

  final SharedPreferencesLoader _sharedPreferencesLoader;
  final DateTime Function() _now;
  final Duration _retryBaseDelay;
  final Duration _maxRetryDelay;
  final Duration _dedupeWindow;
  final String storageKey;
  final String dedupeStorageKey;

  final StreamController<FeedRefreshTrigger> _feedRefreshController =
      StreamController<FeedRefreshTrigger>.broadcast(sync: true);
  final List<ReliableQueuedEvent> _pending = <ReliableQueuedEvent>[];
  final Map<String, DateTime> _deliveredDedupeKeys = <String, DateTime>{};

  SharedPreferences? _preferences;
  ReliableEventSender? _sender;
  ReliableEventCanSend? _canSend;
  Future<void>? _initializeFuture;
  Future<void>? _flushFuture;
  Timer? _retryTimer;

  Stream<FeedRefreshTrigger> get feedRefreshTriggers =>
      _feedRefreshController.stream;

  List<ReliableQueuedEvent> get pendingEvents =>
      List<ReliableQueuedEvent>.unmodifiable(_pending);

  bool get hasPendingEvents => _pending.isNotEmpty;

  void configure({ReliableEventSender? sender, ReliableEventCanSend? canSend}) {
    _sender = sender ?? _sender;
    _canSend = canSend ?? _canSend;
    unawaited(flush());
  }

  void markConnectionRestored() {
    unawaited(flush());
  }

  Future<ReliableQueuedEvent?> enqueue({
    required String topic,
    required String name,
    Map<String, Object?> payload = const <String, Object?>{},
    String? dedupeKey,
    FeedRefreshTrigger? feedRefreshTrigger,
    bool requiresDelivery = true,
  }) async {
    await _ensureInitialized();

    final String? normalizedDedupeKey = _normalizeDedupeKey(dedupeKey);
    if (_isDuplicate(normalizedDedupeKey)) {
      return null;
    }

    final ReliableQueuedEvent event = ReliableQueuedEvent(
      id: _generateUuidV4(),
      topic: topic.trim().isEmpty ? 'client' : topic.trim(),
      name: name.trim(),
      payload: _normalizeMap(payload),
      dedupeKey: normalizedDedupeKey,
      createdAt: _now(),
      nextAttemptAt: requiresDelivery ? _now() : null,
      feedRefreshTrigger: feedRefreshTrigger,
      requiresDelivery: requiresDelivery,
    );

    if (feedRefreshTrigger != null) {
      _feedRefreshController.add(feedRefreshTrigger);
    }

    if (!requiresDelivery) {
      _rememberDedupeKey(normalizedDedupeKey);
      await _persistState();
      return event;
    }

    _pending.add(event);
    await _persistState();
    unawaited(flush());
    return event;
  }

  Future<void> flush() {
    _flushFuture ??= _flushInternal().whenComplete(() {
      _flushFuture = null;
    });
    return _flushFuture!;
  }

  Future<void> dispose() async {
    _retryTimer?.cancel();
    await _feedRefreshController.close();
  }

  Future<void> _ensureInitialized() {
    _initializeFuture ??= _initializeInternal();
    return _initializeFuture!;
  }

  Future<void> _initializeInternal() async {
    _preferences = await _sharedPreferencesLoader();

    final String? encodedQueue = _preferences!.getString(storageKey);
    if (encodedQueue != null && encodedQueue.trim().isNotEmpty) {
      try {
        final List<Object?> rawList =
            (jsonDecode(encodedQueue) as List<Object?>?) ?? const <Object?>[];
        _pending
          ..clear()
          ..addAll(
            rawList.whereType<Map>().map(
              (Map<Object?, Object?> entry) =>
                  ReliableQueuedEvent.fromJson(_mapValue(entry)),
            ),
          );
      } catch (_) {
        _pending.clear();
      }
    }

    final String? encodedDedupe = _preferences!.getString(dedupeStorageKey);
    if (encodedDedupe != null && encodedDedupe.trim().isNotEmpty) {
      try {
        final Map<String, Object?> raw = _mapValue(jsonDecode(encodedDedupe));
        _deliveredDedupeKeys
          ..clear()
          ..addEntries(
            raw.entries
                .map(
                  (MapEntry<String, Object?> entry) =>
                      MapEntry<String, DateTime>(
                        entry.key,
                        DateTime.tryParse(entry.value.toString())?.toUtc() ??
                            _now(),
                      ),
                )
                .where(
                  (MapEntry<String, DateTime> entry) =>
                      _now().difference(entry.value) <= _dedupeWindow,
                ),
          );
      } catch (_) {
        _deliveredDedupeKeys.clear();
      }
    }

    _pruneDedupeKeys();
  }

  Future<void> _flushInternal() async {
    await _ensureInitialized();
    _retryTimer?.cancel();

    if (_sender == null) {
      return;
    }
    if (_canSend != null && !_canSend!.call()) {
      return;
    }

    while (true) {
      final DateTime now = _now();
      final ReliableQueuedEvent? next = _nextReadyEvent(now);
      if (next == null) {
        _scheduleRetryIfNeeded(now);
        return;
      }
      try {
        await _sender!.call(next);
        _pending.removeWhere(
          (ReliableQueuedEvent event) => event.id == next.id,
        );
        _rememberDedupeKey(next.dedupeKey);
        await _persistState();
      } catch (_) {
        final int nextAttemptCount = next.attemptCount + 1;
        final ReliableQueuedEvent retryable = next.copyWith(
          attemptCount: nextAttemptCount,
          lastAttemptAt: now,
          nextAttemptAt: now.add(_retryDelay(nextAttemptCount)),
        );
        _replaceEvent(retryable);
        await _persistState();
        _scheduleRetryIfNeeded(now);
        return;
      }
    }
  }

  ReliableQueuedEvent? _nextReadyEvent(DateTime now) {
    for (final ReliableQueuedEvent event in _pending) {
      final DateTime? nextAttemptAt = event.nextAttemptAt;
      if (nextAttemptAt == null || !nextAttemptAt.isAfter(now)) {
        return event;
      }
    }
    return null;
  }

  void _replaceEvent(ReliableQueuedEvent updated) {
    final int index = _pending.indexWhere(
      (ReliableQueuedEvent event) => event.id == updated.id,
    );
    if (index < 0) {
      return;
    }
    _pending[index] = updated;
  }

  void _scheduleRetryIfNeeded(DateTime now) {
    _retryTimer?.cancel();
    final ReliableQueuedEvent? next = _pending
        .where(
          (ReliableQueuedEvent event) =>
              event.nextAttemptAt != null && event.nextAttemptAt!.isAfter(now),
        )
        .fold<ReliableQueuedEvent?>(null, (
          ReliableQueuedEvent? current,
          ReliableQueuedEvent candidate,
        ) {
          if (current == null) {
            return candidate;
          }
          return candidate.nextAttemptAt!.isBefore(current.nextAttemptAt!)
              ? candidate
              : current;
        });
    if (next == null) {
      return;
    }
    final Duration delay = next.nextAttemptAt!.difference(now);
    _retryTimer = Timer(delay, () {
      unawaited(flush());
    });
  }

  Duration _retryDelay(int attemptCount) {
    final int safeAttempt = math.max(0, attemptCount - 1);
    final int multiplier = 1 << safeAttempt.clamp(0, 12);
    final int milliseconds = _retryBaseDelay.inMilliseconds * multiplier;
    return Duration(
      milliseconds: math.min(milliseconds, _maxRetryDelay.inMilliseconds),
    );
  }

  bool _isDuplicate(String? dedupeKey) {
    if (dedupeKey == null) {
      return false;
    }
    final bool pendingDuplicate = _pending.any(
      (ReliableQueuedEvent event) => event.dedupeKey == dedupeKey,
    );
    if (pendingDuplicate) {
      return true;
    }
    final DateTime? deliveredAt = _deliveredDedupeKeys[dedupeKey];
    if (deliveredAt == null) {
      return false;
    }
    return _now().difference(deliveredAt) <= _dedupeWindow;
  }

  void _rememberDedupeKey(String? dedupeKey) {
    if (dedupeKey == null) {
      return;
    }
    _deliveredDedupeKeys[dedupeKey] = _now();
    _pruneDedupeKeys();
  }

  void _pruneDedupeKeys() {
    final DateTime cutoff = _now().subtract(_dedupeWindow);
    _deliveredDedupeKeys.removeWhere(
      (String _, DateTime deliveredAt) => deliveredAt.isBefore(cutoff),
    );
    if (_deliveredDedupeKeys.length <= 128) {
      return;
    }
    final List<MapEntry<String, DateTime>> sortedEntries = _deliveredDedupeKeys
      .entries
      .toList(growable: false)..sort(
      (MapEntry<String, DateTime> left, MapEntry<String, DateTime> right) =>
          right.value.compareTo(left.value),
    );
    _deliveredDedupeKeys
      ..clear()
      ..addEntries(sortedEntries.take(128));
  }

  Future<void> _persistState() async {
    final SharedPreferences? preferences = _preferences;
    if (preferences == null) {
      return;
    }
    await preferences.setString(
      storageKey,
      jsonEncode(
        _pending
            .map((ReliableQueuedEvent event) => event.toJson())
            .toList(growable: false),
      ),
    );
    await preferences.setString(
      dedupeStorageKey,
      jsonEncode(
        _deliveredDedupeKeys.map(
          (String key, DateTime value) =>
              MapEntry<String, String>(key, value.toUtc().toIso8601String()),
        ),
      ),
    );
  }
}

final ReliableEventQueue gteReliableEventQueue = ReliableEventQueue();

DateTime? _parseDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value.toString())?.toUtc();
}

FeedRefreshTrigger? _parseFeedRefreshTrigger(Object? value) {
  final String raw = _nullableStringValue(value) ?? '';
  for (final FeedRefreshTrigger trigger in FeedRefreshTrigger.values) {
    if (trigger.name == raw) {
      return trigger;
    }
  }
  return null;
}

String? _normalizeDedupeKey(String? value) {
  final String trimmed = value?.trim() ?? '';
  return trimmed.isEmpty ? null : trimmed;
}

Map<String, Object?> _mapValue(Object? value) {
  if (value is Map<String, Object?>) {
    return _normalizeMap(value);
  }
  if (value is Map) {
    final Map<String, Object?> result = <String, Object?>{};
    for (final MapEntry<Object?, Object?> entry in value.entries) {
      result[entry.key.toString()] = _normalizeValue(entry.value);
    }
    return result;
  }
  return const <String, Object?>{};
}

Map<String, Object?> _normalizeMap(Map<String, Object?> value) {
  final Map<String, Object?> normalized = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in value.entries) {
    normalized[entry.key] = _normalizeValue(entry.value);
  }
  return normalized;
}

Object? _normalizeValue(Object? value) {
  if (value == null || value is String || value is num || value is bool) {
    return value;
  }
  if (value is DateTime) {
    return value.toUtc().toIso8601String();
  }
  if (value is Enum) {
    return value.name;
  }
  if (value is Map<String, Object?>) {
    return _normalizeMap(value);
  }
  if (value is Map) {
    return _mapValue(value);
  }
  if (value is Iterable) {
    return value.map(_normalizeValue).toList(growable: false);
  }
  return value.toString();
}

String _stringValue(Object? value, {String fallback = ''}) {
  final String text = value?.toString().trim() ?? '';
  return text.isEmpty ? fallback : text;
}

String? _nullableStringValue(Object? value) {
  final String text = _stringValue(value);
  return text.isEmpty ? null : text;
}

int _intValue(Object? value, {int fallback = 0}) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? fallback;
}

bool _boolValue(Object? value, {required bool fallback}) {
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
    return true;
  }
  if (normalized == 'false' || normalized == '0' || normalized == 'no') {
    return false;
  }
  return fallback;
}

String _generateUuidV4() {
  final math.Random random = math.Random.secure();
  final List<int> bytes = List<int>.generate(
    16,
    (_) => random.nextInt(256),
    growable: false,
  );
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final StringBuffer buffer = StringBuffer();
  for (int index = 0; index < bytes.length; index += 1) {
    if (index == 4 || index == 6 || index == 8 || index == 10) {
      buffer.write('-');
    }
    buffer.write(bytes[index].toRadixString(16).padLeft(2, '0'));
  }
  return buffer.toString();
}
