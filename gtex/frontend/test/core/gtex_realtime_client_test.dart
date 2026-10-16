import 'dart:async';
import 'dart:convert';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/runtime/gtex_realtime_client.dart';

void main() {
  test('multiplexes topics over one backend realtime stream', () async {
    final List<_FakeRealtimeSocket> sockets = <_FakeRealtimeSocket>[];
    final GtexRealtimeClient client = GtexRealtimeClient(
      apiBaseUrl: 'https://api.example.test',
      accessTokenProvider: () => 'token-1',
      socketFactory: (Uri uri) {
        final _FakeRealtimeSocket socket = _FakeRealtimeSocket(uri);
        sockets.add(socket);
        return socket;
      },
    );
    final List<Map<String, Object?>> matchEvents = <Map<String, Object?>>[];
    final List<Map<String, Object?>> marketEvents = <Map<String, Object?>>[];

    final StreamSubscription<Map<String, Object?>> matchSubscription = client
        .subscribeMatch('match-42')
        .listen(matchEvents.add);
    await _pump();

    expect(sockets, hasLength(1));
    expect(sockets.single.uri.scheme, 'wss');
    expect(sockets.single.uri.path, '/realtime/stream');
    expect(sockets.single.uri.queryParameters['token'], 'token-1');
    expect(
      sockets.single.uri.queryParameters['topics']!.split(','),
      containsAll(<String>['match:match-42', 'commentary:match-42']),
    );
    expect(_lastSentType(sockets.single), 'subscribe');

    final StreamSubscription<Map<String, Object?>> marketSubscription = client
        .subscribe('market')
        .listen(marketEvents.add);
    await _pump();

    expect(sockets, hasLength(1));
    expect(_lastSentTopics(sockets.single), <String>['market']);

    sockets.single.emitJson(<String, Object?>{
      'type': 'market_price_update',
      'data': <String, Object?>{'player_id': 'player-7'},
    });
    sockets.single.emitJson(<String, Object?>{
      'type': 'match_update',
      'data': <String, Object?>{'match_id': 'match-42', 'status': 'live'},
    });
    await _pump();

    expect(marketEvents, hasLength(1));
    expect(matchEvents, hasLength(1));
    expect(
      matchEvents.single['source_of_truth'],
      'persisted_backend_authority',
    );
    expect(
      matchEvents.single['runtime_source_tag'],
      'persisted_backend_authority',
    );
    expect(matchEvents.single['realtime_topics'], contains('match:match-42'));
    expect(
      matchEvents.single['realtime_provenance'],
      containsPair('transport', 'websocket'),
    );

    await marketSubscription.cancel();
    await _pump();
    expect(_lastSentType(sockets.single), 'unsubscribe');
    expect(_lastSentTopics(sockets.single), <String>['market']);

    await matchSubscription.cancel();
    await _pump();
    expect(sockets.single.closed, isTrue);

    await client.dispose();
  });

  test('fails closed when a stale realtime payload arrives', () async {
    final List<_FakeRealtimeSocket> sockets = <_FakeRealtimeSocket>[];
    final GtexRealtimeClient client = GtexRealtimeClient(
      apiBaseUrl: 'https://api.example.test',
      accessTokenProvider: () => null,
      socketFactory: (Uri uri) {
        final _FakeRealtimeSocket socket = _FakeRealtimeSocket(uri);
        sockets.add(socket);
        return socket;
      },
    );
    final List<Object> errors = <Object>[];

    client
        .subscribe('market')
        .listen((_) {}, onError: (Object error) => errors.add(error));
    await _pump();

    sockets.single.emitJson(<String, Object?>{
      'type': 'market_price_update',
      'payload_age_seconds': 60,
      'data': <String, Object?>{'player_id': 'player-8'},
    });
    await _pump();

    expect(errors.single, isA<StateError>());
    expect(sockets.single.closed, isTrue);

    await client.dispose();
  });

  test('refreshes auth and reconnects after an authenticated close', () async {
    final List<_FakeRealtimeSocket> sockets = <_FakeRealtimeSocket>[];
    String token = 'expired-token';
    int refreshCount = 0;
    final GtexRealtimeClient client = GtexRealtimeClient(
      apiBaseUrl: 'https://api.example.test',
      accessTokenProvider: () => token,
      authRefresh: () {
        refreshCount += 1;
        token = 'fresh-token';
        return token;
      },
      initialReconnectDelay: Duration.zero,
      maxReconnectDelay: Duration.zero,
      socketFactory: (Uri uri) {
        final _FakeRealtimeSocket socket = _FakeRealtimeSocket(uri);
        sockets.add(socket);
        return socket;
      },
    );

    final StreamSubscription<Map<String, Object?>> subscription = client
        .subscribe('wallet')
        .listen((_) {});
    await _pump();
    expect(sockets.single.uri.queryParameters['token'], 'expired-token');

    await sockets.single.closeFromServer(4401);
    await _pump(6);

    expect(refreshCount, 1);
    expect(sockets, hasLength(2));
    expect(sockets.last.uri.queryParameters['token'], 'fresh-token');

    await subscription.cancel();
    await client.dispose();
  });

  test(
    'uses refreshed auth when the token provider still has the rejected token',
    () async {
      final List<_FakeRealtimeSocket> sockets = <_FakeRealtimeSocket>[];
      int refreshCount = 0;
      final List<GtexRealtimeConnectionState> states =
          <GtexRealtimeConnectionState>[];
      final GtexRealtimeClient client = GtexRealtimeClient(
        apiBaseUrl: 'https://api.example.test',
        accessTokenProvider: () => 'expired-token',
        authRefresh: () {
          refreshCount += 1;
          return 'fresh-token';
        },
        initialReconnectDelay: Duration.zero,
        maxReconnectDelay: Duration.zero,
        socketFactory: (Uri uri) {
          final _FakeRealtimeSocket socket = _FakeRealtimeSocket(uri);
          sockets.add(socket);
          return socket;
        },
      );
      final StreamSubscription<GtexRealtimeConnectionState> stateSubscription =
          client.connectionStates.listen(states.add);

      final StreamSubscription<Map<String, Object?>> subscription = client
          .subscribe('wallet')
          .listen((_) {});
      await _pump();
      expect(sockets.single.uri.queryParameters['token'], 'expired-token');

      await sockets.single.closeFromServer(4401);
      await _pump(6);

      expect(refreshCount, 1);
      expect(sockets, hasLength(2));
      expect(sockets.last.uri.queryParameters['token'], 'fresh-token');
      expect(states, contains(GtexRealtimeConnectionState.reconnecting));
      expect(states.last, GtexRealtimeConnectionState.connected);

      await stateSubscription.cancel();
      await subscription.cancel();
      await client.dispose();
    },
  );

  test('sends heartbeat pings and accepts pong responses', () {
    fakeAsync((FakeAsync async) {
      final List<_FakeRealtimeSocket> sockets = <_FakeRealtimeSocket>[];
      final GtexRealtimeClient client = GtexRealtimeClient(
        apiBaseUrl: 'https://api.example.test',
        accessTokenProvider: () => null,
        heartbeatInterval: const Duration(seconds: 5),
        heartbeatTimeout: const Duration(seconds: 2),
        socketFactory: (Uri uri) {
          final _FakeRealtimeSocket socket = _FakeRealtimeSocket(uri);
          sockets.add(socket);
          return socket;
        },
      );

      final StreamSubscription<Map<String, Object?>> subscription = client
          .subscribe('competition')
          .listen((_) {});
      async.flushMicrotasks();

      async.elapse(const Duration(seconds: 5));
      expect(_lastSentType(sockets.single), 'ping');

      sockets.single.emitJson(<String, Object?>{'type': 'pong'});
      async.flushMicrotasks();
      async.elapse(const Duration(seconds: 2));
      expect(sockets, hasLength(1));

      unawaited(subscription.cancel());
      unawaited(client.dispose());
      async.flushMicrotasks();
    });
  });
}

