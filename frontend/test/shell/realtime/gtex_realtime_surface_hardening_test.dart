import 'dart:async';
import 'dart:convert';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shell/realtime/realtime.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('realtime provider surface', () {
    test('websocket uri provider canonicalizes base url and auth token', () {
      final ProviderContainer container = ProviderContainer(
        overrides: [
          apiBaseUrlProvider.overrideWithValue('https://api.gtex.test/base'),
          accessTokenProvider.overrideWithValue('token-123'),
        ],
      );
      addTearDown(container.dispose);

      final Uri? uri = container.read(gtexRealtimeUriProvider);

      expect(uri, isNotNull);
      expect(uri!.scheme, 'wss');
      expect(uri.host, 'api.gtex.test');
      expect(uri.path, '/realtime/stream');
      expect(
        uri.queryParameters['topics'],
        'live_pulse,notifications,activity',
      );
      expect(uri.queryParameters['token'], 'token-123');
    });

    test(
      'fixture mode keeps websocket service disabled and status offline',
      () async {
        final ProviderContainer container = ProviderContainer(
          overrides: [
            criticalBackendModeProvider.overrideWithValue(
              GteBackendMode.fixture,
            ),
          ],
        );
        addTearDown(container.dispose);

        expect(container.read(gtexRealtimeServiceProvider), isNull);
        final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
        final ProviderSubscription<AsyncValue<GtexRealtimeStatus>>
        subscription = container.listen(gtexRealtimeConnectionStateProvider, (
          AsyncValue<GtexRealtimeStatus>? previous,
          AsyncValue<GtexRealtimeStatus> next,
        ) {
          next.whenData(statuses.add);
        });
        addTearDown(subscription.close);

        await _drain();

        expect(statuses.single, GtexRealtimeStatus.disconnected);
      },
    );

    test(
      'event providers retain backlog and filter canonical streams',
      () async {
        final _FakeRealtimeClient fake = _FakeRealtimeClient(
          status: GtexRealtimeStatus.live,
          initialEvents: <GtexRealtimeEvent>[
            const GtexRealtimeEvent(
              type: 'match_pulse',
              topic: 'live',
              payload: <String, Object?>{'headline': 'Kickoff window opened'},
            ),
            const GtexRealtimeEvent(
              type: 'notification_created',
              topic: 'notifications',
              payload: <String, Object?>{'title': 'Bid approved'},
            ),
            const GtexRealtimeEvent(
              type: 'audit_log_created',
              topic: 'audit',
              payload: <String, Object?>{'actor': 'ops'},
            ),
          ],
        );
        final ProviderContainer container = ProviderContainer(
          overrides: [gtexRealtimeServiceProvider.overrideWithValue(fake)],
        );
        addTearDown(container.dispose);

        final List<GtexRealtimeEvent> pulseEvents = <GtexRealtimeEvent>[];
        final List<GtexRealtimeEvent> notificationEvents =
            <GtexRealtimeEvent>[];
        final List<GtexRealtimeEvent> activityEvents = <GtexRealtimeEvent>[];
        final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
        pulseSubscription = container.listen(gtexLivePulseProvider, (
          AsyncValue<GtexRealtimeEvent>? previous,
          AsyncValue<GtexRealtimeEvent> next,
        ) {
          next.whenData(pulseEvents.add);
        });
        final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
        notificationSubscription = container
            .listen(gtexNotificationStreamProvider, (
              AsyncValue<GtexRealtimeEvent>? previous,
              AsyncValue<GtexRealtimeEvent> next,
            ) {
              next.whenData(notificationEvents.add);
            });
        final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
        activitySubscription = container
            .listen(gtexActivityEventStreamProvider, (
              AsyncValue<GtexRealtimeEvent>? previous,
              AsyncValue<GtexRealtimeEvent> next,
            ) {
              next.whenData(activityEvents.add);
            });
        addTearDown(pulseSubscription.close);
        addTearDown(notificationSubscription.close);
        addTearDown(activitySubscription.close);

        await _drain();

        expect(pulseEvents.single.payload['headline'], 'Kickoff window opened');
        expect(notificationEvents.single.payload['title'], 'Bid approved');
        expect(activityEvents.single.payload['actor'], 'ops');

        await fake.dispose();
      },
    );
  });

  group('realtime websocket service', () {
    test(
      'parses websocket events, status hints, and heartbeat pings',
      () async {
        late _FakeWebSocketChannel channel;
        final GtexRealtimeService service = GtexRealtimeService(
          socketUri: Uri.parse('ws://example.test/realtime/stream'),
          channelFactory: (Uri _) {
            channel = _FakeWebSocketChannel();
            return channel;
          },
        );
        addTearDown(service.dispose);

        final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
        final List<GtexRealtimeEvent> pulses = <GtexRealtimeEvent>[];
        final StreamSubscription<GtexRealtimeStatus> statusSubscription =
            service.statuses.listen(statuses.add);
        final StreamSubscription<GtexRealtimeEvent> pulseSubscription = service
            .livePulseStream
            .listen(pulses.add);
        addTearDown(statusSubscription.cancel);
        addTearDown(pulseSubscription.cancel);

        service.connect();
        await _drain();

        channel.emitInbound(jsonEncode(<String, Object?>{'type': 'ping'}));
        channel.emitInbound(
          jsonEncode(<String, Object?>{
            'type': 'live_pulse',
            'topic': 'live_pulse',
            'payload': <String, Object?>{
              'headline': 'Settlement pulse',
              'connection_status': 'syncing',
            },
          }),
        );
        channel.emitInbound(
          jsonEncode(<String, Object?>{
            'type': 'sync_completed',
            'topic': 'system',
            'payload': <String, Object?>{},
          }),
        );
        await _drain();

        expect(channel.outbound, isNotEmpty);
        expect(jsonDecode(channel.outbound.single as String)['type'], 'pong');
        expect(pulses.single.payload['headline'], 'Settlement pulse');
        expect(statuses, <GtexRealtimeStatus>[
          GtexRealtimeStatus.connecting,
          GtexRealtimeStatus.live,
          GtexRealtimeStatus.syncing,
          GtexRealtimeStatus.live,
        ]);
      },
    );

    test('reconnects with linear backoff and degrades after retry budget', () {
      fakeAsync((FakeAsync async) {
        final List<_FakeWebSocketChannel> channels = <_FakeWebSocketChannel>[];
        final GtexRealtimeService service = GtexRealtimeService(
          socketUri: Uri.parse('ws://example.test/realtime/stream'),
          reconnectDelay: const Duration(seconds: 1),
          maxReconnectAttempts: 2,
          channelFactory: (Uri _) {
            final bool shouldFailReady = channels.isNotEmpty;
            final _FakeWebSocketChannel channel = _FakeWebSocketChannel(
              readyError:
                  shouldFailReady ? StateError('handshake failed') : null,
            );
            channels.add(channel);
            return channel;
          },
        );
        final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
        final StreamSubscription<GtexRealtimeStatus> subscription = service
            .statuses
            .listen(statuses.add);

        service.connect();
        async.flushMicrotasks();
        expect(channels, hasLength(1));
        expect(service.status, GtexRealtimeStatus.live);

        channels.single.closeFromServer();
        async.flushMicrotasks();
        expect(service.status, GtexRealtimeStatus.reconnecting);
        async.elapse(const Duration(milliseconds: 999));
        expect(channels, hasLength(1));
        async.elapse(const Duration(milliseconds: 1));
        async.flushMicrotasks();
        expect(channels, hasLength(2));
        expect(service.status, GtexRealtimeStatus.error);

        async.elapse(const Duration(seconds: 2));
        async.flushMicrotasks();
        expect(channels, hasLength(3));

        async.elapse(const Duration(seconds: 2));
        async.flushMicrotasks();

        expect(service.status, GtexRealtimeStatus.degraded);
        expect(
          statuses,
          containsAllInOrder(<GtexRealtimeStatus>[
            GtexRealtimeStatus.connecting,
            GtexRealtimeStatus.live,
            GtexRealtimeStatus.reconnecting,
            GtexRealtimeStatus.error,
            GtexRealtimeStatus.reconnecting,
            GtexRealtimeStatus.degraded,
          ]),
        );

        subscription.cancel();
        service.dispose();
        async.flushMicrotasks();
      });
    });
  });
}

