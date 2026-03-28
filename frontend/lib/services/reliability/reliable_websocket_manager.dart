import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/widgets.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

typedef ReliableWebSocketChannelFactory = WebSocketChannel Function(Uri uri);

enum ReliableWebSocketState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  paused,
  disposed,
}

class ReliableWebSocketManager with WidgetsBindingObserver {
  ReliableWebSocketManager({
    required this.socketUri,
    ReliableWebSocketChannelFactory? channelFactory,
    this.heartbeatInterval = const Duration(seconds: 30),
    this.heartbeatTimeout = const Duration(seconds: 10),
    this.initialReconnectDelay = const Duration(seconds: 1),
    this.maxReconnectDelay = const Duration(seconds: 30),
    this.onConnectionRestored,
  }) : _channelFactory = channelFactory ?? WebSocketChannel.connect {
    WidgetsBinding.instance.addObserver(this);
  }

  final Uri socketUri;
  final ReliableWebSocketChannelFactory _channelFactory;
  final Duration heartbeatInterval;
  final Duration heartbeatTimeout;
  final Duration initialReconnectDelay;
  final Duration maxReconnectDelay;
  final VoidCallback? onConnectionRestored;

  final StreamController<dynamic> _messageController =
      StreamController<dynamic>.broadcast();
  final StreamController<ReliableWebSocketState> _stateController =
      StreamController<ReliableWebSocketState>.broadcast(sync: true);

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _heartbeatTimer;
  Timer? _heartbeatTimeoutTimer;
  Timer? _reconnectTimer;
  bool _disposed = false;
  bool _pausedForLifecycle = false;
  bool _manualDisconnect = false;
  bool _connectionActive = false;
  int _reconnectAttempts = 0;
  ReliableWebSocketState _state = ReliableWebSocketState.disconnected;

  Stream<dynamic> get messages => _messageController.stream;

  Stream<ReliableWebSocketState> get connectionStates =>
      _stateController.stream;

  ReliableWebSocketState get state => _state;

  bool get isConnected => _state == ReliableWebSocketState.connected;

  void connect() {
    if (_disposed || _pausedForLifecycle) {
      return;
    }
    _manualDisconnect = false;
    if (_connectionActive) {
      return;
    }
    _openSocket(isReconnect: _reconnectAttempts > 0);
  }

  Future<void> disconnect() async {
    _manualDisconnect = true;
    _pausedForLifecycle = false;
    _reconnectAttempts = 0;
    _cancelReconnect();
    await _closeSocket();
    _emitState(ReliableWebSocketState.disconnected);
  }

  void reconnect() {
    if (_disposed) {
      return;
    }
    _manualDisconnect = false;
    _pausedForLifecycle = false;
    _cancelReconnect();
    unawaited(_closeSocket().whenComplete(connect));
  }