Future<void> _pump([int count = 3]) async {
  for (int i = 0; i < count; i += 1) {
    await Future<void>.delayed(Duration.zero);
  }
}

String? _lastSentType(_FakeRealtimeSocket socket) {
  final Map<String, Object?>? payload = _lastSentPayload(socket);
  return payload?['type']?.toString();
}

List<String> _lastSentTopics(_FakeRealtimeSocket socket) {
  final Map<String, Object?>? payload = _lastSentPayload(socket);
  final Object? data = payload?['data'];
  if (data is! Map) {
    return const <String>[];
  }
  final Object? topics = data['topics'];
  if (topics is! List) {
    return const <String>[];
  }
  return topics.map((Object? value) => value.toString()).toList();
}

Map<String, Object?>? _lastSentPayload(_FakeRealtimeSocket socket) {
  if (socket.sent.isEmpty) {
    return null;
  }
  final Object? payload = socket.sent.last;
  if (payload is! String) {
    return null;
  }
  final Object? decoded = jsonDecode(payload);
  if (decoded is! Map) {
    return null;
  }
  return Map<String, Object?>.from(decoded);
}

class _FakeRealtimeSocket implements GtexRealtimeSocket {
  _FakeRealtimeSocket(this.uri);

  final Uri uri;
  final StreamController<dynamic> _messages =
      StreamController<dynamic>.broadcast(sync: true);
  final List<Object?> sent = <Object?>[];
  bool closed = false;
  int? _closeCode;
  String? _closeReason;

  @override
  Stream<dynamic> get stream => _messages.stream;

  @override
  Future<void> get ready => Future<void>.value();

  @override
  int? get closeCode => _closeCode;

  @override
  String? get closeReason => _closeReason;

  @override
  void add(Object? payload) {
    sent.add(payload);
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {
    closed = true;
    _closeCode = closeCode ?? _closeCode;
    _closeReason = closeReason ?? _closeReason;
    if (!_messages.isClosed) {
      await _messages.close();
    }
  }

  void emitJson(Map<String, Object?> payload) {
    _messages.add(jsonEncode(payload));
  }

  Future<void> closeFromServer([int? closeCode, String? closeReason]) async {
    closed = true;
    _closeCode = closeCode;
    _closeReason = closeReason;
    if (!_messages.isClosed) {
      await _messages.close();
    }
  }
}