Future<void> _drain() async {
  await Future<void>.microtask(() {});
  await Future<void>.delayed(Duration.zero);
  await Future<void>.delayed(Duration.zero);
}

class _FakeRealtimeClient implements GtexRealtimeClient {
  _FakeRealtimeClient({
    required GtexRealtimeStatus status,
    List<GtexRealtimeEvent> initialEvents = const <GtexRealtimeEvent>[],
  }) : _status = status,
       _events = List<GtexRealtimeEvent>.of(initialEvents);

  final StreamController<GtexRealtimeStatus> _statusController =
      StreamController<GtexRealtimeStatus>.broadcast(sync: true);
  final StreamController<GtexRealtimeEvent> _eventController =
      StreamController<GtexRealtimeEvent>.broadcast();
  final List<GtexRealtimeEvent> _events;

  GtexRealtimeStatus _status;

  @override
  GtexRealtimeStatus get status => _status;

  @override
  Stream<GtexRealtimeStatus> get statuses => _statusController.stream;

  @override
  Stream<GtexRealtimeEvent> get events => Stream<GtexRealtimeEvent>.multi((
    MultiStreamController<GtexRealtimeEvent> controller,
  ) {
    for (final GtexRealtimeEvent event in _events) {
      controller.add(event);
    }
    final StreamSubscription<GtexRealtimeEvent> subscription = _eventController
        .stream
        .listen(controller.add, onError: controller.addError);
    controller.onCancel = subscription.cancel;
  });

