import 'dart:convert';

enum GtexRealtimeStatus {
  disconnected,
  connecting,
  live,
  syncing,
  reconnecting,
  degraded,
  error,
}

extension GtexRealtimeStatusX on GtexRealtimeStatus {
  String get label {
    switch (this) {
      case GtexRealtimeStatus.disconnected:
        return 'Disconnected';
      case GtexRealtimeStatus.connecting:
        return 'Connecting';
      case GtexRealtimeStatus.live:
        return 'Live';
      case GtexRealtimeStatus.syncing:
        return 'Syncing';
      case GtexRealtimeStatus.reconnecting:
        return 'Reconnecting';
      case GtexRealtimeStatus.degraded:
        return 'Degraded';
      case GtexRealtimeStatus.error:
        return 'Error';
    }
  }

  bool get requiresAttention {
    switch (this) {
      case GtexRealtimeStatus.disconnected:
      case GtexRealtimeStatus.reconnecting:
      case GtexRealtimeStatus.degraded:
      case GtexRealtimeStatus.error:
        return true;
      case GtexRealtimeStatus.connecting:
      case GtexRealtimeStatus.live:
      case GtexRealtimeStatus.syncing:
        return false;
    }
  }
}

GtexRealtimeStatus? gtexRealtimeStatusFrom(Object? value) {
  switch (_normalize(value?.toString() ?? '')) {
    case 'disconnected':
    case 'offline':
    case 'closed':
      return GtexRealtimeStatus.disconnected;
    case 'connecting':
    case 'opening':
      return GtexRealtimeStatus.connecting;
    case 'live':
    case 'connected':
    case 'confirmed':
    case 'sync_complete':
    case 'sync_completed':
      return GtexRealtimeStatus.live;
    case 'syncing':
    case 'sync_start':
    case 'sync_started':
      return GtexRealtimeStatus.syncing;
    case 'reconnecting':
    case 'retrying':
      return GtexRealtimeStatus.reconnecting;
    case 'degraded':
    case 'delayed':
      return GtexRealtimeStatus.degraded;
    case 'error':
    case 'failed':
      return GtexRealtimeStatus.error;
    default:
      return null;
  }
}

class GtexRealtimeEvent {
  const GtexRealtimeEvent({
    required this.type,
    required this.topic,
    required this.payload,
    this.id,
    this.timestamp,
  });

  final String type;
  final String topic;
  final Map<String, Object?> payload;
  final String? id;
  final DateTime? timestamp;

  bool get isLivePulse =>
      _matchesTopic(topic, const <String>{'live_pulse', 'pulse', 'live'}) ||
      _normalize(type).contains('pulse');

  bool get isNotification =>
      _matchesTopic(topic, const <String>{'notification', 'notifications'}) ||
      _normalize(type).contains('notification');

  bool get isActivity =>
      _matchesTopic(topic, const <String>{
        'activity',
        'activities',
        'activity_event',
      }) ||
      _normalize(type).contains('activity') ||
      _normalize(type).contains('audit');

  GtexRealtimeStatus? get statusHint {
    return gtexRealtimeStatusFrom(
      payload['status'] ?? payload['connection_status'] ?? type,
    );
  }

  static GtexRealtimeEvent? fromMessage(Object? message) {
    final Object? decoded = _decodeMessage(message);
    if (decoded is! Map) {
      return null;
    }
    final Map<String, Object?> envelope = _stringMap(decoded);
    final String type = _firstString(<Object?>[
      envelope['type'],
      envelope['event_type'],
      envelope['eventType'],
      envelope['kind'],
    ], fallback: 'message');
    final String topic = _firstString(<Object?>[
      envelope['topic'],
      envelope['channel'],
      envelope['scope'],
    ], fallback: _topicFromType(type));
    final Object? rawPayload = envelope['payload'] ?? envelope['data'];
    return GtexRealtimeEvent(
      id: _optionalString(envelope['id'] ?? envelope['event_id']),
      type: type,
      topic: topic,
      payload:
          rawPayload is Map
              ? _stringMap(rawPayload)
              : _payloadFromEnvelope(envelope),
      timestamp: _parseTimestamp(
        envelope['timestamp'] ?? envelope['sent_at'] ?? envelope['created_at'],
      ),
    );
  }

  @override
  String toString() => 'GtexRealtimeEvent(type: $type, topic: $topic, id: $id)';
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

Map<String, Object?> _stringMap(Map<dynamic, dynamic> value) {
  return <String, Object?>{
    for (final MapEntry<dynamic, dynamic> entry in value.entries)
      entry.key.toString(): entry.value,
  };
}

Map<String, Object?> _payloadFromEnvelope(Map<String, Object?> envelope) {
  const Set<String> envelopeKeys = <String>{
    'id',
    'event_id',
    'type',
    'event_type',
    'eventType',
    'kind',
    'topic',
    'channel',
    'scope',
    'timestamp',
    'sent_at',
    'created_at',
  };
  return <String, Object?>{
    for (final MapEntry<String, Object?> entry in envelope.entries)
      if (!envelopeKeys.contains(entry.key)) entry.key: entry.value,
  };
}

String _firstString(List<Object?> values, {required String fallback}) {
  for (final Object? value in values) {
    final String? resolved = _optionalString(value);
    if (resolved != null) {
      return resolved;
    }
  }
  return fallback;
}

String? _optionalString(Object? value) {
  final String resolved = value?.toString().trim() ?? '';
  return resolved.isEmpty ? null : resolved;
}

String _topicFromType(String type) {
  final String normalized = _normalize(type);
  if (normalized.contains('notification')) {
    return 'notifications';
  }
  if (normalized.contains('activity') || normalized.contains('audit')) {
    return 'activity';
  }
  if (normalized.contains('pulse')) {
    return 'live_pulse';
  }
  return 'system';
}

DateTime? _parseTimestamp(Object? value) {
  final String? raw = _optionalString(value);
  if (raw == null) {
    return null;
  }
  return DateTime.tryParse(raw);
}

bool _matchesTopic(String topic, Set<String> candidates) {
  return candidates.contains(_normalize(topic));
}

String _normalize(String value) {
  return value.trim().toLowerCase().replaceAll('-', '_');
}
