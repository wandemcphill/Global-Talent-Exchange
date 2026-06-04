import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/notifications/notifications.dart';

void main() {
  test('store reduces snapshot, upsert, grouping, and read events', () {
    final NotificationLogStore store = NotificationLogStore();
    addTearDown(store.dispose);

    expect(
      store.applyBackendPayload(
        jsonEncode(<String, Object?>{
          'type': 'notifications_snapshot',
          'topic': 'notifications',
          'payload': <String, Object?>{
            'notifications': <Object?>[
              _backendNotification(
                id: 'notif-match-older',
                topic: 'match',
                templateKey: 'MATCH_STARTS_10M',
                message: 'Lagos Royals kickoff is ten minutes away.',
                createdAt: '2026-05-29T11:50:00Z',
                groupKey: 'match:fixture-771',
                groupLabel: 'Live Match Ops',
              ),
              _backendNotification(
                id: 'notif-wallet',
                topic: 'wallet',
                templateKey: 'DEPOSIT_CONFIRMED',
                message: 'Manual deposit proof was confirmed.',
                createdAt: '2026-05-29T11:55:00Z',
                groupKey: 'wallet:funding',
                groupLabel: 'Wallet Funding',
              ),
            ],
          },
        }),
      ),
      isTrue,
    );

    expect(store.state.notifications.first.notificationId, 'notif-wallet');
    expect(store.unreadCount, 2);
    expect(store.groups, hasLength(2));
    expect(store.groups.first.label, 'Wallet Funding');

    store.applyBackendPayload(<String, Object?>{
      'type': 'notification_created',
      'topic': 'notifications',
      'payload': _backendNotification(
        id: 'notif-match-live',
        topic: 'match',
        templateKey: 'LIVE_MATCH_STARTED',
        message: 'Lagos Royals v Accra Lions is live.',
        createdAt: '2026-05-29T12:00:00Z',
        groupKey: 'match:fixture-771',
        groupLabel: 'Live Match Ops',
      ),
    });

    expect(store.state.notifications.first.notificationId, 'notif-match-live');
    expect(
      store.groups
          .singleWhere(
            (NotificationLogGroup group) =>
                group.groupKey == 'match:fixture-771',
          )
          .unreadCount,
      2,
    );

    store.applyBackendPayload(<String, Object?>{
      'type': 'notification_read',
      'payload': <String, Object?>{
        'notification_id': 'notif-match-live',
        'read_at': '2026-05-29T12:03:00Z',
      },
    });

    final NotificationLogItem readItem = store.state.notifications.singleWhere(
      (NotificationLogItem item) => item.notificationId == 'notif-match-live',
    );
    expect(readItem.isRead, isTrue);
    expect(store.unreadCount, 2);
  });

  test(
    'store consumes backend websocket stream and preserves persisted log',
    () async {
      final StreamController<Object?> controller = StreamController<Object?>();
      final NotificationLogStore store = NotificationLogStore();
      addTearDown(() async {
        await controller.close();
        store.dispose();
      });

      store.bindBackendStream(controller.stream);
      expect(
        store.state.connectionState,
        NotificationLogConnectionState.connecting,
      );

      controller.add(<String, Object?>{
        'type': 'notification_created',
        'topic': 'notifications',
        'payload': _backendNotification(
          id: 'notif-stream-1',
          topic: 'match',
          templateKey: 'HIGHLIGHTS_READY',
          message: 'Highlights are ready for match-771.',
          createdAt: '2026-05-29T12:20:00Z',
          groupKey: 'match:fixture-771',
          groupLabel: 'Live Match Ops',
        ),
      });
      await _drain();

      expect(store.state.notifications.single.notificationId, 'notif-stream-1');

      controller.addError(StateError('notification websocket closed'));
      await _drain();

      expect(
        store.state.connectionState,
        NotificationLogConnectionState.degraded,
      );
      expect(store.state.degradedReason, contains('websocket closed'));
      expect(store.state.notifications.single.notificationId, 'notif-stream-1');
    },
  );
}

Map<String, Object?> _backendNotification({
  required String id,
  required String topic,
  required String templateKey,
  required String message,
  required String createdAt,
  required String groupKey,
  required String groupLabel,
}) {
  return <String, Object?>{
    'notification_id': id,
    'user_id': 'user-1',
    'topic': topic,
    'template_key': templateKey,
    'resource_id': topic == 'wallet' ? 'deposit-99' : 'match-771',
    'fixture_id': topic == 'match' ? 'fixture-771' : null,
    'competition_id': topic == 'match' ? 'competition-9' : null,
    'message': message,
    'metadata': <String, Object?>{
      'group_key': groupKey,
      'group_label': groupLabel,
    },
    'created_at': createdAt,
    'read_at': null,
    'is_read': false,
  };
}

Future<void> _drain() async {
  await Future<void>.microtask(() {});
  await Future<void>.delayed(Duration.zero);
}
