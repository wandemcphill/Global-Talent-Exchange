import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/services/reliability/reliable_event_queue.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('queue assigns UUIDs and suppresses duplicate dedupe keys', () async {
    final ReliableEventQueue queue = ReliableEventQueue();
    addTearDown(() async {
      await queue.dispose();
    });

    final ReliableQueuedEvent? first = await queue.enqueue(
      topic: 'social',
      name: 'profile_follow_toggled',
      dedupeKey: 'club:royal-lagos:true',
      feedRefreshTrigger: FeedRefreshTrigger.followAction,
      requiresDelivery: false,
    );
    final ReliableQueuedEvent? duplicate = await queue.enqueue(
      topic: 'social',
      name: 'profile_follow_toggled',
      dedupeKey: 'club:royal-lagos:true',
      feedRefreshTrigger: FeedRefreshTrigger.followAction,
      requiresDelivery: false,
    );

    expect(
      first?.id,
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
    expect(duplicate, isNull);
    expect(queue.hasPendingEvents, isFalse);
  });

  test('queue persists failed sends and flushes on reconnect', () async {
    final SharedPreferences preferences = await SharedPreferences.getInstance();
    DateTime clock = DateTime.utc(2026, 3, 28, 12);
    bool shouldFail = true;
    final List<String> deliveredIds = <String>[];

    final ReliableEventQueue firstQueue = ReliableEventQueue(
      sharedPreferencesLoader: () async => preferences,
      now: () => clock,
      sender: (ReliableQueuedEvent event) async {
        if (shouldFail) {
          throw StateError('offline');
        }
        deliveredIds.add(event.id);
      },
    );

    final ReliableQueuedEvent? queuedEvent = await firstQueue.enqueue(
      topic: 'interaction',
      name: 'major_interaction',
      payload: <String, Object?>{'action': 'place_order'},
      dedupeKey: 'order:evt-1',
    );
    await firstQueue.flush();

    expect(queuedEvent, isNotNull);
    expect(firstQueue.pendingEvents, hasLength(1));
    expect(firstQueue.pendingEvents.single.attemptCount, 1);

    await firstQueue.dispose();

    shouldFail = false;
    clock = clock.add(const Duration(seconds: 2));

    final ReliableEventQueue secondQueue = ReliableEventQueue(
      sharedPreferencesLoader: () async => preferences,
      now: () => clock,
      sender: (ReliableQueuedEvent event) async {
        deliveredIds.add(event.id);
      },
    );
    addTearDown(() async {
      await secondQueue.dispose();
    });

    await secondQueue.flush();

    expect(deliveredIds, <String>[queuedEvent!.id]);
    expect(secondQueue.pendingEvents, isEmpty);
  });
}
