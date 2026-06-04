import 'dart:async';
import 'dart:convert';

import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'gtex_ws_reconnect_policy.dart';

typedef GtexWsChannelFactory = WebSocketChannel Function(Uri uri);
typedef GtexWsDecoder<T> = T? Function(Map<String, Object?> envelope);

enum GtexWsConnectionStatus {
  disconnected,
  connecting,
  live,
  reconnecting,
  degraded,
  error,
}

class GtexWsConnectionSnapshot<T> {
  const GtexWsConnectionSnapshot({
    required this.status,
    required this.attempt,
    this.lastKnown,
    this.nextRetryIn,
    this.message,
  });

  final GtexWsConnectionStatus status;
  final int attempt;
  final T? lastKnown;
  final Duration? nextRetryIn;
  final String? message;

  GtexSurfaceState<T> toSurfaceState() {
    return switch (status) {
      GtexWsConnectionStatus.disconnected =>
        lastKnown == null
            ? GtexEmpty<T>(reason: 'Realtime feed is disconnected.')
            : GtexPending<T>(stale: lastKnown),
      GtexWsConnectionStatus.connecting => GtexLoading<T>(),
      GtexWsConnectionStatus.live =>
        lastKnown == null
            ? GtexEmpty<T>(reason: 'Waiting for live data.')
            : GtexData<T>(data: lastKnown as T),
      GtexWsConnectionStatus.reconnecting => GtexReconnecting<T>(
        lastKnown: lastKnown,
        attempt: attempt,
      ),
      GtexWsConnectionStatus.degraded =>
        lastKnown == null
            ? GtexError<T>(
              code: 'realtime_degraded',
              message: message ?? 'Realtime feed is degraded.',
            )
            : GtexDegraded<T>(
              current: lastKnown as T,
              warning: message ?? 'Realtime feed is degraded.',
            ),
      GtexWsConnectionStatus.error => GtexError<T>(
        code: 'realtime_error',
        message: message ?? 'Realtime feed failed.',
      ),
    };
  }
}

class GtexWsMessage<T> {
  const GtexWsMessage({
    required this.type,
    required this.topic,
    required this.raw,
    this.data,
    this.timestamp,
  });

  final String type;
  final String topic;
  final Map<String, Object?> raw;
  final T? data;
  final DateTime? timestamp;
}

class GtexWsService<T> {
  GtexWsService({
    Uri? endpoint,
    Iterable<String> topics = const <String>[],
    GtexWsChannelFactory? channelFactory,
    GtexWsReconnectPolicy reconnectPolicy = const GtexWsReconnectPolicy(),
    GtexWsDecoder<T>? decoder,
    this.maxReconnectAttempts = 6,
    this.handshakeTimeout = const Duration(seconds: 10),
  }) : _endpoint = endpoint,
       _topics = List<String>.unmodifiable(
         topics
             .map((String topic) => topic.trim())
             .where((String topic) => topic.isNotEmpty),
       ),
       _channelFactory = channelFactory ?? WebSocketChannel.connect,
       _reconnectPolicy = reconnectPolicy,
       _decoder = decoder;

  final int maxReconnectAttempts;
  final Duration handshakeTimeout;
  final List<String> _topics;
  final GtexWsChannelFactory _channelFactory;
  final GtexWsReconnectPolicy _reconnectPolicy;
  final GtexWsDecoder<T>? _decoder;

  final StreamController<GtexWsConnectionSnapshot<T>> _snapshotController =
      StreamController<GtexWsConnectionSnapshot<T>>.broadcast(sync: true);
  final StreamController<GtexWsMessage<T>> _messageController =
      StreamController<GtexWsMessage<T>>.broadcast(sync: true);

  Uri? _endpoint;
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _handshakeTimer;
  Timer? _reconnectTimer;
  bool _disposed = false;
  bool _manualDisconnect = false;
  bool _opening = false;
  int _attempt = 0;
  T? _lastKnown;
  GtexWsConnectionStatus _status = GtexWsConnectionStatus.disconnected;

  GtexWsConnectionStatus get status => _status;

  int get reconnectAttempt => _attempt;

  T? get lastKnown => _lastKnown;

  GtexWsConnectionSnapshot<T> get snapshot => GtexWsConnectionSnapshot<T>(
    status: _status,
    attempt: _attempt,
    lastKnown: _lastKnown,
  );

