import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/realtime/realtime.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('connects, emits live status, and parses live pulse events', () async {
    late _FakeWebSocketChannel channel;
    final GtexRealtimeService service = GtexRealtimeService(
      socketUri: Uri.parse('ws://example.test/realtime/stream'),
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

    final Future<GtexRealtimeEvent> eventFuture = service.events.first;
    channel.emit(
      '{"type":"live_pulse","topic":"live_pulse","data":{"headline":"Window closing"}}',
    );
    final GtexRealtimeEvent event = await eventFuture;

    expect(statuses, <GtexRealtimeStatus>[
      GtexRealtimeStatus.connecting,
      GtexRealtimeStatus.live,
    ]);
    expect(event.type, 'live_pulse');
    expect(event.topic, 'live_pulse');
    expect(event.payload['headline'], 'Window closing');
    expect(event.isLivePulse, isTrue);

    await statusSubscription.cancel();
    await service.dispose();
  });

  test('responds to ping frames with pong', () async {
    late _FakeWebSocketChannel channel;
    final GtexRealtimeService service = GtexRealtimeService(
      socketUri: Uri.parse('ws://example.test/realtime/stream'),
      channelFactory: (Uri _) {
        channel = _FakeWebSocketChannel();
        return channel;
      },
    )..connect();
    channel.completeReady();
    await _drain();

    channel.emit('{"type":"ping"}');
    await _drain();

    expect(channel.sink.added, hasLength(1));
    final Object? decoded = jsonDecode(channel.sink.added.single.toString());
    expect(decoded, isA<Map<String, dynamic>>());
    expect((decoded as Map<String, dynamic>)['type'], 'pong');

    await service.dispose();
  });
}

Future<void> _drain() => Future<void>.delayed(Duration.zero);

class _FakeWebSocketChannel implements WebSocketChannel {
  _FakeWebSocketChannel()
    : _streamController = StreamController<dynamic>.broadcast(),
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
