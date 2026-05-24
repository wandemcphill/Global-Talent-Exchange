import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

typedef GtexRealtimeAccessTokenProvider = FutureOr<String?> Function();
typedef GtexRealtimeAuthRefreshHook = FutureOr<String?> Function();
typedef GtexRealtimeSocketFactory = GtexRealtimeSocket Function(Uri uri);

enum GtexRealtimeConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  failed,
  disposed,
}

abstract interface class GtexRealtimeSocket {
  Stream<dynamic> get stream;
  Future<void> get ready;
  int? get closeCode;
  String? get closeReason;

  void add(Object? payload);
  Future<void> close([int? closeCode, String? closeReason]);
}

class GtexRealtimeClient {
  GtexRealtimeClient({
    required String apiBaseUrl,
    required GtexRealtimeAccessTokenProvider accessTokenProvider,
    GtexRealtimeAuthRefreshHook? authRefresh,
    WebSocketChannel Function(Uri uri)? connect,
    GtexRealtimeSocketFactory? socketFactory,
    Duration heartbeatInterval = const Duration(seconds: 25),
    Duration heartbeatTimeout = const Duration(seconds: 10),
    Duration initialReconnectDelay = const Duration(seconds: 1),
    Duration maxReconnectDelay = const Duration(seconds: 30),
    Duration stalePayloadThreshold = const Duration(seconds: 45),
    String sourceOfTruthTag = 'persisted_backend_authority',
    DateTime Function()? now,
  }) : _apiBaseUrl = apiBaseUrl,
       _accessTokenProvider = accessTokenProvider,
       _authRefresh = authRefresh,
       _socketFactory =
           socketFactory ??
           ((Uri uri) => _WebSocketGtexRealtimeSocket(
             (connect ?? WebSocketChannel.connect)(uri),
           )),
       _heartbeatInterval = heartbeatInterval,
       _heartbeatTimeout = heartbeatTimeout,
       _initialReconnectDelay = initialReconnectDelay,
       _maxReconnectDelay = maxReconnectDelay,
       _stalePayloadThreshold = stalePayloadThreshold,
       _sourceOfTruthTag = sourceOfTruthTag,
       _now = now ?? DateTime.now;

  final String _apiBaseUrl;
  final GtexRealtimeAccessTokenProvider _accessTokenProvider;
  final GtexRealtimeAuthRefreshHook? _authRefresh;
  final GtexRealtimeSocketFactory _socketFactory;
  final Duration _heartbeatInterval;
  final Duration _heartbeatTimeout;
  final Duration _initialReconnectDelay;
  final Duration _maxReconnectDelay;
  final Duration _stalePayloadThreshold;
  final String _sourceOfTruthTag;
  final DateTime Function() _now;

  final Map<int, _GtexRealtimeSubscription> _subscriptions =
      <int, _GtexRealtimeSubscription>{};
  final Map<String, num> _lastSequenceByTopic = <String, num>{};
  final StreamController<GtexRealtimeConnectionState>
  _connectionStateController =
      StreamController<GtexRealtimeConnectionState>.broadcast(sync: true);

  GtexRealtimeSocket? _socket;
  StreamSubscription<dynamic>? _socketSubscription;
  Timer? _heartbeat;
  Timer? _heartbeatTimeoutTimer;
  Timer? _reconnectTimer;
  bool _disposed = false;
  bool _connecting = false;
  bool _closingSocket = false;
  bool _refreshInFlight = false;
  int _nextSubscriptionId = 0;
  int _reconnectAttempts = 0;
  String? _refreshedAccessToken;
  String? _lastSocketAccessToken;
  String? _rejectedAccessToken;
  GtexRealtimeConnectionState _connectionState =
      GtexRealtimeConnectionState.disconnected;

  Stream<GtexRealtimeConnectionState> get connectionStates =>
      _connectionStateController.stream;

  GtexRealtimeConnectionState get connectionState => _connectionState;

