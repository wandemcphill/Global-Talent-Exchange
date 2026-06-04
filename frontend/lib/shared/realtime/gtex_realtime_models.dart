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
    case 'ready':
    case 'subscribed':
    case 'sync_complete':
    case 'sync_completed':
      return GtexRealtimeStatus.live;
    case 'syncing':
    case 'sync_start':
    case 'sync_started':
    case 'catching_up':
      return GtexRealtimeStatus.syncing;
    case 'reconnecting':
    case 'retrying':
      return GtexRealtimeStatus.reconnecting;
    case 'degraded':
    case 'delayed':
    case 'stale':
      return GtexRealtimeStatus.degraded;
    case 'error':
    case 'failed':
    case 'blocked':
    case 'forbidden':
    case 'unauthorized':
    case 'unauthenticated':
    case 'token_expired':
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
    this.sequence,
  });

  final String type;
  final String topic;
  final Map<String, Object?> payload;
  final String? id;
  final DateTime? timestamp;
  final int? sequence;

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
      payload['status'] ?? payload['connection_status'] ?? payload['state'],
    );
  }

  static GtexRealtimeEvent? fromMessage(Object? message) {
    final GtexRealtimeInboundMessage parsed = GtexRealtimeContractParser.parse(
      message,
    );
    return parsed.event;
  }

  @override
  String toString() {
    return 'GtexRealtimeEvent(type: $type, topic: $topic, id: $id)';
  }
}

enum GtexRealtimeInboundKind {
  event,
  status,
  heartbeatPing,
  heartbeatPong,
  subscriptionAck,
  invalid,
}

class GtexRealtimeInboundMessage {
  const GtexRealtimeInboundMessage._({
    required this.kind,
    this.event,
    this.status,
    this.code,
    this.message,
  });

  factory GtexRealtimeInboundMessage.event(GtexRealtimeEvent event) {
    return GtexRealtimeInboundMessage._(
      kind: GtexRealtimeInboundKind.event,
      event: event,
      status: event.statusHint,
    );
  }

  factory GtexRealtimeInboundMessage.status(GtexRealtimeStatus status) {
    return GtexRealtimeInboundMessage._(
      kind: GtexRealtimeInboundKind.status,
      status: status,
    );
  }

  factory GtexRealtimeInboundMessage.control(GtexRealtimeInboundKind kind) {
    return GtexRealtimeInboundMessage._(kind: kind);
  }

  factory GtexRealtimeInboundMessage.invalid({
    required String code,
    required String message,
  }) {
    return GtexRealtimeInboundMessage._(
      kind: GtexRealtimeInboundKind.invalid,
      code: code,
      message: message,
    );
  }

  final GtexRealtimeInboundKind kind;
  final GtexRealtimeEvent? event;
  final GtexRealtimeStatus? status;
  final String? code;
  final String? message;
}

class GtexRealtimeContractParser {
  const GtexRealtimeContractParser._();

