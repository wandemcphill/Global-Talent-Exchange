import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/realtime/realtime.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  test('streams merged backend snapshots and grouped commentary', () async {
    late _FakeWebSocketChannel channel;
    final BackendLiveMatchRealtimeProvider provider =
        BackendLiveMatchRealtimeProvider(
          socketFactory: (Uri _) {
            channel = _FakeWebSocketChannel();
            return channel;
          },
        );
    final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
    final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
        .watch(
          LiveMatchRealtimeRequest(
            seed: _seedSnapshot(),
            snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
          ),
        )
        .listen(frames.add);

    channel.completeReady();
    await _drain();
    channel.emit(
      jsonEncode(<String, Object?>{
        'type': 'match_update',
        'payload': <String, Object?>{
          'home_score': 1,
          'away_score': 0,
          'minute': 31,
          'status': 'live',
          'phase': 'first_half',
          'timeline_events': <Object?>[
            <String, Object?>{
              'event_type': 'goal',
              'minute': 31,
              'team_name': 'Lagos United',
              'description': 'Backend-confirmed finish.',
            },
          ],
        },
      }),
    );
    await _drain();

    final LiveMatchRealtimeFrame frame = frames.last;
    expect(frame.status, LiveMatchRealtimeStatus.live);
    expect(frame.hasBackendSnapshotTruth, isTrue);
    expect(frame.isUsable, isTrue);
    expect(frame.snapshot.homeScore, 1);
    expect(frame.snapshot.awayScore, 0);
    expect(frame.snapshot.minute, 31);
    expect(frame.snapshot.commentary, hasLength(1));
    expect(frame.commentaryGroups, hasLength(1));
    expect(frame.commentaryGroups.single.minute, 31);
    expect(frame.commentaryGroups.single.hasKeyMoment, isTrue);

    await subscription.cancel();
  });

  test(
    'normalizes nested score snapshots through the live merge contract',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'kind': 'snapshot',
          'payload': <String, Object?>{
            'score': <String, Object?>{'home': 2, 'away': 1},
            'current_minute': 77,
            'status': 'live',
          },
        }),
      );
      await _drain();

      final LiveMatchRealtimeFrame frame = frames.last;
      expect(frame.snapshot.homeScore, 2);
      expect(frame.snapshot.awayScore, 1);
      expect(frame.snapshot.minute, 77);
      expect(frame.hasBackendSnapshotTruth, isTrue);
      expect(frame.isUsable, isTrue);
      expect(frame.snapshot.commentary, isEmpty);

      await subscription.cancel();
    },
  );

  test('streams commentary-only payloads as grouped backend events', () async {
    late _FakeWebSocketChannel channel;
    final BackendLiveMatchRealtimeProvider provider =
        BackendLiveMatchRealtimeProvider(
          socketFactory: (Uri _) {
            channel = _FakeWebSocketChannel();
            return channel;
          },
        );
    final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
    final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
        .watch(
          LiveMatchRealtimeRequest(
            seed: _seedSnapshot(),
            snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
          ),
        )
        .listen(frames.add);

    channel.completeReady();
    await _drain();
    channel.emit(
      jsonEncode(<String, Object?>{
        'type': 'commentary',
        'data': <String, Object?>{
          'event_type': 'incident',
          'minute': 55,
          'team_name': 'Accra City',
          'commentary': 'Backend commentary line.',
        },
      }),
    );
    await _drain();

    final LiveMatchRealtimeFrame frame = frames.last;
    expect(frame.status, LiveMatchRealtimeStatus.live);
    expect(frame.hasBackendSnapshotTruth, isFalse);
    expect(frame.isUsable, isFalse);
    expect(frame.snapshot.homeScore, 0);
    expect(frame.snapshot.awayScore, 0);
    expect(frame.snapshot.minute, 0);
    expect(frame.snapshot.commentary, hasLength(1));
    expect(frame.commentaryGroups.single.minute, 55);
    expect(
      frame.commentaryGroups.single.events.single.detail,
      'Backend commentary line.',
    );

    await subscription.cancel();
  });

  test(
    'commentary becomes usable only after a backend score-clock snapshot',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'commentary',
          'data': <String, Object?>{
            'event_type': 'incident',
            'minute': 12,
            'team_name': 'Accra City',
            'commentary': 'Backend event before snapshot.',
          },
        }),
      );
      await _drain();
      final LiveMatchRealtimeFrame commentaryOnly = frames.last;
      expect(commentaryOnly.hasBackendSnapshotTruth, isFalse);
      expect(commentaryOnly.isUsable, isFalse);
      expect(commentaryOnly.snapshot.minute, 0);
      expect(commentaryOnly.snapshot.commentary, hasLength(1));

      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'match_update',
          'payload': <String, Object?>{
            'home_score': 1,
            'away_score': 1,
            'minute': 33,
            'status': 'live',
          },
        }),
      );
      await _drain();

      final LiveMatchRealtimeFrame usable = frames.last;
      expect(usable.hasBackendSnapshotTruth, isTrue);
      expect(usable.isUsable, isTrue);
      expect(usable.snapshot.homeScore, 1);
      expect(usable.snapshot.awayScore, 1);
      expect(usable.snapshot.minute, 33);
      expect(usable.snapshot.commentary, hasLength(1));

      await subscription.cancel();
    },
  );

  test(
    'backend score-clock authority survives later commentary-only frames',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'match_update',
          'payload': <String, Object?>{
            'home_score': 2,
            'away_score': 1,
            'minute': 64,
            'status': 'live',
          },
        }),
      );
      await _drain();
      expect(frames.last.hasBackendSnapshotTruth, isTrue);
      expect(frames.last.isUsable, isTrue);

      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'commentary',
          'data': <String, Object?>{
            'event_type': 'incident',
            'minute': 65,
            'team_name': 'Lagos United',
            'commentary': 'Backend event after score-clock confirmation.',
          },
        }),
      );
      await _drain();

      final LiveMatchRealtimeFrame commentaryAfterTruth = frames.last;
      expect(commentaryAfterTruth.status, LiveMatchRealtimeStatus.live);
      expect(commentaryAfterTruth.hasBackendSnapshotTruth, isTrue);
      expect(commentaryAfterTruth.isUsable, isTrue);
      expect(commentaryAfterTruth.snapshot.homeScore, 2);
      expect(commentaryAfterTruth.snapshot.awayScore, 1);
      expect(commentaryAfterTruth.snapshot.minute, 64);
      expect(commentaryAfterTruth.snapshot.commentary, hasLength(1));
      expect(commentaryAfterTruth.commentaryGroups.single.minute, 65);

      await subscription.cancel();
    },
  );

  test(
    'missing websocket payload degrades without generating events',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(jsonEncode(<String, Object?>{'type': 'match_update'}));
      await _drain();

      final LiveMatchRealtimeFrame frame = frames.last;
      expect(frame.status, LiveMatchRealtimeStatus.degraded);
      expect(frame.hasBackendSnapshotTruth, isFalse);
      expect(frame.isUsable, isFalse);
      expect(frame.issue?.code, 'missing_websocket_payload');
      expect(frame.snapshot.homeScore, 0);
      expect(frame.snapshot.awayScore, 0);
      expect(frame.snapshot.minute, 0);
      expect(frame.snapshot.commentary, isEmpty);
      expect(frame.commentaryGroups, isEmpty);

      await subscription.cancel();
    },
  );

  test(
    'backend connection state envelopes do not invent match truth',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'connection_status',
          'status': 'syncing',
          'message': 'Backend is reconciling the active match frame.',
        }),
      );
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'connection_status',
          'status': 'confirmed',
        }),
      );
      await _drain();

      expect(
        frames.map((LiveMatchRealtimeFrame frame) => frame.status),
        containsAllInOrder(<LiveMatchRealtimeStatus>[
          LiveMatchRealtimeStatus.syncing,
          LiveMatchRealtimeStatus.confirmed,
        ]),
      );
      expect(frames.last.snapshot.homeScore, 0);
      expect(frames.last.snapshot.awayScore, 0);
      expect(frames.last.snapshot.minute, 0);
      expect(frames.last.snapshot.commentary, isEmpty);
      expect(frames.last.hasBackendSnapshotTruth, isFalse);
      expect(frames.last.isUsable, isFalse);
      expect(
        frames
            .lastWhere(
              (LiveMatchRealtimeFrame frame) =>
                  frame.status == LiveMatchRealtimeStatus.syncing &&
                  frame.issue?.code == 'websocket_syncing',
            )
            .issue
            ?.message,
        'Backend is reconciling the active match frame.',
      );

      await subscription.cancel();
    },
  );

  test(
    'blocked websocket envelopes expose blocked state without events',
    () async {
      late _FakeWebSocketChannel channel;
      final BackendLiveMatchRealtimeProvider provider =
          BackendLiveMatchRealtimeProvider(
            socketFactory: (Uri _) {
              channel = _FakeWebSocketChannel();
              return channel;
            },
          );
      final List<LiveMatchRealtimeFrame> frames = <LiveMatchRealtimeFrame>[];
      final StreamSubscription<LiveMatchRealtimeFrame> subscription = provider
          .watch(
            LiveMatchRealtimeRequest(
              seed: _seedSnapshot(),
              snapshotWebSocketUri: Uri.parse('ws://example.test/match/live'),
            ),
          )
          .listen(frames.add);

      channel.completeReady();
      await _drain();
      channel.emit(
        jsonEncode(<String, Object?>{
          'type': 'blocked',
          'reason': 'operator gate closed',
        }),
      );
      await _drain();

      final LiveMatchRealtimeFrame frame = frames.last;
      expect(frame.status, LiveMatchRealtimeStatus.blocked);
      expect(frame.hasBackendSnapshotTruth, isFalse);
      expect(frame.isUsable, isFalse);
      expect(frame.issue?.code, 'websocket_blocked');
      expect(frame.snapshot.commentary, isEmpty);

      await subscription.cancel();
    },
  );

  test('commentary without backend clock degrades without fake minute', () {
    final LiveMatchRealtimePayloadResult result =
        LiveMatchRealtimePayloadMapper.decode(<String, Object?>{
          'type': 'commentary',
          'data': <String, Object?>{
            'event_type': 'incident',
            'commentary': 'No clock supplied.',
          },
        }, source: LiveMatchRealtimeSource.commentaryWebSocket);

    expect(result.payload, isNull);
    expect(result.status, LiveMatchRealtimeStatus.degraded);
    expect(result.issue?.code, 'missing_event_minute');
  });

  test('status-only payloads expose canonical live match statuses', () {
    for (final MapEntry<String, LiveMatchRealtimeStatus> entry
        in const <String, LiveMatchRealtimeStatus>{
          'syncing': LiveMatchRealtimeStatus.syncing,
          'reconnecting': LiveMatchRealtimeStatus.reconnecting,
          'confirmed': LiveMatchRealtimeStatus.confirmed,
          'error': LiveMatchRealtimeStatus.error,
        }.entries) {
      final LiveMatchRealtimePayloadResult result =
          LiveMatchRealtimePayloadMapper.decode(<String, Object?>{
            'status': entry.key,
          }, source: LiveMatchRealtimeSource.snapshotWebSocket);

      expect(result.payload, isNull, reason: entry.key);
      expect(result.status, entry.value, reason: entry.key);
    }
  });
}

Future<void> _drain() => Future<void>.delayed(Duration.zero);

LiveMatchSnapshot _seedSnapshot() {
  final DateTime expires = DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
  return LiveMatchSnapshot(
    matchId: 'match-1',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 4,
    awayScore: 3,
    minute: 12,
    phase: LiveMatchPhase.firstHalf,
    momentum: const <int>[],
    commentary: const <LiveMatchEvent>[],
    homeLineup: const <LiveMatchLineupPlayer>[],
    awayLineup: const <LiveMatchLineupPlayer>[],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expires,
    premiumHighlightExpiresAt: expires,
  );
}

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