  Stream<Map<String, Object?>> subscribe(String channel) {
    final Set<String> topics = _topicsForChannel(channel);
    if (topics.isEmpty) {
      return Stream<Map<String, Object?>>.error(
        StateError('Realtime channel "$channel" is not supported.'),
      );
    }
    late _GtexRealtimeSubscription subscription;
    late final StreamController<Map<String, Object?>> controller;
    controller = StreamController<Map<String, Object?>>(
      onListen: () {
        subscription = _retainSubscription(topics, controller);
      },
      onCancel: () => _releaseSubscription(subscription.id),
    );
    return controller.stream;
  }

  Stream<Map<String, Object?>> subscribeMatch(String matchId) {
    return subscribe('match:${matchId.trim()}');
  }

  Future<void> dispose() async {
    if (_disposed) {
      return;
    }
    _disposed = true;
    _cancelReconnect();
    _cancelHeartbeat();
    _emitConnectionState(GtexRealtimeConnectionState.disposed);
    final List<_GtexRealtimeSubscription> subscriptions = _subscriptions.values
        .toList(growable: false);
    _subscriptions.clear();
    for (final _GtexRealtimeSubscription subscription in subscriptions) {
      await subscription.controller.close();
    }
    await _closeSocket();
    await _connectionStateController.close();
  }

  _GtexRealtimeSubscription _retainSubscription(
    Set<String> topics,
    StreamController<Map<String, Object?>> controller,
  ) {
    if (_disposed) {
      controller.addError(
        StateError('Realtime client is closed and cannot subscribe.'),
      );
      unawaited(controller.close());
      return _GtexRealtimeSubscription(
        id: -1,
        topics: topics,
        controller: controller,
      );
    }
    final Set<String> previousTopics = _activeTopics();
    final _GtexRealtimeSubscription subscription = _GtexRealtimeSubscription(
      id: _nextSubscriptionId++,
      topics: topics,
      controller: controller,
    );
    _subscriptions[subscription.id] = subscription;
    final Set<String> nextTopics = _activeTopics();
    final Set<String> addedTopics = nextTopics.difference(previousTopics);
    if (_socket == null) {
      _ensureConnected();
    } else if (addedTopics.isNotEmpty) {
      _sendCommand('subscribe', addedTopics);
    }
    return subscription;
  }

  Future<void> _releaseSubscription(int id) async {
    if (id < 0) {
      return;
    }
    final Set<String> previousTopics = _activeTopics();
    _subscriptions.remove(id);
    final Set<String> nextTopics = _activeTopics();
    final Set<String> removedTopics = previousTopics.difference(nextTopics);
    if (removedTopics.isNotEmpty && _socket != null) {
      _sendCommand('unsubscribe', removedTopics);
    }
    if (_subscriptions.isEmpty) {
      _cancelReconnect();
      await _closeSocket();
      _lastSequenceByTopic.clear();
      _emitConnectionState(GtexRealtimeConnectionState.disconnected);
    }
  }

  void _ensureConnected() {
    if (_disposed || _connecting || _socket != null || _subscriptions.isEmpty) {
      return;
    }
    _connecting = true;
    unawaited(_openSocket());
  }

  Future<void> _openSocket() async {
    _emitConnectionState(
      _reconnectAttempts > 0
          ? GtexRealtimeConnectionState.reconnecting
          : GtexRealtimeConnectionState.connecting,
    );
    try {
      final Uri uri = await _streamUri(_activeTopics());
      if (_disposed || _subscriptions.isEmpty) {
        return;
      }
      final GtexRealtimeSocket socket = _socketFactory(uri);
      _socket = socket;
      await socket.ready;
      if (_disposed || _subscriptions.isEmpty || !identical(_socket, socket)) {
        await socket.close();
        return;
      }
      _socketSubscription = socket.stream.listen(
        _handleRawMessage,
        onError: _handleSocketError,
        onDone: _handleSocketDone,
        cancelOnError: true,
      );
      _reconnectAttempts = 0;
      _emitConnectionState(GtexRealtimeConnectionState.connected);
      _startHeartbeat();
      final Set<String> topics = _activeTopics();
      if (topics.isNotEmpty) {
        _sendCommand('subscribe', topics);
      }
    } catch (error, stackTrace) {
      _scheduleReconnect(error, stackTrace);
    } finally {
      _connecting = false;
    }
  }