  Stream<GtexWsConnectionSnapshot<T>> get snapshots =>
      _snapshotController.stream;

  Stream<GtexSurfaceState<T>> get surfaceStates =>
      snapshots.map((GtexWsConnectionSnapshot<T> value) {
        return value.toSurfaceState();
      });

  Stream<GtexWsMessage<T>> get messages => _messageController.stream;

  void connect([Uri? endpoint]) {
    if (endpoint != null) {
      _endpoint = endpoint;
    }
    if (_disposed || _opening || _channel != null) {
      return;
    }
    if (_endpoint == null) {
      _emit(
        GtexWsConnectionStatus.error,
        message: 'Realtime endpoint is missing.',
      );
      return;
    }
    _manualDisconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _openSocket(isReconnect: _attempt > 0);
  }

  void send(Object payload) {
    final WebSocketChannel? channel = _channel;
    if (channel == null || _disposed) {
      return;
    }
    channel.sink.add(_encodePayload(payload));
  }

  Future<void> disconnect() async {
    _manualDisconnect = true;
    _attempt = 0;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _handshakeTimer?.cancel();
    _handshakeTimer = null;
    await _closeSocket();
    _emit(GtexWsConnectionStatus.disconnected);
  }

  Future<void> dispose() async {
    if (_disposed) {
      return;
    }
    _disposed = true;
    _reconnectTimer?.cancel();
    _handshakeTimer?.cancel();
    await _closeSocket();
    await _snapshotController.close();
    await _messageController.close();
  }

  void _openSocket({required bool isReconnect}) {
    final Uri? endpoint = _endpoint;
    if (_disposed || endpoint == null || _channel != null) {
      return;
    }
    _opening = true;
    _emit(
      isReconnect
          ? GtexWsConnectionStatus.reconnecting
          : GtexWsConnectionStatus.connecting,
    );

    try {
      final WebSocketChannel channel = _channelFactory(endpoint);
      _channel = channel;
      _subscription = channel.stream.listen(
        _handleMessage,
        onDone: () => _handleDisconnect(fromError: false),
        onError: (_, __) => _handleDisconnect(fromError: true),
        cancelOnError: true,
      );
      _handshakeTimer = Timer(handshakeTimeout, () {
        if (_opening && _channel == channel) {
          _handleDisconnect(fromError: true);
        }
      });
      unawaited(
        channel.ready.then(
          (_) {
            if (_disposed || _channel != channel) {
              return;
            }
            _opening = false;
            _handshakeTimer?.cancel();
            _handshakeTimer = null;
            _attempt = 0;
            _emit(GtexWsConnectionStatus.live);
            _subscribe();
          },
          onError: (_) {
            if (_channel == channel) {
              _handleDisconnect(fromError: true);
            }
          },
        ),
      );
    } catch (_) {
      _opening = false;
      _scheduleReconnect(fromError: true);
    }
  }

  void _subscribe() {
    if (_topics.isEmpty) {
      return;
    }
    send(<String, Object?>{'type': 'subscribe', 'topics': _topics});
  }

  void _handleMessage(dynamic message) {
    final Object? decoded = _decodeMessage(message);
    if (decoded == 'ping') {
      send(<String, Object?>{
        'type': 'pong',
        'sent_at': DateTime.now().toUtc().toIso8601String(),
      });
      return;
    }
    if (decoded == 'pong') {
      return;
    }
    if (decoded is! Map) {
      _emit(
        GtexWsConnectionStatus.degraded,
        message: 'Realtime message is not a contract envelope.',
      );
      return;
    }

    final Map<String, Object?> envelope = _stringMap(decoded);
    final String type = _firstString(<Object?>[
      envelope['type'],
      envelope['event_type'],
      envelope['kind'],
    ], fallback: 'message');
    final String normalizedType = _normalize(type);
    if (normalizedType == 'ping') {
      send(<String, Object?>{
        'type': 'pong',
        'sent_at': DateTime.now().toUtc().toIso8601String(),
      });
      return;
    }
    if (normalizedType == 'pong') {
      return;
    }
    if (const <String>{
      'ack',
      'subscription_ack',
      'subscribed',
    }.contains(normalizedType)) {
      _emit(GtexWsConnectionStatus.live);
      return;
    }

    final T? data = _decodeData(envelope);
    if (data != null) {
      _lastKnown = data;
    }

    final GtexWsMessage<T> event = GtexWsMessage<T>(
      type: type,
      topic: _firstString(<Object?>[
        envelope['topic'],
        envelope['channel'],
        envelope['scope'],
      ], fallback: _topicFromType(type)),
      raw: envelope,
      data: data,
      timestamp: _parseTimestamp(
        envelope['timestamp'] ?? envelope['sent_at'] ?? envelope['created_at'],
      ),
    );
    _messageController.add(event);
    if (_status == GtexWsConnectionStatus.connecting ||
        _status == GtexWsConnectionStatus.reconnecting ||
        _status == GtexWsConnectionStatus.degraded) {
      _emit(GtexWsConnectionStatus.live);
    } else if (data != null) {
      _emit(_status);
    }
  }

