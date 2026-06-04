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

class GtexRealtimeBackoffPolicy {
  const GtexRealtimeBackoffPolicy({
    this.initialDelay = const Duration(seconds: 1),
    this.maxDelay = const Duration(seconds: 30),
    this.multiplier = 2,
  });

  final Duration initialDelay;
  final Duration maxDelay;
  final int multiplier;

  Duration delayForAttempt(int attempt) {
    if (attempt <= 1) {
      return initialDelay;
    }
    int factor = 1;
    for (int index = 1; index < attempt; index += 1) {
      factor *= multiplier;
    }
    final Duration delay = initialDelay * factor;
    return delay > maxDelay ? maxDelay : delay;
  }
}

class GtexRealtimeService implements GtexRealtimeClient {
  GtexRealtimeService({
    Uri? socketUri,
    Iterable<String> topics = const <String>[],
    GtexRealtimeChannelFactory? channelFactory,
    GtexRealtimeBackoffPolicy backoffPolicy = const GtexRealtimeBackoffPolicy(),
    this.maxReconnectAttempts = 6,
    this.handshakeTimeout = const Duration(seconds: 10),
  }) : _socketUri = socketUri,
       _topics = List<String>.unmodifiable(
         topics
             .map((String topic) => topic.trim())
             .where((String topic) => topic.isNotEmpty),
       ),
       _backoffPolicy = backoffPolicy,
       _channelFactory = channelFactory ?? WebSocketChannel.connect;

  final int maxReconnectAttempts;
  final Duration handshakeTimeout;
  final GtexRealtimeChannelFactory _channelFactory;
  final GtexRealtimeBackoffPolicy _backoffPolicy;
  final List<String> _topics;

  final StreamController<GtexRealtimeStatus> _statusController =
      StreamController<GtexRealtimeStatus>.broadcast(sync: true);
  final StreamController<GtexRealtimeEvent> _eventController =
      StreamController<GtexRealtimeEvent>.broadcast();

  Uri? _socketUri;
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _handshakeTimer;
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
      _emitStatus(GtexRealtimeStatus.error);
      return;
    }
    _manualDisconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _openSocket(isReconnect: _reconnectAttempts > 0);
  }

  @override
  void send(Object payload) {
    final WebSocketChannel? channel = _channel;
    if (channel == null || _disposed) {
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
    _handshakeTimer?.cancel();
    _handshakeTimer = null;
    _reconnectAttempts = 0;
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
    _handshakeTimer?.cancel();
    _handshakeTimer = null;
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
            _reconnectAttempts = 0;
            _emitStatus(
              _topics.isEmpty
                  ? GtexRealtimeStatus.live
                  : GtexRealtimeStatus.syncing,
            );
            _sendSubscribe();
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

  void _sendSubscribe() {
    if (_topics.isEmpty) {
      return;
    }
    send(<String, Object?>{'type': 'subscribe', 'topics': _topics});
  }

  void _handleMessage(dynamic message) {
    final GtexRealtimeInboundMessage parsed = GtexRealtimeContractParser.parse(
      message,
    );
    switch (parsed.kind) {
      case GtexRealtimeInboundKind.heartbeatPing:
        send(<String, Object?>{
          'type': 'pong',
          'sent_at': DateTime.now().toUtc().toIso8601String(),
        });
        return;
      case GtexRealtimeInboundKind.heartbeatPong:
        return;
      case GtexRealtimeInboundKind.subscriptionAck:
        _emitStatus(GtexRealtimeStatus.live);
        return;
      case GtexRealtimeInboundKind.status:
        _emitStatus(parsed.status ?? GtexRealtimeStatus.live);
        return;
      case GtexRealtimeInboundKind.invalid:
        _emitStatus(GtexRealtimeStatus.degraded);
        return;
      case GtexRealtimeInboundKind.event:
        final GtexRealtimeEvent? event = parsed.event;
        if (event == null) {
          _emitStatus(GtexRealtimeStatus.degraded);
          return;
        }
        final GtexRealtimeStatus? status = parsed.status ?? event.statusHint;
        if (status != null) {
          _emitStatus(status);
        } else if (_status == GtexRealtimeStatus.syncing ||
            _status == GtexRealtimeStatus.connecting ||
            _status == GtexRealtimeStatus.reconnecting) {
          _emitStatus(GtexRealtimeStatus.live);
        }
        if (!_eventController.isClosed) {
          _eventController.add(event);
        }
        return;
    }
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
    if (_reconnectAttempts > maxReconnectAttempts) {
      _emitStatus(
        fromError ? GtexRealtimeStatus.error : GtexRealtimeStatus.degraded,
      );
      return;
    }
    _emitStatus(GtexRealtimeStatus.reconnecting);
    final Duration delay = _backoffPolicy.delayForAttempt(_reconnectAttempts);
    _reconnectTimer = Timer(delay, () {
      _reconnectTimer = null;
      _openSocket(isReconnect: true);
    });
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