  void send(Object payload) {
    final WebSocketChannel? channel = _channel;
    if (channel == null) {
      return;
    }
    channel.sink.add(_encodeOutboundPayload(payload));
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_disposed) {
      return;
    }
    switch (state) {
      case AppLifecycleState.resumed:
        if (_pausedForLifecycle) {
          _pausedForLifecycle = false;
          reconnect();
        }
        return;
      case AppLifecycleState.inactive:
      case AppLifecycleState.hidden:
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
        _pausedForLifecycle = true;
        _manualDisconnect = false;
        _cancelReconnect();
        unawaited(
          _closeSocket().whenComplete(() {
            if (!_disposed) {
              _emitState(ReliableWebSocketState.paused);
            }
          }),
        );
        return;
    }
  }

  Future<void> dispose() async {
    if (_disposed) {
      return;
    }
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _cancelReconnect();
    await _closeSocket();
    _emitState(ReliableWebSocketState.disposed);
    await _messageController.close();
    await _stateController.close();
  }

  void _openSocket({required bool isReconnect}) {
    if (_disposed || _pausedForLifecycle || _connectionActive) {
      return;
    }
    _connectionActive = true;
    _emitState(
      isReconnect
          ? ReliableWebSocketState.reconnecting
          : ReliableWebSocketState.connecting,
    );
    try {
      final WebSocketChannel channel = _channelFactory(socketUri);
      _channel = channel;
      _subscription = channel.stream.listen(
        _handleMessage,
        onError: (_) => _handleDisconnect(),
        onDone: _handleDisconnect,
        cancelOnError: true,
      );
      _reconnectAttempts = 0;
      _startHeartbeat();
      _emitState(ReliableWebSocketState.connected);
      onConnectionRestored?.call();
    } catch (_) {
      _connectionActive = false;
      _scheduleReconnect();
    }
  }

  void _handleMessage(dynamic message) {
    _markHeartbeatResponse();
    if (_isHeartbeatPayload(message, expectedType: 'ping')) {
      _sendHeartbeatFrame('pong');
      return;
    }
    if (_isHeartbeatPayload(message, expectedType: 'pong')) {
      return;
    }
    _messageController.add(message);
  }

  void _handleDisconnect() {
    _connectionActive = false;
    _cancelHeartbeat();
    final WebSocketChannel? channel = _channel;
    _channel = null;
    unawaited(_subscription?.cancel());
    _subscription = null;
    unawaited(channel?.sink.close());

    if (_disposed) {
      return;
    }
    if (_pausedForLifecycle) {
      _emitState(ReliableWebSocketState.paused);
      return;
    }
    if (_manualDisconnect) {
      _emitState(ReliableWebSocketState.disconnected);
      return;
    }
    _scheduleReconnect();
  }

  Future<void> _closeSocket() async {
    _connectionActive = false;
    _cancelHeartbeat();
    final StreamSubscription<dynamic>? subscription = _subscription;
    final WebSocketChannel? channel = _channel;
    _subscription = null;
    _channel = null;
    await subscription?.cancel();
    await channel?.sink.close();
  }

  void _startHeartbeat() {
    _cancelHeartbeat();
    _heartbeatTimer = Timer.periodic(heartbeatInterval, (_) {
      _sendHeartbeatFrame('ping');
      _heartbeatTimeoutTimer?.cancel();
      _heartbeatTimeoutTimer = Timer(heartbeatTimeout, _handleHeartbeatMiss);
    });
  }

  void _markHeartbeatResponse() {
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = null;
  }

  void _handleHeartbeatMiss() {
    if (_disposed || _pausedForLifecycle || _manualDisconnect) {
      return;
    }
    _connectionActive = false;
    unawaited(_closeSocket().whenComplete(_scheduleReconnect));
  }

  void _sendHeartbeatFrame(String type) {
    final WebSocketChannel? channel = _channel;
    if (channel == null) {
      return;
    }
    channel.sink.add(
      jsonEncode(<String, Object?>{
        'type': type,
        'sent_at': DateTime.now().toUtc().toIso8601String(),
      }),
    );
  }

  void _scheduleReconnect() {
    if (_disposed || _pausedForLifecycle || _manualDisconnect) {
      return;
    }
    if (_reconnectTimer != null) {
      return;
    }
    _emitState(ReliableWebSocketState.reconnecting);
    _reconnectAttempts += 1;
    final Duration delay = _reconnectDelay(_reconnectAttempts);
    _reconnectTimer = Timer(delay, () {
      _reconnectTimer = null;
      _openSocket(isReconnect: true);
    });
  }

  Duration _reconnectDelay(int attempt) {
    final int safeAttempt = math.max(0, attempt - 1).clamp(0, 12);
    final int multiplier = 1 << safeAttempt;
    return Duration(
      milliseconds: math.min(
        initialReconnectDelay.inMilliseconds * multiplier,
        maxReconnectDelay.inMilliseconds,
      ),
    );
  }

  void _cancelHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = null;
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void _emitState(ReliableWebSocketState nextState) {
    if (_state == nextState) {
      return;
    }
    _state = nextState;
    if (!_stateController.isClosed) {
      _stateController.add(nextState);
    }
  }
}

Object _encodeOutboundPayload(Object payload) {
  if (payload is String || payload is List<int>) {
    return payload;
  }
  if (payload is Map || payload is Iterable) {
    return jsonEncode(payload);
  }
  return payload.toString();
}

bool _isHeartbeatPayload(dynamic message, {required String expectedType}) {
  if (message is String) {
    final String trimmed = message.trim();
    if (trimmed.toLowerCase() == expectedType) {
      return true;
    }
    try {
      final Object? decoded = jsonDecode(trimmed);
      if (decoded is Map) {
        final Object? type = decoded['type'];
        return type?.toString().trim().toLowerCase() == expectedType;
      }
    } catch (_) {
      return false;
    }
  }
  if (message is Map) {
    final Object? type = message['type'];
    return type?.toString().trim().toLowerCase() == expectedType;
  }
  return false;
}
