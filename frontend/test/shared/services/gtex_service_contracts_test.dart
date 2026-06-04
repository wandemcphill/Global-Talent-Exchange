import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/services/api/api.dart';
import 'package:gte_frontend/services/audit/audit.dart';
import 'package:gte_frontend/services/websocket/websocket.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GtexDioClient', () {
    test('attaches bearer token and maps backend error envelopes', () async {
      final Dio dio = GtexDioClient.create(
        baseUrl: 'https://api.gtex.test/v1',
        accessTokenProvider: () => 'token-1',
      );
      final _QueuedDioAdapter adapter = _QueuedDioAdapter(<_DioReply>[
        (RequestOptions options) {
          expect(options.headers['Authorization'], 'Bearer token-1');
          expect(options.headers['X-GTEX-Client'], 'flutter');
          return _jsonResponse(
            409,
            <String, Object?>{
              'code': 'admin_lock_conflict',
              'message': 'Admin item is locked by another actor.',
            },
            headers: <String, List<String>>{
              'x-request-id': <String>['req-7'],
            },
          );
        },
      ]);
      dio.httpClientAdapter = adapter;

      await expectLater(
        dio.get<dynamic>('/admin/items/locked'),
        throwsA(
          isA<DioException>().having(
            (DioException error) {
              return error.error;
            },
            'mapped error',
            isA<GtexApiException>()
                .having(
                  (GtexApiException error) => error.code,
                  'code',
                  'admin_lock_conflict',
                )
                .having(
                  (GtexApiException error) => error.requestId,
                  'requestId',
                  'req-7',
                ),
          ),
        ),
      );
    });

    test('refreshes a 401 once and retries the original request', () async {
      int refreshCount = 0;
      final Dio dio = GtexDioClient.create(
        baseUrl: 'https://api.gtex.test/v1',
        accessTokenProvider: () => 'token-1',
        refreshToken: () {
          refreshCount += 1;
          return 'token-2';
        },
      );
      final _QueuedDioAdapter adapter = _QueuedDioAdapter(<_DioReply>[
        (RequestOptions options) {
          expect(options.headers['Authorization'], 'Bearer token-1');
          return _jsonResponse(401, <String, Object?>{
            'code': 'token_expired',
            'message': 'Expired',
          });
        },
        (RequestOptions options) {
          expect(options.headers['Authorization'], 'Bearer token-2');
          return _jsonResponse(200, <String, Object?>{'ok': true});
        },
      ]);
      dio.httpClientAdapter = adapter;

      final Response<dynamic> response = await dio.get<dynamic>('/secure');

      expect(refreshCount, 1);
      expect(adapter.requests, hasLength(2));
      expect(response.data, <String, Object?>{'ok': true});
    });
  });

  group('GtexWsService', () {
    test('uses blueprint exponential backoff sequence', () {
      const GtexWsReconnectPolicy policy = GtexWsReconnectPolicy();

      expect(policy.delayForAttempt(1), const Duration(seconds: 1));
      expect(policy.delayForAttempt(2), const Duration(seconds: 2));
      expect(policy.delayForAttempt(3), const Duration(seconds: 4));
      expect(policy.delayForAttempt(4), const Duration(seconds: 8));
      expect(policy.delayForAttempt(6), const Duration(seconds: 30));
    });

    test('emits GtexReconnecting with attempt and last-known data', () {
      fakeAsync((FakeAsync async) {
        final List<_FakeWebSocketChannel> channels = <_FakeWebSocketChannel>[];
        final GtexWsService<Map<String, Object?>> service =
            GtexWsService<Map<String, Object?>>(
              endpoint: Uri.parse('ws://api.gtex.test/realtime/stream'),
              reconnectPolicy: const GtexWsReconnectPolicy(),
              channelFactory: (Uri _) {
                final _FakeWebSocketChannel channel = _FakeWebSocketChannel();
                channels.add(channel);
                return channel;
              },
              decoder: (Map<String, Object?> envelope) {
                final Object? data = envelope['data'] ?? envelope['payload'];
                if (data is Map) {
                  return <String, Object?>{
                    for (final MapEntry<dynamic, dynamic> entry in data.entries)
                      entry.key.toString(): entry.value,
                  };
                }
                return null;
              },
            );
        final List<GtexSurfaceState<Map<String, Object?>>> states =
            <GtexSurfaceState<Map<String, Object?>>>[];
        final StreamSubscription<GtexSurfaceState<Map<String, Object?>>>
        subscription = service.surfaceStates.listen(states.add);

        service.connect();
        channels.single.completeReady();
        async.flushMicrotasks();
        channels.single.emit(
          jsonEncode(<String, Object?>{
            'type': 'market.player.updated',
            'topic': 'market.player.player-1',
            'data': <String, Object?>{'id': 'player-1', 'value': 42},
          }),
        );
        async.flushMicrotasks();

        expect(states.whereType<GtexData<Map<String, Object?>>>().last.data, {
          'id': 'player-1',
          'value': 42,
        });

        channels.single.closeFromServer();
        async.flushMicrotasks();

        final GtexReconnecting<Map<String, Object?>> reconnecting =
            states.whereType<GtexReconnecting<Map<String, Object?>>>().last;
        expect(reconnecting.attempt, 1);
        expect(reconnecting.lastKnown, <String, Object?>{
          'id': 'player-1',
          'value': 42,
        });
        expect(channels, hasLength(1));

        async.elapse(const Duration(milliseconds: 999));
        expect(channels, hasLength(1));
        async.elapse(const Duration(milliseconds: 1));
        expect(channels, hasLength(2));

        subscription.cancel();
        service.dispose();
        async.flushMicrotasks();
      });
    });
  });

  group('AuditLogger', () {
    test(
      'serializes actor/entity/before-after contract and returns audit ref',
      () async {
        final Dio dio = Dio(BaseOptions(baseUrl: 'https://api.gtex.test'));
        final _QueuedDioAdapter adapter = _QueuedDioAdapter(<_DioReply>[
          (_) => _jsonResponse(201, <String, Object?>{'audit_ref': 'aud-1'}),
        ]);
        dio.httpClientAdapter = adapter;
        final List<AuditEvent> localEvents = <AuditEvent>[];
        final AuditLogger logger = AuditLogger(
          dio: dio,
          localSink: localEvents.add,
        );
        final GtexAuditEvent event = GtexAuditEvent.majorAction(
          type: 'market.bid.submitted',
          actorId: 'user-1',
          entityType: 'market_bid',
          entityId: 'bid-1',
          timestamp: DateTime.utc(2026, 6, 2, 12),
          before: const <String, Object?>{'status': 'draft'},
          after: const <String, Object?>{'status': 'submitted'},
          metadata: const <String, Object?>{'source': 'contract_test'},
          idempotencyKey: 'idem-1',
        );

        final AuditLogResult result = await logger.log(event);

        expect(result.confirmed, isTrue);
        expect(result.auditRef, 'aud-1');
        expect(localEvents.single, same(event));
        expect(adapter.requests.single.path, '/audit/events');
        expect(jsonDecode(adapter.bodies.single), <String, Object?>{
          'type': 'market.bid.submitted',
          'actor_id': 'user-1',
          'entity_type': 'market_bid',
          'entity_id': 'bid-1',
          'timestamp': '2026-06-02T12:00:00.000Z',
          'before': <String, Object?>{'status': 'draft'},
          'after': <String, Object?>{'status': 'submitted'},
          'metadata': <String, Object?>{'source': 'contract_test'},
          'idempotency_key': 'idem-1',
        });
      },
    );
  });
}

