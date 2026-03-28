import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/actions/event_service.dart';

void main() {
  test(
    'event service batches events into a single clip ingestion call',
    () async {
      final _RecordingTransport transport = _RecordingTransport();
      final _MemoryQueueStore store = _MemoryQueueStore();
      final EventService service = EventService(
        transport: transport,
        store: store,
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

      await Future<void>.delayed(const Duration(milliseconds: 80));

      expect(transport.batches, hasLength(1));
      expect(transport.batches.single, hasLength(2));
      expect(
        transport.batches.single
            .map((QueuedEvent event) => event.eventId)
            .toSet(),
        hasLength(2),
      );
      expect(store.queue, isEmpty);
    },
  );

  test('event service retries failed batches and persists the queue', () async {
    final _FailOnceTransport transport = _FailOnceTransport();
    final _MemoryQueueStore store = _MemoryQueueStore();
    final EventService service = EventService(
      transport: transport,
      store: store,
      batchWindow: const Duration(milliseconds: 20),
      retryBaseDelay: const Duration(milliseconds: 80),
      retryMaxDelay: const Duration(milliseconds: 80),
      deviceResolver: () => 'ios',
      uuidGenerator: _sequentialUuid(),
    );
    addTearDown(service.dispose);

    await service.trackEvent(
      const TrackEventRequest(
        clipId: 'clip-retry',
        eventType: 'complete',
        videoLengthMs: 12000,
        referrer: 'viral_feed',
      ),
    );

    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(transport.attempts, 1);
    expect(store.queue, hasLength(1));
    expect(store.queue.single.retryCount, 1);

    await Future<void>.delayed(const Duration(milliseconds: 120));
    expect(transport.attempts, 2);
    expect(store.queue, isEmpty);
  });
}

class _RecordingTransport implements EventTransport {
  final List<List<QueuedEvent>> batches = <List<QueuedEvent>>[];

  @override
  Future<void> postEvents(List<QueuedEvent> events) async {
    batches.add(List<QueuedEvent>.from(events));
  }
}

class _FailOnceTransport implements EventTransport {
  int attempts = 0;

  @override
  Future<void> postEvents(List<QueuedEvent> events) async {
    attempts += 1;
    if (attempts == 1) {
      throw Exception('network down');
    }
  }
}

class _MemoryQueueStore implements EventQueueStore {
  List<QueuedEvent> queue = const <QueuedEvent>[];
  String? _sessionId;

  @override
  Future<List<QueuedEvent>> readQueue() async {
    return List<QueuedEvent>.from(queue);
  }

  @override
  Future<String?> readSessionId() async => _sessionId;

  @override
  Future<void> writeQueue(List<QueuedEvent> events) async {
    queue = List<QueuedEvent>.from(events);
  }

  @override
  Future<void> writeSessionId(String sessionId) async {
    _sessionId = sessionId;
  }
}

String Function() _sequentialUuid() {
  int counter = 0;
  return () {
    counter += 1;
    return '00000000-0000-4000-8000-${counter.toString().padLeft(12, '0')}';
  };
}