  @override
  void connect([Uri? endpoint]) {}

  @override
  Future<void> disconnect() async {
    _status = GtexRealtimeStatus.disconnected;
    _statusController.add(_status);
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
    await _eventController.close();
  }

  @override
  void send(Object payload) {}
}

class _FakeWebSocketChannel implements WebSocketChannel {
  _FakeWebSocketChannel({Object? readyError})
    : sink = _FakeWebSocketSink(),
      _readyError = readyError;

  final StreamController<dynamic> _inboundController =
      StreamController<dynamic>.broadcast(sync: true);
  final Object? _readyError;

  @override
  final _FakeWebSocketSink sink;

  @override
  int? get closeCode => null;

  @override
  String? get closeReason => null;

  @override
  String? get protocol => null;

  @override
  Future<void> get ready {
    final Object? readyError = _readyError;
    if (readyError != null) {
      return Future<void>.error(readyError);
    }
    return Future<void>.value();
  }

  @override
  Stream<dynamic> get stream => _inboundController.stream;

  List<Object?> get outbound => sink.outbound;

  void emitInbound(Object? message) {
    _inboundController.add(message);
  }

  void closeFromServer() {
    _inboundController.close();
  }

  void failFromServer(Object error) {
    _inboundController.addError(error);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeWebSocketSink implements WebSocketSink {
  final List<Object?> outbound = <Object?>[];
  final Completer<void> _done = Completer<void>();
  bool _closed = false;

  @override
  Future<void> get done => _done.future;

  @override
  void add(Object? event) {
    if (!_closed) {
      outbound.add(event);
    }
  }

  @override
  void addError(Object error, [StackTrace? stackTrace]) {}

  @override
  Future<void> addStream(Stream stream) async {
    await for (final Object? event in stream) {
      add(event);
    }
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {
    _closed = true;
    if (!_done.isCompleted) {
      _done.complete();
    }
  }
}
