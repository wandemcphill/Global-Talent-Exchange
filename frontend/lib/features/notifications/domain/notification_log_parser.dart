import 'dart:convert';

import 'notification_log_models.dart';

NotificationLogEvent? parseNotificationLogBackendMessage(
  Object? message, {
  DateTime? receivedAt,
}) {
  final Object? decoded = _decodeBackendMessage(message);
  final DateTime fallbackReceivedAt = receivedAt ?? DateTime.now().toUtc();
  if (decoded is List) {
    return NotificationLogEvent(
      type: NotificationLogEventType.snapshot,
      notifications: _notificationList(decoded, fallbackReceivedAt),
      receivedAt: fallbackReceivedAt,
      rawType: 'notifications_snapshot',
    );
  }
  if (decoded is! Map) {
    return null;
  }

  final Map<String, Object?> envelope = _stringMap(decoded);
  final String rawType =
      _firstNonEmptyString(<Object?>[
        envelope['type'],
        envelope['event_type'],
        envelope['eventType'],
        envelope['kind'],
        envelope['action'],
      ]) ??
      'notification';
  final String normalizedType = _normalize(rawType);
  final Object? payload = _payloadFromEnvelope(envelope);
  final Map<String, Object?> payloadMap = _stringMap(payload);
  final DateTime eventReceivedAt =
      _parseDateTime(
        _firstValue(envelope, <String>['timestamp', 'sent_at', 'created_at']),
      ) ??
      fallbackReceivedAt;

  if (_isConnectionEvent(normalizedType, payloadMap, envelope)) {
    return NotificationLogEvent(
      type: NotificationLogEventType.connectionChanged,
      connectionState: _connectionStateFrom(normalizedType, payloadMap),
      degradedReason: _firstNonEmptyString(<Object?>[
        payloadMap['reason'],
        payloadMap['message'],
        envelope['reason'],
        envelope['message'],
      ]),
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }

  if (_isSnapshotEvent(normalizedType, envelope, payload)) {
    return NotificationLogEvent(
      type: NotificationLogEventType.snapshot,
      notifications: _notificationList(
        _snapshotListPayload(envelope, payload),
        eventReceivedAt,
      ),
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }

  if (_isMarkAllReadEvent(normalizedType)) {
    return NotificationLogEvent(
      type: NotificationLogEventType.markAllRead,
      readAt: _readAt(payloadMap, envelope, eventReceivedAt),
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }

  if (_isMarkReadEvent(normalizedType)) {
    return NotificationLogEvent(
      type: NotificationLogEventType.markRead,
      notificationId: _notificationId(payloadMap, envelope),
      readAt: _readAt(payloadMap, envelope, eventReceivedAt),
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }

  if (_isRemoveEvent(normalizedType)) {
    return NotificationLogEvent(
      type: NotificationLogEventType.remove,
      notificationId: _notificationId(payloadMap, envelope),
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }

  final Map<String, Object?>? notification = _notificationPayload(
    envelope,
    payload,
  );
  if (notification == null) {
    return NotificationLogEvent(
      type: NotificationLogEventType.noop,
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }
  final NotificationLogItem item = NotificationLogItem.fromBackendJson(
    notification,
    fallbackCreatedAt: eventReceivedAt,
  );
  if (item.notificationId.trim().isEmpty) {
    return NotificationLogEvent(
      type: NotificationLogEventType.noop,
      receivedAt: eventReceivedAt,
      rawType: rawType,
    );
  }
  return NotificationLogEvent(
    type: NotificationLogEventType.upsert,
    notification: item,
    receivedAt: eventReceivedAt,
    rawType: rawType,
  );
}

Object? _decodeBackendMessage(Object? message) {
  if (message is List<int>) {
    return _decodeBackendMessage(utf8.decode(message));
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

Object? _payloadFromEnvelope(Map<String, Object?> envelope) {
  if (envelope.containsKey('payload')) {
    return envelope['payload'];
  }
  if (envelope.containsKey('data')) {
    return envelope['data'];
  }
  if (envelope.containsKey('notification')) {
    return envelope['notification'];
  }
  return envelope;
}

bool _isConnectionEvent(
  String normalizedType,
  Map<String, Object?> payload,
  Map<String, Object?> envelope,
) {
  if (_hasNotificationId(payload) || _hasNotificationId(envelope)) {
    return false;
  }
  if (normalizedType.contains('connection') ||
      normalizedType.contains('websocket') ||
      normalizedType.contains('socket') ||
      normalizedType.contains('stream')) {
    return _connectionStateFrom(normalizedType, payload) != null;
  }
  return const <String>{
    'connected',
    'live',
    'restored',
    'reconnected',
    'disconnected',
    'degraded',
    'offline',
  }.contains(normalizedType);
}

NotificationLogConnectionState? _connectionStateFrom(
  String normalizedType,
  Map<String, Object?> payload,
) {
  final String status = _normalize(
    _firstNonEmptyString(<Object?>[
          payload['status'],
          payload['connection_status'],
          payload['connectionState'],
          normalizedType,
        ]) ??
        '',
  );
  if (status.contains('degraded') ||
      status.contains('stale') ||
      status.contains('delayed')) {
    return NotificationLogConnectionState.degraded;
  }
  if (status.contains('connecting')) {
    return NotificationLogConnectionState.connecting;
  }
  if (status.contains('disconnect') ||
      status.contains('offline') ||
      status.contains('closed')) {
    return NotificationLogConnectionState.disconnected;
  }
  if (status.contains('live') ||
      status.contains('connected') ||
      status.contains('restored') ||
      status.contains('reconnected')) {
    return NotificationLogConnectionState.live;
  }
  return null;
}

bool _isSnapshotEvent(
  String normalizedType,
  Map<String, Object?> envelope,
  Object? payload,
) {
  if (normalizedType.contains('snapshot') ||
      normalizedType.contains('sync') ||
      normalizedType.contains('hydrate')) {
    return true;
  }
  if (payload is List) {
    return true;
  }
  final Map<String, Object?> payloadMap = _stringMap(payload);
  return _firstValue(payloadMap, const <String>[
            'notifications',
            'items',
            'results',
          ])
          is List ||
      _firstValue(envelope, const <String>['notifications', 'items', 'results'])
          is List;
}

Object? _snapshotListPayload(Map<String, Object?> envelope, Object? payload) {
  if (payload is List) {
    return payload;
  }
  final Map<String, Object?> payloadMap = _stringMap(payload);
  return _firstValue(payloadMap, const <String>[
        'notifications',
        'items',
        'results',
      ]) ??
      _firstValue(envelope, const <String>[
        'notifications',
        'items',
        'results',
      ]);
}

bool _isMarkAllReadEvent(String normalizedType) {
  return normalizedType.contains('read_all') ||
      normalizedType.contains('all_read') ||
      normalizedType.contains('notifications_read');
}

bool _isMarkReadEvent(String normalizedType) {
  return normalizedType.contains('read') ||
      normalizedType.contains('acknowledged') ||
      normalizedType.contains('seen');
}

bool _isRemoveEvent(String normalizedType) {
  return normalizedType.contains('delete') || normalizedType.contains('remove');
}

Map<String, Object?>? _notificationPayload(
  Map<String, Object?> envelope,
  Object? payload,
) {
  if (_hasNotificationId(payload)) {
    return _withGrouping(_stringMap(payload), envelope, _stringMap(payload));
  }
  final Map<String, Object?> payloadMap = _stringMap(payload);
  final Object? nestedNotification =
      payloadMap['notification'] ??
      payloadMap['record'] ??
      payloadMap['item'] ??
      envelope['notification'];
  if (_hasNotificationId(nestedNotification)) {
    return _withGrouping(_stringMap(nestedNotification), envelope, payloadMap);
  }
  if (_hasNotificationId(envelope)) {
    return _withGrouping(envelope, envelope, payloadMap);
  }
  return null;
}

Map<String, Object?> _withGrouping(
  Map<String, Object?> notification,
  Map<String, Object?> envelope,
  Map<String, Object?> payload,
) {
  return <String, Object?>{
    ...notification,
    if (!notification.containsKey('group_key'))
      if (_firstValue(payload, const <String>['group_key', 'groupKey']) ??
              _firstValue(envelope, const <String>['group_key', 'groupKey'])
          case final Object groupKey?)
        'group_key': groupKey,
    if (!notification.containsKey('group_label'))
      if (_firstValue(payload, const <String>['group_label', 'groupLabel']) ??
              _firstValue(envelope, const <String>['group_label', 'groupLabel'])
          case final Object groupLabel?)
        'group_label': groupLabel,
  };
}

List<NotificationLogItem> _notificationList(
  Object? value,
  DateTime fallbackCreatedAt,
) {
  if (value is! List) {
    return const <NotificationLogItem>[];
  }
  return value
      .map((Object? item) {
        final NotificationLogItem notification =
            NotificationLogItem.fromBackendJson(
              item,
              fallbackCreatedAt: fallbackCreatedAt,
            );
        return notification.notificationId.trim().isEmpty ? null : notification;
      })
      .whereType<NotificationLogItem>()
      .toList(growable: false);
}

String? _notificationId(
  Map<String, Object?> payload,
  Map<String, Object?> envelope,
) {
  return _firstNonEmptyString(<Object?>[
    payload['notification_id'],
    payload['notificationId'],
    payload['id'],
    envelope['notification_id'],
    envelope['notificationId'],
    envelope['id'],
  ]);
}

DateTime _readAt(
  Map<String, Object?> payload,
  Map<String, Object?> envelope,
  DateTime fallback,
) {
  return _parseDateTime(
        _firstValue(payload, const <String>['read_at', 'readAt']) ??
            _firstValue(envelope, const <String>['read_at', 'readAt']),
      ) ??
      fallback;
}

bool _hasNotificationId(Object? value) {
  if (value is! Map) {
    return false;
  }
  return _firstNonEmptyString(<Object?>[
        value['notification_id'],
        value['notificationId'],
        value['id'],
      ]) !=
      null;
}

Map<String, Object?> _stringMap(Object? value) {
  if (value is! Map) {
    return <String, Object?>{};
  }
  return <String, Object?>{
    for (final MapEntry<dynamic, dynamic> entry in value.entries)
      entry.key.toString(): entry.value,
  };
}

Object? _firstValue(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    if (json.containsKey(key)) {
      return json[key];
    }
  }
  return null;
}

String? _firstNonEmptyString(List<Object?> values) {
  for (final Object? value in values) {
    final String resolved = value?.toString().trim() ?? '';
    if (resolved.isNotEmpty) {
      return resolved;
    }
  }
  return null;
}

DateTime? _parseDateTime(Object? value) {
  final String? raw = _firstNonEmptyString(<Object?>[value]);
  if (raw == null) {
    return null;
  }
  return DateTime.tryParse(raw);
}

String _normalize(String value) {
  return value.trim().toLowerCase().replaceAll('-', '_').replaceAll('.', '_');
}
