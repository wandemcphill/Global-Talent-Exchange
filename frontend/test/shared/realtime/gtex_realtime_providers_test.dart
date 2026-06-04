import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/realtime/realtime.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('connection provider emits current state then updates', () async {
    final _FakeRealtimeClient fake = _FakeRealtimeClient(
      status: GtexRealtimeStatus.reconnecting,
    );
    final ProviderContainer container = ProviderContainer(
      overrides: [gtexRealtimeClientProvider.overrideWithValue(fake)],
    );
    final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
    final ProviderSubscription<AsyncValue<GtexRealtimeStatus>> subscription =
        container.listen(gtexRealtimeConnectionStatusProvider, (
          AsyncValue<GtexRealtimeStatus>? previous,
          AsyncValue<GtexRealtimeStatus> next,
        ) {
          next.whenData(statuses.add);
        }, fireImmediately: true);

    await _drain();
    fake.emitStatus(GtexRealtimeStatus.live);
    await _drain();

    expect(statuses, <GtexRealtimeStatus>[
      GtexRealtimeStatus.reconnecting,
      GtexRealtimeStatus.live,
    ]);

    subscription.close();
    container.dispose();
    await fake.dispose();
  });

  test(
    'event providers split pulse, notification, and activity events',
    () async {
      final _FakeRealtimeClient fake = _FakeRealtimeClient(
        status: GtexRealtimeStatus.live,
      );
      final ProviderContainer container = ProviderContainer(
        overrides: [gtexRealtimeClientProvider.overrideWithValue(fake)],
      );

      final List<GtexRealtimeEvent> pulses = <GtexRealtimeEvent>[];
      final List<GtexRealtimeEvent> notifications = <GtexRealtimeEvent>[];
      final List<GtexRealtimeEvent> activities = <GtexRealtimeEvent>[];
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      pulseSubscription = container.listen(gtexRealtimeLivePulseProvider, (
        AsyncValue<GtexRealtimeEvent>? previous,
        AsyncValue<GtexRealtimeEvent> next,
      ) {
        next.whenData(pulses.add);
      }, fireImmediately: true);
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      notificationSubscription = container.listen(
        gtexRealtimeNotificationStreamProvider,
        (
          AsyncValue<GtexRealtimeEvent>? previous,
          AsyncValue<GtexRealtimeEvent> next,
        ) {
          next.whenData(notifications.add);
        },
        fireImmediately: true,
      );
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      activitySubscription = container.listen(
        gtexRealtimeActivityStreamProvider,
        (
          AsyncValue<GtexRealtimeEvent>? previous,
          AsyncValue<GtexRealtimeEvent> next,
        ) {
          next.whenData(activities.add);
        },
        fireImmediately: true,
      );

      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'live_pulse',
          topic: 'live_pulse',
          payload: <String, Object?>{'headline': 'Window closing'},
        ),
      );
      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'notification.created',
          topic: 'notifications',
          payload: <String, Object?>{'notificationId': 'ntf-1'},
        ),
      );
      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'activity.created',
          topic: 'activity',
          payload: <String, Object?>{'activityId': 'act-1'},
        ),
      );
      await _drain();

      expect(pulses.single.payload['headline'], 'Window closing');
      expect(notifications.single.payload['notificationId'], 'ntf-1');
      expect(activities.single.payload['activityId'], 'act-1');

      pulseSubscription.close();
      notificationSubscription.close();
      activitySubscription.close();
      container.dispose();
      await fake.dispose();
    },
  );

  test('endpoint builder converts http API URLs to websocket stream URLs', () {
    final Uri? uri = buildGtexRealtimeUri(
      'https://api.gtex.test/v1',
      accessToken: ' token-123 ',
      topics: const <String>['live_pulse', 'notifications'],
    );

    expect(uri, isNotNull);
    expect(uri!.scheme, 'wss');
    expect(uri.host, 'api.gtex.test');
    expect(uri.path, '/realtime/stream');
    expect(uri.queryParameters['topics'], 'live_pulse,notifications');
    expect(uri.queryParameters['token'], 'token-123');
  });
}

Future<void> _drain() async {
  await Future<void>.microtask(() {});
  await Future<void>.delayed(Duration.zero);
}

class _FakeRealtimeClient implements GtexRealtimeClient {
  _FakeRealtimeClient({required GtexRealtimeStatus status}) : _status = status;

  final StreamController<GtexRealtimeStatus> _statusController =
      StreamController<GtexRealtimeStatus>.broadcast(sync: true);
  final StreamController<GtexRealtimeEvent> _eventController =
      StreamController<GtexRealtimeEvent>.broadcast(sync: true);

  GtexRealtimeStatus _status;

  @override
  GtexRealtimeStatus get status => _status;

  @override
  Stream<GtexRealtimeStatus> get statuses => _statusController.stream;

  @override
  Stream<GtexRealtimeEvent> get events => _eventController.stream;

  @override
  void connect([Uri? endpoint]) {}

  @override
  Future<void> disconnect() async {
    emitStatus(GtexRealtimeStatus.disconnected);
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
    await _eventController.close();
  }

  @override
  void send(Object payload) {}

  void emitStatus(GtexRealtimeStatus status) {
    _status = status;
    _statusController.add(status);
  }

  void emitEvent(GtexRealtimeEvent event) {
    _eventController.add(event);
  }
}