  Future<Uri> _streamUri(Set<String> topics) async {
    final Uri base = Uri.parse(_apiBaseUrl);
    if (!base.hasScheme || base.host.trim().isEmpty) {
      throw StateError('A live API base URL is required for realtime.');
    }
    final String scheme = switch (base.scheme) {
      'https' => 'wss',
      'http' => 'ws',
      'ws' || 'wss' => base.scheme,
      _ => 'wss',
    };
    final String accessToken = (await _accessToken()).trim();
    _lastSocketAccessToken = accessToken;
    final Map<String, String> query = <String, String>{
      if (topics.isNotEmpty) 'topics': topics.join(','),
      if (accessToken.isNotEmpty) 'token': accessToken,
    };
    return base.replace(
      scheme: scheme,
      path: '/realtime/stream',
      queryParameters: query.isEmpty ? null : query,
    );
  }

  Future<String> _accessToken() async {
    final String? providedToken = await _accessTokenProvider();
    final String provided = providedToken?.trim() ?? '';
    final String refreshed = _refreshedAccessToken?.trim() ?? '';
    final String rejected = _rejectedAccessToken?.trim() ?? '';
    if (refreshed.isNotEmpty &&
        (provided.isEmpty || (rejected.isNotEmpty && provided == rejected))) {
      return refreshed;
    }
    if (provided.isNotEmpty) {
      if (rejected.isNotEmpty && provided == rejected) {
        return '';
      }
      _refreshedAccessToken = null;
      _rejectedAccessToken = null;
      return provided;
    }
    return refreshed;
  }

  Map<String, Object?>? _decodeEvent(Object? raw) {
    if (raw is Map<String, Object?>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, Object?>.from(raw);
    }
    if (raw is String && raw.trim().isNotEmpty) {
      final Object? decoded = jsonDecode(raw);
      if (decoded is Map) {
        return Map<String, Object?>.from(decoded);
      }
    }
    return null;
  }

  void _handleRawMessage(dynamic raw) {
    try {
      _markHeartbeatResponse();
      if (_isHeartbeatPayload(raw, expectedType: 'ping')) {
        _sendRaw(jsonEncode(<String, Object?>{'type': 'pong'}));
        return;
      }
      if (_isHeartbeatPayload(raw, expectedType: 'pong')) {
        return;
      }
      final Map<String, Object?>? event = _decodeEvent(raw);
      if (event == null) {
        throw StateError('Malformed realtime payload rejected.');
      }
      final String type = _typeOf(event);
      if (type == 'subscription_ack') {
        return;
      }
      _validateLiveEvent(event);
      final Set<String> eventTopics = _topicsForEvent(event);
      if (eventTopics.isEmpty) {
        throw StateError('Unscoped realtime payload rejected.');
      }
      _rejectStaleSequence(event, eventTopics);
      final Map<String, Object?> taggedEvent = _tagEvent(event, eventTopics);
      _deliver(taggedEvent, eventTopics);
    } catch (error, stackTrace) {
      _failClosed(error, stackTrace);
    }
  }

  void _deliver(Map<String, Object?> event, Set<String> eventTopics) {
    for (final _GtexRealtimeSubscription subscription in _subscriptions.values
        .toList(growable: false)) {
      if (!subscription.topics.any(eventTopics.contains)) {
        continue;
      }
      if (!subscription.controller.isClosed) {
        subscription.controller.add(event);
      }
    }
  }