  T? _decodeData(Map<String, Object?> envelope) {
    final GtexWsDecoder<T>? decoder = _decoder;
    if (decoder != null) {
      return decoder(envelope);
    }
    final Object? data = envelope['data'] ?? envelope['payload'];
    if (data is T) {
      return data;
    }
    return null;
  }

  void _handleDisconnect({required bool fromError}) {
    if (_channel == null && !_opening) {
      return;
    }
    _opening = false;
    _handshakeTimer?.cancel();
    _handshakeTimer = null;
    unawaited(_closeSocket());
    if (_disposed) {
      return;
    }
    if (_manualDisconnect) {
      _emit(GtexWsConnectionStatus.disconnected);
      return;
    }
    _scheduleReconnect(fromError: fromError);
  }

  Future<void> _closeSocket() async {
    _opening = false;
    final StreamSubscription<dynamic>? subscription = _subscription;
    final WebSocketChannel? channel = _channel;
    _subscription = null;
    _channel = null;
    await subscription?.cancel();
    await channel?.sink.close();
  }

  void _scheduleReconnect({required bool fromError}) {
    if (_disposed || _manualDisconnect || _reconnectTimer != null) {
      return;
    }
    _attempt += 1;
    if (_attempt > maxReconnectAttempts) {
      _emit(
        fromError
            ? GtexWsConnectionStatus.error
            : GtexWsConnectionStatus.degraded,
        message: 'Realtime reconnect attempts exhausted.',
      );
      return;
    }
    final Duration delay = _reconnectPolicy.delayForAttempt(_attempt);
    _emit(GtexWsConnectionStatus.reconnecting, nextRetryIn: delay);
    _reconnectTimer = Timer(delay, () {
      _reconnectTimer = null;
      _openSocket(isReconnect: true);
    });
  }

  void _emit(
    GtexWsConnectionStatus status, {
    Duration? nextRetryIn,
    String? message,
  }) {
    _status = status;
    final GtexWsConnectionSnapshot<T> next = GtexWsConnectionSnapshot<T>(
      status: status,
      attempt: _attempt,
      lastKnown: _lastKnown,
      nextRetryIn: nextRetryIn,
      message: message,
    );
    if (!_snapshotController.isClosed) {
      _snapshotController.add(next);
    }
  }
}

Object _encodePayload(Object payload) {
  if (payload is String || payload is List<int>) {
    return payload;
  }
  if (payload is Map || payload is Iterable) {
    return jsonEncode(payload);
  }
  return payload.toString();
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

String _firstString(List<Object?> values, {required String fallback}) {
  for (final Object? value in values) {
    final String text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return fallback;
}

String _topicFromType(String type) {
  final String normalized = _normalize(type);
  if (normalized.contains('notification')) {
    return 'notifications';
  }
  if (normalized.contains('activity') || normalized.contains('audit')) {
    return 'activity';
  }
  if (normalized.contains('market')) {
    return 'market';
  }
  if (normalized.contains('match')) {
    return 'match';
  }
  return 'system';
}

DateTime? _parseTimestamp(Object? value) {
  final String raw = value?.toString().trim() ?? '';
  return raw.isEmpty ? null : DateTime.tryParse(raw);
}

String _normalize(String value) {
  return value.trim().toLowerCase().replaceAll('-', '_');
}
