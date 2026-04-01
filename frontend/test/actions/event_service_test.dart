import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/actions/event_service.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'event service posts immediately with persisted identity context',
    () async {
      final _RecordingTransport transport = _RecordingTransport();
      final _MemoryQueueStore store = _MemoryQueueStore();
      final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
      final MemoryDeviceIdentityStore deviceIdentityStore =
          MemoryDeviceIdentityStore();
      await authSessionStore.writeSession(
        const AuthSession(
          userId: 'user-1',
          accessToken: 'token-1',
          refreshToken: 'refresh-1',
          sessionId: 'session-1',
        ),
      );
      await deviceIdentityStore.writeDeviceId('device-1');
      final EventService service = EventService(
        transport: transport,
        store: store,
        authSessionStore: authSessionStore,
        deviceIdentityStore: deviceIdentityStore,
        batchWindow: const Duration(milliseconds: 20),
        retryBaseDelay: const Duration(milliseconds: 20),
        retryMaxDelay: const Duration(milliseconds: 20),
        deviceResolver: () => 'android',
        uuidGenerator: _sequentialUuid(),
      );
      addTearDown(service.dispose);

      await service.trackEvent(
        const TrackEventRequest(
          clipId: 'clip-1',
          eventType: 'like',
          creatorId: 'creator-1',
          formatKey: 'highlight',
          referrer: 'viral_feed',
        ),
      );
      await service.trackEvent(
        const TrackEventRequest(
          clipId: 'clip-2',
          eventType: 'scroll',
          referrer: 'viral_feed',
        ),
      );

      expect(transport.batches, hasLength(2));
      expect(transport.batches.first, hasLength(1));
      expect(transport.batches.last, hasLength(1));
      expect(transport.authSessions, hasLength(2));
      expect(transport.authSessions.first.userId, 'user-1');
      expect(transport.authSessions.first.sessionId, 'session-1');
      expect(transport.deviceIds, everyElement('device-1'));
      expect(transport.batches.first.single.userId, 'user-1');
      expect(transport.batches.first.single.sessionId, 'session-1');
      expect(transport.batches.first.single.metadata.creatorId, 'creator-1');
      expect(transport.batches.first.single.metadata.formatKey, 'highlight');
      expect(store.queue, isEmpty);
    },
  );

  test('event service retries failed batches and persists the queue', () async {
    final _FailOnceTransport transport = _FailOnceTransport();
    final _MemoryQueueStore store = _MemoryQueueStore();
    final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
    final MemoryDeviceIdentityStore deviceIdentityStore =
        MemoryDeviceIdentityStore();
    await authSessionStore.writeSession(
      const AuthSession(
        userId: 'user-retry',
        accessToken: 'token-retry',
        refreshToken: 'refresh-retry',
        sessionId: 'session-retry',
      ),
    );
    await deviceIdentityStore.writeDeviceId('device-retry');
    final EventService service = EventService(
      transport: transport,
      store: store,
      authSessionStore: authSessionStore,
      deviceIdentityStore: deviceIdentityStore,
      batchWindow: const Duration(milliseconds: 20),
      retryBaseDelay: const Duration(milliseconds: 80),
      retryMaxDelay: const Duration(milliseconds: 80),
      deviceResolver: () => 'ios',
      uuidGenerator: _sequentialUuid(),
    );
    addTearDown(service.dispose);

    await service
        .trackEvent(
          const TrackEventRequest(
            clipId: 'clip-retry',
            eventType: 'complete',
            creatorId: 'creator-retry',
            videoLengthMs: 12000,
            referrer: 'viral_feed',
          ),
        )
        .catchError((Object _) {});

    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(transport.attempts, 1);
    expect(store.queue, hasLength(1));
    expect(store.queue.single.retryCount, 1);
    expect(store.queue.single.userId, 'user-retry');
    expect(store.queue.single.sessionId, 'session-retry');

    await Future<void>.delayed(const Duration(milliseconds: 120));
    expect(transport.attempts, 2);
    expect(store.queue, isEmpty);
  });

  test('event service drops stale queued events after logout', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final _MemoryQueueStore store = _MemoryQueueStore(
      queue: <QueuedEvent>[
        QueuedEvent(
          eventId: 'queued-stale',
          clipId: 'clip-stale',
          userId: 'user-stale',
          sessionId: 'session-stale',
          timestamp: DateTime.utc(2026, 3, 28, 12),
          eventType: 'scroll',
          metadata: const EventMetadata(
            device: 'ios',
            country: 'NG',
            referrer: 'viral_feed',
          ),
        ),
      ],
    );
    final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
    final MemoryDeviceIdentityStore deviceIdentityStore =
        MemoryDeviceIdentityStore();
    await authSessionStore.writeSession(
      const AuthSession(
        userId: 'user-stale',
        accessToken: 'token-stale',
        refreshToken: 'refresh-stale',
        sessionId: 'session-stale',
      ),
    );
    await deviceIdentityStore.writeDeviceId('device-stale');
    final EventService service = EventService(
      transport: transport,
      store: store,
      authSessionStore: authSessionStore,
      deviceIdentityStore: deviceIdentityStore,
      batchWindow: const Duration(milliseconds: 20),
      retryBaseDelay: const Duration(milliseconds: 20),
      retryMaxDelay: const Duration(milliseconds: 20),
      uuidGenerator: _sequentialUuid(),
    );
    addTearDown(service.dispose);

    await authSessionStore.writeSession(null);

    await service.flush();

    expect(store.queue, isEmpty);
    expect(transport.batches, isEmpty);
  });
}

class _RecordingTransport implements EventTransport {
  final List<List<QueuedEvent>> batches = <List<QueuedEvent>>[];
  final List<AuthSession> authSessions = <AuthSession>[];
  final List<String> deviceIds = <String>[];

  @override
  Future<void> postEvents(
    List<QueuedEvent> events, {
    required AuthSession authSession,
    required String deviceId,
  }) async {
    batches.add(List<QueuedEvent>.from(events));
    authSessions.add(authSession);
    deviceIds.add(deviceId);
  }
}

class _FailOnceTransport implements EventTransport {
  int attempts = 0;

  @override
  Future<void> postEvents(
    List<QueuedEvent> events, {
    required AuthSession authSession,
    required String deviceId,
  }) async {
    attempts += 1;
    if (attempts == 1) {
      throw Exception('network down');
    }
  }
}

class _MemoryQueueStore implements EventQueueStore {
  _MemoryQueueStore({this.queue = const <QueuedEvent>[]});

  List<QueuedEvent> queue;

  @override
  Future<List<QueuedEvent>> readQueue() async {
    return List<QueuedEvent>.from(queue);
  }

  @override
  Future<void> writeQueue(List<QueuedEvent> events) async {
    queue = List<QueuedEvent>.from(events);
  }
}

String Function() _sequentialUuid() {
  int counter = 0;
  return () {
    counter += 1;
    return '00000000-0000-4000-8000-${counter.toString().padLeft(12, '0')}';
  };
}