  Map<String, Object?> _tagEvent(
    Map<String, Object?> event,
    Set<String> eventTopics,
  ) {
    final List<String> topics = eventTopics.toList(growable: false)..sort();
    return <String, Object?>{
      ...event,
      'source_of_truth': _sourceOfTruthTag,
      'runtime_source': _sourceOfTruthTag,
      'runtime_source_tag': _sourceOfTruthTag,
      'realtime_topics': topics,
      'realtime_received_at': _now().toUtc().toIso8601String(),
      'realtime_provenance': <String, Object?>{
        'transport': 'websocket',
        'source_of_truth': _sourceOfTruthTag,
        'topics': topics,
      },
    };
  }

  void _validateLiveEvent(Map<String, Object?> event) {
    final Map<String, Object?> data = _mapValue(event['data']);
    final Map<String, Object?> metadata = _mapValue(
      data['metadata'] ?? event['metadata'],
    );
    final String normalizedSourceOfTruth =
        _firstNonEmptyObject(<Object?>[
          event['source_of_truth'],
          data['source_of_truth'],
        ])?.trim().toLowerCase() ??
        '';
    final List<String> normalizedSources = <Object?>[
          event['runtime_source'],
          data['runtime_source'],
          event['source'],
          data['source'],
          metadata['source'],
        ]
        .map((Object? value) => value?.toString().trim().toLowerCase() ?? '')
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);
    final bool sourceOfTruthMismatch =
        normalizedSourceOfTruth.isNotEmpty &&
        normalizedSourceOfTruth != _sourceOfTruthTag.toLowerCase();
    final bool fixtureLike = normalizedSources.any(_isFixtureLikeSource);
    if (sourceOfTruthMismatch ||
        fixtureLike ||
        _flaggedAsFixture(event, data)) {
      throw StateError(
        'Synthetic realtime payload rejected in strict-live runtime.',
      );
    }
    final Object? stale =
        event['stale'] ??
        event['is_stale'] ??
        data['stale'] ??
        data['is_stale'];
    final Object? ageSeconds =
        event['payload_age_seconds'] ??
        event['age_seconds'] ??
        data['payload_age_seconds'] ??
        data['age_seconds'];
    final num? parsedAge =
        ageSeconds is num ? ageSeconds : num.tryParse('$ageSeconds');
    if (stale == true ||
        (parsedAge != null && parsedAge > _stalePayloadThreshold.inSeconds) ||
        _isTimestampStale(event, data)) {
      throw StateError(
        'Stale realtime payload rejected in strict-live runtime.',
      );
    }
  }

  bool _isFixtureLikeSource(String normalizedSource) {
    return normalizedSource == 'demo' ||
        normalizedSource == 'fixture' ||
        normalizedSource == 'synthetic' ||
        normalizedSource.startsWith('demo') ||
        normalizedSource.startsWith('fixture') ||
        normalizedSource.contains('mock');
  }

  void _rejectStaleSequence(
    Map<String, Object?> event,
    Set<String> eventTopics,
  ) {
    final Map<String, Object?> data = _mapValue(event['data']);
    final Object? rawSequence =
        event['sequence'] ??
        event['cursor'] ??
        data['sequence'] ??
        data['cursor'];
    final num? sequence =
        rawSequence is num ? rawSequence : num.tryParse('$rawSequence');
    if (sequence == null) {
      return;
    }
    for (final String topic in eventTopics) {
      final num? previous = _lastSequenceByTopic[topic];
      if (previous != null && sequence <= previous) {
        throw StateError(
          'Out-of-order realtime payload rejected for topic $topic.',
        );
      }
    }
    for (final String topic in eventTopics) {
      _lastSequenceByTopic[topic] = sequence;
    }
  }

  bool _isTimestampStale(
    Map<String, Object?> event,
    Map<String, Object?> data,
  ) {
    final String? rawTimestamp = _firstNonEmptyObject(<Object?>[
      event['published_at'],
      event['occurred_at'],
      event['created_at'],
      data['published_at'],
      data['occurred_at'],
      data['created_at'],
    ]);
    if (rawTimestamp == null) {
      return false;
    }
    final DateTime? parsed = DateTime.tryParse(rawTimestamp);
    if (parsed == null) {
      throw StateError('Invalid realtime timestamp rejected.');
    }
    final Duration age = _now().toUtc().difference(parsed.toUtc());
    return age > _stalePayloadThreshold;
  }

  bool _flaggedAsFixture(
    Map<String, Object?> event,
    Map<String, Object?> data,
  ) {
    return _truthy(event['fixture']) ||
        _truthy(event['demo']) ||
        _truthy(event['synthetic']) ||
        _truthy(data['fixture']) ||
        _truthy(data['demo']) ||
        _truthy(data['synthetic']);
  }

  void _handleSocketError(Object error, StackTrace stackTrace) {
    _scheduleReconnect(error, stackTrace);
  }

  void _handleSocketDone() {
    final GtexRealtimeSocket? socket = _socket;
    final int? closeCode = socket?.closeCode;
    _socket = null;
    _cancelHeartbeat();
    unawaited(_socketSubscription?.cancel());
    _socketSubscription = null;
    if (_closingSocket || _disposed || _subscriptions.isEmpty) {
      if (!_disposed && _subscriptions.isEmpty) {
        _emitConnectionState(GtexRealtimeConnectionState.disconnected);
      }
      return;
    }
    if (_isAuthCloseCode(closeCode)) {
      _rejectedAccessToken = _lastSocketAccessToken?.trim();
      _emitConnectionState(GtexRealtimeConnectionState.reconnecting);
      unawaited(_refreshAuthThenReconnect());
      return;
    }
    _scheduleReconnect(
      StateError('Realtime socket closed unexpectedly.'),
      StackTrace.current,
    );
  }

  Future<void> _refreshAuthThenReconnect() async {
    if (_refreshInFlight) {
      return;
    }
    _refreshInFlight = true;
    try {
      final GtexRealtimeAuthRefreshHook? refresh = _authRefresh;
      if (refresh == null) {
        _failClosed(
          StateError(
            'Realtime authentication failed and no refresh hook exists.',
          ),
          StackTrace.current,
        );
        return;
      }
      final String? nextToken = await refresh();
      final String token = nextToken?.trim() ?? '';
      if (token.isNotEmpty) {
        _refreshedAccessToken = token;
      }
      if ((await _accessToken()).trim().isEmpty) {
        _failClosed(
          StateError(
            'Realtime authentication refresh did not produce a token.',
          ),
          StackTrace.current,
        );
        return;
      }
      _scheduleReconnect(null, null, immediate: true);
    } catch (error, stackTrace) {
      _failClosed(error, stackTrace);
    } finally {
      _refreshInFlight = false;
    }
  }

  void _scheduleReconnect(
    Object? error,
    StackTrace? stackTrace, {
    bool immediate = false,
  }) {
    if (_disposed || _subscriptions.isEmpty) {
      return;
    }
    if (error is StateError &&
        error.message.contains('live API base URL is required')) {
      _failClosed(error, stackTrace ?? StackTrace.current);
      return;
    }
    _emitConnectionState(GtexRealtimeConnectionState.reconnecting);
    _cancelHeartbeat();
    unawaited(_closeSocket());
    if (_reconnectTimer != null) {
      return;
    }
    _reconnectAttempts += 1;
    final Duration delay =
        immediate ? Duration.zero : _reconnectDelay(_reconnectAttempts);
    _reconnectTimer = Timer(delay, () {
      _reconnectTimer = null;
      _ensureConnected();
    });
  }

  Duration _reconnectDelay(int attempt) {
    final int safeAttempt = (attempt - 1).clamp(0, 12).toInt();
    final int multiplier = 1 << safeAttempt;
    final int delayMilliseconds =
        (_initialReconnectDelay.inMilliseconds * multiplier)
            .clamp(
              _initialReconnectDelay.inMilliseconds,
              _maxReconnectDelay.inMilliseconds,
            )
            .toInt();
    return Duration(milliseconds: delayMilliseconds);
  }

  void _startHeartbeat() {
    _cancelHeartbeat();
    _heartbeat = Timer.periodic(_heartbeatInterval, (_) {
      _sendRaw(jsonEncode(<String, Object?>{'type': 'ping'}));
      _heartbeatTimeoutTimer?.cancel();
      _heartbeatTimeoutTimer = Timer(_heartbeatTimeout, () {
        _scheduleReconnect(
          StateError('Realtime heartbeat timed out.'),
          StackTrace.current,
        );
      });
    });
  }

  void _markHeartbeatResponse() {
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = null;
  }

  void _sendCommand(String type, Set<String> topics) {
    if (topics.isEmpty) {
      return;
    }
    _sendRaw(
      jsonEncode(<String, Object?>{
        'type': type,
        'data': <String, Object?>{'topics': topics.toList(growable: false)},
      }),
    );
  }

  void _sendRaw(Object payload) {
    final GtexRealtimeSocket? socket = _socket;
    if (socket == null) {
      return;
    }
    socket.add(payload);
  }

  Future<void> _closeSocket() async {
    final GtexRealtimeSocket? socket = _socket;
    final StreamSubscription<dynamic>? subscription = _socketSubscription;
    _socket = null;
    _socketSubscription = null;
    _cancelHeartbeat();
    if (socket == null && subscription == null) {
      return;
    }
    _closingSocket = true;
    try {
      await subscription?.cancel();
      await socket?.close();
    } finally {
      _closingSocket = false;
    }
  }

  void _cancelHeartbeat() {
    _heartbeat?.cancel();
    _heartbeat = null;
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = null;
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void _failClosed(Object error, StackTrace stackTrace) {
    _disposed = true;
    _cancelReconnect();
    _cancelHeartbeat();
    _emitConnectionState(GtexRealtimeConnectionState.failed);
    unawaited(_closeSocket());
    final List<_GtexRealtimeSubscription> subscriptions = _subscriptions.values
        .toList(growable: false);
    _subscriptions.clear();
    for (final _GtexRealtimeSubscription subscription in subscriptions) {
      if (!subscription.controller.isClosed) {
        subscription.controller.addError(error, stackTrace);
        unawaited(subscription.controller.close());
      }
    }
    unawaited(_connectionStateController.close());
  }

  void _emitConnectionState(GtexRealtimeConnectionState nextState) {
    if (_connectionState == nextState || _connectionStateController.isClosed) {
      return;
    }
    _connectionState = nextState;
    _connectionStateController.add(nextState);
  }

  Set<String> _activeTopics() {
    return <String>{
      for (final _GtexRealtimeSubscription subscription
          in _subscriptions.values)
        ...subscription.topics,
    };
  }

  Set<String> _topicsForChannel(String channel) {
    final String normalized = channel.trim().replaceFirst(RegExp(r'^/+'), '');
    if (normalized.isEmpty) {
      return const <String>{};
    }
    if (normalized == 'market' ||
        normalized == 'competition' ||
        normalized == 'wallet' ||
        normalized.startsWith('wallet:')) {
      return <String>{normalized};
    }
    if (normalized.startsWith('commentary:')) {
      return <String>{normalized};
    }
    if (normalized.startsWith('match:')) {
      final String matchId = normalized.substring('match:'.length);
      final String cleanedMatchId =
          matchId.endsWith(':events')
              ? matchId.substring(0, matchId.length - ':events'.length)
              : matchId;
      return _matchTopics(cleanedMatchId);
    }
    final List<String> parts = normalized.split('/');
    if (parts.length >= 2 &&
        (parts.first == 'match' || parts.first == 'matches')) {
      return _matchTopics(parts[1]);
    }
    if (parts.length >= 2 && parts.first == 'commentary') {
      return <String>{'commentary:${parts[1].trim()}'};
    }
    return <String>{normalized};
  }

  Set<String> _matchTopics(String matchId) {
    final String resolved = matchId.trim();
    if (resolved.isEmpty) {
      return const <String>{};
    }
    return <String>{'match:$resolved', 'commentary:$resolved'};
  }

  Set<String> _topicsForEvent(Map<String, Object?> event) {
    final Map<String, Object?> data = _mapValue(event['data']);
    final Set<String> topics = <String>{};

    void addTopic(Object? value) {
      final String? topic = value?.toString().trim();
      if (topic == null || topic.isEmpty) {
        return;
      }
      if (topic.startsWith('match:') && topic.endsWith(':events')) {
        final String matchId = topic.substring(
          'match:'.length,
          topic.length - ':events'.length,
        );
        topics.add('match:$matchId');
        return;
      }
      topics.add(topic);
    }

    void addTopics(Object? value) {
      if (value is Iterable) {
        for (final Object? topic in value) {
          addTopic(topic);
        }
        return;
      }
      if (value is String && value.contains(',')) {
        for (final String topic in value.split(',')) {
          addTopic(topic);
        }
        return;
      }
      addTopic(value);
    }

    addTopic(event['topic']);
    addTopic(event['channel']);
    addTopics(event['topics']);
    addTopics(event['channels']);
    addTopic(data['topic']);
    addTopic(data['channel']);
    addTopics(data['topics']);
    addTopics(data['channels']);
    final String type = _typeOf(event);
    final String? matchId = _firstNonEmptyObject(<Object?>[
      data['match_id'],
      data['matchId'],
      event['match_id'],
      event['matchId'],
    ]);
    if (matchId != null) {
      if (type == 'commentary') {
        topics.add('commentary:$matchId');
      } else {
        topics.add('match:$matchId');
      }
    }
    if (type == 'market_price_update') {
      topics.add('market');
    }
    if (type == 'competition_update') {
      topics.add('competition');
    }
    if (type == 'wallet_update' ||
        type == 'jackpot_triggered' ||
        type == 'notification') {
      topics.add('wallet');
      final String? userId = _firstNonEmptyObject(<Object?>[
        data['user_id'],
        data['userId'],
        event['user_id'],
        event['userId'],
      ]);
      if (userId != null) {
        topics.add('wallet:$userId');
      }
    }
    return topics;
  }

  String _typeOf(Map<String, Object?> event) {
    return (event['type'] ?? event['message_type'] ?? '')
        .toString()
        .trim()
        .toLowerCase();
  }

  bool _isAuthCloseCode(int? closeCode) {
    return closeCode == 4401 || closeCode == 4403;
  }
}