  static GtexRealtimeInboundMessage parse(Object? message) {
    final Object? decoded = _decodeMessage(message);
    if (decoded == null) {
      return GtexRealtimeInboundMessage.invalid(
        code: 'empty_message',
        message: 'Realtime websocket message was empty or invalid JSON.',
      );
    }
    if (decoded is String) {
      final String type = _normalize(decoded);
      if (type == 'ping') {
        return GtexRealtimeInboundMessage.control(
          GtexRealtimeInboundKind.heartbeatPing,
        );
      }
      if (type == 'pong') {
        return GtexRealtimeInboundMessage.control(
          GtexRealtimeInboundKind.heartbeatPong,
        );
      }
      return GtexRealtimeInboundMessage.invalid(
        code: 'unsupported_text_message',
        message: 'Realtime websocket text message is not a contract envelope.',
      );
    }
    if (decoded is! Map) {
      return GtexRealtimeInboundMessage.invalid(
        code: 'unsupported_message_shape',
        message: 'Realtime websocket message must be a JSON object envelope.',
      );
    }

    final Map<String, Object?> envelope = _stringMap(decoded);
    final String type = _firstString(<Object?>[
      envelope['type'],
      envelope['event_type'],
      envelope['eventType'],
      envelope['kind'],
    ], fallback: 'message');
    final String normalizedType = _normalize(type);

    if (normalizedType == 'ping') {
      return GtexRealtimeInboundMessage.control(
        GtexRealtimeInboundKind.heartbeatPing,
      );
    }
    if (normalizedType == 'pong') {
      return GtexRealtimeInboundMessage.control(
        GtexRealtimeInboundKind.heartbeatPong,
      );
    }
    if (const <String>{
      'ack',
      'subscription_ack',
      'subscribed',
      'ready',
    }.contains(normalizedType)) {
      final GtexRealtimeStatus? status = gtexRealtimeStatusFrom(
        envelope['status'] ?? envelope['state'] ?? normalizedType,
      );
      return status == null
          ? GtexRealtimeInboundMessage.control(
            GtexRealtimeInboundKind.subscriptionAck,
          )
          : GtexRealtimeInboundMessage.status(status);
    }

    final GtexRealtimeStatus? status = gtexRealtimeStatusFrom(
      envelope['status'] ?? envelope['state'],
    );
    final bool statusOnly = _isStatusOnlyEnvelope(envelope, normalizedType);
    if (statusOnly && status != null) {
      return GtexRealtimeInboundMessage.status(status);
    }

    final String? topic = _optionalString(
      envelope['topic'] ?? envelope['channel'] ?? envelope['scope'],
    );
    final Object? rawPayload = envelope['payload'] ?? envelope['data'];
    final bool hasEventContract =
        topic != null ||
        rawPayload is Map ||
        envelope.containsKey('event_id') ||
        envelope.containsKey('id');
    if (!hasEventContract) {
      return GtexRealtimeInboundMessage.invalid(
        code: 'missing_event_contract',
        message: 'Realtime event must include a topic/channel or payload.',
      );
    }

    final Map<String, Object?> payload =
        rawPayload is Map
            ? _stringMap(rawPayload)
            : _payloadFromEnvelope(envelope);
    return GtexRealtimeInboundMessage.event(
      GtexRealtimeEvent(
        id: _optionalString(envelope['id'] ?? envelope['event_id']),
        type: type,
        topic: topic ?? _topicFromType(type),
        payload: payload,
        timestamp: _parseTimestamp(
          envelope['timestamp'] ??
              envelope['sent_at'] ??
              envelope['created_at'],
        ),
        sequence: _parseInt(
          envelope['sequence'] ?? envelope['seq'] ?? envelope['offset'],
        ),
      ),
    );
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
    if (trimmed == 'ping' || trimmed == 'pong') {
      return trimmed;
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
    'sequence',
    'seq',
    'offset',
  };
  return <String, Object?>{
    for (final MapEntry<String, Object?> entry in envelope.entries)
      if (!envelopeKeys.contains(entry.key)) entry.key: entry.value,
  };
}

bool _isStatusOnlyEnvelope(
  Map<String, Object?> envelope,
  String normalizedType,
) {
  if (const <String>{
    'status',
    'connection_status',
    'connection_state',
    'sync_start',
    'sync_started',
    'sync_complete',
    'sync_completed',
    'error',
  }.contains(normalizedType)) {
    return true;
  }
  return !envelope.containsKey('payload') &&
      !envelope.containsKey('data') &&
      !envelope.containsKey('topic') &&
      !envelope.containsKey('channel') &&
      !envelope.containsKey('scope') &&
      (envelope.containsKey('status') || envelope.containsKey('state'));
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

int? _parseInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  final String? raw = _optionalString(value);
  return raw == null ? null : int.tryParse(raw);
}

bool _matchesTopic(String topic, Set<String> candidates) {
  return candidates.contains(_normalize(topic));
}

String _normalize(String value) {
  return value.trim().toLowerCase().replaceAll('-', '_');
}
