import 'dart:async';
import 'dart:convert';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/realtime/realtime.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'subscribes after ready and enters live after subscription ack',
    () async {
      late _FakeWebSocketChannel channel;
      final GtexRealtimeService service = GtexRealtimeService(
        socketUri: Uri.parse('ws://example.test/realtime/stream'),
        topics: const <String>['notifications', 'activity'],
        channelFactory: (Uri _) {
          channel = _FakeWebSocketChannel();
          return channel;
        },
      );
      final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
      final StreamSubscription<GtexRealtimeStatus> statusSubscription = service
          .statuses
          .listen(statuses.add);

      service.connect();
      channel.completeReady();
      await _drain();

      expect(statuses, <GtexRealtimeStatus>[
        GtexRealtimeStatus.connecting,
        GtexRealtimeStatus.syncing,
      ]);
      expect(channel.sink.added, hasLength(1));
      expect(
        jsonDecode(channel.sink.added.single.toString()),
        <String, Object?>{
          'type': 'subscribe',
          'topics': <Object?>['notifications', 'activity'],
        },
      );

      channel.emit('{"type":"subscription_ack"}');
      await _drain();

      expect(statuses.last, GtexRealtimeStatus.live);

      await statusSubscription.cancel();
      await service.dispose();
    },
  );

  test('invalid websocket messages degrade without emitting events', () async {
    late _FakeWebSocketChannel channel;
    final GtexRealtimeService service = GtexRealtimeService(
      socketUri: Uri.parse('ws://example.test/realtime/stream'),
      channelFactory: (Uri _) {
        channel = _FakeWebSocketChannel();
        return channel;
      },
    );
    final List<GtexRealtimeEvent> events = <GtexRealtimeEvent>[];
    final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
    final StreamSubscription<GtexRealtimeEvent> eventSubscription = service
        .events
        .listen(events.add);
    final StreamSubscription<GtexRealtimeStatus> statusSubscription = service
        .statuses
        .listen(statuses.add);

    service.connect();
    channel.completeReady();
    await _drain();

    channel.emit('not-json');
    await _drain();

    expect(statuses, contains(GtexRealtimeStatus.degraded));
    expect(events, isEmpty);

    await eventSubscription.cancel();
    await statusSubscription.cancel();
    await service.dispose();
  });

  test('uses bounded reconnect backoff before reopening transport', () {
    fakeAsync((FakeAsync async) {
      final List<_FakeWebSocketChannel> channels = <_FakeWebSocketChannel>[];
      final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
      final GtexRealtimeService service = GtexRealtimeService(
        socketUri: Uri.parse('ws://example.test/realtime/stream'),
        channelFactory: (Uri _) {
          final _FakeWebSocketChannel channel = _FakeWebSocketChannel();
          channels.add(channel);
          return channel;
        },
        backoffPolicy: const GtexRealtimeBackoffPolicy(
          initialDelay: Duration(seconds: 1),
          maxDelay: Duration(seconds: 5),
        ),
      );
      final StreamSubscription<GtexRealtimeStatus> statusSubscription = service
          .statuses
          .listen(statuses.add);

      service.connect();
      channels.single.completeReady();
      async.flushMicrotasks();
      expect(statuses, <GtexRealtimeStatus>[
        GtexRealtimeStatus.connecting,
        GtexRealtimeStatus.live,
      ]);

      channels.single.closeFromServer();
      async.flushMicrotasks();
      expect(statuses.last, GtexRealtimeStatus.reconnecting);
      expect(channels, hasLength(1));

      async.elapse(const Duration(milliseconds: 999));
      expect(channels, hasLength(1));

      async.elapse(const Duration(milliseconds: 1));
      expect(channels, hasLength(2));
      channels.last.completeReady();
      async.flushMicrotasks();
      expect(statuses.last, GtexRealtimeStatus.live);

      statusSubscription.cancel();
      service.dispose();
      async.flushMicrotasks();
    });
  });
}

Future<void> _drain() async {
  await Future<void>.microtask(() {});
  await Future<void>.delayed(Duration.zero);
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