class _GtexRealtimeSubscription {
  const _GtexRealtimeSubscription({
    required this.id,
    required this.topics,
    required this.controller,
  });

  final int id;
  final Set<String> topics;
  final StreamController<Map<String, Object?>> controller;
}

class _WebSocketGtexRealtimeSocket implements GtexRealtimeSocket {
  const _WebSocketGtexRealtimeSocket(this._channel);

  final WebSocketChannel _channel;

  @override
  Stream<dynamic> get stream => _channel.stream;

  @override
  Future<void> get ready => _channel.ready;

  @override
  int? get closeCode => _channel.closeCode;

  @override
  String? get closeReason => _channel.closeReason;

  @override
  void add(Object? payload) {
    _channel.sink.add(payload);
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) {
    return _channel.sink.close(closeCode, closeReason);
  }
}

String? _firstNonEmptyObject(Iterable<Object?> values) {
  for (final Object? value in values) {
    final String resolved = value?.toString().trim() ?? '';
    if (resolved.isNotEmpty) {
      return resolved;
    }
  }
  return null;
}

Map<String, Object?> _mapValue(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? entryValue) =>
          MapEntry<String, Object?>(key.toString(), entryValue),
    );
  }
  return const <String, Object?>{};
}

bool _truthy(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  return normalized == 'true' || normalized == '1' || normalized == 'yes';
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