typedef _DioReply = ResponseBody Function(RequestOptions options);

class _QueuedDioAdapter implements HttpClientAdapter {
  _QueuedDioAdapter(this._replies);

  final List<_DioReply> _replies;
  final List<RequestOptions> requests = <RequestOptions>[];
  final List<String> bodies = <String>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    bodies.add(await _bodyFrom(requestStream));
    if (_replies.isEmpty) {
      throw StateError('No queued Dio response for ${options.uri}.');
    }
    return _replies.removeAt(0)(options);
  }

  @override
  void close({bool force = false}) {}
}

Future<String> _bodyFrom(Stream<Uint8List>? requestStream) async {
  if (requestStream == null) {
    return '';
  }
  final BytesBuilder builder = BytesBuilder();
  await for (final Uint8List chunk in requestStream) {
    builder.add(chunk);
  }
  return utf8.decode(builder.takeBytes());
}

ResponseBody _jsonResponse(
  int statusCode,
  Object? body, {
  Map<String, List<String>> headers = const <String, List<String>>{},
}) {
  return ResponseBody.fromString(
    jsonEncode(body),
    statusCode,
    headers: <String, List<String>>{
      Headers.contentTypeHeader: <String>['application/json'],
      ...headers,
    },
  );
}

class _FakeWebSocketChannel implements WebSocketChannel {
  _FakeWebSocketChannel()
    : _streamController = StreamController<dynamic>.broadcast(sync: true),
      sink = _FakeWebSocketSink();

  final StreamController<dynamic> _streamController;
  final Completer<void> _ready = Completer<void>();

  @override
  final _FakeWebSocketSink sink;

  @override
  Stream<dynamic> get stream => _streamController.stream;

  @override
  Future<void> get ready => _ready.future;

  @override
  String? get protocol => null;

  @override
  int? get closeCode => sink.closeCode;

  @override
  String? get closeReason => sink.closeReason;

  void completeReady() {
    if (!_ready.isCompleted) {
      _ready.complete();
    }
  }

  void emit(Object? message) {
    _streamController.add(message);
  }

  void closeFromServer() {
    unawaited(_streamController.close());
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeWebSocketSink implements WebSocketSink {
  final List<Object?> added = <Object?>[];

  int? closeCode;
  String? closeReason;

  @override
  Future<void> get done => Future<void>.value();

  @override
  void add(Object? event) {
    added.add(event);
  }

  @override
  void addError(Object error, [StackTrace? stackTrace]) {}

  @override
  Future<void> addStream(Stream<dynamic> stream) async {
    await for (final Object? event in stream) {
      add(event);
    }
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {
    this.closeCode = closeCode;
    this.closeReason = closeReason;
  }
}
