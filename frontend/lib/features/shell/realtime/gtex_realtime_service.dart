import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'gtex_realtime_models.dart';

typedef GtexRealtimeChannelFactory = WebSocketChannel Function(Uri uri);

abstract interface class GtexRealtimeClient {
  GtexRealtimeStatus get status;

  Stream<GtexRealtimeStatus> get statuses;

  Stream<GtexRealtimeEvent> get events;

  void connect([Uri? endpoint]);

  void send(Object payload);

  Future<void> disconnect();

  Future<void> dispose();
}

class GtexRealtimeService implements GtexRealtimeClient {
  GtexRealtimeService({
    Uri? socketUri,
    GtexRealtimeChannelFactory? channelFactory,
    this.reconnectDelay = const Duration(seconds: 2),
    this.maxReconnectAttempts = 6,
  }) : _socketUri = socketUri,
       _channelFactory = channelFactory ?? WebSocketChannel.connect;

  final Duration reconnectDelay;
  final int maxReconnectAttempts;
  final GtexRealtimeChannelFactory _channelFactory;

  final StreamController<GtexRealtimeStatus> _statusController =
      StreamController<GtexRealtimeStatus>.broadcast(sync: true);
  final StreamController<GtexRealtimeEvent> _eventController =
      StreamController<GtexRealtimeEvent>.broadcast();

  Uri? _socketUri;
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;
  bool _disposed = false;
  bool _manualDisconnect = false;
  bool _opening = false;
  int _reconnectAttempts = 0;
  GtexRealtimeStatus _status = GtexRealtimeStatus.disconnected;

  @override
  GtexRealtimeStatus get status => _status;

  @override
  Stream<GtexRealtimeStatus> get statuses => _statusController.stream;

  @override
  Stream<GtexRealtimeEvent> get events => _eventController.stream;

  Stream<GtexRealtimeStatus> get statusStream => statuses;

  Stream<GtexRealtimeEvent> get livePulseStream =>
      events.where((GtexRealtimeEvent event) => event.isLivePulse);

  Stream<GtexRealtimeEvent> get notificationStream =>
      events.where((GtexRealtimeEvent event) => event.isNotification);

  Stream<GtexRealtimeEvent> get activityStream =>
      events.where((GtexRealtimeEvent event) => event.isActivity);

  @override
  void connect([Uri? endpoint]) {
    if (endpoint != null) {
      _socketUri = endpoint;
    }
    if (_disposed || _opening || _channel != null) {
      return;
    }
    if (_socketUri == null) {
      _emitStatus(GtexRealtimeStatus.degraded);
      return;
    }
    _manualDisconnect = false;
    _openSocket(isReconnect: false);
  }

  @override
  void send(Object payload) {
    final WebSocketChannel? channel = _channel;
    if (channel == null) {
      return;
    }
    channel.sink.add(_encodePayload(payload));
  }

  void sendJson(Map<String, Object?> payload) {
    send(payload);
  }

  @override
  Future<void> disconnect() async {
    _manualDisconnect = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    await _closeSocket();
    _emitStatus(GtexRealtimeStatus.disconnected);
  }

  @override
  Future<void> dispose() async {
    if (_disposed) {
      return;
    }
    _disposed = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    await _closeSocket();
    _emitStatus(GtexRealtimeStatus.disconnected);
    await _statusController.close();
    await _eventController.close();
  }

  void _openSocket({required bool isReconnect}) {
    final Uri? socketUri = _socketUri;
    if (_disposed || socketUri == null || _channel != null) {
      return;
    }
    _opening = true;
    _emitStatus(
      isReconnect
          ? GtexRealtimeStatus.reconnecting
          : GtexRealtimeStatus.connecting,
    );
    try {
      final WebSocketChannel channel = _channelFactory(socketUri);
      _channel = channel;
      _subscription = channel.stream.listen(
        _handleMessage,
        onError: (_, __) => _handleDisconnect(fromError: true),
        onDone: () => _handleDisconnect(fromError: false),
        cancelOnError: true,
      );
      unawaited(
        channel.ready.then(
          (_) {
            if (_disposed || _channel != channel) {
              return;
            }
            _opening = false;
            _reconnectAttempts = 0;
            _emitStatus(GtexRealtimeStatus.live);
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

  void _handleMessage(dynamic message) {
    if (_isHeartbeat(message, expectedType: 'ping')) {
      send(<String, Object?>{
        'type': 'pong',
        'sent_at': DateTime.now().toUtc().toIso8601String(),
      });
      return;
    }
    if (_isHeartbeat(message, expectedType: 'pong')) {
      return;
    }
    final GtexRealtimeEvent? event = GtexRealtimeEvent.fromMessage(message);
    if (event == null) {
      return;
    }
    _applyStatusHint(event);
    if (!_eventController.isClosed) {
      _eventController.add(event);
    }
  }

  void _handleDisconnect({required bool fromError}) {
    if (_channel == null && !_opening) {
      return;
    }
    _opening = false;
    unawaited(_closeSocket());
    if (_disposed) {
      return;
    }
    if (_manualDisconnect) {
      _emitStatus(GtexRealtimeStatus.disconnected);
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
    _reconnectAttempts += 1;
    _emitStatus(
      _reconnectAttempts > maxReconnectAttempts
          ? GtexRealtimeStatus.degraded
          : fromError
          ? GtexRealtimeStatus.error
          : GtexRealtimeStatus.reconnecting,
    );
    if (_reconnectAttempts > maxReconnectAttempts) {
      return;
    }
    _reconnectTimer = Timer(reconnectDelay * _reconnectAttempts, () {
      _reconnectTimer = null;
      _openSocket(isReconnect: true);
    });
  }

  void _applyStatusHint(GtexRealtimeEvent event) {
    final Object? rawHint =
        event.payload['status'] ??
        event.payload['connection_status'] ??
        event.type;
    final String hint = _normalizedString(rawHint);
    final GtexRealtimeStatus? status = gtexRealtimeStatusFrom(rawHint);
    if (status != null) {
      _emitStatus(status);
      return;
    }
    switch (hint) {
      case 'sync_complete':
      case 'sync_completed':
        _emitStatus(GtexRealtimeStatus.live);
        return;
      default:
        return;
    }
  }

  void _emitStatus(GtexRealtimeStatus nextStatus) {
    if (_status == nextStatus) {
      return;
    }
    _status = nextStatus;
    if (!_statusController.isClosed) {
      _statusController.add(nextStatus);
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

bool _isHeartbeat(Object? message, {required String expectedType}) {
  final GtexRealtimeEvent? event = GtexRealtimeEvent.fromMessage(message);
  if (event == null) {
    return _normalizedString(message) == expectedType;
  }
  return _normalizedString(event.type) == expectedType;
}

String _normalizedString(Object? value) {
  return value?.toString().trim().toLowerCase().replaceAll('-', '_') ?? '';
}
