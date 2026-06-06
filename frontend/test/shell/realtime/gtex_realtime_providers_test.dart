import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/providers/gtex_realtime_providers.dart'
    as provider_compat;
import 'package:gte_frontend/features/shell/realtime/realtime.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('provider compatibility path re-exports canonical providers', () {
    expect(
      provider_compat.gtexRealtimeServiceProvider,
      same(gtexRealtimeServiceProvider),
    );
    expect(
      provider_compat.gtexRealtimeStatusProvider,
      same(gtexRealtimeStatusProvider),
    );
    expect(provider_compat.gtexLivePulseProvider, same(gtexLivePulseProvider));
    expect(
      provider_compat.gtexNotificationStreamProvider,
      same(gtexNotificationStreamProvider),
    );
    expect(
      provider_compat.gtexActivityEventStreamProvider,
      same(gtexActivityEventStreamProvider),
    );
  });

  test('connection provider emits current status and updates', () async {
    final _FakeRealtimeClient fake = _FakeRealtimeClient(
      status: GtexRealtimeStatus.reconnecting,
    );
    final ProviderContainer container = ProviderContainer(
      overrides: [gtexRealtimeServiceProvider.overrideWithValue(fake)],
    );
    addTearDown(container.dispose);
    final List<GtexRealtimeStatus> statuses = <GtexRealtimeStatus>[];
    final ProviderSubscription<AsyncValue<GtexRealtimeStatus>> subscription =
        container.listen(gtexRealtimeConnectionStateProvider, (
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
    await fake.dispose();
  });

  test(
    'event providers filter pulse, notification, and activity streams',
    () async {
      final _FakeRealtimeClient fake = _FakeRealtimeClient(
        status: GtexRealtimeStatus.live,
      );
      final ProviderContainer container = ProviderContainer(
        overrides: [gtexRealtimeServiceProvider.overrideWithValue(fake)],
      );
      addTearDown(container.dispose);

      final List<GtexRealtimeEvent> pulseEvents = <GtexRealtimeEvent>[];
      final List<GtexRealtimeEvent> notificationEvents = <GtexRealtimeEvent>[];
      final List<GtexRealtimeEvent> activityEvents = <GtexRealtimeEvent>[];
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      pulseSubscription = container.listen(gtexLivePulseProvider, (
        AsyncValue<GtexRealtimeEvent>? previous,
        AsyncValue<GtexRealtimeEvent> next,
      ) {
        next.whenData(pulseEvents.add);
      }, fireImmediately: true);
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      notificationSubscription = container.listen(
        gtexNotificationStreamProvider,
        (
          AsyncValue<GtexRealtimeEvent>? previous,
          AsyncValue<GtexRealtimeEvent> next,
        ) {
          next.whenData(notificationEvents.add);
        },
        fireImmediately: true,
      );
      final ProviderSubscription<AsyncValue<GtexRealtimeEvent>>
      activitySubscription = container.listen(gtexActivityEventStreamProvider, (
        AsyncValue<GtexRealtimeEvent>? previous,
        AsyncValue<GtexRealtimeEvent> next,
      ) {
        next.whenData(activityEvents.add);
      }, fireImmediately: true);
      await _drain();

      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'live_pulse',
          topic: 'live_pulse',
          payload: <String, Object?>{'headline': 'Market open'},
        ),
      );
      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'notification_created',
          topic: 'notifications',
          payload: <String, Object?>{'title': 'Proof reviewed'},
        ),
      );
      fake.emitEvent(
        const GtexRealtimeEvent(
          type: 'activity_event',
          topic: 'activity',
          payload: <String, Object?>{'actor': 'admin'},
        ),
      );
      await _drain();

      expect(pulseEvents.single.payload['headline'], 'Market open');
      expect(notificationEvents.single.payload['title'], 'Proof reviewed');
      expect(activityEvents.single.payload['actor'], 'admin');

      pulseSubscription.close();
      notificationSubscription.close();
      activitySubscription.close();
      await fake.dispose();
    },
  );
}

Future<void> _drain() async {
  await Future<void>.microtask(() {});
  await Future<void>.microtask(() {});
  await Future<void>.microtask(() {});
  await Future<void>.delayed(Duration.zero);
  await Future<void>.delayed(Duration.zero);
}

class _FakeRealtimeClient implements GtexRealtimeClient {
  _FakeRealtimeClient({required GtexRealtimeStatus status}) : _status = status;

  final StreamController<GtexRealtimeStatus> _statusController =
      StreamController<GtexRealtimeStatus>.broadcast();
  final StreamController<GtexRealtimeEvent> _eventController =
      StreamController<GtexRealtimeEvent>.broadcast();
  final List<GtexRealtimeEvent> _events = <GtexRealtimeEvent>[];

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

  void emitStatus(GtexRealtimeStatus status) {
    _status = status;
    _statusController.add(status);
  }

  void emitEvent(GtexRealtimeEvent event) {
    _events.add(event);
    scheduleMicrotask(() {
      if (!_eventController.isClosed) {
        _eventController.add(event);
      }
    });
  }
}
